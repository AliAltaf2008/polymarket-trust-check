import time
from urllib.parse import quote
import httpx

GAMMA_KEYSET_URL = "https://gamma-api.polymarket.com/markets/keyset"
CLOB_PRICES_URL = "https://clob.polymarket.com/prices-history"
CLOB_BOOK_URL = "https://clob.polymarket.com/book"
GAMMA_EVENT_URL = "https://gamma-api.polymarket.com/events/slug/"


def fetch_order_book(token_id):
    """Return the raw order book dict for one token (the YES token's id)."""
    return _get_json(CLOB_BOOK_URL, {"token_id": token_id})

def _get_json(url, params, retries=3):
    for attempt in range(retries):
        try:
            response = httpx.get(url, params = params, timeout = 30)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as err:
            status = err.response.status_code
            retryable = status == 429 or status >= 500
            if not retryable or attempt == retries - 1:
                raise
            wait = 2 ** attempt
            print(f"HTTP {status}. Retrying in {wait}s")
            time.sleep(wait)
        except httpx.RequestError as err:
            if attempt == retries - 1:
                raise
            wait = 2**attempt
            print(f"Request failed ({err}). Retrying in {wait}s...")
            time.sleep(wait)

def fetch_price_history(token_id, start_ts, end_ts, fidelity=60):
    params = {
        "market": token_id,
        "startTs": int(start_ts),
        "endTs": int(end_ts),
        "fidelity": fidelity,
    }

    data = _get_json(CLOB_PRICES_URL, params)

    return data.get("history", [])

DEFAULT_END_DATE_MIN = "2025-01-01T00:00:00Z"
DEFAULT_END_DATE_MAX = "2026-11-01T00:00:00Z"

def build_page_params(cursor=None, limit=20, volume_min=5000, volume_max = None, end_date_min = DEFAULT_END_DATE_MIN, end_date_max = DEFAULT_END_DATE_MAX):
    params = {
        "closed": "true",
        "limit": limit,
        "order": "volumeNum",
        "ascending": "false",
        "end_date_min": end_date_min,
        "end_date_max": end_date_max,
        "volume_num_min": volume_min,
        "include_tag": "true",
    }

    if volume_max is not None:
        params["volume_num_max"] = volume_max
    if cursor:
        params["after_cursor"] = cursor
    return params

def fetch_resolved_page(cursor=None, limit=20, volume_min=5000, volume_max=None, end_date_min = DEFAULT_END_DATE_MIN, end_date_max=DEFAULT_END_DATE_MAX):
    params = build_page_params(
        cursor=cursor, limit=limit, volume_min=volume_min, volume_max=volume_max,
        end_date_min=end_date_min, end_date_max=end_date_max,
    )
    data = _get_json(GAMMA_KEYSET_URL, params)

    return data["markets"], data.get("next_cursor")


def fetch_event_by_slug(slug):
    return _get_json(GAMMA_EVENT_URL + quote(slug, safe=""), {})