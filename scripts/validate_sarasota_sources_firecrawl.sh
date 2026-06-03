#!/usr/bin/env bash
# Ethical source validation via Firecrawl CLI (see fixtures/sarasota/SOURCE_VALIDATION.md).
# Requires: firecrawl-cli and FIRECRAWL_API_KEY or `firecrawl login --browser`.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${ROOT}/.firecrawl/sarasota-validation"
mkdir -p "${OUT}"

if ! command -v firecrawl >/dev/null 2>&1; then
  echo "firecrawl CLI not found. Install: npm install -g firecrawl-cli" >&2
  exit 1
fi

if ! firecrawl --version --auth-status 2>&1 | grep -q 'authenticated: true'; then
  if [[ -z "${FIRECRAWL_API_KEY:-}" ]]; then
    echo "Not authenticated. Run: firecrawl login --browser" >&2
    echo "Or set FIRECRAWL_API_KEY in .env and export it." >&2
    exit 1
  fi
fi

CLERK_URL="https://www.sarasotaclerk.com/Home-and-Property/Tax-Deeds/Tax-Deed-Auctions"
REALTAXDEED_URL="https://www.sarasota.realtaxdeed.com/"
WAIT_MS="${FIRECRAWL_WAIT_MS:-5000}"

echo "Scraping clerk landing -> ${OUT}/clerk-tax-deed-auctions.md"
firecrawl scrape "${CLERK_URL}" \
  --wait-for "${WAIT_MS}" \
  --format markdown,links,html \
  --json \
  -o "${OUT}/clerk-tax-deed-auctions.json"

echo "Scraping RealTaxDeed -> ${OUT}/realtaxdeed-home.md"
firecrawl scrape "${REALTAXDEED_URL}" \
  --wait-for "${WAIT_MS}" \
  --format markdown,links,html \
  --json \
  -o "${OUT}/realtaxdeed-home.json"

echo "Done. Review ${OUT}/ and redact before copying HTML into fixtures/sarasota/html/."
