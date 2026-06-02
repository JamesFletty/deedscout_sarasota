# DeedScout Sarasota — MVP PRD

Version: 0.2
Project Type: Scraper-first, agent-driven tax deed auction triage MVP
POC County: Sarasota County, Florida
Primary Deployment Target: Azure
LLM Strategy: Provider-agnostic Azure / GitHub Models / local / mock router

---

## 1. Product Overview

DeedScout Sarasota is an MVP platform that imports Sarasota tax deed auction
records, stores source evidence, normalizes property-level data, filters obvious bad
candidates, identifies records worth further review, and presents parcel-level triage
results in a dashboard.

The platform is designed as a portfolio-grade proof of concept. It should feel like a
serious vertical slice of a larger Florida tax deed underwriting platform, not a mockup or
generic AI wrapper.

---

## 2. Objective

Build a working MVP that proves the following:

1. Sarasota tax deed auction records can be imported automatically.
2. Raw source evidence can be preserved for audit/replay.
3. Auction records can be normalized into a stable schema.
4. Deterministic rules can reject obvious junk and low-spread parcels.
5. LLM calls can be minimized through cost-gated routing.
6. Ambiguous records can be classified through a provider-agnostic LLM interface.
7. The UI can present conservative investor-facing grades and red flags.
8. The system can export reports in an Excel-compatible format.
9. The app can run locally and deploy to Azure.

---

## 3. Scope

### In Scope


- Sarasota tax deed auction batch import
- Playwright scraper worker
- Raw HTML snapshot storage
- Screenshot storage
- Content hashes
- Parser version tracking
- Normalized auction record schema
- Data quality validation
- Quarantine workflow
- Deterministic junk parcel filters
- Opening-bid-to-assessment spread scoring
- Ambiguity classification through LLM provider router
- Mock LLM provider for tests
- GitHub Models provider fallback
- Azure OpenAI / Microsoft Foundry provider support
- Optional local Ollama provider
- Dashboard with batch and parcel views
- Evidence drawer
- Excel and CSV exports
- Cost/event ledger
- Azure deployment path

### Out of Scope

- Multi-county support
- Automated bidding
- Login credential management beyond local/manual configuration
- CAPTCHA bypass
- Anti-bot evasion
- Full official-records title-chain parser
- Attorney-grade surviving-lien conclusion
- Paid AVM integration
- ATTOM, PropStream, or RentCast integration
- GIS/flood-zone automation
- Billing/subscriptions
- Investor account/team management
- Power BI embedding
- Mobile app

---


## 4. Personas

### Primary Persona: Solo Tax Deed Investor

The solo investor reviews auction lists manually, often using county sites, property
appraiser records, maps, and spreadsheets. They need a faster way to reject obvious
bad parcels and focus on the small set worth deeper research.

### Secondary Persona: Wholesaler / Land Investor

The land investor screens many low-cost parcels and needs to avoid unusable lots,
weak spreads, vacant-land traps, missing address records, and parcels requiring too
much manual validation.

### Portfolio Reviewer Persona

The reviewer is an AI engineering or automation hiring manager. They need to see a
concrete system with scraping, data normalization, cloud deployment, cost controls,
and agentic routing — not a vague chatbot.

---

## 5. Core User Stories

### US-001 — Import Auction Batch

As a user, I want to click “Import Sarasota Auction Batch” so that the system
automatically collects current auction records instead of requiring manual entry.

Acceptance criteria:

- User can start an import from the dashboard.
- System creates an `auction_batch` record.
- System runs scraper job.
- System shows job status.
- System records success/failure counts.

### US-002 — Preserve Source Evidence

As a user, I want the system to save source HTML, screenshots, timestamps, and
content hashes so that each parsed result can be verified later.


Acceptance criteria:

- Each successfully loaded source page stores HTML.
- Detail pages store screenshots when screenshot mode is enabled.
- Each snapshot stores source URL, timestamp, content hash, and parser version.
- Parsed records link to their source snapshots.

### US-003 — Normalize Auction Records

As a user, I want scraped auction data normalized into consistent fields so that records
can be filtered, sorted, and graded.

Acceptance criteria:

- Extract case number where available.
- Extract parcel ID where available.
- Extract auction date where available.
- Extract auction status.
- Extract opening bid.
- Extract Property Appraiser assessment when visible.
- Extract relevant source/detail links.
- Normalize money to cents.
- Normalize parcel IDs.
- Assign parse confidence.
- Quarantine low-confidence records.

### US-004 — Run Tier 1 Triage

As a user, I want the system to classify records as rejected, watchlist, research
candidate, manual review, quarantined, or inactive.

Acceptance criteria:

- Deterministic filters run before LLM calls.
- Obvious inactive/canceled records are not promoted.
- Low-spread records are rejected.
- Missing critical fields route to quarantine or manual review.
- Each triage result includes evidence.
- Each triage result includes recommended next action.

### US-005 — Use LLM Only for Ambiguity


As a user, I want model calls used only where they add value, so the system remains
cheap and explainable.

Acceptance criteria:

