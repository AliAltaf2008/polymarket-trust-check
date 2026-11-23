import pytest

from trustcheck.orderbook import parse_book, walk_asks


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