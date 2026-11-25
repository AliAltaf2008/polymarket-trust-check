import sys
import time
from collections import Counter
from datetime import datetime

import httpx

from trustcheck.api import (
    DEFAULT_END_DATE_MAX,
    DEFAULT_END_DATE_MIN,
    fetch_price_history,
    fetch_resolved_page,
)
from trustcheck.db import get_connection, init_db, upsert_record
from trustcheck.ingest import build_record, nearest_price, reference_time, skip_reason

DAY = 86400
MAX_REFERENCE_GAP = 6 * 3600

def ingest_page(raw_markets, verbose=True):
    kept = []
    counts = Counter()
    for i, raw in enumerate(raw_markets, start=1):
        #Verbose turns off per-market terminal outputs so hundreds of markets are not in the console when false
        if verbose:
            print(f"[{i}/{len(raw_markets)}] {raw.get('question', '')[:50]}", flush=True)
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

        ref = reference_time(record["anchor_time"])

        try:
            history = fetch_price_history(record["yes_token_id"], ref- DAY, ref+ DAY)
        except httpx.HTTPError as err:
            counts["history_error"] += 1
            print(f"history failed for market {record['id']}: {err!r}")
            continue
        time.sleep(0.3)

        price = nearest_price(history, ref, max_gap=MAX_REFERENCE_GAP)
        if price is None:
            counts["no_ref_price"] += 1
            continue

        record["ref_price"] = price
        record["ref_ts"] = ref
        kept.append(record)

    return kept, counts

def to_iso_utc(text):
    if "T" in text:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
        return text
    datetime.strptime(text, "%Y-%m-%d")
    return f"{text}T00:00:00Z"

def parse_args(argv):
    """Turn command-line arguments into (volume_min, volume_max, limit)"""
    volume_min = float(argv[0]) if len(argv) > 0 else 5000
    if len(argv) > 1 and argv[1].lower() != "none":
        volume_max = float(argv[1])
    else:
        volume_max = None
    target_kept = int(argv[2]) if len(argv) > 2 else 20
    page_size = int(argv[3]) if len(argv) > 3 else 20

    if len(argv) > 4 and argv[4].lower() != "default":
        end_date_min = to_iso_utc(argv[4])
    else:
        end_date_min = DEFAULT_END_DATE_MIN
    if len(argv) > 5 and argv[5].lower() != "default":
        end_date_max = to_iso_utc(argv[5])
    else:
        end_date_max = DEFAULT_END_DATE_MAX

    def as_dt(s):
        return datetime.fromisoformat(s.replace("Z", "+00:00"))

    if as_dt(end_date_min) >= as_dt(end_date_max):
        raise ValueError(f"end_date_min {end_date_min} must be before end_date_max {end_date_max}")

    return volume_min, volume_max, target_kept, page_size, end_date_min, end_date_max

def collect(volume_min, volume_max, target_kept, max_pages=30, page_size=20, verbose=True,
            end_date_min=DEFAULT_END_DATE_MIN, end_date_max=DEFAULT_END_DATE_MAX):
    cursor = None
    total_kept = 0
    processed = 0
    total_counts = Counter()
    ref_prices = []
    stop_reason = "page cap reached"

    conn = get_connection()
    init_db(conn)
    try:
        for page in range(1, max_pages + 1):
            try:
                raw_markets, cursor = fetch_resolved_page(
                    cursor=cursor, limit=page_size,
                    volume_min=volume_min, volume_max=volume_max,
                    end_date_min=end_date_min, end_date_max=end_date_max,
                )
            except httpx.HTTPError as err:
                stop_reason = f"request failed: {err!r}"
                break

            if not raw_markets:
                stop_reason = "empty page"
                break

            kept, counts = ingest_page(raw_markets, verbose=verbose)
            for record in kept:
                upsert_record(conn, record)

            processed += len(raw_markets)
            total_kept += len(kept)
            total_counts.update(counts)
            ref_prices.extend(r["ref_price"] for r in kept)

            print(f"Page {page}: processed {processed}, kept {total_kept}/{target_kept}," f"dropped {dict(total_counts)}", flush=True)

            if total_kept >= target_kept:
                stop_reason = "target reached"
                break
            if not cursor:
                stop_reason = "no more pages"
                break
            time.sleep(0.5)

    finally:
        conn.close()

    return total_kept, processed, total_counts, ref_prices, stop_reason


if __name__ == "__main__":
    (volume_min, volume_max, target_kept, page_size,
     end_date_min, end_date_max) = parse_args(sys.argv[1:])
    print(f"Band: volume {volume_min:,.0f} to {volume_max if volume_max is not None else 'no limit'}, "
          f"ends {end_date_min[:10]} to {end_date_max[:10]}, "
          f"target {target_kept} kept, pages of {page_size}")

    started = time.time()
    kept_n, processed, counts, ref_prices, stop_reason = collect(
        volume_min, volume_max, target_kept, page_size=page_size,
        verbose=(target_kept <= 50),
        end_date_min=end_date_min, end_date_max=end_date_max,
    )
    elapsed = time.time() - started

    print(f"\nStopped: {stop_reason}")
    print(f"Processed {processed} markets, kept {kept_n} (saved to the database), "
          f"{elapsed:.0f} seconds")

    print("\nDropped:")
    for reason, n in counts.most_common():
        print(f"  {reason:<14} {n}")

    total = kept_n + sum(counts.values())
    print(f"\nCounts add up: {'OK' if total == processed else f'MISMATCH ({total} vs {processed})'}")

    mid = [p for p in ref_prices if 0.10 <= p <= 0.90]
    print(f"Kept with ref_price between 10% and 90%: {len(mid)} of {kept_n}")
