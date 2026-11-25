import json

import pytest

from trustcheck.ingest import (
    is_sports,
    nearest_price,
    reference_time,
    was_disputed,
    winner,
    build_record,
    skip_reason,
    anchor_time,
)

from trustcheck.ingest import RECURRING_TAGS, is_recurring

YES_NO = ["Yes", "No"]

HISTORY = [
    {"t": 100, "p": 0.1},
    {"t": 200, "p": 0.2},
    {"t": 300, "p": 0.3},
]

CLOSE = "2025-01-20T22:51:36Z"

RAW_MARKET = {
    "id": "555",
    "question": "Will X happen?",
    "slug": "will-x-happen",
    "conditionId": "0xabc",
    "endDate": "2025-01-20T12:00:00Z",
    "umaEndDate": "2025-01-20T22:51:36Z",
    "volumeNum": 2500000.5,
    "liquidityNum": 1000.25,
    "closed": True,
    "outcomes": '["Yes", "No"]',
    "outcomePrices": '["1", "0"]',
    "umaResolutionStatuses": '["proposed", "resolved"]',
    "events": [{"id": "999"}],
    "tags": [{"label": "Politics"}, {"label": "Iran"}],
    "clobTokenIds": '["111", "222"]',
}

def test_yes_wins():
    assert winner(YES_NO, [1.0, 0.0]) == "Yes"


def test_no_wins():
    assert winner(YES_NO, [0.0, 1.0]) == "No"


def test_both_zero_is_unresolved():
    assert winner(YES_NO, [0.0, 0.0]) is None


def test_near_certain_still_counts():
    assert winner(YES_NO, [0.995, 0.005]) == "Yes"


def test_uncertain_prices_give_none():
    assert winner(YES_NO, [0.6, 0.4]) is None


def test_non_yes_no_outcomes_give_none():
    assert winner(["Up", "Down"], [1.0, 0.0]) is None


def test_wrong_number_of_prices_gives_none():
    assert winner(YES_NO, [1.0]) is None


def test_sports_tag_detected():
    assert is_sports(["NBA", "Basketball", "Sports", "NBA Playoffs"]) is True


def test_sports_tag_ignores_case():
    assert is_sports(["sports"]) is True


def test_politics_is_not_sports():
    assert is_sports(["Politics", "Iran"]) is False


def test_empty_or_missing_tags_not_sports():
    assert is_sports([]) is False
    assert is_sports(None) is False


def test_disputed_detected():
    assert was_disputed(["proposed", "disputed", "proposed", "resolved"]) is True


def test_not_disputed():
    assert was_disputed(["proposed", "resolved"]) is False


def test_empty_or_missing_statuses_not_disputed():
    assert was_disputed([]) is False
    assert was_disputed(None) is False



def test_picks_closest_point():
    assert nearest_price(HISTORY, 190) == 0.2

def test_exact_match():
    assert nearest_price(HISTORY, 300) == 0.3

def test_empty_history_outputs_none():
    assert nearest_price([], 150) is None

def test_reference_before_first_point():
    assert nearest_price(HISTORY, 0) == 0.1

def test_reference_before_last_point():
    assert nearest_price(HISTORY, 1000) == 0.3

def test_tie_picks_earlier_point():
    assert nearest_price(HISTORY, 150) == 0.1




def test_reference_time_is_seven_days_before_close():
    assert reference_time(CLOSE) == 1736808696


def test_reference_time_custom_days():
    assert reference_time(CLOSE, days=1) == 1736808696 + 518400


def test_reference_time_zero_days_is_the_close_itself():
    assert reference_time(CLOSE, days=0) == 1737413496


def test_reference_time_returns_an_int():
    assert isinstance(reference_time(CLOSE), int)


def test_clean_yes_winner_record():
    record = build_record(RAW_MARKET)
    assert record["winner"] == "Yes"
    assert record["is_sports"] is False
    assert record["was_disputed"] is False

def test_sports_tag_sets_is_sports():
    raw = {**RAW_MARKET, "tags": [{"label": "NBA"}, {"label": "Sports"}]}
    assert build_record(raw)["is_sports"] is True

def test_disputed_status_sets_was_disputed():
    raw = {**RAW_MARKET, "umaResolutionStatuses": '["proposed", "disputed", "proposed"]'}
    assert build_record(raw)["was_disputed"] is True


def test_zero_prices_give_no_winner():
    raw = {**RAW_MARKET, "outcomePrices": '["0", "0"]'}
    assert build_record(raw)["winner"] is None


def test_missing_tags_key_gives_empty_list():
    raw = {k: v for k, v in RAW_MARKET.items() if k != "tags"}
    record = build_record(raw)
    assert record["tags"] == "[]"
    assert record["is_sports"] is False


def test_tags_are_stored_as_json_text():
    record = build_record(RAW_MARKET)
    assert isinstance(record["tags"], str)
    assert json.loads(record["tags"]) == ["Politics", "Iran"]


def test_close_time_comes_from_uma_end_date():
    assert build_record(RAW_MARKET)["close_time"] == "2025-01-20T22:51:36Z"


def test_event_id_taken_from_first_event():
    assert build_record(RAW_MARKET)["event_id"] == "999"


