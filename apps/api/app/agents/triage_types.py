from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal

Tier1Status = Literal[
    "REJECTED",
    "WATCHLIST",
    "RESEARCH_CANDIDATE",
    "MANUAL_REVIEW",
    "QUARANTINED",
    "CANCELED_OR_INACTIVE",
]
Grade = Literal["A", "B", "C", "D", "F", "U"]
DecisionImpact = Literal["positive", "negative", "neutral", "quarantine", "manual_review", "inactive", "reject"]


@dataclass(frozen=True)
class Evidence:
    rule_name: str
    field_inspected: str
    value: Any
    decision_impact: DecisionImpact
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "field_inspected": self.field_inspected,
            "value": self.value,
            "decision_impact": self.decision_impact,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class DataQualityResult:
    score: Decimal
    missing_fields: tuple[str, ...]
    risk_flags: tuple[str, ...]
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True)
class SpreadScore:
    estimated_spread_cents: int | None
    opening_bid_ratio: Decimal | None
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True)
class JunkSignal:
    hard_reject: bool
    ambiguous: bool
    risk_flags: tuple[str, ...]
    matched_terms: tuple[str, ...]
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True)
class TriageDecision:
    tier_1_status: Tier1Status
    grade: Grade
    estimated_spread_cents: int | None
    opening_bid_ratio: Decimal | None
    data_quality_score: Decimal
    risk_flags: tuple[str, ...]
    positive_signals: tuple[str, ...]
    evidence: tuple[Evidence, ...]
    recommended_next_action: str
    requires_human_review: bool
    llm_calls_used: int = 0
    estimated_cost_usd: Decimal = Decimal("0")

    def evidence_json(self) -> list[dict[str, Any]]:
        return [item.as_dict() for item in self.evidence]


@dataclass
class RuleContext:
    risk_flags: list[str] = field(default_factory=list)
    positive_signals: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
