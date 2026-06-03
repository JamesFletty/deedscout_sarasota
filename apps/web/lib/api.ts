export type BatchSummary = {
  id: string;
  county: string;
  source: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  records_found: number;
  records_valid: number;
  records_quarantined: number;
  records_rejected: number;
  records_watchlist: number;
  records_research_candidates: number;
  records_manual_review: number;
  llm_calls_used: number;
  estimated_cost_usd: string;
  error_message: string | null;
  created_at: string;
};

export type BatchListResponse = {
  items: BatchSummary[];
  limit: number;
  offset: number;
  total: number;
};

export type ImportBatchResponse = {
  batch_id: string;
  job_id: string;
  job_status: string;
};

export type TriageSummary = {
  tier_1_status: string;
  grade: string;
  estimated_spread_cents: number | null;
  opening_bid_ratio: string | null;
  data_quality_score: string;
  risk_flags: unknown[];
  positive_signals: unknown[];
  recommended_next_action: string;
  requires_human_review: boolean;
  llm_calls_used: number;
  estimated_cost_usd: string;
  created_at: string;
};

export type AuctionRecord = {
  id: string;
  batch_id: string;
  county: string;
  case_number: string | null;
  parcel_id_raw: string | null;
  parcel_id_normalized: string | null;
  auction_date: string | null;
  auction_status: string | null;
  opening_bid_cents: number | null;
  appraiser_assessment_cents: number | null;
  detail_url: string | null;
  notice_url: string | null;
  tax_deed_record_url: string | null;
  parse_confidence: string;
  missing_fields: unknown[];
  parse_warnings: unknown[];
  created_at: string;
  latest_triage: TriageSummary | null;
};

export type RecordListResponse = {
  items: AuctionRecord[];
  limit: number;
  offset: number;
  total: number;
};

export type SourceSnapshot = {
  id: string;
  source_url: string;
  html_path: string | null;
  screenshot_path: string | null;
  content_hash: string;
  page_structure_hash: string | null;
  parser_version: string;
  scraped_at: string;
  created_at: string;
};

export type AgentRun = {
  id: string;
  agent_name: string;
  status: string;
  output_json: Record<string, unknown> | null;
  error_message: string | null;
  model_name: string | null;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: string;
  started_at: string;
  completed_at: string | null;
};

export type CostEvent = {
  id: string;
  service: string;
  event_type: string;
  unit_count: string;
  estimated_cost_usd: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
};

export type RecordEvidence = {
  record_id: string;
  snapshots: SourceSnapshot[];
  triage_evidence: Array<Record<string, unknown>>;
  agent_runs: AgentRun[];
  cost_events: CostEvent[];
};

export type JobResponse = {
  job_id: string;
  job_type: string;
  status: string;
  batch_id: string | null;
  message: string | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
};

export type TriageRunResponse = {
  batch: BatchSummary;
  triage_results_created: number;
  ambiguity_classifier_attempted: number;
};

export type ClassificationRunResponse = {
  attempted: number;
  skipped: number;
  updated: number;
  cost_cap_skipped: number;
  agent_runs: number;
  cost_events: number;
};

const API_BASE_URL = process.env.DEEDSCOUT_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(detail || `Request failed: ${response.status}`, response.status);
  }
  return (await response.json()) as T;
}

export function listBatches(): Promise<BatchListResponse> {
  return request<BatchListResponse>("/api/batches?limit=20");
}

export function getBatch(batchId: string): Promise<BatchSummary> {
  return request<BatchSummary>(`/api/batches/${batchId}`);
}

export function getBatchRecords(batchId: string): Promise<RecordListResponse> {
  return request<RecordListResponse>(`/api/batches/${batchId}/records?limit=100`);
}

export function getRecordEvidence(recordId: string): Promise<RecordEvidence> {
  return request<RecordEvidence>(`/api/records/${recordId}/evidence`);
}

export function importSarasotaBatch(sourceUrl?: string): Promise<ImportBatchResponse> {
  return request<ImportBatchResponse>("/api/batches/sarasota/import", {
    method: "POST",
    body: JSON.stringify({ source_url: sourceUrl || undefined, snapshot_only: true }),
  });
}

export function runTier1Triage(batchId: string): Promise<TriageRunResponse> {
  return request<TriageRunResponse>(`/api/batches/${batchId}/triage`, {
    method: "POST",
    body: JSON.stringify({ include_llm_ambiguity_classifier: false }),
  });
}

export function classifyAmbiguous(batchId: string): Promise<ClassificationRunResponse> {
  return request<ClassificationRunResponse>(`/api/batches/${batchId}/classify-ambiguous`, { method: "POST" });
}

export function getJob(jobId: string): Promise<JobResponse> {
  return request<JobResponse>(`/api/jobs/${jobId}`);
}
