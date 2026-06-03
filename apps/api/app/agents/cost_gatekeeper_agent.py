from __future__ import annotations

from decimal import Decimal

from app.agents.triage_types import Evidence


def deterministic_no_llm_evidence() -> Evidence:
    return Evidence(
        "cost_gatekeeper.no_llm",
        "llm_calls_used",
        0,
        "neutral",
        "Tier 1 triage is deterministic; no LLM provider is called and estimated model cost is $0.",
    )


def llm_cost_usd() -> Decimal:
    return Decimal("0")
