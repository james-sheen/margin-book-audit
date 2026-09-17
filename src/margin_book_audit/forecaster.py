"""A reference forecaster. It lives HERE because a model is domain knowledge.

THE ENGINE CARRIES NO MODEL, deliberately: putting one there would put *which
indicators matter and how they move* into a core built to carry neither. What
the engine keeps is the contract a forecast arrives in and the books kept on it,
and that asymmetry is the whole argument for the split -- models change monthly,
and the scoring contract can stand for a decade.

WHAT THIS ONE IS. An exponentially-weighted level, with the spread taken from
the model's OWN residuals rather than from a distribution assumed for it. A
margin balance is not Gaussian and saying so costs nothing here: the residual
quantiles are whatever the series produced, and the count they were measured
over travels with them so a reader can see how thin the tails are.

WHAT IT IS NOT. It is not a good forecaster, and this package never claims it
is -- the engine scores it against a random walk exactly so that claim has to be
earned per book. It is here so the bridge has something to feed, and so the
comparison has a second entrant.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Sequence, Tuple

#: The levels this model emits. `q05` and `q95` are what the engine requires;
#: `q50` is the point estimate a desk reads.
LEVELS: Tuple[Tuple[str, float], ...] = (("q05", 0.05), ("q50", 0.50), ("q95", 0.95))

#: Below this many residuals the spread is not a measurement. The model declines
#: rather than emitting an interval it cannot support -- the same rule the
#: engine applies to its own projector, applied on this side of the line.
MINIMUM_RESIDUALS = 8

MODEL_ID = "ewma_v1"


@dataclass(frozen=True)
class Prediction:
    account_id: str
    quantiles: Dict[str, float]
    residuals_n: int


def _ewma(series: Sequence[float], alpha: float) -> float:
    level = series[0]
    for value in series[1:]:
        level = alpha * value + (1.0 - alpha) * level
    return level


def _empirical_quantile(sorted_values: Sequence[float], level: float) -> float:
    """Linear interpolation between order statistics. No distribution assumed."""
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = level * (len(sorted_values) - 1)
    low = int(math.floor(position))
    high = min(low + 1, len(sorted_values) - 1)
    weight = position - low
    return sorted_values[low] * (1.0 - weight) + sorted_values[high] * weight


def predict(account_id: str, history: Sequence[float], *,
            alpha: float = 0.3, steps_ahead: float = 1.0) -> Optional[Prediction]:
    """A forecast, or None when the series cannot support one.

    `None` is not a failure to handle later -- it is the honest answer, and the
    caller files nothing rather than filing an interval invented from too few
    points. A forecast the engine cannot distinguish from a guess is worse than
    a gap, because the gap is reportable and the guess is scored.
    """
    values = [float(v) for v in history if v == v]
    if len(values) < MINIMUM_RESIDUALS + 2:
        return None

    residuals = []
    level = values[0]
    for value in values[1:]:
        residuals.append(value - level)
        level = alpha * value + (1.0 - alpha) * level

    if len(residuals) < MINIMUM_RESIDUALS:
        return None

    # Spread grows with the square root of the horizon under an independent-
    # increment assumption. THAT ASSUMPTION IS THIS MODEL'S, not the engine's,
    # and it is the kind of thing the engine declines to make on a producer's
    # behalf -- so it is stated here, where it can be argued with.
    scale = math.sqrt(max(steps_ahead, 1.0))
    ordered = sorted(residuals)
    centre = _ewma(values, alpha)
    quantiles = {
        name: centre + scale * _empirical_quantile(ordered, level_value)
        for name, level_value in LEVELS}
    # An interval that has inverted is not an interval. Monotonicity in the
    # levels is a property of quantiles, and emitting a record without it would
    # hand the engine something to score that cannot be right.
    if not (quantiles["q05"] <= quantiles["q50"] <= quantiles["q95"]):
        return None
    return Prediction(account_id, quantiles, len(residuals))
