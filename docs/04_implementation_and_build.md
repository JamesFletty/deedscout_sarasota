# DeedScout Sarasota — Implementation and Build Document

Version: 0.3
Build Style: Vertical-slice MVP
Primary Implementation Tools: Codex, GitHub, Azure, Microsoft 365-compatible
exports
LLM Plan: Provider-agnostic adapter with mock-first development

---

## 1. Build Strategy

Build this as a vertical slice, not as disconnected features.

The first successful slice should be:

```text
Trigger import → scrape source page → save HTML/screenshot → parse one or more
records → store normalized records → run deterministic triage → show dashboard
record → export report.
```

Do not start with full official-records parsing, paid AVMs, multi-county expansion, or
perfect UI polish. The first win is a real scraper-first ingestion and triage path.

**Tactical priority:** Get to deterministic triage producing real grades from fixture data
as fast as possible. That is the "magic moment" where raw HTML turns into investor-grade signals. Everything after that is polish and provider adapters.

---

## 2. Implementation Order

Correct order:

1. Repo setup
2. Backend foundation
3. Database schema
4. Storage abstraction
5. **Source validation & discovery** *(NEW: validate Sarasota page structure before
writing parser)*
6. Scraper skeleton


7. Snapshot storage *(enhanced with page-structure hash)*
8. Parser fixtures
9. Normalized records *(with deduplication / staleness strategy)*
10. Batch dashboard *(start with simple FastAPI/Jinja2 or minimal Next.js)*
11. Deterministic triage *(enhanced with fuzzy junk detection)*
12. Mock LLM provider + router + GitHub Models + Azure providers *(combined
milestone)*
13. Evidence drawer
14. **Export: single-sheet MVP first, multi-tab later** *(CHANGED: simplify first
export)*
15. Dockerization
16. Azure deployment
17. Portfolio case study

Why mock before cloud LLMs:

- Tests should not require live credentials.
- The pipeline should be usable even if Azure model access is delayed.
- Ambiguous records can safely route to manual review when providers fail.

---

## 3. Repository Structure

Recommended monorepo:

```text
deedscout/
├── apps/
│ ├── web/
│ │ ├── app/
│ │ ├── components/
│ │ ├── lib/
│ │ ├── package.json
│ │ └── tsconfig.json
│ └── api/
│    ├── app/
│    │ ├── agents/
│    │ ├── api/
│    │ ├── core/
│    │ ├── db/
│    │ ├── llm/


│   │ ├── models/
│   │ ├── parsing/
│   │ ├── schemas/
│   │ ├── scraping/
│   │ ├── services/
│   │ ├── storage/
│   │ └── workers/
│   ├── tests/
│   ├── alembic/
│   ├── pyproject.toml
│   └── Dockerfile
├── fixtures/
│ └── sarasota/
│   ├── html/
│   ├── screenshots/
│   └── expected/
├── infra/
│ ├── docker-compose.yml
│ ├── azure/
│ └── github-actions/
├── docs/
│ ├── 01_project_summary.md
│ ├── 02_mvp_prd.md
│ ├── 03_architecture_and_stack.md
│ ├── 04_implementation_and_build.md
│ └── portfolio_case_study.md
└── README.md
```

---

## 4. Backend Module Plan

### app/core

```text
config.py
logging.py
errors.py
constants.py
```


### app/db

```text
session.py
base.py
migrations.py
```

### app/models

```text
auction_batch.py
auction_record.py
source_snapshot.py
triage_result.py
agent_run.py
cost_event.py
scraper_failure.py *(NEW: dead-letter queue for failed page fetches)*
```

### app/schemas

```text
auction.py
triage.py
llm.py
export.py
jobs.py
```

### app/scraping

```text
playwright_client.py
sarasota_source_discovery.py
sarasota_auction_scraper.py
sarasota_detail_scraper.py
rate_limiter.py
snapshotter.py
```

### app/parsing


```text
auction_parser.py
money_parser.py
date_parser.py
parcel_parser.py
status_parser.py
confidence.py
```

### app/agents

```text
orchestrator.py
data_quality_agent.py
dedupe_agent.py
junk_filter_agent.py
spread_scoring_agent.py
ambiguity_classifier_agent.py
cost_gatekeeper_agent.py
final_triage_agent.py
export_agent.py
```

### app/llm

