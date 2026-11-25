import json
import sqlite3

import pytest

from trustcheck.db import init_db, upsert_record
from trustcheck.stats import (
    BUCKET_EDGES,
    MIN_SAMPLE,
    NUM_BUCKETS,
    bucket_bounds,
    bucket_index,
    similar_record,
    wilson_interval,
)

from trustcheck.stats import (
    BUCKET_EDGES,
    NUM_BUCKETS,
    bucket_bounds,
    bucket_index,
    wilson_interval,
)


def test_ten_of_twenty():
    low, high = wilson_interval(10, 20)
    assert low == pytest.approx(0.2993, abs=0.001)
    assert high == pytest.approx(0.7007, abs=0.001)


def test_seven_of_ten_is_wide():
    low, high = wilson_interval(7, 10)
    assert low == pytest.approx(0.3967, abs=0.001)
    assert high == pytest.approx(0.8922, abs=0.001)


def test_seven_hundred_of_a_thousand_is_narrow():
    # Same 70% rate as the test above, but far more evidence.
    low, high = wilson_interval(700, 1000)
    assert low == pytest.approx(0.6709, abs=0.001)
    assert high == pytest.approx(0.7276, abs=0.001)



def test_zero_of_ten_starts_at_zero_but_is_not_certain():
    low, high = wilson_interval(0, 10)
    assert low == pytest.approx(0.0, abs=0.001)
    assert high == pytest.approx(0.2775, abs=0.001)


def test_ten_of_ten_ends_at_one_but_is_not_certain():
    low, high = wilson_interval(10, 10)
    assert low == pytest.approx(0.7225, abs=0.001)
    assert high == pytest.approx(1.0, abs=0.001)


def test_larger_sample_gives_a_narrower_interval():
    small_low, small_high = wilson_interval(5, 10)
    big_low, big_high = wilson_interval(50, 100)
    assert (big_high - big_low) < (small_high - small_low)


def test_higher_confidence_gives_a_wider_interval():
    low95, high95 = wilson_interval(10, 20, z=1.96)
    low99, high99 = wilson_interval(10, 20, z=2.576)
    assert (high99 - low99) > (high95 - low95)


@pytest.mark.parametrize("successes, n", [(0, 5), (1, 5), (3, 7), (15, 40), (99, 100)])
def test_interval_contains_the_observed_rate(successes, n):
    low, high = wilson_interval(successes, n)
    assert low <= successes / n <= high


@pytest.mark.parametrize("successes, n", [(0, 1), (1, 1), (0, 3), (3, 3), (0, 100), (100, 100)])
def test_result_stays_inside_zero_and_one(successes, n):
    low, high = wilson_interval(successes, n)
    assert 0.0 <= low <= high <= 1.0


def test_mirror_symmetry():
    low, high = wilson_interval(3, 10)
    mirror_low, mirror_high = wilson_interval(7, 10)
    assert low == pytest.approx(1 - mirror_high)
    assert high == pytest.approx(1 - mirror_low)



def test_zero_markets_raises():
    with pytest.raises(ValueError):
        wilson_interval(0, 0)


def test_negative_successes_raises():
    with pytest.raises(ValueError):
        wilson_interval(-1, 10)


def test_more_successes_than_markets_raises():
    with pytest.raises(ValueError):
        wilson_interval(11, 10)


def test_zero_is_the_first_bucket():
    assert bucket_index(0.0) == 0


def test_one_is_the_last_bucket():
    assert bucket_index(1.0) == NUM_BUCKETS - 1


@pytest.mark.parametrize("price, expected", [
    (0.02, 0), (0.12, 1), (0.40, 2), (0.60, 3), (0.85, 4),
])
def test_price_inside_a_bucket(price, expected):
    assert bucket_index(price) == expected


@pytest.mark.parametrize("price, expected", [
    (0.05, 1), (0.30, 2), (0.50, 3), (0.70, 4),
])
def test_price_on_an_edge_goes_to_the_upper_bucket(price, expected):
    assert bucket_index(price) == expected


@pytest.mark.parametrize("price, expected", [
    (0.0499, 0), (0.2999, 1), (0.4999, 2), (0.6999, 3),
])
def test_price_just_below_an_edge_stays_in_the_lower_bucket(price, expected):
    assert bucket_index(price) == expected


