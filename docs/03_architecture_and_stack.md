# DeedScout Sarasota — Architecture and Stack Document

Version: 0.2
Architecture Style: Scraper-first ingestion + deterministic rules + provider-agnostic LLM
routing
Primary Runtime: Azure
Secondary/Optional: Google Cloud Run deployment comparison
Export Layer: Microsoft 365-compatible Excel, future Microsoft Graph integration

---

## 1. Architecture Principle

The system must not be a loose chain of prompts. It should be a real data product with
an agentic workflow layered on top of deterministic scraping, parsing, validation, and
triage rules.

The central principle:

> Use code for extraction, parsing, validation, scoring, routing, cost control, and
storage. Use LLMs only for ambiguity classification and summary generation where
deterministic logic is insufficient.

---

## 2. High-Level Architecture

```text
Next.js Dashboard
  ↓
FastAPI Backend
  ↓
Auction Batch Service
  ↓
Azure Container Apps Scraper Job
  ↓
Playwright Sarasota Scraper
  ↓
Raw HTML + Screenshot Snapshot Storage
  ↓
Parser / Normalizer
  ↓


Postgres Normalized Records
  ↓
Tier 1 Rule Engine
  ↓
LLM Router for Ambiguous Records Only
  ↓
Final Triage Result
  ↓
Dashboard + Evidence Drawer + Excel Export
```

---

## 3. Recommended Stack

### Frontend

```text
Next.js
TypeScript
Tailwind CSS
shadcn/ui
TanStack Table
Recharts or Tremor for simple dashboard charts
```

Reasoning:

- Fast to build.
- Strong portfolio presentation.
- Good table/filtering support.
- Clean dashboard UX.

### Backend

```text
Python
FastAPI
Pydantic
SQLAlchemy or SQLModel
Alembic
pytest


ruff
mypy
```

Reasoning:

- Python is strongest for scraping, parsing, Playwright, LLM integrations, and data
workflows.
- FastAPI provides a clean API boundary for frontend and worker orchestration.

### Scraping

```text
Python Playwright
BeautifulSoup or lxml
Tenacity retries
Structured logging
Saved fixtures
```

Reasoning:

- Sarasota/auction pages may be dynamic.
- Playwright gives browser-level rendering, screenshots, and debugging.
- Saved fixtures make parser development cheap and safe.

### Agent Orchestration

```text
LangGraph
Pydantic schemas
Provider-agnostic LLM router
Mock provider for tests
```

Reasoning:

- The workflow has state, gates, branching, retries, fallbacks, and replay requirements.
- LangGraph is a better fit than loosely choreographed “agents.”

### Database


```text
Postgres
```

Stores:

- Auction batches
- Auction records
- Source snapshots
- Agent runs
- Triage results
- Cost events
- Export metadata

### Object Storage

```text
Azure Blob Storage in deployment
Local filesystem adapter in development
```

Stores:

- Raw HTML
- Screenshots
- Export files
- Optional future PDFs

### Runtime / Deployment

```text
Azure Container Apps
Azure Container Registry
Azure Blob Storage
Azure Database for PostgreSQL or POC Postgres container
GitHub Actions
```

### Optional Secondary Deployment

```text
Google Cloud Run


```

Purpose:

- Portability proof
- Cloud runtime comparison
- Not part of MVP critical path

---

## 4. Cloud Strategy

### Azure-First

Azure is the primary environment because student credits can support:

- Containerized backend
- Containerized scraper worker
- Blob evidence storage
- Postgres
- Monitoring
- Scheduled jobs
- Cost controls
- Azure OpenAI / Microsoft Foundry if available

### Google as Optional Secondary

Google Cloud should not be part of the critical path. It may be added later to show that
the scraper/backend container can run on Cloud Run.

### Microsoft 365 as Export Layer

Microsoft 365 integration is a product feature because target users will actually use
spreadsheets.

MVP:

- Generate `.xlsx` files server-side.
- Download from dashboard.

Future:


- Save to OneDrive/SharePoint via Microsoft Graph.
- Possibly email report through Outlook.

---

## 5. LLM Provider Architecture

The app must avoid hard dependency on a normal OpenAI API key.

All model calls go through:

```text
app/llm/base.py
app/llm/router.py
app/llm/providers/*
```

### Required Providers

```text
mock
```

Required for tests, offline development, demos, and CI.

```text
github_models
```

Fast prototyping fallback. Useful if Azure model access is delayed.

```text
azure_openai
```

Preferred Azure-hosted provider where Azure OpenAI deployments are available.

```text
azure_foundry
```

Preferred Microsoft Foundry provider if using Foundry deployment endpoints.


```text
ollama
```

Optional local fallback.

```text
openai
```

Future optional direct OpenAI provider. Not required for MVP.

### Provider Selection

Environment variable:

```text
LLM_PROVIDER=mock|github_models|azure_openai|azure_foundry|ollama|openai
```

