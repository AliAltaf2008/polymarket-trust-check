from fetch_markets import clean_market

RAW = {
    "id": "123",
    "question": "Will X happen?",
    "slug": "will-x-happen",
    "conditionId": "0xabc",
    "events": [{"id": "999"}],
    "endDate": "2027-01-01T04:59:00Z",
    "volumeNum": 1500.5,
    "liquidityNum": 300.25,
    "outcomes": '["Yes", "No"]',
    "outcomePrices": '["0.0165", "0.9835"]',
    "clobTokenIds": '["111", "222"]',
    "closed": False,
}


def test_converts_types():
    result = clean_market(RAW)
    assert result["volume"] == 1500.5
    assert result["outcome_prices"] == [0.0165, 0.9835]
    assert result["outcomes"] == ["Yes", "No"]
    assert result["event_id"] == "999"


def test_missing_events_gives_none():
    """Test the case where raw has an empty event"""
    raw = {**RAW, "events": []}
    result = clean_market(raw)
    assert result["event_id"] is None

def test_missing_volume_defaults_to_zero():
    """Allows us to test the defaults of clean_market()"""
    raw = {k: v for k, v in RAW.items() if k!= "volumeNum"}
    result = clean_market(raw)
    assert result["volume"] == 0