def test_missing_events_gives_none_event_id():
    raw = {**RAW_MARKET, "events": []}
    assert build_record(raw)["event_id"] is None


def test_yes_token_id_is_first_when_yes_is_first():
    assert build_record(RAW_MARKET)["yes_token_id"] == "111"


def test_yes_token_id_follows_outcome_order():
    raw = {**RAW_MARKET, "outcomes": '["No", "Yes"]', "outcomePrices": '["0", "1"]'}
    assert build_record(raw)["yes_token_id"] == "222"


def test_missing_token_ids_gives_none():
    raw = {k: v for k, v in RAW_MARKET.items() if k != "clobTokenIds"}
    assert build_record(raw)["yes_token_id"] is None


def test_no_yes_outcome_gives_no_token():
    raw = {**RAW_MARKET, "outcomes": '["Up", "Down"]'}
    assert build_record(raw)["yes_token_id"] is None


def test_short_token_list_gives_none():
    raw = {**RAW_MARKET, "outcomes": '["No", "Yes"]', "clobTokenIds": '["111"]'}
    assert build_record(raw)["yes_token_id"] is None

def test_max_gap_rejects_a_stale_point():
    assert nearest_price(HISTORY, 1000, max_gap=50) is None


def test_max_gap_keeps_a_close_point():
    assert nearest_price(HISTORY, 190, max_gap=50) == 0.2


def test_gap_exactly_equal_to_max_gap_is_kept():
    assert nearest_price(HISTORY, 250, max_gap=50) == 0.2


def test_max_gap_zero_means_exact_match_only():
    assert nearest_price(HISTORY, 200, max_gap=0) == 0.2
    assert nearest_price(HISTORY, 201, max_gap=0) is None


def test_no_max_gap_means_no_limit():
    assert nearest_price(HISTORY, 1000) == 0.3




def clean_record():
    return build_record(RAW_MARKET)


def test_clean_record_is_kept():
    assert skip_reason(clean_record()) is None


def test_sports_record_is_skipped():
    assert skip_reason({**clean_record(), "is_sports": True}) == "sports"


def test_missing_winner_is_skipped():
    assert skip_reason({**clean_record(), "winner": None}) == "no_winner"


def test_missing_close_time_is_skipped():
    assert skip_reason({**clean_record(), "close_time": None}) == "no_close_time"


def test_empty_close_time_is_skipped():
    # An empty string is just as unusable as None.
    assert skip_reason({**clean_record(), "close_time": ""}) == "no_close_time"


def test_missing_token_id_is_skipped():
    assert skip_reason({**clean_record(), "yes_token_id": None}) == "no_token_id"


def test_sports_is_reported_before_other_problems():
    record = {**clean_record(), "is_sports": True, "winner": None}
    assert skip_reason(record) == "sports"


def test_winner_is_reported_before_missing_token():
    record = {**clean_record(), "winner": None, "yes_token_id": None}
    assert skip_reason(record) == "no_winner"



def test_disputed_market_uses_the_deadline():
    assert anchor_time("2026-06-15T00:00:00Z", "2026-06-18T00:32:19Z") == "2026-06-15T00:00:00Z"


def test_early_close_uses_the_close_time():
    assert anchor_time("2025-06-23T12:00:00Z", "2025-04-17T08:51:19Z") == "2025-04-17T08:51:19Z"


def test_same_day_close_uses_the_deadline():
    assert anchor_time("2025-01-20T12:00:00Z", "2025-01-20T22:51:36Z") == "2025-01-20T12:00:00Z"


def test_missing_end_date_falls_back_to_close():
    assert anchor_time(None, "2025-01-20T22:51:36Z") == "2025-01-20T22:51:36Z"


def test_missing_close_time_falls_back_to_end_date():
    assert anchor_time("2025-01-20T12:00:00Z", None) == "2025-01-20T12:00:00Z"


def test_both_missing_gives_none():
    assert anchor_time(None, None) is None


def test_tie_returns_end_date():
    assert anchor_time("2025-01-20T12:00:00Z", "2025-01-20T12:00:00+00:00") == "2025-01-20T12:00:00Z"


def test_build_record_includes_anchor_time():
    assert build_record(RAW_MARKET)["anchor_time"] == "2025-01-20T12:00:00Z"

def test_the_recurring_set_is_the_four_labels_we_chose():
    assert RECURRING_TAGS == {"recurring", "tweet markets", "weekly", "monthly"}


@pytest.mark.parametrize("label", ["Recurring", "Tweet Markets", "Weekly", "Monthly"])
def test_each_recurring_label_matches(label):
    assert is_recurring([label]) is True


@pytest.mark.parametrize("label", ["RECURRING", "recurring", "tWeet MaRkEts"])
def test_matching_ignores_capitalization(label):
    assert is_recurring([label]) is True


def test_one_matching_label_among_others_is_enough():
    assert is_recurring(["Politics", "Weekly", "Crypto"]) is True


def test_unrelated_labels_do_not_match():
    assert is_recurring(["Politics", "Crypto", "Elections"]) is False


def test_the_whole_label_must_match_not_part_of_it():
    assert is_recurring(["Weekly Recap", "Monthly Review"]) is False


@pytest.mark.parametrize("tags", [[], None])
def test_missing_or_empty_tags_are_not_recurring(tags):
    assert is_recurring(tags) is False
