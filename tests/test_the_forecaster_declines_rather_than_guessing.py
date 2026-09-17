"""The reference model, and the cases where it refuses.

A FORECAST THE ENGINE CANNOT TELL FROM A GUESS IS WORSE THAN A GAP, because the
gap is reportable and the guess is scored. So this model returns None rather
than emitting an interval it cannot support, and the bridge files nothing.

IT IS NOT A GOOD FORECASTER and this file does not claim it is. That claim has
to be earned per book, against the random walk the engine files beside it.
"""

from __future__ import annotations

import math

import pytest

from margin_book_audit.forecaster import LEVELS, MINIMUM_RESIDUALS, predict


def _series(n, start=100.0, step=0.5):
    return [start + step * i for i in range(n)]


def test_a_short_series_declines():
    assert predict("a", _series(MINIMUM_RESIDUALS)) is None


def test_an_empty_series_declines():
    assert predict("a", []) is None


def test_a_long_enough_series_produces_all_three_levels():
    prediction = predict("a", _series(40))
    assert prediction is not None
    assert set(prediction.quantiles) == {name for name, _ in LEVELS}


def test_the_interval_is_ordered():
    """An interval that has inverted is not an interval, and handing one to the
    engine would be handing it something that cannot be right."""
    prediction = predict("a", _series(40))
    q = prediction.quantiles
    assert q["q05"] <= q["q50"] <= q["q95"]


def test_the_residual_count_travels_with_the_interval():
    """A spread measured over nine residuals and over nine hundred are
    different statements the interval alone presents identically."""
    prediction = predict("a", _series(40))
    assert prediction.residuals_n >= MINIMUM_RESIDUALS


def test_a_longer_horizon_widens_the_interval():
    near = predict("a", _series(60), steps_ahead=1)
    far = predict("a", _series(60), steps_ahead=9)
    width = lambda p: p.quantiles["q95"] - p.quantiles["q05"]
    assert width(far) > width(near)
    # Independent increments: the spread scales with the square root of the
    # horizon. THAT IS THIS MODEL'S ASSUMPTION, stated where it can be argued
    # with rather than buried in a core that refuses to make it.
    assert width(far) == pytest.approx(width(near) * math.sqrt(9), rel=1e-9)


def test_a_flat_series_gives_a_degenerate_but_ordered_interval():
    """A series that never moves has no spread to measure. The model must not
    invent one, and must not emit an inverted interval either."""
    prediction = predict("a", [100.0] * 40)
    assert prediction is not None
    q = prediction.quantiles
    assert q["q05"] <= q["q50"] <= q["q95"]


def test_a_nan_never_reaches_the_interval():
    prediction = predict("a", _series(40) + [float("nan")])
    if prediction is not None:
        assert all(v == v for v in prediction.quantiles.values())
