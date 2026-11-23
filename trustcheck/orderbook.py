def _parse_levels(levels):
    parsed = []

    for level in levels:
        price = float(level["price"])
        size = float(level["size"])
        if size > 0:
            parsed.append((price,size))
    return parsed

def parse_book(raw):
    bids = _parse_levels(raw.get("bids") or [])
    asks = _parse_levels(raw.get("asks") or [])

    bids.sort(key = lambda level: level[0], reverse = True)
    asks.sort(key = lambda level: level[0])

    return {
        "bids": bids,
        "asks": asks,
        #Need a loud error so no .get()
        "tick_size": float(raw["tick_size"]),
        "min_order_size": float(raw["min_order_size"])
    }

def walk_asks(asks, dollars):
    if dollars <=0:
        raise ValueError(f"dolalrs must be above zero, got {dollars} instead")

    remaining = dollars
    shares = 0.0
    spent = 0.0

    for price, size in asks:
        if remaining <= 0:
            break
        if price <=0:
            continue

        level_dollars = price * size
        take = min(remaining, level_dollars)

        shares += take / price
        spent += take
        remaining -= take

    return {
        "shares": shares,
        "spent": spent,
        "unfilled": max(dollars - spent, 0.0),
        "avg_price": spent / shares if shares > 0 else None,
    }
        