def test_every_edge_starts_its_own_bucket():
    for i, edge in enumerate(BUCKET_EDGES[:-1]):
        assert bucket_index(edge) == i


@pytest.mark.parametrize("price", [-0.01, 1.01, -5, 2])
def test_out_of_range_price_raises(price):
    with pytest.raises(ValueError):
        bucket_index(price)


def test_nan_price_raises():
    with pytest.raises(ValueError):
        bucket_index(float("nan"))


def test_bounds_match_the_edges():
    for i in range(NUM_BUCKETS):
        assert bucket_bounds(i) == (BUCKET_EDGES[i], BUCKET_EDGES[i + 1])


@pytest.mark.parametrize("index", [-1, NUM_BUCKETS, 99])
def test_bad_bucket_index_raises(index):
    with pytest.raises(ValueError):
        bucket_bounds(index)


def test_buckets_cover_zero_to_one_without_gaps():
    assert bucket_bounds(0)[0] == 0.0
    assert bucket_bounds(NUM_BUCKETS - 1)[1] == 1.0
    for i in range(NUM_BUCKETS - 1):
        assert bucket_bounds(i)[1] == bucket_bounds(i + 1)[0]


def test_every_price_lies_inside_its_own_bucket():
    for i in range(101):
        price = i / 100
        low, high = bucket_bounds(bucket_index(price))
        assert low <= price <= high




def make_conn():
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return conn


def save(conn, market_id, ref_price, winner, tags=None):
    record = {"id": market_id, "ref_price": ref_price, "winner": winner}
    if tags is not None:
        record["tags"] = json.dumps(tags)
    upsert_record(conn, record)


def save_many(conn, price, yes, no, tags=None, prefix=""):
    for i in range(yes):
        save(conn, f"{prefix}{price}-yes-{i}", price, "Yes", tags)
    for i in range(no):
        save(conn, f"{prefix}{price}-no-{i}", price, "No", tags)


def test_counts_markets_in_the_same_bucket():
    conn = make_conn()
    save_many(conn, 0.40, yes=4, no=6)
    result = similar_record(conn, 0.45)      
    assert result["n"] == 10
    assert result["yes"] == 4
    assert result["rate"] == pytest.approx(0.4)
    assert result["bucket"] == (0.30, 0.50)


def test_markets_in_other_buckets_are_not_counted():
    conn = make_conn()
    save_many(conn, 0.40, yes=2, no=3)       
    save_many(conn, 0.60, yes=5, no=5)       
    result = similar_record(conn, 0.45)
    assert result["n"] == 5
    assert result["yes"] == 2


def test_a_price_exactly_on_an_edge_counts_in_the_upper_bucket():
    conn = make_conn()
    save_many(conn, 0.30, yes=1, no=1)        
    assert similar_record(conn, 0.40)["n"] == 2   
    assert similar_record(conn, 0.10)["n"] == 0  


def test_markets_without_a_winner_are_ignored():
    conn = make_conn()
    save_many(conn, 0.40, yes=1, no=2)
    save(conn, "still-open", 0.40, None)      
    assert similar_record(conn, 0.40)["n"] == 3


def test_markets_without_a_reference_price_are_ignored():
    conn = make_conn()
    save_many(conn, 0.40, yes=1, no=2)
    save(conn, "no-price", None, "Yes")      
    assert similar_record(conn, 0.40)["n"] == 3


def test_interval_matches_wilson_interval():
    conn = make_conn()
    save_many(conn, 0.40, yes=7, no=13)
    result = similar_record(conn, 0.40)
    assert result["interval"] == wilson_interval(7, 20)


def test_enough_flag_switches_at_the_minimum_sample():
    below = make_conn()
    save_many(below, 0.40, yes=10, no=MIN_SAMPLE - 11)   
    assert similar_record(below, 0.40)["n"] == MIN_SAMPLE - 1
    assert similar_record(below, 0.40)["enough"] is False

    at = make_conn()
    save_many(at, 0.40, yes=10, no=MIN_SAMPLE - 10)     
    assert similar_record(at, 0.40)["n"] == MIN_SAMPLE
    assert similar_record(at, 0.40)["enough"] is True


def test_small_bucket_still_reports_its_numbers():
    conn = make_conn()
    save_many(conn, 0.40, yes=2, no=3)
    result = similar_record(conn, 0.40)
    assert result["enough"] is False
    assert result["rate"] == pytest.approx(0.4)
    assert result["interval"] is not None


