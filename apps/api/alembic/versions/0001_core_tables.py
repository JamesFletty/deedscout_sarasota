"""create core mvp tables

Revision ID: 0001_core_tables
Revises:
Create Date: 2026-06-02 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

JSON_VARIANT = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

revision: str = "0001_core_tables"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "auction_batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("county", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("records_found", sa.Integer(), nullable=False),
        sa.Column("records_valid", sa.Integer(), nullable=False),
        sa.Column("records_quarantined", sa.Integer(), nullable=False),
        sa.Column("records_rejected", sa.Integer(), nullable=False),
        sa.Column("records_watchlist", sa.Integer(), nullable=False),
        sa.Column("records_research_candidates", sa.Integer(), nullable=False),
        sa.Column("records_manual_review", sa.Integer(), nullable=False),
        sa.Column("llm_calls_used", sa.Integer(), nullable=False),
        sa.Column("estimated_cost_usd", sa.Numeric(12, 4), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auction_batches_status", "auction_batches", ["status"])
    op.create_table(
        "auction_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("county", sa.Text(), nullable=False),
        sa.Column("case_number", sa.Text(), nullable=True),
        sa.Column("parcel_id_raw", sa.Text(), nullable=True),
        sa.Column("parcel_id_normalized", sa.Text(), nullable=True),
        sa.Column("auction_date", sa.Date(), nullable=True),
        sa.Column("auction_status", sa.Text(), nullable=True),
        sa.Column("opening_bid_cents", sa.BigInteger(), nullable=True),
        sa.Column("appraiser_assessment_cents", sa.BigInteger(), nullable=True),
        sa.Column("detail_url", sa.Text(), nullable=True),
        sa.Column("notice_url", sa.Text(), nullable=True),
        sa.Column("tax_deed_record_url", sa.Text(), nullable=True),
        sa.Column("parse_confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("missing_fields", JSON_VARIANT, nullable=False),
        sa.Column("parse_warnings", JSON_VARIANT, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["auction_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auction_records_batch_id", "auction_records", ["batch_id"])
    op.create_index("ix_auction_records_parcel_id_normalized", "auction_records", ["parcel_id_normalized"])
    op.create_index("ix_auction_records_auction_status", "auction_records", ["auction_status"])
    op.create_table(
        "source_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("auction_record_id", sa.Uuid(), nullable=True),
        sa.Column("batch_id", sa.Uuid(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("html_path", sa.Text(), nullable=True),
        sa.Column("screenshot_path", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("page_structure_hash", sa.String(length=64), nullable=True),
        sa.Column("parser_version", sa.Text(), nullable=False),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["auction_record_id"], ["auction_records.id"]),
        sa.ForeignKeyConstraint(["batch_id"], ["auction_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_source_snapshots_batch_id", "source_snapshots", ["batch_id"])
    op.create_table(
        "triage_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("auction_record_id", sa.Uuid(), nullable=False),
        sa.Column("tier_1_status", sa.Text(), nullable=False),
        sa.Column("grade", sa.Text(), nullable=False),
        sa.Column("estimated_spread_cents", sa.BigInteger(), nullable=True),
        sa.Column("opening_bid_ratio", sa.Numeric(8, 4), nullable=True),
        sa.Column("data_quality_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("risk_flags", JSON_VARIANT, nullable=False),
        sa.Column("positive_signals", JSON_VARIANT, nullable=False),
        sa.Column("evidence", JSON_VARIANT, nullable=False),
        sa.Column("recommended_next_action", sa.Text(), nullable=False),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False),
        sa.Column("llm_calls_used", sa.Integer(), nullable=False),
        sa.Column("estimated_cost_usd", sa.Numeric(12, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["auction_record_id"], ["auction_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_triage_results_auction_record_id", "triage_results", ["auction_record_id"])
    op.create_index("ix_triage_results_tier_1_status", "triage_results", ["tier_1_status"])
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=True),
        sa.Column("auction_record_id", sa.Uuid(), nullable=True),
        sa.Column("agent_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("input_json", JSON_VARIANT, nullable=False),
        sa.Column("output_json", JSON_VARIANT, nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("model_name", sa.Text(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("estimated_cost_usd", sa.Numeric(12, 4), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["auction_record_id"], ["auction_records.id"]),
        sa.ForeignKeyConstraint(["batch_id"], ["auction_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_runs_batch_id", "agent_runs", ["batch_id"])
    op.create_index("ix_agent_runs_auction_record_id", "agent_runs", ["auction_record_id"])
    op.create_table(
        "cost_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=True),
        sa.Column("auction_record_id", sa.Uuid(), nullable=True),
        sa.Column("service", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("unit_count", sa.Numeric(12, 4), nullable=False),
        sa.Column("estimated_cost_usd", sa.Numeric(12, 4), nullable=False),
        sa.Column("metadata", JSON_VARIANT, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["auction_record_id"], ["auction_records.id"]),
        sa.ForeignKeyConstraint(["batch_id"], ["auction_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cost_events_batch_id", "cost_events", ["batch_id"])
    op.create_index("ix_cost_events_auction_record_id", "cost_events", ["auction_record_id"])

    op.create_table(
        "scraper_failures",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["auction_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scraper_failures_batch_id", "scraper_failures", ["batch_id"])


def downgrade() -> None:
    op.drop_table("scraper_failures")
    op.drop_table("cost_events")
    op.drop_table("agent_runs")
    op.drop_table("triage_results")
    op.drop_table("source_snapshots")
    op.drop_table("auction_records")
    op.drop_table("auction_batches")