```text
base.py
router.py
providers/
 mock_provider.py
 github_models_provider.py
 azure_openai_provider.py
 azure_foundry_provider.py
 ollama_provider.py
 openai_provider.py
```

### app/storage

```text
base.py


local_storage.py
azure_blob_storage.py
```

### app/services

```text
batch_service.py
record_service.py
triage_service.py
export_service.py
cost_service.py
job_service.py
```

---

## 5. Environment Configuration

`.env.example`:

```text
APP_ENV=development
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/deedscout
REDIS_URL=redis://localhost:6379/0

STORAGE_BACKEND=local
LOCAL_STORAGE_ROOT=./.storage
AZURE_STORAGE_CONNECTION_STRING=
AZURE_STORAGE_CONTAINER=deedscout

SCRAPER_HEADLESS=true
SCRAPER_MAX_PAGES=150
SCRAPER_MAX_RETRIES=2
SCRAPER_DELAY_MS=1500
SCRAPER_TIMEOUT_MS=30000
SCRAPER_SCREENSHOTS_ENABLED=true

LLM_PROVIDER=mock
LLM_MAX_CALLS_PER_BATCH=25
LLM_MAX_INPUT_CHARS=4000
LLM_REQUIRE_JSON=true


LLM_TIMEOUT_SECONDS=30
LLM_RETRY_COUNT=1

GITHUB_TOKEN=
GITHUB_MODELS_ENDPOINT=https://models.github.ai/inference
GITHUB_MODELS_MODEL=

AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_API_VERSION=
AZURE_OPENAI_DEPLOYMENT_NAME=

AZURE_FOUNDRY_ENDPOINT=
AZURE_FOUNDRY_API_KEY=
AZURE_FOUNDRY_DEPLOYMENT_NAME=

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

---

## 6. Core Pydantic Schemas

### ScrapedAuctionRecord

```python
from datetime import date
from typing import Literal, Optional
from pydantic import BaseModel

class ScrapedAuctionRecord(BaseModel):
   county: Literal["sarasota"]
   case_number: Optional[str] = None
   parcel_id_raw: Optional[str] = None
   auction_date: Optional[date] = None
   auction_status: Literal[
     "scheduled",
     "running",
     "closed",
     "canceled",
     "postponed",


     "redeemed",
     "unknown"
  ] = "unknown"
  opening_bid_raw: Optional[str] = None
  appraiser_assessment_raw: Optional[str] = None
  detail_url: str
  notice_url: Optional[str] = None
  tax_deed_record_url: Optional[str] = None
```

### NormalizedAuctionRecord

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import date

class NormalizedAuctionRecord(BaseModel):
   county: Literal["sarasota"]
   case_number: str
   parcel_id_raw: str
   parcel_id_normalized: str
   auction_date: Optional[date]
   auction_status: str
   opening_bid_cents: int
   appraiser_assessment_cents: Optional[int]
   detail_url: str
   notice_url: Optional[str]
   tax_deed_record_url: Optional[str]
   parse_confidence: float = Field(ge=0.0, le=1.0)
   missing_fields: list[str] = []
   parse_warnings: list[str] = []
```

### TriageResultSchema

```python
class TriageResultSchema(BaseModel):
   tier_1_status: Literal[
      "REJECTED",
      "WATCHLIST",
      "RESEARCH_CANDIDATE",


    "MANUAL_REVIEW",
    "QUARANTINED",
    "CANCELED_OR_INACTIVE"
  ]
  grade: Literal["A", "B", "C", "D", "F", "U"]
  estimated_spread_cents: Optional[int]
  opening_bid_ratio: Optional[float]
  data_quality_score: float = Field(ge=0.0, le=1.0)
  risk_flags: list[str]
  positive_signals: list[str]
  evidence: list[dict]
  recommended_next_action: str
  requires_human_review: bool
  llm_calls_used: int = 0
  estimated_cost_usd: float = 0.0
```

### LLM Interfaces

```python
from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel

class LLMRequest(BaseModel):
   system: str
   user: str
   json_schema: dict[str, Any] | None = None
   temperature: float = 0
   max_tokens: int = 800

class LLMResponse(BaseModel):
   provider: str
   model: str
   content: str
   input_tokens: int | None = None
   output_tokens: int | None = None
   estimated_cost_usd: float = 0.0
   raw: dict[str, Any] | None = None

class LLMProvider(ABC):
   @abstractmethod


  async def complete(self, request: LLMRequest) -> LLMResponse:
    ...
```

