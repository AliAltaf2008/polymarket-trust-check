"""Print the similar_record table for a few reference prices.

Usage (from the project root):
    python check_buckets.py
"""
from trustcheck.db import get_connection
from trustcheck.stats import MIN_SAMPLE, similar_record

# One price inside each bucket we want to look at.
PRICES = [0.002, 0.03, 0.07, 0.15, 0.25, 0.40, 0.60, 0.80]


def pct(x):
    """0.123 -> '12.3%'. Shows '-' for None (an empty bucket has no rate)."""
    return "-" if x is None else f"{x:.1%}"


# get_connection() opens the same database file the app uses.
conn = get_connection()

# The header row. ">8" means "right-align in 8 characters", so the columns line up.
print(f"{'price':>6} {'bucket':>11} {'set':>8} {'n':>4} {'yes':>4} {'rate':>6} {'95% interval':>16}  n>={MIN_SAMPLE}")

for price in PRICES:
    # Each price is checked twice: all markets, then without recurring ones.
    for label, exclude in [("all", False), ("excl rec", True)]:
        r = similar_record(conn, price, exclude_recurring=exclude)

        low, high = r["bucket"]                       # unpack the (low, high) pair
        if r["interval"] is None:
            interval = "-"
        else:
            interval = f"{pct(r['interval'][0])} to {pct(r['interval'][1])}"

        print(f"{price:>6} {f'{low:.2f}-{high:.2f}':>11} {label:>8} {r['n']:>4} {r['yes']:>4} "
              f"{pct(r['rate']):>6} {interval:>16}  {'yes' if r['enough'] else 'NO'}")

conn.close()
