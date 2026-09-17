"""The engine range is written once.

A NUMBER WRITTEN TWICE WILL DRIFT. The package states its range for a reader and
`pyproject.toml` states it for a resolver, and the two disagreeing means a
consumer installs a release the package believes it does not support -- silently,
because nothing compares them at install time.
"""

from __future__ import annotations

import pathlib
import re

from margin_book_audit import ENGINE_RANGE

PYPROJECT = pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml"


def test_the_extra_and_the_constant_agree():
    text = PYPROJECT.read_text(encoding="utf-8")
    declared = re.findall(r'"arbiter-engine([^"]*)"', text)
    assert declared, "pyproject declares no arbiter-engine dependency"
    assert set(declared) == {ENGINE_RANGE}, (
        f"pyproject says {declared} and the package says {ENGINE_RANGE!r}")


def test_the_engine_is_an_extra_and_not_a_hard_dependency():
    """Stage one runs without it; making it required would make a stage that
    needs nothing refuse to install without everything."""
    text = PYPROJECT.read_text(encoding="utf-8")
    core = text.split("[project.optional-dependencies]")[0]
    assert "arbiter-engine" not in core
