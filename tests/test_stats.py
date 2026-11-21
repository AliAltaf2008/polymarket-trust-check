import pytest

from trustcheck.stats import wilson_interval



def test_ten_of_twenty():
    low, high = wilson_interval(10, 20)
    assert low == pytest.approx(0.2993, abs=0.001)
    assert high == pytest.approx(0.7007, abs=0.001)


def test_seven_of_ten_is_wide():
    low, high = wilson_interval(7, 10)
    assert low == pytest.approx(0.3967, abs=0.001)
    assert high == pytest.approx(0.8922, abs=0.001)


def test_seven_hundred_of_a_thousand_is_narrow():
    # Same 70% rate as the test above, but far more evidence.
    low, high = wilson_interval(700, 1000)
    assert low == pytest.approx(0.6709, abs=0.001)
    assert high == pytest.approx(0.7276, abs=0.001)



def test_zero_of_ten_starts_at_zero_but_is_not_certain():
    low, high = wilson_interval(0, 10)
    assert low == pytest.approx(0.0, abs=0.001)
    assert high == pytest.approx(0.2775, abs=0.001)


def test_ten_of_ten_ends_at_one_but_is_not_certain():
    low, high = wilson_interval(10, 10)
    assert low == pytest.approx(0.7225, abs=0.001)
    assert high == pytest.approx(1.0, abs=0.001)


def test_larger_sample_gives_a_narrower_interval():
    small_low, small_high = wilson_interval(5, 10)
    big_low, big_high = wilson_interval(50, 100)
    assert (big_high - big_low) < (small_high - small_low)


def test_higher_confidence_gives_a_wider_interval():
    low95, high95 = wilson_interval(10, 20, z=1.96)
    low99, high99 = wilson_interval(10, 20, z=2.576)
    assert (high99 - low99) > (high95 - low95)


@pytest.mark.parametrize("successes, n", [(0, 5), (1, 5), (3, 7), (15, 40), (99, 100)])
def test_interval_contains_the_observed_rate(successes, n):
    low, high = wilson_interval(successes, n)
    assert low <= successes / n <= high


@pytest.mark.parametrize("successes, n", [(0, 1), (1, 1), (0, 3), (3, 3), (0, 100), (100, 100)])
def test_result_stays_inside_zero_and_one(successes, n):
    low, high = wilson_interval(successes, n)
    assert 0.0 <= low <= high <= 1.0


def test_mirror_symmetry():
    low, high = wilson_interval(3, 10)
    mirror_low, mirror_high = wilson_interval(7, 10)
    assert low == pytest.approx(1 - mirror_high)
    assert high == pytest.approx(1 - mirror_low)



def test_zero_markets_raises():
    with pytest.raises(ValueError):
        wilson_interval(0, 0)


def test_negative_successes_raises():
    with pytest.raises(ValueError):
        wilson_interval(-1, 10)


def test_more_successes_than_markets_raises():
    with pytest.raises(ValueError):
        wilson_interval(11, 10)