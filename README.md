# PolyChecker

> **Unofficial.** Not affiliated with, endorsed by, or connected to Polymarket.
> **Informational only, not financial advice.**
> **Read-only:** no wallet, no login, no trading. It only reads public market data.

## What it is

Paste a Polymarket link, pick a market (if the event has several), and PolyChecker shows:

- **The cost to buy YES right now** at $100, $500 and $1,000. It walks the live order book from the
  cheapest offer upward, the way a real buy order would fill, and splits the cost into a
  *trade cost* (paying more than the midpoint) and Polymarket's *taker fee*.
- **Warnings** about the order book: a wide spread, a thin best bid, or a side with no orders.
- **A similar-market record:** among past resolved markets that were priced like this one about a
  week before they closed, how often YES actually happened, with a 95% range.

## Setup and run

Requires Python 3.12.

```zsh
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 1. Build the database

The similar-market record reads from a local SQLite file, `data/trustcheck.db`. It is not in the
repo, so build it first with `run_ingest.py`:

```zsh
python run_ingest.py [min] [max|none] [target] [page_size] [date_min|default] [date_max|default]

# example: volume $5,000 to $500,000, stop after 100 kept markets, 50 per page, markets ending in 2024
python run_ingest.py 5000 500000 100 50 2024-01-01 2025-01-01
```

| Argument | Meaning | Default |
|---|---|---|
| `min` | minimum market volume in dollars | 5000 |
| `max` | maximum volume, or `none` for no limit | none |
| `target` | stop once this many markets are kept | 20 |
| `page_size` | markets per API page (the API allows at most 100) | 20 |
| `date_min` / `date_max` | window for the market's end date, as `YYYY-MM-DD`, or `default` | 2025-01-01 to 2026-11-01 |

It stops at the target, when the API runs out of pages, or after 30 pages. It saves after every
page, so re-running adds to the database instead of starting over. At the end it prints how many
markets were dropped and why.

TODO: list the exact runs (bands and windows) used to build the current database.

### 2. Run the app

```zsh
streamlit run app.py
```

### 3. Run the tests

```zsh
python -m pytest
```

The tests don't need the database or the internet.

### Helper scripts

- **`check_buckets.py`**: prints the similar-market table for one price in each bucket, both "all"
  and "excluding recurring": the bucket range, the number of markets, YES count, rate, 95% range and
  whether there are enough markets. Use it to check the database after an ingest.
- **`compare.py <polymarket link>`**: prints the raw numbers for one market (fee schedule, best bid
  and ask, spread, and the shares, average price and fee for $100 and $500) so they can be checked
  against what the Polymarket site shows.

## Methodology

### Cost to buy YES

- **Midpoint** is the reference price: halfway between the best bid and the best ask.
  Spread = best ask − best bid.
- **Walking the book:** asks are filled from the lowest price up until the dollar amount is used up.
  If the book runs out first, the card shows how much was actually fillable.
- **Trade cost** = (average fill price − midpoint) × shares bought.
- **Taker fee**, worked out for each price level that was filled and then added up:

  ```
  fee = shares × rate × (price × (1 − price)) ^ exponent
  ```

  `rate` and `exponent` come from the market's own `feeSchedule`. A market with `feesEnabled`
  false has no fee.
- **On buys, the fee is taken out of the shares you receive**, not added to the price. Verified on
  the live site (see [Validation](#validation)): $100 at 0.2¢ shows 47,505 shares, not 50,000.
  Shares after the fee = shares − fee ÷ average price.
- **Total cost** = trade cost + fee.
- **Percentages** are of the amount actually spent, which can be less than the amount asked for
  when the book is thin.
- **Cost per share** on the card = total cost ÷ shares kept after the fee.
- With no bids there is no midpoint, so the trade cost can't be measured. The card shows the average
  price and the fee instead.

### Warnings

| Warning | When it shows |
|---|---|
| Wide spread | the spread is more than 5 ticks (ticks are the market's own tick size) |
| Thin best bid | the best bid is under $100 (price × size) |
| No bids | the bid side of the book is empty |
| No asks | the ask side is empty, so there is nothing to buy |

### Similar-market record

- **Which markets:** resolved Yes/No markets whose end dates run from 2023 to 2026, sports excluded
  (by tag, e.g. NBA, NFL, soccer, UFC). A market counts as resolved only if its final prices are
  ≥ 0.99 / ≤ 0.01, so unclear results are left out. Markets marked as disputed are recorded but are
  not currently excluded.
- **Which price:** the YES price 7 days before the market's anchor time (the earlier of its
  scheduled end date and its actual close time). The nearest point in the price history is used,
  and only if it is within 6 hours of that moment. Otherwise the market is dropped.
- **Price buckets:** the current midpoint is placed in one of these ranges (`BUCKET_EDGES` in
  `trustcheck/stats.py`). A price exactly on an edge goes to the upper bucket:

  `0–1% · 1–5% · 5–10% · 10–20% · 20–30% · 30–50% · 50–70% · 70–100%`
- **95% range:** a Wilson score interval. It stays sensible at 0 or 100% YES, where a simple
  ± formula would claim certainty.
- **Not enough data:** a bucket with fewer than 30 markets (`MIN_SAMPLE`) shows "not enough similar
  markets" instead of a rate.
- **Excluding recurring:** a second line leaves out repeating series, i.e. markets tagged
  `Recurring`, `Tweet Markets`, `Weekly` or `Monthly` (capitalization ignored). Many near-identical
  copies of one series could otherwise dominate a bucket.
- **Why the buckets are narrow at low prices:** in the current data, outcomes change quickly near 0.
  Markets priced under 1% had 0 YES out of 387, while 1–5% had 9 YES out of 276 (3.3%). One wide
  0–5% bucket would blend them and overstate the chance for a 0.2¢ market. There are enough markets
  at low prices to split them and still keep every bucket above 30.

## Limitations

1. **YES-side buys only.** It doesn't cost selling, or buying NO.
2. **One snapshot.** The order book is read once, when the page loads. Prices move, so reload to
   refresh.
3. **Volume-based taker rebates are ignored.** The fee shown is the full taker fee.
4. **Past markets do not predict this one.** The record shows how *other* markets at a similar price
   turned out, not the odds for this market.
5. **Fee rules can change.** The formula follows the fee schedule Polymarket publishes for each
   market today.
6. **The sample leans toward big markets.** The ingest orders by volume, so famous, liquid political
   and event markets are over-represented. That can make the record less reliable for small markets.

## Validation

Polymarket's site compared with PolyChecker on the Phil Murphy market, buying $100 of YES:

| | Polymarket site | PolyChecker |
|---|---|---|
| Best bid / ask | 0.1¢ / 0.2¢ | 0.1¢ / 0.2¢ |
| Spread | 0.1¢ | 0.1¢ |
| Average price | 0.2¢ | 0.2¢ |
| Shares received | 47,505 | 47,505 |

TODO: add the market link and the date of the comparison.

This case is also a test: `test_trade_cost_fee_is_taken_in_shares` in `tests/test_orderbook.py`.
