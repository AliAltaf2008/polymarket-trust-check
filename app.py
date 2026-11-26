import json
from datetime import datetime, timezone

import streamlit as st

from trustcheck.api import fetch_event_by_slug, fetch_order_book
from trustcheck.db import get_connection
from trustcheck.lookup import candidate_markets, choosable, parse_polymarket_url
from trustcheck.orderbook import parse_book
from trustcheck.report import build_report, cost_line, cost_per_share, similar_line

st.set_page_config(page_title="Polychecker", page_icon="🔍", layout="centered")

BLUE = "#4c6fff"    # trade cost
AMBER = "#ffb020"   # fee

FLAG_TEXT = {
    "no_bids": "Nobody is bidding to buy this market right now, so there is no midpoint and the trade cost can't be measured.",
    "no_asks": "Nobody is selling YES shares right now, so there is nothing to buy.",
    "wide_spread": "The gap between the best buy price and the best sell price is wide (more than 5 ticks), so the midpoint may not reflect a price you could actually get.",
    "thin_best_bid": "The best bid is under $100 of buying interest, so the midpoint may be misleading.",
}


def esc(text):
    # Streamlit treats $...$ as math, so a backslash makes each $ print as a plain dollar sign.
    return text.replace("$", "\\$")


def cents(price):
    """Price in cents. Under 1 cent we need two decimals, or 0.15 cents shows as 0.1 cents."""
    c = price * 100
    return f"{c:.2f}¢" if c < 1 else f"{c:.1f}¢"


def cost_bar(c, max_pct):
    """One horizontal bar: blue = trade cost, amber = fee, both scaled so the biggest bar fills the track.
    &#36; is the HTML code for a dollar sign (same math problem as esc, different fix)."""
    base = c["spent"] * max_pct
    trade_w = max(c["cost_dollars"], 0) / base * 100
    fee_w = c["fee"] / base * 100
    return (
        '<div style="display:flex;align-items:center;gap:10px;margin:8px 0">'
        f'<div style="width:70px;font-weight:600">&#36;{c["dollars"]:,}</div>'
        '<div style="flex:1;background:rgba(128,128,128,.18);border-radius:6px;height:18px;'
        'display:flex;overflow:hidden">'
        f'<div style="width:{trade_w:.1f}%;background:{BLUE}"></div>'
        f'<div style="width:{fee_w:.1f}%;background:{AMBER}"></div></div>'
        f'<div style="width:60px;text-align:right;font-weight:600">{c["total_pct"]:.1%}</div>'
        '</div>'
    )


def range_bar(lo, hi, rate):
    """A 0-100% track, a shaded stretch for the 95% range and a dark tick for the observed YES rate."""
    return (
        '<div style="position:relative;height:14px;background:rgba(128,128,128,.18);'
        'border-radius:8px;margin:14px 0 4px">'
        f'<div style="position:absolute;left:{lo * 100:.1f}%;width:{(hi - lo) * 100:.1f}%;height:14px;'
        f'background:{BLUE};opacity:.45;border-radius:8px"></div>'
        f'<div style="position:absolute;left:{rate * 100:.1f}%;top:-3px;width:4px;height:20px;'
        f'background:{BLUE};border-radius:2px"></div></div>'
        '<div style="display:flex;justify-content:space-between;font-size:12px;opacity:.6">'
        '<span>0%</span><span>100%</span></div>'
    )


@st.cache_data(ttl=60)
def load_options(event_slug, market_slug):
    """Cached for 60s: Streamlit re-runs this file on every click, and this stops each click from re-downloading the event."""
    event = fetch_event_by_slug(event_slug)
    return choosable(candidate_markets(event, market_slug))


