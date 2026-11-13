# API Notes

Read-only use of Polymarket's public, documented APIs. No auth, no wallet.

| API   | Base URL                            | Used for                         |
|-------|-------------------------------------|----------------------------------|
| Gamma | https://gamma-api.polymarket.com    | Market/event discovery           |
| CLOB  | https://clob.polymarket.com         | Order books, prices-history      |
| Data  | https://data-api.polymarket.com     | Trades                           |

## Log
- 2026-11-13: Emailed Polymarket support to confirm read-only research use. Reply: _pending_

## Field quirks
- `outcomePrices` (and similar) come back as JSON strings -> `json.loads`.
- `category`: _check how often it's filled in_

## The three API checks (Sat Nov 14)
1. Price history available for resolved markets? _result:_
2. Which field gives the winning outcome? _result:_
3. Do trades identify unique traders? _result:_
