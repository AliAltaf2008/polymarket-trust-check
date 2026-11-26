import pytest

from trustcheck.orderbook import parse_book, walk_asks, trade_cost, taker_fee, fee_schedule_for, book_flags


def make_raw(bids=None, asks=None):
    """A minimal raw book, shaped like the API's response."""
    return {
        "bids": bids if bids is not None else [],
        "asks": asks if asks is not None else [],
        "tick_size": "0.01",
        "min_order_size": "5",
    }


def level(price, size):
    return {"price": price, "size": size}


def test_strings_become_floats():
    book = parse_book(make_raw(bids=[level("0.45", "100")]))
    assert book["bids"] == [(0.45, 100.0)]
    assert isinstance(book["bids"][0][0], float)


def test_bids_come_out_highest_first_from_ascending_input():
    # This is the order the live API actually used.
    raw = make_raw(bids=[level("0.01", "10"), level("0.03", "10"), level("0.06", "10")])
    assert [p for p, _ in parse_book(raw)["bids"]] == [0.06, 0.03, 0.01]


def test_bids_come_out_highest_first_from_descending_input():
    raw = make_raw(bids=[level("0.06", "10"), level("0.03", "10"), level("0.01", "10")])
    assert [p for p, _ in parse_book(raw)["bids"]] == [0.06, 0.03, 0.01]


def test_asks_come_out_lowest_first_from_descending_input():
    # This is the order the live API actually used.
    raw = make_raw(asks=[level("0.99", "10"), level("0.50", "10"), level("0.07", "10")])
    assert [p for p, _ in parse_book(raw)["asks"]] == [0.07, 0.50, 0.99]


def test_asks_come_out_lowest_first_from_ascending_input():
    raw = make_raw(asks=[level("0.07", "10"), level("0.50", "10"), level("0.99", "10")])
    assert [p for p, _ in parse_book(raw)["asks"]] == [0.07, 0.50, 0.99]


def test_each_price_keeps_its_own_size_after_sorting():
    raw = make_raw(asks=[level("0.60", "300"), level("0.50", "100")])
    assert parse_book(raw)["asks"] == [(0.50, 100.0), (0.60, 300.0)]


@pytest.mark.parametrize("side", ["bids", "asks"])
def test_an_empty_side_gives_an_empty_list(side):
    assert parse_book(make_raw())[side] == []


def test_a_missing_or_null_side_gives_an_empty_list():
    raw = {"bids": None, "tick_size": "0.01", "min_order_size": "5"}   # asks missing
    book = parse_book(raw)
    assert book["bids"] == []
    assert book["asks"] == []


def test_levels_with_zero_size_are_dropped():
    raw = make_raw(asks=[level("0.50", "0"), level("0.52", "200")])
    assert parse_book(raw)["asks"] == [(0.52, 200.0)]


def test_tick_size_and_min_order_size_are_converted():
    book = parse_book(make_raw())
    assert book["tick_size"] == 0.01
    assert book["min_order_size"] == 5.0


def test_missing_tick_size_raises():
    raw = {"bids": [], "asks": [], "min_order_size": "5"}
    with pytest.raises(KeyError):
        parse_book(raw)


def test_the_input_is_not_changed():
    raw = make_raw(asks=[level("0.99", "10"), level("0.07", "10")])
    parse_book(raw)
    assert raw["asks"] == [level("0.99", "10"), level("0.07", "10")]


ASKS = [(0.50, 100.0), (0.52, 200.0)]


def test_a_small_buy_fills_at_the_best_price():
    result = walk_asks(ASKS, 30)
    assert result["shares"] == pytest.approx(60)     
    assert result["spent"] == pytest.approx(30)
    assert result["unfilled"] == pytest.approx(0)
    assert result["avg_price"] == pytest.approx(0.50)


def test_a_buy_that_crosses_into_the_second_level():
    result = walk_asks(ASKS, 100)
    assert result["shares"] == pytest.approx(100 + 50 / 0.52)
    assert result["spent"] == pytest.approx(100)
    assert result["unfilled"] == pytest.approx(0)
    assert result["avg_price"] == pytest.approx(100 / (100 + 50 / 0.52))   # about 0.5098


