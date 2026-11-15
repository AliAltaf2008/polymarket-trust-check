"""Fetch markets from the Gamma API and save them to data/markets.json."""
import httpx
import json
from pathlib import Path
import time

GAMMA_URL = "https://gamma-api.polymarket.com/markets"

def fetch_markets(limit=100, offset=0, closed=False, retries=3):
    params = {"limit": limit, "offset": offset, "closed": str(closed).lower()}

    for attempt in range(retries):
        try:
            response = httpx.get(GAMMA_URL, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as err:
            if attempt == retries - 1:
                raise #If the retries are at their max then raise the error again to exit out of the loop
            wait = 2 ** attempt # exponential backoff for the server
            print(f"Request failed with err. Trying in {wait}s")
            time.sleep(wait) #waits and then executes the loop again using expontential backoff assigned to wait before

def clean_market(raw):
    """Cleans the api call into useful data"""
    events = raw.get("events") or []
    return {
        "id": raw["id"],
        "question": raw["question"],
        "slug": raw["slug"],
        "condition_id": raw["conditionId"],
        "event_id": events[0]["id"] if events else None,
        "end_date": raw.get("endDate"),
        "volume": float(raw.get("volumeNum") or 0),
        "liquidity": float(raw.get("liquidityNum") or 0),
        "outcomes": json.loads(raw.get("outcomes") or "[]"),
        "outcome_prices": [float(p) for p in json.loads(raw.get("outcomePrices") or "[]")],
        "token_ids": json.loads(raw.get("clobTokenIds") or "[]"),
        "closed": raw["closed"],
    }

def main():
    raw_markets = fetch_markets(limit=100)
    markets = []
    for m in raw_markets:
        markets.append(clean_market(m))
    Path("data").mkdir(exist_ok=True)
    with open("data/markets.json", "w") as f:
        json.dump(markets, f, indent=2)
    print(f"Saved {len(markets)} markets to data/markets.json")

if __name__ == "__main__":
    main()

