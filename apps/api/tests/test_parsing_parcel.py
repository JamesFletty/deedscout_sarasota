import pytest

from app.parsing.parcel_parser import ParcelParseError, normalize_parcel_id


def test_normalize_parcel_id_preserves_raw_format_and_creates_search_safe_id() -> None:
    parcel = normalize_parcel_id(" 0123-45-6789 ")

    assert parcel.raw == "0123-45-6789"
    assert parcel.normalized == "0123456789"


def test_normalize_parcel_id_does_not_guess_missing_ids() -> None:
    with pytest.raises(ParcelParseError, match="Missing parcel ID"):
        normalize_parcel_id("  ")