def test_a_buy_bigger_than_the_book_reports_what_is_unfilled():
    result = walk_asks(ASKS, 1000)
    assert result["spent"] == pytest.approx(154)           
    assert result["unfilled"] == pytest.approx(846)
    assert result["shares"] == pytest.approx(300)
    assert result["avg_price"] == pytest.approx(154 / 300)


def test_an_empty_book_fills_nothing():
    result = walk_asks([], 100)
    assert result["shares"] == 0
    assert result["spent"] == 0
    assert result["unfilled"] == pytest.approx(100)
    assert result["avg_price"] is None


@pytest.mark.parametrize("dollars", [0, -5])
def test_a_non_positive_amount_raises(dollars):
    with pytest.raises(ValueError):
        walk_asks(ASKS, dollars)


def test_levels_beyond_the_amount_are_untouched():
    result = walk_asks(ASKS, 10)
    assert result["shares"] == pytest.approx(20)         
    assert result["avg_price"] == pytest.approx(0.50)    


def test_exactly_emptying_a_level_does_not_touch_the_next():
    result = walk_asks(ASKS, 50)
    assert result["shares"] == pytest.approx(100)
    assert result["avg_price"] == pytest.approx(0.50)
    assert result["unfilled"] == pytest.approx(0)


def test_a_zero_price_level_is_skipped_not_a_crash():
    result = walk_asks([(0.0, 100.0), (0.50, 100.0)], 25)
    assert result["shares"] == pytest.approx(50)


@pytest.mark.parametrize("dollars", [1, 49.99, 50, 50.01, 100, 153.99, 154, 154.01, 1000])
def test_spent_plus_unfilled_always_equals_the_amount(dollars):
    result = walk_asks(ASKS, dollars)
    assert result["spent"] + result["unfilled"] == pytest.approx(dollars)


@pytest.mark.parametrize("dollars", [1, 100, 1000])
def test_shares_times_average_price_equals_spent(dollars):
    result = walk_asks(ASKS, dollars)
    assert result["shares"] * result["avg_price"] == pytest.approx(result["spent"])



BOOK = {"bids": [(0.48, 100.0)], "asks": [(0.50, 100.0), (0.52, 200.0)]}  


def test_midpoint_and_spread():
    result = trade_cost(BOOK, 30)
    assert result["mid"] == pytest.approx(0.49)
    assert result["spread"] == pytest.approx(0.02)


def test_cost_of_a_small_buy():
    result = trade_cost(BOOK, 30)
    assert result["cost_dollars"] == pytest.approx(0.60)    
    assert result["cost_pct"] == pytest.approx(0.02)        


def test_cost_grows_when_the_buy_reaches_deeper_levels():
    result = trade_cost(BOOK, 100)
    assert result["cost_dollars"] == pytest.approx(100 - 0.49 * (100 + 50 / 0.52))  
    assert result["cost_pct"] == pytest.approx(0.0388, abs=1e-4)
    assert result["cost_pct"] > trade_cost(BOOK, 30)["cost_pct"]


def test_fill_numbers_pass_through_from_walk_asks():
    result = trade_cost(BOOK, 1000)
    assert result["spent"] == pytest.approx(154)
    assert result["unfilled"] == pytest.approx(846)


def test_no_bids_means_no_midpoint_and_no_cost_but_the_fill_still_works():
    result = trade_cost({"bids": [], "asks": BOOK["asks"]}, 30)
    assert result["mid"] is None
    assert result["spread"] is None
    assert result["cost_dollars"] is None
    assert result["cost_pct"] is None
    assert result["shares"] == pytest.approx(60)


def test_no_asks_means_nothing_fills_and_no_cost():
    result = trade_cost({"bids": BOOK["bids"], "asks": []}, 30)
    assert result["shares"] == 0
    assert result["avg_price"] is None
    assert result["cost_dollars"] is None
    assert result["cost_pct"] is None


