# Sarasota Tax Deed Source Validation

**Validated:** 2026-06-03 (DeedScout takeover branch)  
**Validator:** Autonomous agent (cloud environment) + public clerk/platform documentation  
**Parser target (MVP):** `https://www.sarasota.realtaxdeed.com/` (Grant Street / RealTaxDeed platform)

---

## 1. Validation checklist (docs/04 §7)

| # | Check | Result |
|---|--------|--------|
| 1 | Load clerk marketing URL | **Blocked (HTTP 403)** from cloud agent IP; page is informational only (see §2) |
| 2 | List-view fields: case, parcel, opening bid, date, status | **On auction platform**, not on clerk marketing page (see §3) |
| 3 | Property Appraiser assessment on clerk page | **No** — clerk landing page has calendar links and disclaimers, not parcel rows |
| 4 | Assessment requires second site? | **Partially** — foreclosure FAQ states the *online auction platform* exposes appraiser assessment; separate Sarasota Property Appraiser portal may still be needed for depth |
| 5 | Fixture HTML captured before parser work | **Yes** — synthetic fixtures under `fixtures/sarasota/html/` (§5) |

### Live fetch log (this environment)

All requests used user-agent `DeedScout research prototype`, single attempt, no retries beyond client default, no CAPTCHA bypass.

| URL | HTTP | Notes |
|-----|------|--------|
| `https://www.sarasotaclerk.com/robots.txt` | 403 | Akamai “Access Denied” |
| `https://www.sarasotaclerk.com/Home-and-Property/Tax-Deeds/Tax-Deed-Auctions` | 403 | Marketing / calendar entry point |
| `https://www.sarasotaclerk.com/e-services/online-property-auctions/property-auction-faqs` | 403 | Platform FAQs |
| `https://www.sarasota.realtaxdeed.com/` | 403 | **Primary scrape target** |
| `https://www.sarasota.realforeclose.com/` | 403 | Foreclosure sibling platform (out of MVP scope) |

**Action for developers:** Re-run validation on a residential or office network with `python -m app.cli scrape-sarasota --url https://www.sarasota.realtaxdeed.com/ --headful --max-pages 3` and replace fixtures with redacted live HTML when access succeeds. If the platform returns CAPTCHA or login, **stop** and record a `scraper_failures` row; do not evade controls.

### Firecrawl MCP and CLI (2026-06-03 retry)

| Channel | Status | Notes |
|---------|--------|--------|
| **Firecrawl MCP** | **Not available** in Cursor cloud agent | MCP catalog lists Azure and Firebase only; no Firecrawl server is registered |
| **Firecrawl CLI** | Installed (`firecrawl` v1.19.0) | `authenticated: false`; no `FIRECRAWL_API_KEY` in environment |
| **CLI scrape attempt** | **Blocked at login** | Interactive prompt; cannot complete browser login in unattended cloud |

**Recommended path (local or Cursor with API key):**

