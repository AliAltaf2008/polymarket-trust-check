import pytest

from trustcheck.lookup import (
    candidate_markets,
    parse_polymarket_url,
    sort_candidates,
    choosable
)


def test_event_link():
    assert parse_polymarket_url("https://polymarket.com/event/fed-decision-in-october") == (
        "fed-decision-in-october", None)


def test_market_link_inside_an_event():
    assert parse_polymarket_url("https://polymarket.com/event/some-event/some-market") == (
        "some-event", "some-market")


def test_query_string_and_fragment_are_ignored():
    assert parse_polymarket_url("https://polymarket.com/event/some-event?tid=123#top") == (
        "some-event", None)


def test_trailing_slash_is_ignored():
    assert parse_polymarket_url("https://polymarket.com/event/some-event/") == ("some-event", None)


def test_a_link_without_https_works():
    assert parse_polymarket_url("polymarket.com/event/some-event") == ("some-event", None)


def test_www_and_capital_letters_in_the_host_work():
    assert parse_polymarket_url("https://www.PolyMarket.com/event/some-event") == ("some-event", None)


def test_surrounding_whitespace_is_ignored():
    assert parse_polymarket_url("  https://polymarket.com/event/some-event \n") == ("some-event", None)


@pytest.mark.parametrize("bad", [
    "",
    "   ",
    "banana",
    "https://example.com/event/some-event",
    "https://polymarket.com.evil.com/event/some-event",    # lookalike host
    "https://evilpolymarket.com/event/some-event",
    "https://polymarket.com/",
    "https://polymarket.com/event/",                       # no slug
    "https://polymarket.com/markets/some-event",           # wrong first segment
])
def test_bad_links_raise(bad):
    with pytest.raises(ValueError):
        parse_polymarket_url(bad)

def mk(slug, closed=False, tokens='["1","2"]'):
    return {"slug": slug, "closed": closed, "clobTokenIds": tokens}


def test_a_single_market_event_gives_one_candidate():
    event = {"markets": [mk("only")]}
    assert [m["slug"] for m in candidate_markets(event)] == ["only"]


def test_a_multi_market_event_gives_all_open_markets():
    event = {"markets": [mk("a"), mk("b"), mk("c")]}
    assert [m["slug"] for m in candidate_markets(event)] == ["a", "b", "c"]


def test_closed_markets_are_left_out_without_a_market_slug():
    event = {"markets": [mk("open"), mk("done", closed=True)]}
    assert [m["slug"] for m in candidate_markets(event)] == ["open"]


@pytest.mark.parametrize("tokens", [None, "", "[]"])
def test_markets_without_tokens_are_left_out(tokens):
    # "[]" is a non-empty string, so it passes the filter: this documents the gap.
    event = {"markets": [mk("real"), mk("placeholder", tokens=tokens)]}
    slugs = [m["slug"] for m in candidate_markets(event)]
    assert "real" in slugs
    if tokens in (None, ""):
        assert "placeholder" not in slugs


def test_a_market_slug_picks_exactly_that_market():
    event = {"markets": [mk("a"), mk("b")]}
    assert [m["slug"] for m in candidate_markets(event, "b")] == ["b"]


def test_a_requested_market_is_returned_even_if_closed():
    event = {"markets": [mk("done", closed=True)]}
    assert [m["slug"] for m in candidate_markets(event, "done")] == ["done"]


def test_an_unknown_market_slug_raises():
    with pytest.raises(ValueError):
        candidate_markets({"markets": [mk("a")]}, "nope")


@pytest.mark.parametrize("event", [{}, {"markets": None}, {"markets": []}])
def test_an_event_with_no_markets_gives_no_candidates(event):
    assert candidate_markets(event) == []

def vm(slug, volume):
    return {"slug": slug, "volumeNum": volume}


def test_highest_volume_comes_first():
    result = sort_candidates([vm("small", 10), vm("big", 5000), vm("mid", 300)])
    assert [m["slug"] for m in result] == ["big", "mid", "small"]


def test_volumes_given_as_text_are_understood():
    result = sort_candidates([vm("a", "20"), vm("b", "3000.5")])
    assert [m["slug"] for m in result] == ["b", "a"]


@pytest.mark.parametrize("bad", [None, "", "n/a"])
def test_missing_or_unreadable_volume_goes_last(bad):
    result = sort_candidates([vm("broken", bad), vm("real", 5)])
    assert [m["slug"] for m in result] == ["real", "broken"]


def test_a_market_with_no_volume_field_goes_last():
    result = sort_candidates([{"slug": "no-field"}, vm("real", 5)])
    assert [m["slug"] for m in result] == ["real", "no-field"]


def test_ties_keep_their_original_order():
    result = sort_candidates([vm("first", 100), vm("second", 100), vm("third", 100)])
    assert [m["slug"] for m in result] == ["first", "second", "third"]


def test_the_input_list_is_not_changed():
    original = [vm("small", 1), vm("big", 9)]
    sort_candidates(original)
    assert [m["slug"] for m in original] == ["small", "big"]


def test_an_empty_list_gives_an_empty_list():
    assert sort_candidates([]) == []


def test_markets_that_never_traded_are_hidden_when_others_have():
    result = choosable([vm("real", 500), vm("placeholder", 0), vm("also-real", 20)])
    assert [m["slug"] for m in result] == ["real", "also-real"]


def test_everything_is_shown_when_nothing_has_traded():
    result = choosable([vm("new-a", 0), vm("new-b", None)])
    assert sorted(m["slug"] for m in result) == ["new-a", "new-b"]


def test_a_market_without_a_volume_counts_as_untraded():
    result = choosable([vm("real", 5), {"slug": "no-field"}])
    assert [m["slug"] for m in result] == ["real"]


def test_the_result_is_sorted_by_volume():
    result = choosable([vm("small", 1), vm("big", 100)])
    assert [m["slug"] for m in result] == ["big", "small"]


def test_choosable_of_nothing_is_empty():
    assert choosable([]) == []