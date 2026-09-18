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


def test_the_readme_states_the_same_range():
    """The THIRD copy, and the one that drifted.

    This file's own premise is that a number written twice will drift, and it
    compared two places while the range was written in three. The README said
    `>=0.1.16` through the whole life of the 0.1.17 floor -- a reader deciding
    whether their install was supported would have been told the wrong thing by
    the only document written for them, and every test here passed.

    Matched loosely on purpose: the README is prose and may reasonably say the
    range inside a sentence, in backticks, more than once. What it may not do is
    state a DIFFERENT one.
    """
    readme = (pathlib.Path(__file__).resolve().parents[1]
              / "README.md").read_text(encoding="utf-8")
    stated = set(re.findall(r">=0\.\d+\.\d+,<\d+\.\d+", readme))
    assert stated, "the README states no engine range at all"
    assert stated == {ENGINE_RANGE}, (
        f"the README states {sorted(stated)} and the package says "
        f"{ENGINE_RANGE!r}. Earlier floors belong in prose that names the "
        f"version without restating the range, or this goes red every time "
        f"one is recorded.")