---

## 7. Source Validation & Discovery *(NEW SECTION)*

Before writing the auction parser, manually validate the Sarasota Clerk auction page
structure.

### Validation Checklist

1. Load `https://www.sarasotaclerk.com/Home-and-Property/Tax-Deeds/Tax-Deed-Auctions`
2. Confirm which fields are present in the auction list view:
  - Case number
  - Parcel ID
  - Opening bid
  - Auction date
  - Auction status
  - **Property Appraiser assessment** *(critical: may NOT be present on Clerk page)*
3. If assessment is missing from Clerk page, document whether it requires cross-referencing the Sarasota Property Appraiser portal.
4. Capture a sample HTML fixture and save to `fixtures/sarasota/html/` before writing
any parser code.

### Cross-Reference Risk

If the Clerk page does not expose assessment values, the deterministic spread
calculation cannot run without a second scrape. For MVP, decide one of:

- **Option A:** Scrape both Clerk and Property Appraiser pages (higher complexity,
higher failure rate).
- **Option B:** Drop assessment from the deterministic spread calculation and rely on
opening bid + status + junk signals only, with manual assessment lookup as a future
enhancement.
- **Option C:** If assessment IS present on the Clerk page, proceed with full spread
scoring.

**Recommendation:** Choose Option B if assessment requires a second site. A working
triage pipeline with 80% of fields is better than a broken pipeline chasing 100%


coverage.

---

## 8. Scraper Implementation Requirements

### Scraper Config

```python
from pydantic import BaseModel

class ScraperConfig(BaseModel):
   county: str = "sarasota"
   headless: bool = True
   max_pages: int = 150
   max_retries: int = 2
   delay_between_pages_ms: int = 1500
   timeout_ms: int = 30000
   screenshot_enabled: bool = True
   save_html_enabled: bool = True
   user_agent: str = "DeedScout research prototype"
```

### Required Behavior

The scraper must:

- Launch Playwright browser.
- Load configured Sarasota auction source.
- Extract links to property/detail pages when possible.
- Visit detail pages.
- Save HTML before parse.
- Save screenshot when enabled.
- Write `source_snapshots` row.
- Return parsed raw records.
- Retry failed page loads up to max retries.
- Stop if access is blocked.
- Never bypass CAPTCHA.
- Never use anti-bot evasion.
- **Store failed page fetches in `scraper_failures` table with URL, error, and
timestamp.** *(NEW)*


### Dead-Letter Queue for Failures *(NEW)*

If a detail page fails after max retries, store:

```sql
create table scraper_failures (
  id uuid primary key,
  batch_id uuid references auction_batches(id),
  source_url text not null,
  error_message text,
  retry_count int not null default 0,
  failed_at timestamptz not null default now()
);
```

This allows post-run inspection without digging through logs. The batch status should
still be `PARTIAL` if any failures exist.

### Fixture Replay

Every parser must support fixture replay:

```bash
python -m app.cli replay-fixture fixtures/sarasota/html/sample_detail.html
```

This avoids repeated live scraping during parser development.

---

## 9. Snapshot Storage Enhancements *(MODIFIED)*

### source_snapshots schema update

Add `page_structure_hash` to detect DOM changes:

```sql
create table source_snapshots (
 id uuid primary key,
 auction_record_id uuid references auction_records(id),
 batch_id uuid references auction_batches(id),
 source_url text not null,


  html_path text,
  screenshot_path text,
  content_hash text not null,
  page_structure_hash text, *(NEW: normalized DOM structure hash)*
  parser_version text not null,
  scraped_at timestamptz not null,
  created_at timestamptz not null default now()
);
```

**Purpose:** When the county redesigns their page, the content hash may change for
legitimate reasons, but the `page_structure_hash` alerts you that the DOM structure
changed and parsers may need updating. Compute this by hashing a normalized
representation of key CSS selectors or tag structure.

---

## 10. Parser Implementation

### Money Parser

Requirements:

- Convert `$8,420.00` to `842000`.
- Strip commas and symbols.
- Reject ambiguous values.
- Return warnings for unparsable values.

### Parcel Parser

Requirements:

