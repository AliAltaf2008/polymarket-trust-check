# Polymarket Trust Check

> Unofficial, informational, not advice. Not affiliated with Polymarket.
> Market data analytics only: read-only, no trading features.

Paste a Polymarket market link and get a report card: cost to trade, activity,
flags, and how similar past markets actually resolved.

**Status:** private, in development.

## Setup
```zsh
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest
```

## Methodology
_To be written._

## Limitations
1. Ordering by volume gives the most famous and liquid marekts so the samples are skewed towards big political and event markets and will affect how much "similar markets" can be trusted for smaller markets
