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

def was_disputed(statuses):
    #Checks the status history of the market to ensure that it is not disputed and therefore cause the program to ingest bad data
    if not statuses:
        return False
    return "disputed" in statuses

