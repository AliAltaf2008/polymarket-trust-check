from trustcheck.api import build_page_params
from trustcheck.api import DEFAULT_END_DATE_MAX, DEFAULT_END_DATE_MIN


def test_defaults_match_the_old_behavior():
    params = build_page_params()
    assert params["closed"] == "true"
    assert params["order"] == "volumeNum"
    assert params["ascending"] == "false"
    assert params["volume_num_min"] == 5000
    assert params["limit"] == 20


def test_no_max_key_by_default():
    assert "volume_num_max" not in build_page_params()


def test_volume_band_sets_both_limits():
    params = build_page_params(volume_min=50000, volume_max=500000)
    assert params["volume_num_min"] == 50000
    assert params["volume_num_max"] == 500000


def test_zero_max_is_kept():
    assert build_page_params(volume_max=0)["volume_num_max"] == 0


def test_no_cursor_key_without_a_cursor():
    assert "after_cursor" not in build_page_params()


def test_cursor_is_passed_through():
    assert build_page_params(cursor="abc")["after_cursor"] == "abc"


def test_limit_passes_through():
    assert build_page_params(limit=50)["limit"] == 50


def test_date_window_is_included():
    params = build_page_params()
    assert "end_date_min" in params
    assert "end_date_max" in params

WINDOW_2024 = {
    "end_date_min": "2024-01-01T00:00:00Z",
    "end_date_max": "2025-01-01T00:00:00Z",
}


def test_default_window_is_unchanged():
    params = build_page_params()
    assert params["end_date_min"] == "2025-01-01T00:00:00Z"
    assert params["end_date_max"] == "2026-11-01T00:00:00Z"
    assert DEFAULT_END_DATE_MIN == params["end_date_min"]
    assert DEFAULT_END_DATE_MAX == params["end_date_max"]


def test_custom_window_is_used():
    params = build_page_params(**WINDOW_2024)
    assert params["end_date_min"] == "2024-01-01T00:00:00Z"
    assert params["end_date_max"] == "2025-01-01T00:00:00Z"


def test_window_does_not_disturb_the_other_keys():
    base = build_page_params()
    custom = build_page_params(**WINDOW_2024)
    for key in base:
        if key not in ("end_date_min", "end_date_max"):
            assert custom[key] == base[key]
    assert set(custom) == set(base)   


def test_window_combines_with_band_and_cursor():
    params = build_page_params(cursor="abc", volume_min=50000, volume_max=500000, **WINDOW_2024)
    assert params["after_cursor"] == "abc"
    assert params["volume_num_min"] == 50000
    assert params["volume_num_max"] == 500000
    assert params["end_date_min"] == "2024-01-01T00:00:00Z"


def test_old_positional_order_still_works():
    params = build_page_params("abc", 50, 1000, 9000)
    assert params["after_cursor"] == "abc"
    assert params["limit"] == 50
    assert params["volume_num_min"] == 1000
    assert params["volume_num_max"] == 9000