Fallback behavior:

```text
If provider is missing, unavailable, times out, or returns invalid JSON, route the record
to MANUAL_REVIEW.
```

### LLM Interface

```python
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Any

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

### Provider Environment Variables

```text
LLM_PROVIDER=mock
LLM_MAX_CALLS_PER_BATCH=25
LLM_MAX_INPUT_CHARS=4000
LLM_REQUIRE_JSON=true
LLM_TIMEOUT_SECONDS=30
LLM_RETRY_COUNT=1
```

Azure OpenAI:

```text
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_API_VERSION=
AZURE_OPENAI_DEPLOYMENT_NAME=
```

Azure Foundry:

```text
AZURE_FOUNDRY_ENDPOINT=
AZURE_FOUNDRY_API_KEY=
AZURE_FOUNDRY_DEPLOYMENT_NAME=
```


GitHub Models:

```text
GITHUB_TOKEN=
GITHUB_MODELS_ENDPOINT=https://models.github.ai/inference
GITHUB_MODELS_MODEL=
```

Ollama:

```text
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

---

## 6. Agent Architecture

### Agent List

```text
Chief Orchestrator Agent
├── Source Discovery Agent
├── Sarasota Auction Scraper Agent
├── Property Detail Scraper Agent
├── Snapshot Evidence Agent
├── Parser / Normalizer Agent
├── Data Quality Agent
├── Deduplication Agent
├── Junk Parcel Rule Agent
├── Spread Scoring Agent
├── Ambiguity Classifier Agent
├── Cost Gatekeeper Agent
├── Final Triage Agent
└── Export Agent
```

### Deterministic Agents

These should not call LLMs:


```text
Source Discovery Agent
Sarasota Auction Scraper Agent
Property Detail Scraper Agent
Snapshot Evidence Agent
Parser / Normalizer Agent
Data Quality Agent
Deduplication Agent
Junk Parcel Rule Agent
Spread Scoring Agent
Cost Gatekeeper Agent
Export Agent
```

### LLM-Backed Agents

These may call LLMs:

```text
Ambiguity Classifier Agent
Final Explanation Summarizer
```

Even then, they must call through the LLM router.

### Deferred Agents

Not MVP:

```text
Official Records Lien Risk Agent
GIS Access Agent
Flood Zone Agent
Paid AVM Agent
Full Title Chain Agent
County Expansion Agent
```

---

## 7. Data Flow


### Import Data Flow

```text
POST /api/batches/sarasota/import
  ↓
Create auction_batches row
  ↓
Dispatch scraper worker
  ↓
Scraper loads source pages
  ↓
Save HTML + screenshots
  ↓
Parser extracts records
  ↓
Normalize fields
  ↓
Save auction_records
  ↓
Update batch counters
```

### Triage Data Flow

```text
POST /api/batches/{batch_id}/triage
   ↓
Fetch validated records
   ↓
Run data quality checks
   ↓
Run inactive/canceled status checks
   ↓
Run junk parcel filter
   ↓
Run spread scorer
   ↓
Check ambiguity triggers
   ↓
If ambiguous and budget allows: call LLM router
   ↓


Validate model JSON
  ↓
Write triage_results
  ↓
Write agent_runs
  ↓
Write cost_events
```

### Export Data Flow

```text
GET /api/batches/{batch_id}/export.xlsx
  ↓
Fetch batch + records + triage + evidence
  ↓
Generate Excel workbook
  ↓
Store export artifact
  ↓
Return download URL/file stream
```

---

## 8. Database Schema

### auction_batches

```sql
create table auction_batches (
 id uuid primary key,
 county text not null,
 source text not null,
 status text not null,
 started_at timestamptz,
 completed_at timestamptz,
 records_found int not null default 0,
 records_valid int not null default 0,
 records_quarantined int not null default 0,
 records_rejected int not null default 0,
 records_watchlist int not null default 0,


  records_research_candidates int not null default 0,
  records_manual_review int not null default 0,
  llm_calls_used int not null default 0,
  estimated_cost_usd numeric not null default 0,
  error_message text,
  created_at timestamptz not null default now()
);
```

### auction_records

```sql
create table auction_records (
  id uuid primary key,
  batch_id uuid not null references auction_batches(id),
  county text not null,
  case_number text,
  parcel_id_raw text,
  parcel_id_normalized text,
  auction_date date,
  auction_status text,
  opening_bid_cents bigint,
  appraiser_assessment_cents bigint,
  detail_url text,
  notice_url text,
  tax_deed_record_url text,
  parse_confidence numeric not null default 0,
  missing_fields jsonb not null default '[]',
  parse_warnings jsonb not null default '[]',
  created_at timestamptz not null default now()
);
```

### source_snapshots

