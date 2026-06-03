from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.ambiguity_classifier_agent import (
    AmbiguityClassifierAgent,
    AmbiguityClassifierOutput,
    should_classify_with_llm,
    spread_rules_pass,
)
from app.agents.triage_types import Evidence
from app.core.config import Settings, get_settings
from app.llm.router import LLMRouter
from app.models.core import AgentRun, AuctionBatch, AuctionRecord, CostEvent, TriageResult
from app.services.llm_cost_service import record_llm_cost_event


class AmbiguityClassificationSummary:
    def __init__(self) -> None:
        self.attempted = 0
        self.skipped = 0
        self.updated = 0
        self.cost_cap_skipped = 0
        self.agent_runs: list[AgentRun] = []
        self.cost_events: list[CostEvent] = []


def classify_ambiguous_records(
    *,
    session: Session,
    batch_id: UUID,
    settings: Settings | None = None,
    router: LLMRouter | None = None,
    force: bool = False,
) -> AmbiguityClassificationSummary:
    active_settings = settings or get_settings()
    active_router = router or LLMRouter(active_settings)
    agent = AmbiguityClassifierAgent(settings=active_settings, router=active_router)
    summary = AmbiguityClassificationSummary()
    rows = session.execute(
        select(AuctionRecord, TriageResult)
        .join(TriageResult, TriageResult.auction_record_id == AuctionRecord.id)
        .where(AuctionRecord.batch_id == batch_id)
        .order_by(AuctionRecord.created_at, TriageResult.created_at)
    ).all()

    calls_made = 0
    for record, triage_result in rows:
        if not should_classify_with_llm(triage_result, force=force):
            summary.skipped += 1
            continue
        if calls_made >= active_settings.llm_max_calls_per_batch:
            _apply_cap_exceeded(triage_result)
            summary.cost_cap_skipped += 1
            summary.updated += 1
            continue

        started_at = datetime.now(UTC)
        classifier_result = agent.classify(record=record, triage_result=triage_result)
        completed_at = datetime.now(UTC)
        response = classifier_result.response
        agent_run = AgentRun(
            batch_id=batch_id,
            auction_record_id=record.id,
            agent_name="ambiguity_classifier",
            status="failed" if classifier_result.error_message else "completed",
            input_json=classifier_result.input_payload.model_dump(mode="json"),
            output_json=(
                classifier_result.output.model_dump(mode="json") if classifier_result.output is not None else None
            ),
            error_message=classifier_result.error_message,
            model_name=response.model_name if response is not None else None,
            input_tokens=response.input_tokens if response is not None else 0,
            output_tokens=response.output_tokens if response is not None else 0,
            estimated_cost_usd=Decimal(str(response.estimated_cost_usd)) if response is not None else Decimal("0"),
            started_at=started_at,
            completed_at=completed_at,
        )
        session.add(agent_run)
        summary.agent_runs.append(agent_run)
        summary.attempted += 1

        if response is not None:
            calls_made += 1
            cost_event = record_llm_cost_event(
                session=session,
                batch_id=batch_id,
                auction_record_id=record.id,
                response=response,
            )
            summary.cost_events.append(cost_event)

        _apply_classifier_output(triage_result, classifier_result.output, classifier_result.invalid_output)
        if response is not None:
            triage_result.llm_calls_used += 1
            triage_result.estimated_cost_usd += Decimal(str(response.estimated_cost_usd))
        summary.updated += 1

    batch = session.get(AuctionBatch, batch_id)
    if batch is not None:
        batch.llm_calls_used = sum(result.llm_calls_used for _, result in rows)
        batch.estimated_cost_usd = sum(
            (result.estimated_cost_usd for _, result in rows),
            Decimal("0"),
        )
    session.commit()
    return summary


def _apply_classifier_output(
    triage_result: TriageResult,
    output: AmbiguityClassifierOutput | None,
    invalid_output: bool,
) -> None:
    if invalid_output or output is None:
        triage_result.tier_1_status = "MANUAL_REVIEW"
        triage_result.grade = "U"
        triage_result.requires_human_review = True
        triage_result.risk_flags = [*triage_result.risk_flags, "LLM_OUTPUT_INVALID"]
        triage_result.evidence = [
            *triage_result.evidence,
            Evidence(
                "llm.invalid_output",
                "classifier_output",
                None,
                "manual_review",
                "LLM classifier output was invalid or unavailable; routed to manual review.",
            ).as_dict(),
        ]
        return

    triage_result.risk_flags = list(dict.fromkeys([*triage_result.risk_flags, *output.risk_flags]))
    triage_result.positive_signals = list(dict.fromkeys([*triage_result.positive_signals, *output.positive_reasons]))
    triage_result.evidence = [
        *triage_result.evidence,
        Evidence(
            "llm.ambiguity_classifier",
            "classification",
            output.model_dump(mode="json"),
            "manual_review" if output.requires_human_review else "neutral",
            "Provider-agnostic ambiguity classifier output; deterministic rules remain authoritative gates.",
        ).as_dict(),
    ]

    if output.classification == "likely_junk" and output.confidence >= 0.85:
        triage_result.tier_1_status = "REJECTED"
        triage_result.grade = "F"
        triage_result.requires_human_review = False
        triage_result.recommended_next_action = (
            "Reject from Tier 1 based on high-confidence ambiguity classifier junk signal."
        )
    elif (
        output.classification == "likely_investable"
        and output.confidence >= 0.75
        and spread_rules_pass(triage_result)
    ):
        triage_result.tier_1_status = "RESEARCH_CANDIDATE"
        triage_result.grade = "B"
        triage_result.requires_human_review = True
        triage_result.recommended_next_action = (
            "Research candidate for qualified human review; classifier output is not bidding or title advice."
        )
    elif output.classification == "ambiguous":
        triage_result.requires_human_review = True
        if triage_result.tier_1_status not in {"WATCHLIST", "MANUAL_REVIEW"}:
            triage_result.tier_1_status = "MANUAL_REVIEW"
        triage_result.recommended_next_action = (
            "Manual review required because ambiguity classifier remained uncertain."
        )


def _apply_cap_exceeded(triage_result: TriageResult) -> None:
    triage_result.tier_1_status = "MANUAL_REVIEW"
    triage_result.grade = "U"
    triage_result.requires_human_review = True
    triage_result.risk_flags = [*triage_result.risk_flags, "LLM_COST_CAP_EXCEEDED"]
    triage_result.evidence = [
        *triage_result.evidence,
        Evidence(
            "llm.cost_cap_exceeded",
            "LLM_MAX_CALLS_PER_BATCH",
            None,
            "manual_review",
            "LLM call cap was reached; remaining ambiguous records route to manual review without model calls.",
        ).as_dict(),
    ]