- Preserve raw parcel ID.
- Normalize spacing and punctuation.
- Validate known Sarasota-style patterns where possible.
- Do not invent missing parcel IDs.

### Status Parser

Map source statuses to:

```text


scheduled
running
closed
canceled
postponed
redeemed
unknown
```

### Confidence Scoring

```text
+0.20 case number present
+0.20 parcel ID present
+0.20 opening bid parsed
+0.15 auction status parsed
+0.15 appraiser assessment parsed
+0.10 source/detail URL present
```

Minimum confidence for triage:

```text
0.70
```

---

## 11. Deterministic Triage Implementation *(MODIFIED — junk detection)*

Pseudo-code:

```python
def triage_record(record: NormalizedAuctionRecord) -> TriageResultSchema:
  if record.parse_confidence < 0.70:
      return quarantined(record, "LOW_PARSE_CONFIDENCE")

  if record.auction_status in {"canceled", "postponed", "redeemed", "closed"}:
      return inactive(record, "AUCTION_NOT_ACTIVE")

  if not record.parcel_id_normalized:
     return rejected(record, "MISSING_PARCEL_ID")


     if record.opening_bid_cents <= 0:
         return rejected(record, "INVALID_OPENING_BID")

     if not record.appraiser_assessment_cents or record.appraiser_assessment_cents <=
0:
       return manual_review(record, "NO_APPRAISER_ASSESSMENT")

     opening_bid_ratio = record.opening_bid_cents / record.appraiser_assessment_cents
     estimated_spread = record.appraiser_assessment_cents - record.opening_bid_cents

     if opening_bid_ratio >= 0.90:
        return rejected(record, "OPENING_BID_TOO_CLOSE_TO_ASSESSMENT")

     if estimated_spread < 1_000_000:
        return rejected(record, "SPREAD_TOO_SMALL")

     if has_hard_junk_signal(record):
        return rejected(record, "JUNK_PARCEL_SIGNAL")

     if is_ambiguous(record):
         return route_to_ambiguity_classifier(record)

     if opening_bid_ratio <= 0.65 and estimated_spread >= 1_500_000:
        return research_candidate(record)

  return watchlist(record)
```

Every return path must include:

- Status
- Grade
- Evidence
- Risk flags
- Positive signals
- Recommended next action
- Human review flag

### Fuzzy Junk Detection *(NEW — replaces naive substring matching)*

The junk signal list:


```text
RETENTION
RETENTION POND
DRAINAGE
DRAINAGE EASEMENT
STORMWATER
WATER MANAGEMENT
UTILITY
UTILITY EASEMENT
RIGHT OF WAY
R/W
ROAD
ALLEY
CANAL
DITCH
BUFFER
CONSERVATION
WETLAND
PRESERVE
COMMON AREA
TRACT ONLY
LIFT STATION
PUMP STATION
SUBMERGED
WASTE LAND
RAILROAD
CEMETERY
EASEMENT PARCEL
```

**Rules:**

- "RETENTION POND" and "LIFT STATION" → hard reject.
- "TRACT" alone → route to ambiguity review (LLM or manual). Do NOT substring-match "TRACT" because it appears in legitimate names like "OAK TRACT ESTATES."
Use boundary-aware matching or context scoring.
- "WETLAND" → does not auto-reject without supporting evidence.
- Vacant land → does not auto-reject solely for being vacant.

**Implementation approach:** Use weighted token matching with word boundaries, not
naive `in` checks. For "TRACT", require it to appear without adjacent residential


indicators (e.g., "ESTATES", "HOMES", "SUBDIVISION") to trigger ambiguity. Document
the scoring logic in `junk_filter_agent.py`.

---

## 12. Data Refresh & Deduplication *(NEW SECTION)*

Tax deed auctions change daily (canceled, redeemed, postponed). The system must
handle updates without creating orphaned duplicates.

### Deduplication Strategy

Use a natural key of `(county, case_number, parcel_id_normalized)` or `(county,
parcel_id_normalized, auction_date)`.

On re-import of the same batch or a new batch:

1. Check if `(county, case_number, parcel_id)` already exists in `auction_records`.
2. If found and source data changed:
  - Create a new `source_snapshots` row.
  - Update `auction_records` fields.
  - Increment a `version` counter on the record.
  - Archive previous triage result or overwrite based on `updated_at`.
3. If found and source data unchanged:
  - Skip re-parsing to save scraper cost.