def test_empty_bucket_gives_no_rate_and_no_crash():
    conn = make_conn()
    result = similar_record(conn, 0.40)
    assert result["n"] == 0
    assert result["yes"] == 0
    assert result["rate"] is None
    assert result["interval"] is None
    assert result["enough"] is False


def test_price_of_one_uses_the_last_bucket():
    conn = make_conn()
    save(conn, "favorite", 0.99, "Yes")
    result = similar_record(conn, 1.0)
    assert result["n"] == 1
    assert result["bucket"] == (0.70, 1.0)


@pytest.mark.parametrize("price", [-0.1, 1.5])
def test_out_of_range_price_raises(price):
    conn = make_conn()
    with pytest.raises(ValueError):
        similar_record(conn, price)

def test_recurring_markets_count_by_default():
    conn = make_conn()
    save_many(conn, 0.40, yes=2, no=3, prefix="plain-")
    save_many(conn, 0.40, yes=4, no=1, tags=["Weekly"], prefix="weekly-")
    result = similar_record(conn, 0.45)
    assert result["n"] == 10
    assert result["yes"] == 6


def test_excluding_recurring_removes_them_from_n_and_yes():
    conn = make_conn()
    save_many(conn, 0.40, yes=2, no=3, prefix="plain-")
    save_many(conn, 0.40, yes=4, no=1, tags=["Weekly"], prefix="weekly-")
    result = similar_record(conn, 0.45, exclude_recurring=True)
    assert result["n"] == 5
    assert result["yes"] == 2
    assert result["rate"] == pytest.approx(0.4)


def test_tags_are_matched_regardless_of_capitalization():
    conn = make_conn()
    save_many(conn, 0.40, yes=1, no=1, tags=["RECURRING"], prefix="r-")
    assert similar_record(conn, 0.40, exclude_recurring=True)["n"] == 0


def test_markets_with_no_tags_count_as_not_recurring():
    conn = make_conn()
    save_many(conn, 0.40, yes=1, no=1)
    assert similar_record(conn, 0.40, exclude_recurring=True)["n"] == 2


def test_markets_with_an_empty_tag_list_count_as_not_recurring():
    conn = make_conn()
    save_many(conn, 0.40, yes=1, no=1, tags=[])
    assert similar_record(conn, 0.40, exclude_recurring=True)["n"] == 2


def test_markets_with_only_unrelated_tags_are_kept():
    conn = make_conn()
    save_many(conn, 0.40, yes=1, no=1, tags=["Politics", "Elections"])
    assert similar_record(conn, 0.40, exclude_recurring=True)["n"] == 2


def test_enough_is_judged_on_the_reduced_count():
    conn = make_conn()
    save_many(conn, 0.40, yes=10, no=15, prefix="plain-")
    save_many(conn, 0.40, yes=2, no=3, tags=["Weekly"], prefix="weekly-")
    assert similar_record(conn, 0.40)["enough"] is True
    reduced = similar_record(conn, 0.40, exclude_recurring=True)
    assert reduced["n"] == 25
    assert reduced["enough"] is False


def test_a_bucket_of_only_recurring_markets_ends_up_empty_without_crashing():
    conn = make_conn()
    save_many(conn, 0.40, yes=3, no=3, tags=["Tweet Markets"])
    result = similar_record(conn, 0.40, exclude_recurring=True)
    assert result["n"] == 0
    assert result["rate"] is None
    assert result["interval"] is None
    assert result["enough"] is False


def test_excluding_recurring_only_changes_the_bucket_it_filters():
    conn = make_conn()
    save_many(conn, 0.40, yes=1, no=1, tags=["Weekly"], prefix="a-")
    save_many(conn, 0.60, yes=1, no=1, tags=["Weekly"], prefix="b-")
    assert similar_record(conn, 0.40, exclude_recurring=True)["n"] == 0
    assert similar_record(conn, 0.60, exclude_recurring=True)["n"] == 0
    assert similar_record(conn, 0.40)["n"] == 2
    assert similar_record(conn, 0.60)["n"] == 2


def test_malformed_tags_raise_instead_of_being_ignored():
    conn = make_conn()
    upsert_record(conn, {"id": "bad", "ref_price": 0.40, "winner": "Yes", "tags": "not json"})
    with pytest.raises(ValueError):
        similar_record(conn, 0.40, exclude_recurring=True)
