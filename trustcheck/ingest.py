from datetime import datetime, timedelta
import json

SPORTS_TAGS = {
    "sports", "nba", "nfl", "mlb", "nhl", "soccer", "basketball",
    "football", "baseball", "hockey", "tennis", "golf", "ufc", "mma",
    "fifa world cup", "epl", "formula 1",
}

def winner(outcomes, prices):
    #Outcomes is a safety check to ensure lists that contain other elements other than yes and no are checked
    if outcomes != ["Yes", "No"]:
        return None

    if len(prices) != 2:
        return None

    yes_price, no_price = prices

    #There exists markets with 0 and 0 etc so these unclear markets should be filtered
    if(yes_price>= 0.99 and no_price <= 0.01):
        return "Yes"
    if(no_price >= 0.99 and yes_price <= 0.01):
        return "No"

    #Leave out the unclear markets
    return None

def is_sports(tag_labels):
    if not tag_labels:
        return False

    label_check = any(label.lower() in SPORTS_TAGS for label in tag_labels)
    return label_check

RECURRING_TAGS = {"recurring", "tweet markets", "weekly", "monthly"}

def is_recurring(tag_labels):
    if not tag_labels:
        return False

    return any(label.lower() in RECURRING_TAGS for label in tag_labels)

def was_disputed(statuses):
    #Checks the status history of the market to ensure that it is not disputed and therefore cause the program to ingest bad data
    if not statuses:
        return False
    return "disputed" in statuses

def nearest_price(history, ref_ts, max_gap=None):
    #history is a list of prices and times so we compare which time is closest to the reference time and output that price
    if not history:
        return None
    closest = min(history, key=lambda point: abs(point["t"] - ref_ts))

    #Reject a price gap that is greater than the max_gap as it is considered as a stale price
    if max_gap is not None and abs(closest["t"] - ref_ts) > max_gap:
        return None

    return closest["p"]

def reference_time(close_time, days=7):
    close = datetime.fromisoformat(close_time.replace("Z", "+00:00"))

    reference  = close - timedelta(days=days)
    return int(reference.timestamp())


def build_record(raw):
    events = raw.get("events") or []
    tag_objects = raw.get("tags") or []
    #Makes a list that keeps only the labels from the API call
    labels = [t["label"] for t in tag_objects if t.get("label")]

    outcomes = json.loads(raw.get("outcomes") or "[]")
    prices = [float(p) for p in json.loads(raw.get("outcomePrices") or "[]")]
    statuses = json.loads(raw.get("umaResolutionStatuses") or "[]")
    token_ids = json.loads(raw.get("clobTokenIds") or "[]")

    yes_token_id = None
    if "Yes" in outcomes:
        position = outcomes.index("Yes")
        #In the case of malformed data from the API, we return None as the yes_token_id eg. ["No", "Yes"] is malformed data
        if position < len(token_ids):
            yes_token_id = token_ids[position]

    return {
        # id and conditionId must exist so it does not use .get() so its failure is known
        "id": raw["id"],
        "question": raw.get("question"),
        "slug": raw.get("slug"),
        "condition_id": raw["conditionId"],
        "event_id": events[0]["id"] if events else None,
        "end_date": raw.get("endDate"),
        "volume": float(raw.get("volumeNum") or 0),
        "liquidity": float(raw.get("liquidityNum") or 0),
        "closed": bool(raw.get("closed")),
        "close_time": raw.get("umaEndDate"),
        "winner": winner(outcomes, prices),
        "tags": json.dumps(labels),
        "is_sports": is_sports(labels),
        "was_disputed": was_disputed(statuses),
        "yes_token_id": yes_token_id,
        "anchor_time": anchor_time(raw.get("endDate"), raw.get("umaEndDate")),
    }

def skip_reason(record):
    """Return the first reason to drop a record or return None if it is kept"""

    if record["is_sports"]:
        return "sports"
    if record["winner"] is None:
        return "no_winner"
    if not record["close_time"]:
        return "no_close_time"
    if record["yes_token_id"] is None:
        return "no_token_id"

    return None

def anchor_time(end_date, close_time):
    #NOTE:endDate is the scheduled end for the market and closedTime/umeEndDate is the actual end time of the market and disputing the market
    # or closing the market early causes the closeTime to differ from endDate
    if not end_date:
        return close_time or None
    if not close_time:
        return end_date

    end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    close = datetime.fromisoformat(close_time.replace("Z", "+00:00"))

    return end_date if end <= close else close_time