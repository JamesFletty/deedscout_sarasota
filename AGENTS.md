# DeedScout Sarasota Agent Instructions

## 1. Project purpose
DeedScout Sarasota is a scraper-first, agent-assisted due-diligence triage MVP for Sarasota County tax deed auction records. The product ingests Sarasota auction/property source pages, preserves raw evidence, normalizes parcel-level records, applies deterministic triage rules, and produces Excel-compatible review reports for human analysts.

DeedScout must help organize public-record research. It must never provide legal, investment, title, appraisal, zoning, surveying, environmental, or bidding advice, and user-facing text must clearly frame outputs as research triage requiring qualified human review.

## 2. Architecture principles
- Build production-shaped MVP components, not throwaway prototypes.
- Keep the workflow scraper-first: source acquisition, evidence preservation, parsing, normalization, deterministic triage, optional LLM review, export.
- Run deterministic validation and triage rules before any LLM call.
- Treat LLM output as non-authoritative enrichment; persist model inputs, outputs, costs, and review status.
- Keep backend services modular under `apps/api/app/` and isolate API, scraping, parsing, storage, database, triage/service, worker, and LLM-provider concerns.
- Prefer local development defaults that work without cloud credentials; Azure is the primary deployment target.
- Design adapters for replaceable infrastructure: storage, LLM providers, scraping workers, and exports.
- Do not invent features beyond the MVP scope without explicit user direction.

## 3. Coding standards
- Python backend code must be typed, linted with Ruff, checked with mypy where configured, and covered by pytest for new behavior.
- FastAPI routes must be thin and delegate business logic to services or adapters.
- Pydantic models/settings must validate configuration at process boundaries.
- Database models and migrations must stay synchronized; schema changes require Alembic migrations and tests.
- TypeScript frontend code must use strict TypeScript conventions and small composable components.
- Avoid global mutable state except for well-defined application singletons such as settings factories.
- Never wrap imports in `try`/`catch` or broad import fallbacks.
- Do not add vague comments, dead code, or unused abstractions.

## 4. Testing requirements
- Every functional change must include or update tests at the appropriate layer.
- Backend changes require `pytest`; lint with `ruff check`; run `mypy` when configured.
- Storage, parsing, normalization, deterministic triage, LLM routing, and database persistence need unit tests before use in higher-level workflows.
- Tests must not call external LLM APIs, live auction sites, Azure services, GitHub Models, or Ollama unless explicitly marked integration and disabled by default.
- Scraper/parser tests should use fixtures under `fixtures/sarasota/` and saved evidence, not live network pages.
- Health checks must remain fast and deterministic.

## 5. LLM-provider abstraction requirements
- All model access must go through `apps/api/app/llm/` provider interfaces and router logic.
- Supported provider names are `mock`, `azure_openai`, `azure_foundry`, `github_models`, and `ollama`.
- The mock provider must be deterministic and sufficient for local tests.
- External providers must fail explicitly with clear configuration errors when required credentials or endpoints are missing.
- Do not hardcode provider secrets, deployment names, API keys, or model-specific assumptions.
- Enforce configurable limits such as max calls per batch, max input characters, JSON-required mode, timeout, and retry count.
- If LLM access is unavailable or an input exceeds configured limits, route records to human/manual review rather than blocking deterministic processing.

## 6. Scraping boundaries
- Respect robots.txt, website terms, rate limits, and normal public access boundaries.
- Do not bypass CAPTCHAs, login gates, paywalls, IP blocks, bot protections, or anti-automation mechanisms.
- Do not implement stealth automation, proxy rotation for evasion, user-agent deception, or CAPTCHA-solving services.
- Prefer stable public pages, official downloads, and reproducible fixture-based parsing.
- Scrapers must use configurable headless mode, page limits, retry counts, screenshot mode, delays, and timeouts.
- Before writing parser code for a Sarasota source, validate the live source structure, capture fixture HTML, and document whether assessment values are present or require manual lookup.
- Preserve source URLs and timestamps for every captured artifact.
- Failed page fetches after bounded retries must be stored in `scraper_failures` for post-run review; do not hide them in logs only.

## 7. Data/evidence preservation rules
- Save raw HTML and screenshots before parsing when scraping source pages.
- Store deterministic content hashes for artifacts and database source snapshots.
- Parsed/normalized records must link back to source evidence wherever possible.
- Do not overwrite raw evidence; create new artifacts for new scrape runs.
- Keep parser versions in source snapshot metadata so parsing can be replayed.
- Store `page_structure_hash` for source snapshots when scraper code captures live pages so DOM drift can be detected.
- Generated local artifacts belong under the configured local storage root, defaulting to `./.storage`, and must not be committed.

## 8. Security rules
- Never commit secrets, API keys, passwords, cookies, tokens, private certificates, or downloaded confidential records.
- Use `.env.example` for documented variables and safe defaults only.
- Validate and constrain file paths for local storage to prevent path traversal.
- Treat scraped HTML as untrusted input; avoid rendering it directly in the frontend.
- Log structured operational metadata, not secrets or full sensitive payloads.
- Keep dependency additions minimal and justified for MVP requirements.

## 9. No-placeholder rule
- Do not add vague TODOs, pass-only stubs, fake implementations, or comments that promise future work without behavior.
- Minimal implementations are allowed only when they are executable, tested, and fail clearly if a non-implemented external capability is requested.
- Empty directories may contain `.gitkeep` only when required to preserve the intended repo layout.

## 10. Required validation before finishing a task
Before finishing a code task, review `docs/01_project_summary.md`, `docs/02_mvp_prd.md`, `docs/03_architecture_and_stack.md`, and `docs/04_implementation_and_build.md` for applicable constraints, then run the most relevant validation commands and report exact results. For backend changes, run `pytest`, `ruff check`, and `mypy` if configured. For frontend changes, run the package manager lint/type checks or explain any environment limitation. For database changes, verify migrations apply cleanly. For storage changes, verify artifacts are hash-stable and written to ignored paths. For LLM-provider changes, verify mock routing and explicit provider configuration failures without network calls.
