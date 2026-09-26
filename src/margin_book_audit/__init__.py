"""margin-book-audit: which forecasts a book expected, and which can be scored.

A bridge from a desk's forecast feed to `arbiter-engine`, built to the method in
that repository's `BRIDGES.md`.

THE DIVISION THIS PACKAGE KEEPS. The engine owns the axioms, the closed
vocabulary of reasons it refuses to judge, and the schema results arrive in. The
domain nouns are here: what an account is, what a margin requirement means, how
a balance moves, and what a desk does about a breach. A forecasting model is
domain knowledge by that division, which is why `forecaster.py` is in this
package and nothing like it is in the engine.
"""

__version__ = "0.1.4"

#: The engine range this package is built against and has been measured on.
#: `battery/probe_pin.py --sweep` is the oracle; `pyproject.toml` carries the
#: same range and the two are pinned equal by `tests/test_pin_is_one_number.py`.
ENGINE_RANGE = ">=0.2.7,<0.3"
