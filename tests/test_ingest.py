from trustcheck.ingest import is_sports, was_disputed, winner

YES_NO = ["Yes", "No"]


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