- LLM is not called for records that deterministic rules can classify.
- LLM is called only for ambiguous records.
- LLM output is strict JSON.
- Invalid LLM output routes to manual review.
- Cost ledger records model usage.
- Batch-level model-call cap is enforced.
- If no provider is configured, ambiguous records route to manual review.

### US-006 — View Parcel Evidence

As a user, I want to open an evidence drawer for each parcel so that I can see why the
system assigned a status and grade.

Acceptance criteria:

- Drawer shows auction fields.
- Drawer shows source snapshot metadata.
- Drawer shows parser warnings.
- Drawer shows rule decisions.
- Drawer shows LLM classification if used.
- Drawer shows cost events related to the record.

### US-007 — Export Investor Report

As a user, I want to export a batch report to Excel/CSV so that I can work with the
results in Microsoft 365 or share them externally.

Acceptance criteria:

- `.xlsx` export includes all required tabs.
- CSV fallback is available.
- Export is downloadable.
- Export includes evidence index and cost ledger.
- Export does not imply legal/title certainty.

---


## 6. Functional Requirements

### 6.1 Import Flow

The dashboard must include a button:

```text
Import Sarasota Auction Batch
```

On click:

1. Backend creates an auction batch.
2. Scraper worker starts.
3. Batch status changes to `RUNNING`.
4. Scraper loads source pages.
5. Snapshots are stored.
6. Parsed records are saved.
7. Batch status changes to `SCRAPED`, `FAILED`, or `PARTIAL`.
8. User can run triage.

For MVP, triage can run automatically after scrape if import succeeds, but it should also
be manually rerunnable from the UI.

### 6.2 Scraper Requirements

The scraper must:

- Use Playwright.
- Run headless in deployment.
- Support visible/headful debug mode locally.
- Respect configurable rate delay.
- Use bounded retries.
- Stop gracefully when blocked.
- Store raw HTML before parsing.
- Store screenshot when enabled.
- Avoid CAPTCHA bypass.
- Avoid anti-bot evasion techniques.
- Support fixture replay from stored HTML.

### 6.3 Parser Requirements


The parser must:

- Extract fields deterministically.
- Track missing fields.
- Track parser warnings.
- Normalize money to integer cents.
- Normalize parcel IDs.
- Normalize status values.
- Assign parse confidence.
- Quarantine records below confidence threshold.

Parse confidence formula:

```text
+0.20 case number present
+0.20 parcel ID present
+0.20 opening bid parsed
+0.15 auction status parsed
+0.15 appraiser assessment parsed
+0.10 source/detail URL present
```

Minimum triage confidence:

```text
0.70
```

Below that, route to:

```text
QUARANTINED
```

### 6.4 Triage Statuses

Required statuses:

```text
REJECTED
WATCHLIST
RESEARCH_CANDIDATE


MANUAL_REVIEW
QUARANTINED
CANCELED_OR_INACTIVE
```

Definitions:

- `REJECTED`: The parcel failed deterministic rules or contains obvious non-investable
indicators.
- `WATCHLIST`: The parcel has some positive signal but insufficient confidence for
deeper research.
- `RESEARCH_CANDIDATE`: The parcel has enough basic spread and data quality to
justify further due diligence.
- `MANUAL_REVIEW`: The system cannot classify safely due to ambiguity or
conflicting data.
- `QUARANTINED`: The scraper/parser failed to produce a reliable normalized record.
- `CANCELED_OR_INACTIVE`: The auction appears canceled, postponed, redeemed,
closed, or otherwise inactive.

### 6.5 Grade Definitions

Grades must be conservative:

```text
A = Strong research candidate. Still requires due diligence.
B = Research candidate with unresolved issues.
C = Watchlist. Some signal, but not enough for escalation.
D = Likely not worth deeper research.
F = Reject.
U = Unknown / insufficient data.
```

Grades must never be described as buy/sell recommendations.

### 6.6 Deterministic Filters

Reject if:

- Auction status is canceled, redeemed, postponed, inactive, or unavailable.
- Parcel ID missing.
- Opening bid missing or unparsable.
- Appraiser assessment missing or zero and no alternate value basis exists.


- Opening bid exceeds appraiser assessment.
- Opening bid / appraiser assessment >= 0.90.
- Estimated spread < $10,000.
- Hard junk terms are detected with supporting conditions.

Watchlist if:

- Vacant land with moderate spread.
- Missing situs/property address.
- Ambiguous “TRACT” language.
- Weak value basis.
- Missing property-use fields.
- High spread but data quality below ideal threshold.

Research candidate if:

- Record is active/scheduled/running.
- Parcel ID is present.
- Opening bid is present.
- Appraiser assessment is present.
- Opening bid / assessment <= 0.65.
- Estimated spread >= $15,000.
- No hard junk indicator is detected.
- Data quality score >= 0.70.

### 6.7 Junk Signal Terms

Initial terms:

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

Rules:

- “RETENTION POND” and “LIFT STATION” should usually hard reject.
- “TRACT” alone should usually route to ambiguity review.
- “WETLAND” should not automatically hard reject without supporting evidence.
- Vacant land should not be rejected solely for being vacant.