# ---------- Header ----------
st.markdown(
    """
    <div style="text-align:center;padding:1.5rem 0 0.5rem">
      <div style="font-size:3.2rem;font-weight:800;letter-spacing:-1px;line-height:1.1">
        <span>🔍</span>
        <span style="background:linear-gradient(90deg,#4c6fff,#9b5cff);
                     -webkit-background-clip:text;-webkit-text-fill-color:transparent">PolyChecker</span>
      </div>
      <div style="font-size:1.1rem;opacity:.8;margin-top:.5rem">
        See what a Polymarket trade would <b>really cost</b>,<br>and how similar markets turned out.
      </div>
      <div style="font-size:.85rem;opacity:.55;margin-top:.6rem">
        Unofficial and not affiliated with Polymarket. Informational only, not advice.
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

url = st.text_input("Polymarket link", placeholder="https://polymarket.com/event/...",
                    label_visibility="collapsed")

if url:
    # 1. Link -> event -> markets.
    try:
        event_slug, market_slug = parse_polymarket_url(url)
        with st.spinner("Finding the market..."):
            options = load_options(event_slug, market_slug)
    except ValueError as e:
        st.error(f"Couldn't use that link: {e}")
        st.stop()

    if not options:
        st.warning("No tradable markets found in this event.")
        st.stop()

    # 2. One market: nothing to choose. Several: the dropdown (typing filters it).
    if len(options) == 1:
        market = options[0]
    else:
        market = st.selectbox(
            f"{len(options)} markets in this event. Pick one (type to search)",
            options,
            format_func=lambda m: m["question"],
        )

    # 3. Live order book, then the report.
    try:
        with st.spinner("Reading the live order book..."):
            yes_token = json.loads(market["clobTokenIds"])[0]
            book = parse_book(fetch_order_book(yes_token))
    except Exception as e:   # network trouble or an unexpected response: show it, don't crash the page
        st.error(f"Couldn't load the order book: {e}")
        st.stop()

    conn = get_connection()
    try:
        report = build_report(market, book, conn)
    finally:
        conn.close()

    # ---------- Card: headline ----------
    st.header(report["question"])

    m1, m2, m3 = st.columns(3)
    if report["mid"] is None:
        m1.metric("Midpoint", "none")
        m2.metric("Spread", "none")
    else:
        m1.metric("Midpoint (YES)", cents(report["mid"]),
                  help="The price halfway between the best buy offer and the best sell offer.")
        m2.metric("Spread", cents(report["spread"]),
                  help="The gap between the best buy offer and the best sell offer. Wider usually means a more expensive trade.")
    m3.metric("Warnings", len(report["flags"]))

    for code in report["flags"]:
        st.warning(FLAG_TEXT.get(code, code), icon="⚠️")

    # ---------- Card: cost ----------
    with st.container(border=True):
        st.subheader("Cost to buy YES now")
        costs = report["costs"]
        measurable = [c for c in costs if c["total_cost"] is not None]

        if measurable:
            max_pct = max(c["total_pct"] for c in measurable)
            if max_pct > 0:
                st.markdown(
                    "".join(cost_bar(c, max_pct) for c in measurable)
                    + f'<div style="font-size:13px;opacity:.75">'
                      f'<span style="color:{BLUE}">■</span> trade cost &nbsp; '
                      f'<span style="color:{AMBER}">■</span> fee &nbsp; '
                      f'(share of the amount you spend)</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.success("No measurable cost over the midpoint at these sizes.")
        else:
            st.info("There are no bids, so the trade cost can't be measured against a midpoint.")

        st.markdown("")
        cols = st.columns(len(costs))
        for col, c in zip(cols, costs):
            with col:
                if c["shares"] == 0:
                    col.metric(f"${c['dollars']:,}", "n/a")
                    col.caption("nothing to buy")
                elif c["total_cost"] is None:
                    col.metric(f"${c['dollars']:,}", cents(c["avg_price"]),
                               help="Average price per share. No trade cost without a midpoint.")
                    col.caption(esc(f"fee ${c['fee']:.2f}"))
                else:
                    col.metric(f"${c['dollars']:,}", f"{c['total_pct']:.1%}")
                    col.caption(esc(f"${c['total_cost']:.2f} total = ${c['cost_dollars']:.2f} cost + ${c['fee']:.2f} fee"))
                    # None means it can't be measured, so the line is skipped rather than showing a fake number.
                    per_share = cost_per_share(c)
                    if per_share is not None:
                        col.caption(f"≈ {cents(per_share)} per share above the midpoint")

                # NEW: shares you'd receive. Skipped when nothing could be bought.
                if c["shares"] > 0:
                    col.caption(f"≈ {c['shares_net']:,.0f} shares after the fee")

                if c["unfilled"] > 0:
                    col.caption(esc(f"⚠️ only ${c['spent']:.2f} fillable"))

        with st.expander("Show the same numbers as sentences"):
            for c in costs:
                st.markdown(esc(cost_line(c)))

    # ---------- Card: similar markets ----------
    with st.container(border=True):
        st.subheader("Similar-market record")
        st.caption("How resolved markets in the same price range turned out.")
        for label, key in (("All similar markets", "similar_all"), ("Excluding recurring", "similar_no_recurring")):
            s = report[key]
            st.markdown(f"**{label}**")
            if s is not None and s["enough"] and s["interval"] is not None:
                lo, hi = s["interval"]
                st.markdown(range_bar(lo, hi, s["rate"]), unsafe_allow_html=True)
            st.caption(esc(similar_line(label, s)))

        # Shown once, under both record lines: this market trades less than anything it is compared with.
        volume, floor = report["volume"], report["sample_floor"]
        if volume is not None and floor is not None and volume < floor:
            st.info(esc(f"This market has less trading than any market in the record "
                        f"(about ${volume:,.0f} vs. at least ${floor:,.0f}), "
                        f"so the comparison may not fit it well."))

    # ---------- Footer ----------
    with st.expander("What do these numbers mean?"):
        st.markdown(
            "- **Midpoint**: halfway between the best price to buy and the best price to sell.\n"
            "- **Trade cost**: how much more than the midpoint you'd pay on average, because buying uses up the cheapest offers first.\n"
            "- **Fee**: Polymarket's taker fee for buying at the current price.\n"
            "- **Similar-market record**: how often YES happened among resolved markets in the same price range. "
            "The shaded stretch is the 95% range; the tick is the observed rate."
        )
    st.caption(f"Order book snapshot: {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} UTC. "
               "Prices change; reload to refresh.")
    st.caption("Record covers resolved non-sports markets from 2023 to 2026 with a price "
               "recorded about 7 days before close. Past markets do not predict this one.")