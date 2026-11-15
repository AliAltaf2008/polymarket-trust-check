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


## Discoveries made from calling Gamma and CLOB
1. old resolved markets from around 2020 have outcomePrices that can be ['0', '0'] or very close to 0 or very close to 1
2. default ordering of sortbyvolume will return the latest, highest volume markets which will heavily skew the data
3. closedTime is the true close. endDate isnt reliable as closedTime varies within days or even months from it
4. Price history works for resovled markets and returns hourly points -> tested on two markets in 2025
5. Need a spread of reference prices ideally from plenty of markets in the 10-90 percent range
6. Category is None in recent markets but does exist for old markets like ones back in 2020
7. Tags are useful to filter markets based on sports, politics, etc. But sportsMarketType and gameId are not reliable for futures-style sports markets
8. keyset call works with order=volumeNum date filters and volume_num_min
8. Cluster by event_id. Many markets share an event which will cause clustering when sampling markets