import math
import bisect
import json
from trustcheck.ingest import is_recurring
BUCKET_EDGES = [0.0, 0.05, 0.30, 0.50, 0.70, 1.0]
NUM_BUCKETS = len(BUCKET_EDGES) - 1
MIN_SAMPLE = 30

def wilson_interval(successes, n, z=1.96):
    if n<= 0:
        raise ValueError("n must be at least one")
    if successes < 0 or successes > n:
        raise ValueError("successes must be within 0 and n")

    #Observed rate
    p = successes / n

    z2 = z * z

    denominator = 1 + z2 / n

    #Center is not exactly at p and is pulled towards 0.5 so it does not claim certainty at 0% or 100%
    center = (p + z2 / (2* n)) / denominator
    half_width = z * math.sqrt(p * (1-p) / n+ z2 / (4 * n * n)) / denominator

    low = max(0.0, center - half_width)
    high = min(1.0, center + half_width)
    return low, high

def bucket_index(price):
    """Return which bucket a price falls into"""

    #Price exactly at the edge will go in the upper bucket
    
    #Bad Inputs/Values
    if not (0.0 <= price <= 1.0):
        raise ValueError(f"Price must be in between 0 and 1 and {price} was given")

    #bisect_right counts how many edges are <=price then subtracting 1 from the number of edge cases the price is greater than decides the bucket number
    index = bisect.bisect_right(BUCKET_EDGES, price) - 1

    #Ensure that index is not out of range of the buckets
    return min(index, NUM_BUCKETS - 1)

def bucket_bounds(index):
    if not (0 <= index < NUM_BUCKETS):
        raise ValueError(f"bucket index must be 0 to {NUM_BUCKETS-1}, got {index}")
    return BUCKET_EDGES[index], BUCKET_EDGES[index+1]

def similar_record(conn, price, exclude_recurring = False):
    target = bucket_index(price)

    rows = conn.execute(
        "SELECT ref_price, winner, tags FROM markets "
        "WHERE winner IS NOT NULL AND ref_price IS NOT NULL" 
    ).fetchall()

    n = 0
    yes = 0
    for ref_price, winner, tags in rows:
        if bucket_index(ref_price) != target:
            continue

        if exclude_recurring and tags is not None:
            if is_recurring(json.loads(tags)):
                continue
        n += 1
        if winner == "Yes":
            yes+=1

    if n == 0:
        rate = None
        interval = None
    else: 
        rate = yes / n
        interval = wilson_interval(yes, n)

    return {
        "bucket": bucket_bounds(target),
        "n": n,
        "yes": yes,
        "rate": rate,
        "interval": interval,
        "enough": n >= MIN_SAMPLE,
    }
