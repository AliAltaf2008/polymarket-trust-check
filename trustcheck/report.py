from trustcheck.orderbook import book_flags, fee_schedule_for, trade_cost
from trustcheck.stats import similar_record

TRADE_SIZES = (100, 500, 1000)

def build_report(market, book, conn):
    schedule = fee_schedule_for(market)

    costs = [dict(trade_cost(book, d, schedule), dollars = d) for d in TRADE_SIZES]

    mid = costs[0]["mid"]
    spread = costs[0]["spread"]

    if mid is not None:
        similar_all = similar_record(conn, mid)
        similar_no_recurring = similar_record(conn, mid, exclude_recurring=True)
    else:
        similar_all = None
        similar_no_recurring = None

    return {
        "question": market.get("question"),
        "slug": market.get("slug"),
        "mid": mid,
        "spread": spread,
        "tick_size": book["tick_size"],
        "fee_schedule": schedule,
        "costs": costs,
        "similar_all": similar_all,
        "similar_no_recurring": similar_no_recurring,
        "flags": book_flags(book),
    }

def cost_line(c):
    d = c["dollars"]

    if c["shares"] == 0:
        return f"${d}: nothing to buy (no asks)"

    note = f" (only ${c['spent']:.2f} fillable)" if c["unfilled"] > 0 else ""

    if c["total_cost"] is None:
        return (f"${d}: you'd pay about {c['avg_price'] * 100:.1f}¢/share, fee ${c['fee']:.2f}. "
                f"Trade cost can't be measured: no bids{note}")

    return (f"${d}: trade cost ${c['cost_dollars']:.2f} + fee ${c['fee']:.2f} "
            f"= ${c['total_cost']:.2f} ({c['total_pct']:.1%}){note}")

def cost_per_share(c):
    """Total cost (trade cost + fee) spread over the shares you actually keep, in dollars per share.
    `c` is one entry of report["costs"]. Returns None when it can't be measured."""
    # No midpoint (no bids) means no total cost, and with no shares there is nothing to divide by.
    if c["total_cost"] is None or c["shares_net"] <= 0:
        return None
    # Divide by shares_net, not shares: the fee is taken out of the shares you receive.
    return c["total_cost"] / c["shares_net"]

def similar_line(label, s):
    """One card line for a similar-market record. `s` is similar_record's dict, or None."""
    if s is None:
        return f"{label}: not available"

    lo, hi = s["bucket"]
    where = f"markets priced {lo:.0%}-{hi:.0%}"    

    if not s["enough"]:
        return f"{label} ({where}): not enough similar markets (only {s['n']})"

    ilo, ihi = s["interval"]
    return f"{label} ({where}): {s['yes']} of {s['n']} resolved YES ({s['rate']:.1%}, 95% range {ilo:.1%} to {ihi:.1%})"