```sql
create table source_snapshots (
 id uuid primary key,
 auction_record_id uuid references auction_records(id),
 batch_id uuid references auction_batches(id),
 source_url text not null,
 html_path text,


  screenshot_path text,
  content_hash text not null,
  parser_version text not null,
  scraped_at timestamptz not null,
  created_at timestamptz not null default now()
);
```

### triage_results

```sql
create table triage_results (
  id uuid primary key,
  auction_record_id uuid not null references auction_records(id),
  tier_1_status text not null,
  grade text not null,
  estimated_spread_cents bigint,
  opening_bid_ratio numeric,
  data_quality_score numeric not null,
  risk_flags jsonb not null default '[]',
  positive_signals jsonb not null default '[]',
  evidence jsonb not null default '[]',
  recommended_next_action text not null,
  requires_human_review boolean not null default false,
  llm_calls_used int not null default 0,
  estimated_cost_usd numeric not null default 0,
  created_at timestamptz not null default now()
);
```

### agent_runs

```sql
create table agent_runs (
 id uuid primary key,
 batch_id uuid references auction_batches(id),
 auction_record_id uuid references auction_records(id),
 agent_name text not null,
 status text not null,
 input_json jsonb not null,
 output_json jsonb,
 error_message text,


  provider text,
  model_name text,
  input_tokens int not null default 0,
  output_tokens int not null default 0,
  estimated_cost_usd numeric not null default 0,
  started_at timestamptz not null,
  completed_at timestamptz
);
```

### cost_events

```sql
create table cost_events (
  id uuid primary key,
  batch_id uuid references auction_batches(id),
  auction_record_id uuid references auction_records(id),
  service text not null,
  event_type text not null,
  unit_count numeric not null,
  estimated_cost_usd numeric not null default 0,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);
```

---

## 9. API Design

### Batch Endpoints

```text
POST /api/batches/sarasota/import
GET /api/batches
GET /api/batches/{batch_id}
GET /api/batches/{batch_id}/records
POST /api/batches/{batch_id}/triage
GET /api/batches/{batch_id}/export.xlsx
GET /api/batches/{batch_id}/export.csv
```


### Record Endpoints

```text
GET /api/records/{record_id}
GET /api/records/{record_id}/evidence
GET /api/records/{record_id}/agent-runs
```

### Job/System Endpoints

```text
GET /api/jobs/{job_id}
GET /health
GET /api/system/costs
GET /api/system/config
```

---

## 10. Local Development Architecture

Use Docker Compose:

```text
frontend
backend
postgres
redis or lightweight job queue
scraper-worker
local-storage volume
```

Local storage should mimic Blob Storage via a storage interface, not direct path
assumptions scattered across the app.

---

## 11. Deployment Architecture

Azure deployment target:

```text


GitHub Actions
  ↓
Build Docker images
  ↓
Push to Azure Container Registry
  ↓
Deploy backend to Azure Container Apps
  ↓
Deploy scraper as Azure Container Apps Job
  ↓
Use Azure Blob Storage for snapshots/exports
  ↓
Use Azure Database for PostgreSQL or POC Postgres service
```

MVP may use a simpler POC deployment if needed, but the repo should still be
structured for the target architecture.

---

## 12. Observability

Use structured JSON logs.

Required events:

```text
batch_created
scrape_started
page_loaded
page_failed
snapshot_saved
record_parsed
record_quarantined
triage_started
rule_triggered
llm_call_started
llm_call_failed
llm_output_invalid
triage_completed
export_created
batch_completed


```

Example log:

```json
{
  "event": "record_triaged",
  "batch_id": "uuid",
  "record_id": "uuid",
  "parcel_id": "0997-XX-XXXX",
  "status": "RESEARCH_CANDIDATE",
  "grade": "B",
  "provider": "github_models",
  "llm_calls_used": 1,
  "estimated_cost_usd": 0.0
}
```

---

## 13. Security

MVP security requirements:

- No secrets in repo.
- Use `.env.example` only.
- Use Azure Key Vault later for deployed secrets.
- Do not log LLM credentials.
- Do not log browser/session credentials.
- Do not build CAPTCHA bypass.
- Do not build anti-bot evasion.
- Protect deployed dashboard with basic auth, invite-only auth, or network restriction.
- Keep source snapshots private by default.

---

## 14. Source Notes

- Azure for Students: https://azure.microsoft.com/en-us/free/students
- Azure OpenAI / Microsoft Foundry OpenAI reference: https://learn.microsoft.com/en-us/azure/foundry/openai/reference
- GitHub Models billing/free prototyping notes: https://docs.github.com/billing/managing-billing-for-your-products/about-billing-for-github-models
- GitHub Models prototyping docs: https://docs.github.com/github-models/prototyping-with-ai-models
- Microsoft Graph Excel overview: https://learn.microsoft.com/en-us/graph/excel-concept-overview
- Microsoft Graph OneDrive/files overview: https://learn.microsoft.com/en-us/graph/onedrive-concept-overview
