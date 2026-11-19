import json

from trustcheck.ingest import (
    is_sports,
    nearest_price,
    reference_time,
    was_disputed,
    winner,
    build_record,
)

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


def test_numbers_are_floats():
    record = build_record(RAW_MARKET)
    assert record["volume"] == 2500000.5
    assert isinstance(record["liquidity"], float)

