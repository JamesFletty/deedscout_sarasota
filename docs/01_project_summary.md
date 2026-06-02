# DeedScout Sarasota — Project Summary

Version: 0.2
POC County: Sarasota County, Florida
Project Type: Scraper-first, agent-driven tax deed auction triage platform
Primary Goal: Portfolio-grade MVP with real product potential
Primary Deployment Target: Azure using student credits
LLM Plan: Provider-agnostic router using Azure OpenAI / Microsoft Foundry Models
first, GitHub Models fallback, local/mock fallback

---

## 1. Executive Summary

DeedScout Sarasota is a proof-of-concept platform that automatically imports Sarasota
County tax deed auction records, preserves source evidence, normalizes parcel-level
data, filters obvious junk properties, scores opening-bid-to-assessment spread, and
presents investor-facing triage results in a dashboard.

The product is not a title opinion, valuation engine, or bidding recommendation system.
It is a due-diligence triage tool designed to reduce the manual burden of reviewing raw
county auction records before an investor spends time or money on deeper research.

The MVP starts with scraping because manual collection is part of the actual user pain.
The system should not require hand-entered auction data to prove the core workflow.
Sarasota is used as the controlled POC county because the county’s tax deed workflow
makes the investor due-diligence burden explicit: auctions are online, properties are
sold as-is, bidders must do their own due diligence, and the auction property list
exposes key fields such as parcel ID, opening bid, Property Appraiser assessment, and
tax deed record access.

---

## 2. Product Thesis

Tax deed auction systems are built primarily for county execution, not investor due
diligence. They publish raw auction records and parcel identifiers, but they do not
answer the investor’s first practical question:

> Which parcels are obvious rejects, which deserve a watchlist, and which are worth
deeper research?


DeedScout turns that raw workflow into a structured screening pipeline:

1. Scrape Sarasota auction listings and parcel detail pages.
2. Store raw HTML, screenshots, timestamps, hashes, and parser versions.
3. Normalize parcel, case, status, opening bid, assessment, and source-link fields.
4. Quarantine unreliable records.
5. Apply deterministic junk and spread filters before any model call.
6. Route only ambiguous records to a low-cost LLM provider.
7. Produce conservative statuses: Rejected, Watchlist, Research Candidate, Manual
Review, Quarantined, or Canceled/Inactive.
8. Show the user a distilled grade and red-flag summary, with expandable evidence for
verification.

The project’s technical credibility comes from the fact that it does not treat “AI agents”
as magic. Most agents are deterministic workers. LLM agents are reserved for
ambiguity classification and evidence summarization.

---

## 3. Target User

Initial target user:

- Florida tax deed investor
- Land investor
- Wholesaler
- Small real estate fund operator
- Auction researcher
- Solo investor who reviews many parcels without a dedicated analyst

They currently work across:

- County tax deed auction portals
- Clerk records
- Property Appraiser sites
- Official Records
- GIS maps
- Flood-zone tools
- Google Maps / Street View
- Spreadsheets
- Notes, screenshots, and browser tabs


---

## 4. Core Pain

The user has to manually collect and reconcile fragmented public-record data before
deciding whether a parcel deserves real due diligence.

Common manual tasks:

- Open auction calendar.
- Review each property page.
- Copy parcel IDs.
- Check opening bid.
- Compare bid against appraiser assessment.
- Identify canceled, postponed, or inactive auctions.
- Detect obvious junk parcels.
- Save links and screenshots.
- Track red flags.
- Decide which records deserve deeper title, zoning, GIS, or valuation research.

The expensive failure mode is not just wasted time. The expensive failure mode is
bidding on a parcel that appears cheap but is functionally unusable, overvalued,
encumbered, inaccessible, non-buildable, or too risky to justify cleanup.

---

## 5. MVP Promise

The MVP promise is:

> Import a Sarasota tax deed auction batch and receive a graded dashboard showing
which parcels are obvious rejects, which are watchlist items, which require manual
review, and which deserve deeper due diligence — with every decision backed by
source evidence.

The MVP does not promise:

- Guaranteed deals
- Investment recommendations
- Automated bidding
- Legal title conclusions
- Lien-free status


- Appraisal-grade valuation
- Full Florida statewide coverage

---

## 6. Why Sarasota First

Sarasota is the proof-of-concept county, not the final business scope.

Sarasota is useful because:

- It has an online tax deed auction workflow.
- Its public-facing materials emphasize bidder due diligence and as-is sale risk.
- Its auction/property workflow exposes the fields needed for a first triage layer: parcel
ID, opening bid, Property Appraiser assessment, Notice of Application for Tax Deed,
and tax deed record access for registered users.
- The county is narrow enough to control scraping, parsing, and UI scope.
- The workflow is complex enough to prove a real automation point.

Sarasota is too small to be the final SaaS market by itself. Its role is to prove the
ingestion, triage, evidence, and agentic orchestration model before expanding to
nearby Florida counties.

---

## 7. Product Boundary

### The product is:

- Due-diligence triage
- Public-record workflow automation
- Parcel prioritization
- Evidence preservation
- Conservative risk flagging
- Cost-gated model routing
- Dashboard and spreadsheet export

