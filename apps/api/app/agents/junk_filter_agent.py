from __future__ import annotations

import re

from app.agents.triage_types import Evidence, JunkSignal

HARD_JUNK_TERMS = (
    "RETENTION POND",
    "DRAINAGE EASEMENT",
    "UTILITY EASEMENT",
    "RIGHT OF WAY",
    "R/W",
    "LIFT STATION",
    "PUMP STATION",
    "SUBMERGED",
    "WASTE LAND",
    "RAILROAD",
    "CEMETERY",
    "EASEMENT PARCEL",
)

AMBIGUOUS_JUNK_TERMS = (
    "RETENTION",
    "DRAINAGE",
    "STORMWATER",
    "WATER MANAGEMENT",
    "UTILITY",
    "ROAD",
    "ALLEY",
    "CANAL",
    "DITCH",
    "BUFFER",
    "CONSERVATION",
    "WETLAND",
    "PRESERVE",
    "COMMON AREA",
)


def evaluate_junk_signals(property_text: str | None) -> JunkSignal:
    if not property_text or not property_text.strip():
        return JunkSignal(
            False,
            False,
            (),
            (),
            (
                Evidence(
                    "junk.keyword_scan",
                    "property_text",
                    None,
                    "neutral",
                    "No legal description or property text was available for junk keyword screening.",
                ),
            ),
        )

    normalized = _normalize(property_text)
    hard_matches = tuple(term for term in HARD_JUNK_TERMS if _contains_term(normalized, term))
    ambiguous_matches = tuple(
        term for term in AMBIGUOUS_JUNK_TERMS if _contains_term(normalized, term) and term not in hard_matches
    )
    tract_only = _contains_term(normalized, "TRACT") and not hard_matches and not ambiguous_matches
    evidence: list[Evidence] = []
    flags: list[str] = []

    if hard_matches:
        flags.extend(f"hard_junk:{term}" for term in hard_matches)
        evidence.append(
            Evidence(
                "junk.hard_keyword",
                "property_text",
                list(hard_matches),
                "reject",
                "Property text contains hard junk parcel indicator(s) that deterministic triage rejects.",
            )
        )
    if ambiguous_matches:
        flags.extend(f"ambiguous_junk:{term}" for term in ambiguous_matches)
        evidence.append(
            Evidence(
                "junk.ambiguous_keyword",
                "property_text",
                list(ambiguous_matches),
                "manual_review",
                "Property text contains ambiguous risk indicator(s); deterministic triage will not treat this as safe.",
            )
        )
    if tract_only:
        evidence.append(
            Evidence(
                "junk.tract_not_hard_reject",
                "property_text",
                "TRACT",
                "neutral",
                "The word TRACT alone is not treated as a hard junk parcel indicator.",
            )
        )
    if not evidence:
        evidence.append(
            Evidence(
                "junk.keyword_scan",
                "property_text",
                "no_matches",
                "neutral",
                "No configured junk parcel keywords were detected in property text.",
            )
        )

    return JunkSignal(
        bool(hard_matches),
        bool(ambiguous_matches),
        tuple(flags),
        hard_matches + ambiguous_matches,
        tuple(evidence),
    )


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.upper()).strip()


def _contains_term(value: str, term: str) -> bool:
    if term == "R/W":
        return "R/W" in value
    return re.search(rf"(?<![A-Z0-9]){re.escape(term)}(?![A-Z0-9])", value) is not None
