# DeedScout Sarasota

DeedScout Sarasota is a production-shaped MVP foundation for scraper-first Sarasota County tax deed auction triage. The system is structured to capture raw source evidence, normalize parcel records, run deterministic triage before any LLM usage, route model calls through provider-agnostic adapters, and support Excel-compatible exports in a later milestone.

## Planning documents

The current product and build constraints live in:

- `docs/01_project_summary.md`
- `docs/02_mvp_prd.md`
- `docs/03_architecture_and_stack.md`
- `docs/04_implementation_and_build.md`

Future implementation work should review these documents before changing architecture, scraper behavior, triage rules, exports, or provider integrations.

## Repository layout

```text
apps/web                  Next.js, TypeScript, Tailwind dashboard shell
apps/api                  FastAPI backend and Python worker foundation
fixtures/sarasota         HTML, screenshot, and expected parser fixtures
infra/docker-compose.yml  Local Postgres and API services
docs                      Project documentation
```

## Local backend setup

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check
mypy app tests
uvicorn app.main:app --reload
```

The backend exposes `GET /health`, returning application environment and database reachability.

## Local frontend setup

```bash
cd apps/web
npm install
npm run dev
```

Open `http://localhost:3000` to view the minimal dashboard shell.

## Cursor Cloud Agent setup

For a fresh Cursor Cloud Agent environment, run the bootstrap script from the
repository root:

```bash
bash scripts/setup_cloud_agent.sh
```

The script installs Python 3.12 venv support when needed, creates
`apps/api/.venv`, installs the backend in editable dev mode, installs
Playwright Chromium support for screenshot capture, installs frontend
dependencies with `npm ci`, and verifies that a headless screenshot can be
captured.

## Docker Compose

```bash
docker compose -f infra/docker-compose.yml up --build
```

Compose starts Postgres and the FastAPI backend on `http://localhost:8000`.

## Configuration

Copy `.env.example` to `.env` for local development. Defaults use local storage and the deterministic mock LLM provider, so no external API keys are required for tests.

Generated local evidence artifacts are written under the configured `LOCAL_STORAGE_ROOT`, which defaults to `./.storage` in `.env.example`.

## Ethical Scraping & Anti-Bot Policy

DeedScout respects county website terms of service. The scraper uses standard browser requests with configurable page limits, bounded retries, screenshots, delays, and timeouts. It does not bypass CAPTCHA, use headless-detection evasion, rotate residential proxies, or otherwise evade anti-bot controls. If a county site blocks access, the system must stop gracefully, preserve any available failure evidence, and route affected records to manual review.

## Safety scope

DeedScout organizes public-record due-diligence research. It does not provide legal, investment, title, appraisal, zoning, surveying, environmental, or bidding advice.
