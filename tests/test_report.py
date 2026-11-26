import sqlite3

import pytest

from trustcheck.db import init_db, upsert_record
from trustcheck.report import (
    TRADE_SIZES,
    build_report,
    cost_line,
    cost_per_share,
    sample_volume_floor,
    similar_line,
)

LIVE = {"exponent": 1, "rate": 0.05, "takerOnly": True, "rebateRate": 0.25}
BOOK = {"bids": [(0.48, 1000.0)], "asks": [(0.50, 100.0), (0.52, 200.0)],
        "tick_size": 0.01, "min_order_size": 5.0}                       # mid 0.49
MARKET = {"question": "Will it happen?", "slug": "will-it-happen", "feesEnabled": False}


def make_conn():
    conn = sqlite3.connect(":memory:")    
    init_db(conn)
    return conn


def save_markets(conn, price, yes, no):
    for i in range(yes):
        upsert_record(conn, {"id": f"y{price}-{i}", "ref_price": price, "winner": "Yes"})
    for i in range(no):
        upsert_record(conn, {"id": f"n{price}-{i}", "ref_price": price, "winner": "No"})


def test_the_report_has_one_cost_per_trade_size_in_order():
    report = build_report(MARKET, BOOK, make_conn())
    assert [c["dollars"] for c in report["costs"]] == list(TRADE_SIZES)


def test_midpoint_and_spread_are_reported():
    report = build_report(MARKET, BOOK, make_conn())
    assert report["mid"] == pytest.approx(0.49)
    assert report["spread"] == pytest.approx(0.02)


def test_question_and_slug_come_through():
    report = build_report(MARKET, BOOK, make_conn())
    assert report["question"] == "Will it happen?"
    assert report["slug"] == "will-it-happen"


def test_similar_markets_are_looked_up_at_the_midpoint():
    conn = make_conn()
    save_markets(conn, 0.40, yes=7, no=28)        
    report = build_report(MARKET, BOOK, conn)      
    assert report["similar_all"]["n"] == 35
    assert report["similar_all"]["yes"] == 7


def test_the_no_recurring_lookup_is_separate_from_the_all_lookup():
    conn = make_conn()
    save_markets(conn, 0.40, yes=2, no=3)
    report = build_report(MARKET, BOOK, conn)
    assert report["similar_no_recurring"]["n"] == 5   


def test_a_market_with_fees_charges_them():
    market = {**MARKET, "feesEnabled": True, "feeSchedule": LIVE}
    report = build_report(market, BOOK, make_conn())
    assert report["fee_schedule"] == LIVE
    assert all(c["fee"] > 0 for c in report["costs"])


def test_a_market_without_fees_has_a_zero_fee():
    report = build_report(MARKET, BOOK, make_conn())
    assert report["fee_schedule"] is None
    assert all(c["fee"] == 0.0 for c in report["costs"])


def test_a_one_sided_book_has_no_similar_record_and_says_why():
    one_sided = {**BOOK, "bids": []}
    report = build_report(MARKET, one_sided, make_conn())
    assert report["mid"] is None
    assert report["similar_all"] is None
    assert report["similar_no_recurring"] is None
    assert "no_bids" in report["flags"]


def test_a_healthy_book_has_no_flags():
    assert build_report(MARKET, BOOK, make_conn())["flags"] == []


def test_a_market_without_a_question_does_not_crash():
    report = build_report({"feesEnabled": False}, BOOK, make_conn())
    assert report["question"] is None

def cost(**overrides):
    base = {"dollars": 100, "shares": 200.0, "spent": 100.0, "unfilled": 0.0,
            "avg_price": 0.5, "cost_dollars": 2.0, "fee": 1.0,
            "total_cost": 3.0, "total_pct": 0.03}
    return {**base, **overrides}

def test_cost_line_normal():
    line = cost_line(cost())
    assert "trade cost $2.00" in line and "fee $1.00" in line and "$3.00 (3.0%)" in line

def test_cost_line_no_bids():
    line = cost_line(cost(cost_dollars=None, total_cost=None, total_pct=None, avg_price=0.002))
    assert "0.2¢/share" in line and "no bids" in line

def test_cost_line_no_asks():
    assert "no asks" in cost_line(cost(shares=0, avg_price=None))

def test_cost_line_partial_fill():
    assert "only $60.00 fillable" in cost_line(cost(spent=60.0, unfilled=40.0))

def rec(**overrides):
    base = {"bucket": (0.05, 0.3), "n": 326, "yes": 60, "rate": 0.184,
            "interval": (0.146, 0.230), "enough": True}
    return {**base, **overrides}

def test_similar_line_normal():
    line = similar_line("all", rec())
    assert "5%-30%" in line and "60 of 326" in line and "18.4%" in line
    assert "14.6% to 23.0%" in line

def test_similar_line_none():
    assert similar_line("all", None) == "all: not available"

def test_similar_line_not_enough():
    line = similar_line("all", rec(n=12, enough=False, interval=None))
    assert "not enough similar markets" in line and "12" in line
    assert "%" in line
    assert "resolved YES" not in line  

def test_cost_per_share_divides_total_cost_by_shares_kept():
    # $3.00 total over 150 shares kept is 2 cents per share.
    assert cost_per_share(cost(shares_net=150.0)) == pytest.approx(0.02)


def test_cost_per_share_is_none_without_bids():
    # No bids: no midpoint, so total_cost is None and there is nothing to spread out.
    assert cost_per_share(cost(total_cost=None, shares_net=150.0)) is None


def test_cost_per_share_is_none_when_nothing_was_bought():
    # Dividing by zero shares would crash, so it must return None first.
    assert cost_per_share(cost(shares=0, shares_net=0)) is None


def save_with_volume(conn, market_id, volume, winner="Yes", ref_price=0.40):
    upsert_record(conn, {"id": market_id, "volume": volume, "winner": winner, "ref_price": ref_price})


def test_sample_floor_is_the_smallest_volume_among_kept_markets():
    conn = make_conn()
    save_with_volume(conn, "a", 90000.0)
    save_with_volume(conn, "b", 42600.0)
    save_with_volume(conn, "c", 500000.0)
    assert sample_volume_floor(conn) == pytest.approx(42600.0)


def test_sample_floor_ignores_rows_the_record_does_not_use():
    # Same filter as similar_record: a row without a winner or a ref_price isn't in the record,
    # so its volume must not lower the floor.
    conn = make_conn()
    save_with_volume(conn, "kept", 50000.0)
    save_with_volume(conn, "no-winner", 100.0, winner=None)
    save_with_volume(conn, "no-price", 200.0, ref_price=None)
    assert sample_volume_floor(conn) == pytest.approx(50000.0)


def test_sample_floor_is_none_for_an_empty_database():
    assert sample_volume_floor(make_conn()) is None


def test_report_includes_volume_and_sample_floor():
    conn = make_conn()
    save_with_volume(conn, "kept", 42600.0)
    report = build_report({**MARKET, "volumeNum": "1234.5"}, BOOK, conn)
    assert report["volume"] == pytest.approx(1234.5)     # text from the API becomes a number
    assert report["sample_floor"] == pytest.approx(42600.0)


@pytest.mark.parametrize("raw", [None, "n/a"])
def test_report_volume_is_none_when_missing_or_unreadable(raw):
    market = dict(MARKET) if raw is None else {**MARKET, "volumeNum": raw}
    assert build_report(market, BOOK, make_conn())["volume"] is None
