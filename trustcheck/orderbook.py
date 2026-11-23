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

def trade_cost(book, dollars):
    """What is costs to buy dollars of 'Yes' in the market"""
    fill = walk_asks(book["asks"], dollars)

    bids = book["bids"]
    asks = book["asks"]

    if bids and asks:
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        mid = (best_bid + best_ask) / 2
        spread = best_ask - best_bid
    else:
        mid = None
        spread = None

    if mid is not None and fill["shares"] > 0:
        cost_dollars = (fill["avg_price"] - mid) * fill["shares"]
        #Divide by the amount that actually absorbed in the market so use "spent"
        cost_pct = cost_dollars / fill["spent"]
    else:
        cost_dollars = None
        cost_pct = None

    return {
        "mid": mid,
        "spread": spread,
        "shares": fill["shares"],
        "spent": fill["spent"],
        "unfilled": fill["unfilled"],
        "avg_price": fill["avg_price"],
        "cost_dollars": cost_dollars,
        "cost_pct": cost_pct,
    }

def fee_schedule_for(market):
    """Return the fee schedule a market dict or None if it has no fees"""

    if not market.get("feesEnabled"):
        return None
    schedule = market.get("feeSchedule")
    if not schedule:
        raise ValueError("feesEnabled is true but the market has no fee schedule")

    return schedule

def taker_fee(shares, price, fee_schedule):
    """Taker fee in dollars for buying shares at price"""

    if shares < 0:
        raise ValueError(f"Shares must not be negative, got {shares}")
    if not (0.0 <=price <= 1.0):
        raise ValueError(f"Price must be between 0 and 1, got {price}")
    if not fee_schedule:
        return 0.0

    rate = float(fee_schedule["rate"])
    exponent = float(fee_schedule["exponent"])
    fee = shares * rate * (price * (1-price)) ** exponent
    return round (fee, 5)