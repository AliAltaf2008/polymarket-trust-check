from urllib.parse import urlparse
import json

VALID_HOSTS = {"polymarket.com", "www.polymarket.com"}

def parse_polymarket_url(text):
    text = text.strip()
    if not text:
        raise ValueError("empty link")

    if "://" not in text:
        text = "http://" + text

    parsed = urlparse(text)

    if parsed.hostname not in VALID_HOSTS:
        raise ValueError(f"not a polymarket link: {text}")

    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2 or parts[0] != "event":
        raise ValueError("expected a link like polymarket.com/event/<slug>")

    event_slug = parts[1]
    market_slug = parts[2] if len(parts) > 2 else None
    return event_slug, market_slug



def _has_tokens(market):
    """True only if clobTokenIds is JSON text for a non-empty list, like '["123", "456"]'."""
    # The API sends clobTokenIds as a string, so "[]" is truthy even though it holds no tokens.
    # Parsing it is the only way to tell a real list from an empty or broken one.
    try:
        tokens = json.loads(market.get("clobTokenIds"))
    except (TypeError, ValueError):
        # TypeError: the key is missing (None). ValueError: the text isn't valid JSON.
        return False
    return isinstance(tokens, list) and len(tokens) > 0

def candidate_markets(event, market_slug = None):
    markets = event.get("markets") or []

    if market_slug is not None:
        matches = [m for m in markets if m.get("slug") == market_slug]
        if not matches:
            raise ValueError(f"no market with slug {market_slug!r} in this event")
        return matches

    return [m for m in markets if not m.get("closed") and _has_tokens(m)]


def _volume(markets):
    """Markets trading volume as a number"""
    try:
        return float(markets.get("volumeNum") or 0)
    except (TypeError, ValueError):
        return 0.0

def sort_candidates(markets):
    return sorted(markets, key = _volume, reverse=True)

def choosable(markets):
    """Markets to offer the chooser where it is those that have traded and it goes from highest volume first"""
    traded = [m for m in markets if _volume(m) > 0]
    return sort_candidates(traded or markets)