def test_a_tight_deep_book_on_a_cheap_market_still_costs_a_tick_percent():
    deep = {"bids": [(0.06, 50000.0)], "asks": [(0.07, 50000.0)]}
    assert trade_cost(deep, 100)["cost_pct"] == pytest.approx(0.005 / 0.07)


def test_a_non_positive_amount_raises():
    with pytest.raises(ValueError):
        trade_cost(BOOK, 0)



POLITICS = {"exponent": 1, "rate": 0.04, "takerOnly": True, "rebateRate": 0.25}
LIVE = {"exponent": 1, "rate": 0.05, "takerOnly": True, "rebateRate": 0.25}  


def test_no_schedule_means_no_fee():
    assert taker_fee(100, 0.50, None) == 0.0


def test_fee_matches_the_docs_table_at_the_peak():
    assert taker_fee(100, 0.50, POLITICS) == pytest.approx(1.00)   
    assert taker_fee(100, 0.50, LIVE) == pytest.approx(1.25)


def test_fee_matches_the_docs_table_near_the_bottom():
    assert taker_fee(100, 0.05, POLITICS) == pytest.approx(0.19)   


def test_a_second_hand_checkable_example():
    assert taker_fee(1000, 0.10, LIVE) == pytest.approx(4.5)     


def test_fee_is_symmetric_around_fifty_percent():
    assert taker_fee(100, 0.30, LIVE) == pytest.approx(taker_fee(100, 0.70, LIVE))


@pytest.mark.parametrize("price", [0.0, 1.0])
def test_fee_is_zero_at_the_extremes(price):
    assert taker_fee(100, price, LIVE) == 0.0


def test_a_tiny_fee_rounds_to_zero():
    tiny = {"exponent": 1, "rate": 0.01, "takerOnly": True, "rebateRate": 0.25}
    assert taker_fee(1, 0.0001, tiny) == 0.0                    


@pytest.mark.parametrize("shares, price", [(-1, 0.5), (10, -0.1), (10, 1.1)])
def test_bad_inputs_raise(shares, price):
    with pytest.raises(ValueError):
        taker_fee(shares, price, LIVE)


def test_schedule_is_returned_when_fees_are_enabled():
    market = {"feesEnabled": True, "feeSchedule": LIVE}
    assert fee_schedule_for(market) == LIVE


@pytest.mark.parametrize("market", [{"feesEnabled": False}, {}, {"feesEnabled": False, "feeSchedule": LIVE}])
def test_no_schedule_when_fees_are_off_or_missing(market):
    assert fee_schedule_for(market) is None


def test_fees_enabled_without_a_schedule_raises():
    with pytest.raises(ValueError):
        fee_schedule_for({"feesEnabled": True})



def test_walk_asks_reports_each_level_it_bought_from():
    result = walk_asks(ASKS, 100)
    assert result["fills"][0] == (0.50, pytest.approx(100.0))
    assert result["fills"][1] == (0.52, pytest.approx(50 / 0.52))
    assert sum(s for _, s in result["fills"]) == pytest.approx(result["shares"])


def test_walk_asks_fills_are_empty_for_an_empty_book():
    assert walk_asks([], 100)["fills"] == []


def test_fee_and_total_for_a_small_buy():
    result = trade_cost(BOOK, 30, LIVE)
    assert result["fee"] == pytest.approx(0.75)             
    assert result["cost_dollars"] == pytest.approx(0.60)
    assert result["total_cost"] == pytest.approx(1.35)
    assert result["total_pct"] == pytest.approx(1.35 / 30)  # 4.5%


def test_fee_is_added_level_by_level_when_the_buy_crosses_levels():
    result = trade_cost(BOOK, 100, LIVE)
    assert result["fee"] == pytest.approx(2.45)
    assert result["total_cost"] == pytest.approx(result["cost_dollars"] + 2.45)


def test_no_schedule_means_zero_fee_and_total_equals_trade_cost():
    result = trade_cost(BOOK, 30)
    assert result["fee"] == 0.0
    assert result["total_cost"] == pytest.approx(result["cost_dollars"])


