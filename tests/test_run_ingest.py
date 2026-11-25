import pytest

from run_ingest import parse_args, to_iso_utc
from trustcheck.api import DEFAULT_END_DATE_MAX, DEFAULT_END_DATE_MIN


def test_bare_date_gets_midnight_utc():
    assert to_iso_utc("2024-01-01") == "2024-01-01T00:00:00Z"


def test_full_timestamp_passes_through():
    assert to_iso_utc("2024-06-15T12:30:00Z") == "2024-06-15T12:30:00Z"


@pytest.mark.parametrize("bad", ["banana", "2024-13-45", "01/02/2024", ""])
def test_bad_date_raises(bad):
    with pytest.raises(ValueError):
        to_iso_utc(bad)


def test_no_arguments_gives_all_defaults():
    assert parse_args([]) == (5000, None, 20, 20, DEFAULT_END_DATE_MIN, DEFAULT_END_DATE_MAX)


def test_band_and_target():
    result = parse_args(["50000", "500000", "40"])
    assert result == (50000.0, 500000.0, 40, 20, DEFAULT_END_DATE_MIN, DEFAULT_END_DATE_MAX)


def test_none_means_no_upper_volume():
    assert parse_args(["500000", "none", "100", "50"])[1] is None


def test_custom_window():
    result = parse_args(["5000", "500000", "100", "50", "2024-01-01", "2025-01-01"])
    assert result[4] == "2024-01-01T00:00:00Z"
    assert result[5] == "2025-01-01T00:00:00Z"


def test_default_keyword_keeps_the_default_window():
    result = parse_args(["5000", "none", "20", "20", "default", "2025-06-01"])
    assert result[4] == DEFAULT_END_DATE_MIN
    assert result[5] == "2025-06-01T00:00:00Z"


def test_backwards_window_raises():
    with pytest.raises(ValueError):
        parse_args(["5000", "none", "20", "20", "2025-01-01", "2024-01-01"])


def test_empty_window_raises():
    with pytest.raises(ValueError):
        parse_args(["5000", "none", "20", "20", "2024-01-01", "2024-01-01"])
