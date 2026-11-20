import time 
from collections import Counter

import httpx

from trustcheck.api import fetch_price_history, fetch_resolved_page
from trustcheck.ingest import build_record, nearest_price, reference_time, skip_reason

DAY = 86400
MAX_REFERENCE_GAP = 6 * 3600

def ingest_page(raw_markets):
    kept = []
    counts = Counter()
    for raw in raw_markets:
        try:
            record = build_record(raw)
        except (KeyError, ValueError, TypeError) as err:
            counts["build_error"] += 1
            print(f"build_record failed for market {raw.get('id')}: {err!r}")
            continue

        reason = skip_reason(record)
        if reason is not None:
            counts[reason] += 1
            continue

        ref = reference_time(record["close_time"])

        try:
            history = fetch_price_history(record["yes_token_id"], ref- DAY, ref+ DAY)
        except httpx.HTTPError as err:
            counts["history_error"] += 1
            print(f"history failed for market {record['id']}: {err!r}")
        time.sleep(0.3)

        price = nearest_price(history, ref, max_gap=MAX_REFERENCE_GAP)
        if price is None:
            counts["no_ref_price"] += 1
            continue

        record["ref_price"] = price
        kept.append(record)

    return kept, counts


if __name__ == "__main__":
    raw_markets, _ = fetch_resolved_page(limit=20)
    kept, counts = ingest_page(raw_markets)

    processed = len(raw_markets)
    print(f"\nProcessed {processed} markets, kept {len(kept)}")

    print("\nDropped:")
    for reason, n in counts.most_common():
        print(f" {reason: <14} {n}")

    #Every market must be counted excatly once
    total = len(kept) + sum(counts.values())
    print(f"\nCounts add up: {'OK' if total == processed else f'MISMATCH ({total} vs {processed})'}")

    #Count of how many ref prices are not stuck near 0 or 1
    mid = [r for r in kept if 0.10<= r["ref_price"] <=0.90]
    print(f"Kept with ref_price between 10% and 90%: {len(mid)} of {len(kept)}")

    print("\nKept Markets:")
    for r in kept:
        print(f"  {r['ref_price']:.3f} | {r['winner']:<3} | {r['question'][:50]}")