4. If not found:
  - Insert new record.

### Batch Staleness

Add `is_current` boolean to `auction_batches`. When a new batch is imported for the
same county, mark previous batches `is_current = false`. The dashboard defaults to
showing only current batches.

---

## 13. LLM Router Implementation *(MODIFIED — combined milestones)*

### Router Rules

The router must:


- Read `LLM_PROVIDER`.
- Instantiate the selected provider.
- Enforce max calls per batch.
- Enforce max input chars.
- Enforce timeout.
- Validate JSON output.
- Record `agent_runs`.
- Record `cost_events`.
- Return structured failure if provider fails.

### Failure Policy

```text
Provider missing → MANUAL_REVIEW
Provider timeout → MANUAL_REVIEW
Invalid JSON → MANUAL_REVIEW
Schema validation failure → MANUAL_REVIEW
Cost cap exceeded → MANUAL_REVIEW
```

### Ambiguity Prompt

```text
You are a parcel triage classifier for a Florida tax deed auction screening system.

Classify whether the parcel is likely investable, likely junk, or ambiguous based only on
the supplied auction/appraiser fields and legal description.

Do not infer market value.
Do not provide legal advice.
Do not claim title is clear.
Do not recommend bidding.
Do not speculate beyond the supplied fields.
Return strict JSON only.

Definitions:
- likely_junk: retention pond, drainage tract, right-of-way, utility parcel, common area,
conservation/wetland tract, tiny unusable strip, submerged/waste land, lift station,
pump station, or no plausible independent real estate utility.
- likely_investable: residential, commercial, multifamily, mobile home, buildable vacant
residential, or another property with plausible independent use.
- ambiguous: unclear from supplied data.


Input:
{{input_json}}

Return JSON:
{
  "classification": "likely_investable|likely_junk|ambiguous",
  "confidence": 0.0,
  "junk_reasons": ["string"],
  "positive_reasons": ["string"],
  "risk_flags": ["string"],
  "requires_human_review": true,
  "recommended_next_step": "reject|watchlist|research_candidate|manual_review"
}
```

### Combined Provider Milestone

Instead of separate milestones for mock, GitHub, and Azure providers, implement them
as one milestone:

```text
app/llm/providers/
 mock_provider.py     — deterministic fake responses for tests/demos
 github_models_provider.py — fast prototyping fallback
 azure_openai_provider.py — preferred Azure provider
 azure_foundry_provider.py — preferred Microsoft Foundry provider
 ollama_provider.py    — local fallback
 openai_provider.py    — future optional adapter
```

**Acceptance:** Triage code does not change when `LLM_PROVIDER` env var
changes. All providers implement the same `LLMProvider` ABC.

---

## 14. Frontend Build

### Pages

```text
/dashboard


/batches/[batchId]
```

Optional:

```text
/records/[recordId]
```

Record details can be a drawer/modal in MVP.

**Vertical slice recommendation:** For the first working slice, a minimal FastAPI/Jinja2
dashboard or a very simple Next.js app is acceptable. Do not let frontend polish block
the pipeline. Swap in a full Next.js frontend once the backend triage is proven.

### Components

```text
BatchSummaryCard
ImportBatchButton
JobStatusIndicator
ParcelGradeBadge
TriageStatusChip
ParcelTable
ParcelCard
EvidenceDrawer
RiskFlagList
AgentDecisionTimeline
CostLedgerPanel
ExportButton
```

### Batch Detail Page Requirements

Show:

- Batch metadata
- Import status
- Counts by status
- LLM calls used
- Estimated cost
- Records table


- Filters by status/grade
- Export button

### Evidence Drawer Requirements

Show:

- Source URL
- HTML snapshot reference
- Screenshot reference
- Parser version
- Parsed fields
- Missing fields
- Parser warnings
- Rule hits
- LLM provider/model if used
- LLM output if used
- Final status/grade
- Recommended next action

---

## 15. Export Implementation *(MODIFIED — phased approach)*

### Phase 1: Single-Sheet MVP Export

For the first working export, generate a single `.xlsx` sheet or CSV containing all
records with columns:

```text
parcel_id, case_number, auction_date, auction_status, opening_bid,
appraiser_assessment, estimated_spread, bid_ratio, status, grade,
risk_flags, positive_signals, recommended_next_action, detail_url
```

