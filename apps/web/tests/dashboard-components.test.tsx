import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BatchSummaryCard } from "@/components/BatchSummaryCard";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { ParcelTable } from "@/components/ParcelTable";
import type { AuctionRecord, BatchSummary, RecordEvidence } from "@/lib/api";

const batch: BatchSummary = {
  id: "12345678-1234-1234-1234-123456789abc",
  county: "Sarasota",
  source: "fixture",
  status: "completed",
  started_at: "2026-01-01T00:00:00Z",
  completed_at: "2026-01-01T00:00:00Z",
  records_found: 2,
  records_valid: 2,
  records_quarantined: 0,
  records_rejected: 1,
  records_watchlist: 1,
  records_research_candidates: 0,
  records_manual_review: 0,
  llm_calls_used: 1,
  estimated_cost_usd: "0.0100",
  error_message: null,
  created_at: "2026-01-01T00:00:00Z",
};

const records: AuctionRecord[] = [
  makeRecord("record-1", "0123456789", "WATCHLIST", "C", ["ambiguous_junk:ROAD"]),
  makeRecord("record-2", "9876543210", "REJECTED", "F", ["high_opening_bid_ratio"]),
];

const evidence: RecordEvidence = {
  record_id: "record-1",
  snapshots: [
    {
      id: "snapshot-1",
      source_url: "https://example.test/detail",
      html_path: null,
      screenshot_path: null,
      content_hash: "a".repeat(64),
      page_structure_hash: "b".repeat(64),
      parser_version: "parser-v1",
      scraped_at: "2026-01-01T00:00:00Z",
      created_at: "2026-01-01T00:00:00Z",
    },
  ],
  triage_evidence: [
    {
      rule_name: "junk.ambiguous_keyword",
      field_inspected: "property_text",
      value: "ROAD TRACT",
      decision_impact: "manual_review",
      reason: "Ambiguous property text.",
    },
  ],
  agent_runs: [
    {
      id: "run-1",
      agent_name: "ambiguity_classifier",
      status: "completed",
      output_json: { classification: "ambiguous" },
      error_message: null,
      model_name: "mock",
      input_tokens: 10,
      output_tokens: 5,
      estimated_cost_usd: "0.0000",
      started_at: "2026-01-01T00:00:00Z",
      completed_at: "2026-01-01T00:00:00Z",
    },
  ],
  cost_events: [
    {
      id: "cost-1",
      service: "mock",
      event_type: "ambiguity_classifier_llm_call",
      unit_count: "15",
      estimated_cost_usd: "0.0000",
      metadata_json: {},
      created_at: "2026-01-01T00:00:00Z",
    },
  ],
};

describe("dashboard components", () => {
  it("renders batch summary counts", () => {
    render(<BatchSummaryCard batch={batch} link={false} />);

    expect(screen.getByText("Batch 12345678")).toBeTruthy();
    expect(screen.getByText("Watchlist")).toBeTruthy();
    expect(screen.getByText("LLM calls")).toBeTruthy();
  });

  it("renders parcel table and filters by parcel search", () => {
    render(<ParcelTable records={records} evidenceByRecordId={{ "record-1": evidence }} />);

    expect(screen.getByText("0123456789")).toBeTruthy();
    expect(screen.getByText("9876543210")).toBeTruthy();

    fireEvent.change(screen.getByPlaceholderText("Search parcel or case number"), { target: { value: "987" } });

    expect(screen.queryByText("0123456789")).toBeNull();
    expect(screen.getByText("9876543210")).toBeTruthy();
  });

  it("opens evidence drawer with evidence sections", () => {
    render(<ParcelTable records={records} evidenceByRecordId={{ "record-1": evidence }} />);

    fireEvent.click(screen.getAllByText("View evidence")[0]);

    expect(screen.getByText("Evidence drawer")).toBeTruthy();
    expect(screen.getByText("Source snapshots")).toBeTruthy();
    expect(screen.getByText("Rule evidence")).toBeTruthy();
    expect(screen.getByText("LLM classifier output and agent timeline")).toBeTruthy();
    expect(screen.getByText("Cost ledger")).toBeTruthy();
    expect(screen.getByText(/Grades indicate research priority only/)).toBeTruthy();
  });

  it("renders empty and error states", () => {
    render(
      <>
        <EmptyState title="No batches yet" description="Create a Sarasota import batch." />
        <ErrorState message="API unavailable" />
      </>,
    );

    expect(screen.getByText("No batches yet")).toBeTruthy();
    expect(screen.getByText("API unavailable")).toBeTruthy();
  });
});

function makeRecord(id: string, parcelId: string, status: string, grade: string, riskFlags: string[]): AuctionRecord {
  return {
    id,
    batch_id: batch.id,
    county: "Sarasota",
    case_number: `2026-TD-${id}`,
    parcel_id_raw: parcelId,
    parcel_id_normalized: parcelId,
    auction_date: "2026-07-01",
    auction_status: "scheduled",
    opening_bid_cents: 5000000,
    appraiser_assessment_cents: 20000000,
    detail_url: "https://example.test/detail",
    notice_url: null,
    tax_deed_record_url: null,
    parse_confidence: "0.9500",
    missing_fields: [],
    parse_warnings: [],
    created_at: "2026-01-01T00:00:00Z",
    latest_triage: {
      tier_1_status: status,
      grade,
      estimated_spread_cents: 15000000,
      opening_bid_ratio: "0.2500",
      data_quality_score: "0.9000",
      risk_flags: riskFlags,
      positive_signals: [],
      recommended_next_action: "Review evidence.",
      requires_human_review: true,
      llm_calls_used: 0,
      estimated_cost_usd: "0.0000",
      created_at: "2026-01-01T00:00:00Z",
    },
  };
}
