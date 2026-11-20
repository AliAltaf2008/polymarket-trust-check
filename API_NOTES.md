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


# API Filter Test (Nov 19)
1. umaResolutionStatuses implies resolved at the end since it repeats proposed/disputed pairs that never end in resolved, but if you call umaResolutionStatus it returns resolved so I am assuming these repeated pairs imply resolved
2. 7 of the 20 markets were disputed which requires heavy analysis so I will see if disputed markets heavily influence the data and if so, I will filter disputed markets out.
3. Keep disputed markets as a flag for now and exclude it later if necessary

# Price History Test on 3 Markets (Nov 19)
1. price-history with the YES token and the fidelity=60 works for resolved markets
2. Token check passed
3. Sparse markets have gaps in price points despite API call requesting hourly price points. Suggests that the price movement is too stale to require a price point but will require further research