Include a disclaimer row and generation timestamp. This satisfies the investor workflow
immediately without heavy formatting work.

### Phase 2: Multi-Tab Workbook

After the pipeline is proven, add the full workbook with tabs:


```text
Summary
Research Candidates
Watchlist
Rejected Parcels
Manual Review
Quarantined Records
Source Evidence
Agent Decisions
Cost Ledger
```

Suggested Python libraries:

```text
openpyxl
xlsxwriter
```

Future Microsoft Graph integration:

```text
Upload generated workbook to OneDrive/SharePoint.
Return share link or file path.
```

---

## 16. Testing Plan

### Backend Tests

```text
test_money_parser.py
test_parcel_normalizer.py
test_status_parser.py
test_auction_parser_fixture.py
test_snapshot_storage.py
test_junk_filter_rules.py
test_spread_scoring.py
test_data_quality_agent.py
test_llm_router_mock.py


test_llm_classifier_schema.py
test_final_triage_agent.py
test_export_generation.py
test_deduplication.py      *(NEW)*
test_scraper_failure_queue.py *(NEW)*
```

### Scraper Tests

```text
Can launch Playwright locally.
Can save HTML snapshot.
Can save screenshot.
Can handle timeout.
Can stop after max pages.
Can retry failed pages no more than max retries.
Can parse fixture HTML.
Can quarantine low-confidence record.
Can store scraper failure in dead-letter queue. *(NEW)*
```

### LLM Tests

```text
Mock provider returns valid JSON.
Invalid JSON routes to MANUAL_REVIEW.
Provider timeout routes to MANUAL_REVIEW.
Cost cap prevents additional calls.
Ambiguous record triggers model call.
Non-ambiguous reject does not trigger model call.
All provider adapters pass same interface test. *(NEW)*
```

### Frontend Tests

```text
Dashboard renders batch counts.
Parcel table filters by status.
Evidence drawer opens.
Export button renders.
Error states render clearly.
```


---

## 17. Milestones *(MODIFIED)*

### Milestone 1 — Repo and Local Foundation

Deliverables:

- Monorepo
- FastAPI app
- Next.js app (or minimal Jinja2 dashboard for first slice)
- Docker Compose
- Postgres
- Health endpoint
- README

Acceptance:

- `docker compose up` starts stack.
- Frontend loads.
- Backend health endpoint works.
- Database migration runs.

### Milestone 2 — Database and Storage

Deliverables:

- SQLAlchemy/SQLModel models
- Alembic migrations
- Local storage adapter
- Azure Blob adapter skeleton
- `scraper_failures` table *(NEW)*

Acceptance:

- Tables created.
- Storage interface tested.
- Sample snapshot metadata can be saved.
- Failed scraper attempts can be stored.

### Milestone 3 — Source Validation & Scraper Skeleton


Deliverables:

- Manual validation of Sarasota page structure
- Playwright client
- Sarasota source discovery
- HTML snapshot save
- Screenshot save
- `page_structure_hash` computation *(NEW)*
- Structured scrape errors
- Dead-letter queue for failures *(NEW)*

Acceptance:

- Scraper loads source page.
- HTML saved.
- Screenshot saved.
- Snapshot row created with structure hash.
- Failed pages store in `scraper_failures`.

### Milestone 4 — Parser and Fixture Replay

Deliverables:

- Auction parser
- Money parser
- Parcel normalizer
- Status parser
- Confidence scoring
- Fixture replay CLI
- Tests

Acceptance:

- Saved HTML fixture parses into normalized record.
- Low-confidence record quarantines.
- Tests pass.

### Milestone 5 — Batch Import Dashboard

Deliverables:


- Import button
- Batch creation
- Job status
- Batch record table
- Deduplication logic *(NEW)*

Acceptance:

- User can trigger import.
- Batch appears in dashboard.
- Records display.
- Errors are visible.
- Re-importing same batch does not duplicate unchanged records.

### Milestone 6 — Deterministic Triage

Deliverables:

- Data Quality Agent
- Junk Filter Agent *(with fuzzy matching)*
- Spread Scoring Agent
- Final Triage Agent

Acceptance:

- Obvious rejects rejected.
- Low spreads rejected.
- Good records promoted.
- "TRACT" in legitimate names does not false-positive.
- Every result includes evidence.