### 6.8 LLM Provider Requirements

The MVP must not directly depend on `OPENAI_API_KEY`.

Required provider interface:

```text
LLM_PROVIDER=mock|github_models|azure_openai|azure_foundry|ollama|openai
```

Provider behavior:

- `mock`: deterministic fake responses for tests and demos.
- `github_models`: prototyping fallback using GitHub Models.
- `azure_openai`: preferred production provider when Azure OpenAI is available.
- `azure_foundry`: preferred Microsoft Foundry provider if using Foundry deployments.
- `ollama`: local fallback.
- `openai`: future optional adapter, not required for MVP.


Required degradation:

```text
If no provider is configured or the provider fails, ambiguous records route to
MANUAL_REVIEW.
```

### 6.9 LLM Ambiguity Classifier

Trigger conditions:

- Legal description/property type ambiguity.
- “TRACT” language without hard junk terms.
- Vacant land with high apparent spread.
- Missing use code but strong spread.
- Conflicting parser fields.

Required prompt behavior:

- Strict JSON only.
- No legal advice.
- No valuation inference.
- No bidding recommendation.
- No title-clearance claim.

Required output schema:

```json
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

### 6.10 Cost Controls


Hard caps:

```text
Max scraper jobs per day: 3
Max records per batch: 150
Max retries per page: 2
Max LLM calls per batch: 25
Max paid real estate API calls: 0
Max frontier model calls: 0 unless manually enabled
```

Track:

- LLM calls
- Input tokens
- Output tokens
- Provider name
- Model/deployment name
- Estimated cost
- Scraper runtime
- Pages fetched
- Pages failed
- Snapshots stored
- Export jobs

### 6.11 Dashboard Requirements

Dashboard must show:

- Recent batches
- Import button
- Batch status
- Records found
- Records validated
- Records quarantined
- Records rejected
- Watchlist count
- Research candidate count
- Manual review count
- LLM calls used
- Estimated cost
- Export button


### 6.12 Parcel Card Requirements

Parcel card must show:

- Parcel ID
- Case number
- Auction date
- Auction status
- Opening bid
- Appraiser assessment
- Estimated spread
- Bid/assessment ratio
- Status
- Grade
- Top risk flags
- Top positive signals
- Evidence drawer button

### 6.13 Evidence Drawer Requirements

Evidence drawer must show:

- Auction source URL
- Snapshot metadata
- HTML path
- Screenshot path
- Content hash
- Parser version
- Parsed fields
- Missing fields
- Parser warnings
- Rule decisions
- LLM decision if used
- Cost events
- Final recommended next action

### 6.14 Export Requirements

Excel workbook tabs:

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

Export constraints:

- Must include disclaimer.
- Must include generation timestamp.
- Must include source snapshot references.
- Must not imply legal/title certainty.

---

## 7. Non-Functional Requirements

### Reliability

- Failed page loads do not crash the batch.
- Partial batches are allowed and visible.
- Parser failures route to quarantine.
- LLM failures route to manual review.

### Replayability

- Saved HTML fixtures must be parseable without hitting live sources.
- Parser tests must use fixtures.
- Triage tests must use normalized records.

### Observability

Log:

- Batch lifecycle
- Scraper lifecycle
- Page fetch success/failure


- Parser confidence
- Missing fields
- Rule hits
- LLM provider calls
- Cost events
- Export generation

### Security

- No secrets in repo.
- Use environment variables or Azure Key Vault.
- No credential logging.
- No CAPTCHA bypass.
- No anti-bot evasion.
- Basic dashboard access protection in deployed MVP.

---

## 8. MVP Acceptance Criteria

The MVP passes when:

- User can deploy or run locally.
- User can trigger Sarasota import.
- Scraper captures source evidence.
- Parser creates normalized records.
- Bad records are quarantined.
- Triage runs without needing a live LLM provider.
- Mock LLM provider works in tests.
- GitHub Models or Azure provider can be configured without changing triage code.
- UI shows batch and parcel results.
- Evidence drawer works.
- Excel/CSV export works.
- Cost ledger records model calls and export/scraper events.
- README and portfolio case study explain the architecture.

---

## 9. Source Notes

- Sarasota Clerk Tax Deed Auctions: https://www.sarasotaclerk.com/Home-and-Property/Tax-Deeds/Tax-Deed-Auctions


- Sarasota Tax Deed Auction FAQ: https://www.sarasotaclerk.com/Home-and-Property/Tax-Deeds/Tax-Deed-Auctions/Tax-Deed-Auction-FAQs
- Azure for Students: https://azure.microsoft.com/en-us/free/students
- Azure OpenAI / Microsoft Foundry OpenAI reference: https://learn.microsoft.com/en-us/azure/foundry/openai/reference
- GitHub Models billing/free prototyping notes: https://docs.github.com/billing/managing-billing-for-your-products/about-billing-for-github-models
- GitHub Models prototyping docs: https://docs.github.com/github-models/prototyping-with-ai-models
- Microsoft Graph Excel overview: https://learn.microsoft.com/en-us/graph/excel-concept-overview