1. Enable Firecrawl in Cursor: Settings → MCP → add Firecrawl server, or set `FIRECRAWL_API_KEY` from [firecrawl.dev](https://firecrawl.dev).
2. Authenticate CLI: `firecrawl login --browser` or `firecrawl login --api-key "$FIRECRAWL_API_KEY"`.
3. Run repo script (writes to `.firecrawl/`, gitignored):

```bash
export FIRECRAWL_API_KEY=fc-...
./scripts/validate_sarasota_sources_firecrawl.sh
```

4. Redact any PII, then copy `rawHtml` from JSON output into `fixtures/sarasota/html/` only if safe to commit.

**Firecrawl CLI equivalents (manual):**

```bash
firecrawl scrape "https://www.sarasota.realtaxdeed.com/" --wait-for 5000 --format markdown,html --json -o .firecrawl/realtaxdeed-home.json
firecrawl scrape "https://www.sarasotaclerk.com/Home-and-Property/Tax-Deeds/Tax-Deed-Auctions" --wait-for 5000 --format markdown,html --json -o .firecrawl/clerk-tax-deed-auctions.json
```

Do not use Firecrawl browser mode on sites with heavy bot detection unless scrape succeeds; prefer `--wait-for` on the RealTaxDeed calendar page first.


---

## 2. Clerk marketing page vs auction platform

The URL in early docs (`…/Tax-Deed-Auctions`) is the **clerk’s public information page**. Public content (via search/index summaries) includes:

- Online auctions Mon–Fri from 9:00 AM ET
- Links to auction calendar and training FAQs
- Buyer-beware / as-is disclaimers
- **No embedded parcel table** suitable for direct parsing

**Canonical auction data** for bidding is hosted on the vendor platform:

- **Tax deed:** `https://www.sarasota.realtaxdeed.com/` (also cited in recorded notices as `www.Sarasota.RealTaxDeed.com`)
- **Foreclosure (out of scope):** `https://www.sarasota.realforeclose.com/`

Official notices reference fields such as **Tax Deed File #** (e.g. `2025 TD 000346`), legal description, assessed owner names, and sale time on RealTaxDeed.

---

## 3. Expected fields on RealTaxDeed (cross-county platform pattern)

Florida clerks using the same vendor family (e.g. Pinellas on `realforeclose.com` / RealTaxDeed) expose an **auction calendar → date → property list** flow. Documented list columns include:

| Field | Expected on platform | MVP parser |
|-------|----------------------|------------|
| Case / tax deed file number | Yes | Yes (`case_number`) |
| Certificate number | Often | Future (not in v1 schema) |
| Parcel ID | Yes | Yes |
| Property address / legal description | Often | Future (junk / ambiguity signals) |
| Opening bid | Yes | Yes |
| Assessed value / appraiser assessment | Yes (list or detail) | Yes (`appraiser_assessment`) |
| Auction date | Yes (calendar context) | Yes |
| Auction status | Yes (scheduled, active, redeemed, canceled, etc.) | Yes |
| Detail URL | Per-row link | Yes (from `href` or row link) |

Sarasota Clerk **Foreclosure Auction FAQs** (same vendor ecosystem) state the online site provides “property information” and the **Property Appraiser’s assessment** alongside calendar data—supporting spread triage when the field is present on the auction UI.

---

## 4. Assessment strategy decision (Option A / B / C)

| Option | Description | Decision |
|--------|-------------|----------|
| **A** | Scrape clerk + Property Appraiser | **Deferred** — second site adds failure modes; not required if platform shows assessed value |
| **B** | Drop assessment from spread rules | **Fallback** — when `appraiser_assessment_cents` is missing, Tier 1 already routes to `MANUAL_REVIEW` (`NO_APPRAISER_ASSESSMENT`) |
| **C** | Full spread when assessment on source page | **Primary** — use opening bid + assessed value from RealTaxDeed when parsed |

**Chosen approach:** **Option C with Option B fallback** — parse `Assessed Value` / `Appraiser Assessment` from RealTaxDeed HTML; never invent assessment; quarantine or manual-review when missing.

Homestead opening-bid rules (half assessed value in statutory bid) are a **data-quality warning**, not a separate scrape for MVP.

---

## 5. Fixture inventory (committed)

| File | Role |
|------|------|
| `html/sample_auction_detail.html` | Generic table layout (bootstrap parser tests) |
| `html/clerk_tax_deed_auctions_landing.html` | Clerk-style landing **without** parcel grid — documents negative case |
| `html/realtaxdeed_property_detail.html` | RealTaxDeed-style **detail** labels for Task 2 parser alignment |
| `html/realtaxdeed_auction_list.html` | RealTaxDeed-style **list row** snippet — structure reference for future list parser |

Fixtures are **synthetic** and labeled as non-live content. They mirror public field names from clerk notices and cross-county RealTaxDeed guides until live HTML is captured.

---

## 6. Scraper configuration implications

- Default import URL for Sarasota should be **`https://www.sarasota.realtaxdeed.com/`** (calendar or sale list), not the clerk marketing page.
- Expect **JavaScript-rendered** pages; Playwright is required for live scrape.
- On HTTP 403 / Akamai block: set batch status `blocked`, write `scraper_failures`, surface manual review in dashboard.
- Store `page_structure_hash` on snapshots to detect vendor DOM changes.

---

## 7. References

- [Sarasota Clerk — Tax Deed Auctions](https://www.sarasotaclerk.com/Home-and-Property/Tax-Deeds/Tax-Deed-Auctions)
- [Sarasota Clerk — Online property auction FAQs](https://www.sarasotaclerk.com/e-services/online-property-auctions/property-auction-faqs)
- [Sarasota Clerk — Foreclosure auction FAQs (platform fields)](https://www.sarasotaclerk.com/Home-and-Property/Foreclosures/Foreclosure-Auctions/Foreclosure-Auction-FAQs)
- Sarasota RealTaxDeed: `https://www.sarasota.realtaxdeed.com/`
- Cross-county list column pattern: [Pinellas tax deed guide (RealForeclose/RealTaxDeed)](https://www.countypull.com/resources/fl/pinellas-county/tax-deed)

---

## 8. Sign-off for Task 2

- [x] Primary scrape target identified (RealTaxDeed, not clerk landing)
- [x] Assessment strategy documented (C + B fallback)
- [x] Fixture HTML available for parser work without live network
- [x] Parser fixtures for RealTaxDeed list + detail (`auction_list_parser`, golden `expected/*.json`)
- [ ] Live HTML capture via Firecrawl or Playwright (pending — cloud agent 403 + Firecrawl unauthenticated)