### Milestone 7 — LLM Router and All Providers *(COMBINED)*

Deliverables:

- LLM base interface
- Router
- Mock provider
- GitHub Models provider
- Azure OpenAI provider
- Azure Foundry provider
- Cost tracking


- Manual-review fallback

Acceptance:

- Tests run without live model credentials.
- Ambiguous records call mock provider.
- Provider failure routes to manual review.
- Switching `LLM_PROVIDER` env var does not change triage code.

### Milestone 8 — Evidence Drawer

Deliverables:

- Parcel drawer
- Snapshot metadata display
- Rule decision timeline
- LLM output display
- Cost events display

Acceptance:

- User can inspect why parcel was classified.
- No result appears without evidence.

### Milestone 9 — Export *(PHASED)*

Deliverables:

- Phase 1: Single-sheet `.xlsx` / CSV export
- Phase 2: Multi-tab workbook *(deferred until after pipeline is proven)*
- Download endpoint

Acceptance:

- Export includes all records with status/grade.
- Export includes disclaimer.
- Export includes generation timestamp.

### Milestone 10 — Azure Deployment

Deliverables:


- Dockerfiles
- GitHub Actions
- Azure Container Registry setup
- Azure Container Apps backend
- Scraper job deployment
- Blob storage config

Acceptance:

- App deploys.
- Backend reachable.
- Scraper job runs.
- Snapshots save to Blob Storage.
- Dashboard shows imported data.

### Milestone 11 — Portfolio Case Study

Deliverables:

- README *(with explicit "no anti-bot" stance)*
- Architecture diagram
- Demo screenshots
- Short demo video
- Portfolio writeup

Acceptance:

- Reviewer can understand problem and architecture quickly.
- Case study highlights scraping, evidence, deterministic rules, provider-agnostic LLM
routing, and cost controls.
- README clearly states ethical scraping boundaries.

---

## 18. Security & Ethical Boundaries *(NEW SECTION)*

MVP security requirements:

- No secrets in repo.
- Use `.env.example` only.
- Use Azure Key Vault later for deployed secrets.
- Do not log LLM credentials.


- Do not log browser/session credentials.
- **Do not build CAPTCHA bypass.** *(document prominently)*
- **Do not build anti-bot evasion.** *(document prominently)*
- Protect deployed dashboard with basic auth, invite-only auth, or network restriction.
- Keep source snapshots private by default.

**README requirement:** Include a prominent section titled "Ethical Scraping & Anti-Bot Policy" that explains:

> DeedScout respects county website terms of service. The scraper uses standard
browser requests with configurable rate limits and bounded retries. It does not bypass
CAPTCHA, use headless detection evasion, or rotate residential proxies. If a county site
blocks access, the system stops gracefully and routes records to manual review.

This signals professional engineering judgment to portfolio reviewers and prevents
misuse.

---

## 19. Local Commands

```bash
# Start local stack
docker compose up --build

# Backend tests
cd apps/api
pytest

# Run parser fixture replay
python -m app.cli replay-fixture fixtures/sarasota/html/sample_detail.html

# Run scraper locally in visible mode
python -m app.cli scrape-sarasota --headful --max-pages 5

# Run triage on a batch
python -m app.cli triage-batch <batch_id>

# Generate export
python -m app.cli export-batch <batch_id>
```


---

## 20. Definition of Done

The MVP is done when:

- App runs locally through Docker.
- A Sarasota import can be triggered.
- Source evidence is stored *(with structure hash)*.
- Records are normalized.
- Bad records are quarantined.
- Deterministic triage works *(with fuzzy junk detection)*.
- LLM ambiguity classification works with mock provider.
- GitHub Models/Azure providers can be configured without changing business logic.
- Dashboard shows batches and parcel results.
- Evidence drawer works.
- Excel/CSV export works *(single-sheet minimum)*.
- Cost ledger is populated.
- Scraper failures are stored in dead-letter queue.
- Azure deployment path is documented and tested.
- README and portfolio case study are ready *(with ethical scraping policy)*.

The MVP is not done if:

- It requires manual data entry as the primary ingestion path.
- It cannot replay from saved fixtures.
- It calls LLMs for every parcel.
- It depends on one unavailable API key.
- It provides legal/title/investment conclusions.
- It cannot explain why a parcel was classified.
- It lacks documented ethical scraping boundaries.
