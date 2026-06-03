from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.llm.base import LLMResponse
from app.models.core import CostEvent


def record_llm_cost_event(
    *,
    session: Session,
    batch_id: UUID,
    auction_record_id: UUID,
    response: LLMResponse,
) -> CostEvent:
    token_count = Decimal(response.input_tokens + response.output_tokens)
    estimated_cost = Decimal(str(response.estimated_cost_usd))
    event = CostEvent(
        batch_id=batch_id,
        auction_record_id=auction_record_id,
        service=response.provider,
        event_type="ambiguity_classifier_llm_call",
        unit_count=token_count,
        estimated_cost_usd=estimated_cost,
        metadata_json={
            "model_name": response.model_name,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
        },
    )
    session.add(event)
    return event