### The product is not:

- Legal advice
- Title insurance
- Appraisal


- Surveying
- Zoning determination
- Environmental due diligence
- Tax advice
- Financial advice
- Automated bidding
- Anti-bot evasion

Required product language:

> This system provides public-record triage and workflow automation. It does not
provide legal, investment, title, appraisal, zoning, surveying, environmental, or tax
advice. Parcel grades indicate research priority only and are not recommendations to
bid or purchase.

---

## 8. High-Level System Concept

User clicks “Import Sarasota Auction Batch.”

The system:

1. Creates an auction batch record.
2. Runs a Playwright scraper against Sarasota auction pages.
3. Captures raw HTML and screenshots.
4. Saves evidence to object storage.
5. Parses and normalizes fields.
6. Quarantines unreliable records.
7. Runs deterministic filters.
8. Computes spread and data-quality scores.
9. Routes ambiguous records to an LLM provider through a provider-agnostic router.
10. Produces parcel statuses and grades.
11. Displays parcel cards with evidence drawers.
12. Exports a Microsoft 365-compatible Excel workbook.

---

## 9. Current Cloud / Tooling Plan

### Primary Cloud


Azure is the primary deployment target because the user has student credits. Azure
should host:

- FastAPI backend
- Scraper worker container
- Postgres database
- Blob storage for evidence snapshots
- Scheduled import jobs
- Logs and monitoring
- Budget/cost controls

### LLM Provider Strategy

The app must not depend on a normal OpenAI API key.

Instead, all model calls go through an internal `LLMProvider` interface.

Provider priority:

1. Mock provider for tests and offline pipeline development.
2. GitHub Models for fast prototyping if Azure model access is delayed.
3. Azure OpenAI / Microsoft Foundry Models as preferred cloud provider.
4. Ollama/local model fallback for offline classification experiments.
5. Future direct OpenAI provider only if available.

The triage pipeline must keep working without live model access. If no model provider
is available, ambiguous records route to `MANUAL_REVIEW` instead of blocking the
batch.

### Microsoft 365

Microsoft 365 should be used as a product feature, not just a free perk.

MVP export:

- Generate `.xlsx` locally/server-side.
- User downloads the workbook.

Future export:

- Save workbook to OneDrive or SharePoint through Microsoft Graph.
- Optionally email reports through Outlook integration.


### Google Developer Tools

Google Cloud is optional and secondary. It should not be part of the critical path unless
used for:

- Cloud Run deployment comparison
- Storage adapter proof
- Student training/certification labs
- Secondary portability demo

---

## 10. MVP Deliverable

The MVP is complete when a user can:

1. Open the deployed dashboard.
2. Trigger a Sarasota auction batch import.
3. See imported and normalized parcel records.
4. Inspect scrape evidence.
5. Run Tier 1 triage.
6. View Reject / Watchlist / Research Candidate / Manual Review outputs.
7. Open parcel evidence drawers.
8. Export an Excel-compatible report.

The MVP is not complete if:

- It relies only on manually entered records.
- It cannot preserve source evidence.
- It cannot explain classifications.
- It calls LLMs for every parcel.
- It needs a paid real estate API to function.
- It gives buy/sell recommendations.
- It cannot be replayed from saved HTML fixtures.
- It only runs on the developer’s machine.

---

## 11. Portfolio Positioning

Public portfolio framing:


> DeedScout is a scraper-first, agent-driven due-diligence triage platform for Sarasota
County tax deed auctions. It imports live auction records, stores source evidence,
normalizes parcel data, applies deterministic risk filters, routes ambiguous records to a
provider-agnostic LLM classifier, and produces conservative investor-facing grades
with expandable audit trails.

The strongest technical claims:

- Scraper-first ingestion solves the actual manual collection problem.
- Raw evidence snapshots make the parser auditable and replayable.
- Deterministic rules avoid wasting model calls.
- LLM providers are swappable, so the MVP is not blocked by a single API key.
- Ambiguous records degrade to manual review instead of hallucinated certainty.
- Microsoft 365 export matches how real investors operate.

---

## 12. Source Notes

Relevant public references used while shaping the plan:

- Sarasota Clerk Tax Deed Auctions: https://www.sarasotaclerk.com/Home-and-Property/Tax-Deeds/Tax-Deed-Auctions
- Sarasota Tax Deed Auction FAQ: https://www.sarasotaclerk.com/Home-and-Property/Tax-Deeds/Tax-Deed-Auctions/Tax-Deed-Auction-FAQs
- Azure for Students: https://azure.microsoft.com/en-us/free/students
- Azure OpenAI / Microsoft Foundry OpenAI reference: https://learn.microsoft.com/en-us/azure/foundry/openai/reference
- GitHub Models billing/free prototyping notes: https://docs.github.com/billing/managing-billing-for-your-products/about-billing-for-github-models
- GitHub Models prototyping docs: https://docs.github.com/github-models/prototyping-with-ai-models
- Microsoft Graph Excel overview: https://learn.microsoft.com/en-us/graph/excel-concept-overview
- Microsoft Graph OneDrive/files overview: https://learn.microsoft.com/en-us/graph/onedrive-concept-overview
