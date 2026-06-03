from __future__ import annotations

from collections import Counter
from uuid import UUID

from app.agents.triage_types import Evidence
from app.models.core import AuctionRecord


def duplicate_evidence(records: list[AuctionRecord]) -> dict[UUID, Evidence]:
    parcel_counts = Counter(record.parcel_id_normalized for record in records if record.parcel_id_normalized)
    case_counts = Counter(record.case_number for record in records if record.case_number)
    output: dict[UUID, Evidence] = {}
    for record in records:
        duplicate_fields: list[str] = []
        if record.parcel_id_normalized and parcel_counts[record.parcel_id_normalized] > 1:
            duplicate_fields.append("parcel_id_normalized")
        if record.case_number and case_counts[record.case_number] > 1:
            duplicate_fields.append("case_number")
        if duplicate_fields:
            output[record.id] = Evidence(
                "dedupe.batch_duplicate",
                ",".join(duplicate_fields),
                {"case_number": record.case_number, "parcel_id_normalized": record.parcel_id_normalized},
                "manual_review",
                "Potential duplicate within batch; deterministic triage keeps the record reviewable.",
            )
    return output
