import json


events = []

with open("samples/samples.json") as f:
    markets = json.load(f)

top3 = sorted(markets, key= lambda m: m["volume"], reverse = True)[:3]

for m in top3:
    print(f"{m["question"]}: {m['volume']}")

counts={}

for m in markets:
    cat = m["category"]
    counts[cat] = counts.get(cat, 0) + 1




