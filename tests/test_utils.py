"""Tests for trustcheck.utils."""

from trustcheck.utils import top_by_volume

MARKETS = [
    {"question": "A", "volume": 100},
    {"question": "B", "volume": 300},
    {"question": "C", "volume": 200},
]

def test_orders_highest_first():
    result = top_by_volume(MARKETS, 2)
    assert result[0]["question"] == "B"
    assert result[1]["question"] == "C"

def test_n_larger_than_list_returns_everything():
    result = top_by_volume(MARKETS, 10)
    assert len(result) == 3