def test_the_fee_still_shows_without_a_midpoint_but_the_total_does_not():
    result = trade_cost({"bids": [], "asks": BOOK["asks"]}, 30, LIVE)
    assert result["fee"] == pytest.approx(0.75)
    assert result["cost_dollars"] is None
    assert result["total_cost"] is None
    assert result["total_pct"] is None


def test_nothing_filled_means_no_fee():
    result = trade_cost({"bids": BOOK["bids"], "asks": []}, 30, LIVE)
    assert result["fee"] == 0.0
    assert result["total_cost"] is None

def make_book(bids=(("0.50", "1000"),), asks=(("0.51", "1000"),), tick="0.01"):
    raw = {
        "bids": [{"price": p, "size": s} for p, s in bids],
        "asks": [{"price": p, "size": s} for p, s in asks],
        "tick_size": tick,
        "min_order_size": "5",
    }
    return parse_book(raw)

def test_flags_healthy_book_is_clean():
    assert book_flags(make_book()) == []

def test_flags_no_bids():
    assert "no_bids" in book_flags(make_book(bids=()))

def test_flags_no_asks():
    assert "no_asks" in book_flags(make_book(asks=()))

def test_flags_empty_book_has_both():
    flags = book_flags(make_book(bids=(), asks=()))
    assert "no_bids" in flags and "no_asks" in flags

def test_flags_one_sided_book_has_no_wide_spread():
    assert "wide_spread" not in book_flags(make_book(bids=()))

def test_flags_wide_spread():
    assert "wide_spread" in book_flags(make_book(bids=(("0.40", "1000"),), asks=(("0.50", "1000"),)))

def test_flags_spread_of_exactly_five_ticks_is_fine():
    assert "wide_spread" not in book_flags(make_book(bids=(("0.50", "1000"),), asks=(("0.55", "1000"),)))

def test_flags_spread_of_six_ticks_is_flagged():
    assert "wide_spread" in book_flags(make_book(bids=(("0.50", "1000"),), asks=(("0.56", "1000"),)))

def test_flags_wide_spread_scales_with_tick_size():
    tight = make_book(bids=(("0.500", "1000"),), asks=(("0.510", "1000"),), tick="0.01")
    wide = make_book(bids=(("0.500", "1000"),), asks=(("0.510", "1000"),), tick="0.001")
    assert "wide_spread" not in book_flags(tight)
    assert "wide_spread" in book_flags(wide)

def test_flags_thin_best_bid():
    assert "thin_best_bid" in book_flags(make_book(bids=(("0.50", "100"),)))

def test_flags_best_bid_of_exactly_100_dollars_is_not_thin():
    assert "thin_best_bid" not in book_flags(make_book(bids=(("0.50", "200"),)))

def test_flags_thin_is_judged_on_the_best_bid_only():
    book = make_book(bids=(("0.50", "10"), ("0.45", "5000")))
    assert "thin_best_bid" in book_flags(book)

MURPHY_FEES = {"exponent": 1, "rate": 0.05, "takerOnly": True, "rebateRate": 0.25}

def test_trade_cost_fee_is_taken_in_shares():
    # Matches the live site: $100 at 0.2c showed 47,505.00 shares, not 50,000.
    book = make_book(bids=(("0.001", "5000"),), asks=(("0.002", "1000000"),))
    c = trade_cost(book, 100, MURPHY_FEES)
    assert c["shares"] == pytest.approx(50000)
    assert c["fee"] == pytest.approx(4.99)
    assert c["fee_shares"] == pytest.approx(2495)      # 4.99 / 0.002
    assert c["shares_net"] == pytest.approx(47505.0)

def test_trade_cost_no_fee_keeps_all_shares():
    book = make_book(bids=(("0.001", "5000"),), asks=(("0.002", "1000000"),))
    c = trade_cost(book, 100, None)
    assert c["fee_shares"] == 0.0
    assert c["shares_net"] == pytest.approx(c["shares"])

def test_trade_cost_nothing_to_buy_has_zero_shares_net():
    # No asks: avg_price is None, so the code must fall back to 0 instead of dividing by None.
    c = trade_cost(make_book(asks=()), 100, MURPHY_FEES)
    assert c["shares_net"] == 0
    assert c["fee_shares"] == 0.0