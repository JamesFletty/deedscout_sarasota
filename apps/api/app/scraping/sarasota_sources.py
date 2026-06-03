"""Canonical Sarasota public auction URLs (see fixtures/sarasota/SOURCE_VALIDATION.md)."""

from __future__ import annotations

SARASOTA_COUNTY = "sarasota"

# Clerk informational page (no parcel grid — discovery may redirect operators to RealTaxDeed).
SARASOTA_CLERK_TAX_DEED_AUCTIONS_URL = (
    "https://www.sarasotaclerk.com/Home-and-Property/Tax-Deeds/Tax-Deed-Auctions"
)

# Grant Street RealTaxDeed platform — primary MVP scrape target for parcel rows.
SARASOTA_REALTAXDEED_URL = "https://www.sarasota.realtaxdeed.com/"
