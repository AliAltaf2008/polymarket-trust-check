import json
import sys
from datetime import datetime, timezone

from trustcheck.api import fetch_event_by_slug, fetch_order_book
from trustcheck.lookup import candidate_markets, choosable, parse_polymarket_url
from trustcheck.orderbook import fee_schedule_for, parse_book, trade_cost

url = sys.argv[1]
event_slug, market_slug = parse_polymarket_url(url)
options = choosable(candidate_markets(fetch_event_by_slug(event_slug), market_slug))

if len(options) > 1:
    for i, m in enumerate(options[:15], start=1):
        print(f"  {i}. {m['question']}")
    choice = input("Number or part of a name: ").strip().lower()
    if choice.isdigit():
        market = options[int(choice) - 1]
    else:
        market = next(m for m in options if choice in m["question"].lower())   # first name match
else:
    market = options[0]

book = parse_book(fetch_order_book(json.loads(market["clobTokenIds"])[0]))
schedule = fee_schedule_for(market)

print(f"\n{market['question']}")
print(f"snapshot {datetime.now(timezone.utc):%H:%M:%S} UTC")
print("fee schedule:", schedule)

first = trade_cost(book, 100, schedule)
if first["mid"] is not None:
    # With a midpoint and a spread, the best bid and ask sit half a spread either side of it.
    print(f"best bid {first['mid'] - first['spread'] / 2:.4f}, "
          f"best ask {first['mid'] + first['spread'] / 2:.4f}, spread {first['spread']:.4f}")

for dollars in (100, 500):
    c = trade_cost(book, dollars, schedule)
    if c["shares"] == 0:
        print(f"${dollars}: nothing to buy")
        continue
    print(f"${dollars}: shares {c['shares']:.2f}, avg price {c['avg_price']:.4f}, fee ${c['fee']:.2f}")
    # If the fee is taken in shares instead of dollars, you'd receive this many:
    print(f"        shares if fee is taken in shares: {c['shares'] - c['fee'] / c['avg_price']:.2f}")