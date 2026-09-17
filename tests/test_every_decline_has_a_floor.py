"""The decline vocabulary is this package's requirements document.

THE ENGINE PUBLISHES A CLOSED SET per discipline, and an unhandled member is not
a gap in coverage -- it is a run that reports INCOMPLETE for a book that is
merely incomplete, which is the worst of both readings. The first floor table
here was written from imagination and missed three of the six reasons the
forecasts leg actually emits; the corpus run reported a broken audit.

DERIVED, NEVER TRANSCRIBED. Reading the set from the engine is the whole point:
a list copied into this repository would be a second record of a fact the engine
already owns, and the two would drift on the first release that adds a reason.
"""

from __future__ import annotations

import pytest

from conftest import needs_engine
from margin_book_audit.floors import CLEAN, DECLINE_FLOORS, FINDINGS, \
    INCOMPLETE, compose, floor_for_decline, floor_for_finding


def _published():
    from arbiter_engine.subenvelope import VOCABULARIES
    return set(VOCABULARIES["forecasts"]) | set(VOCABULARIES["shadow"])


@needs_engine
def test_every_published_reason_has_a_floor():
    missing = sorted(_published() - set(DECLINE_FLOORS))
    assert not missing, (
        f"{missing} can be emitted by the legs this package reads and no floor "
        f"rules on them, so each would fall through to INCOMPLETE and report a "
        f"broken audit for a book that merely has a gap")


@needs_engine
def test_no_floor_rules_on_a_reason_that_cannot_happen():
    """A row for a reason the engine cannot emit is a rule nobody will ever
    exercise, and it reads as coverage."""
    stray = sorted(set(DECLINE_FLOORS) - _published())
    assert not stray, f"{stray} are floored here and not in the published set"


def test_an_unknown_reason_fails_closed():
    """A reason nobody has ruled on must not read as clean."""
    assert floor_for_decline("a_reason_from_a_later_release") == INCOMPLETE


def test_the_normal_state_of_a_fresh_forecast_is_not_a_finding():
    """Every forecast is ungradeable until its outcome is observed. Flooring
    that higher makes a correct run red on every cycle."""
    assert floor_for_decline("ungradeable") == CLEAN


def test_the_gap_this_package_exists_to_report_is_a_finding():
    assert floor_for_decline("forecast_missing") == FINDINGS


def test_a_broken_run_is_never_reported_as_a_healthy_book():
    assert floor_for_decline("checker_error") == INCOMPLETE
    assert compose(CLEAN, FINDINGS, INCOMPLETE) == INCOMPLETE
    assert compose(CLEAN, FINDINGS) == FINDINGS


def test_composing_no_legs_is_not_clean():
    """The shared rule, pinned here because this package depends on it.

    Composing nothing is `2`. A battery whose legs all failed to be collected
    must not read as a clean book -- that is the could-not-run-exits-clean
    failure the three-code contract exists to prevent.
    """
    assert compose() == INCOMPLETE


def test_a_leg_that_ran_and_found_nothing_is_clean():
    """The distinction the rule above does NOT cover, and the one this package
    relies on: zero outcomes inside a leg that is present is a clean book, not
    an uncollected battery."""
    from margin_book_audit.audit import read
    result = read({"meta": {"schema_version": 1},
                   "payload": {"forecasts": {"checked": {"expected": 0},
                                             "findings": [], "not_checked": []}}})
    assert result.exit_code == CLEAN
    assert result.complete


def test_a_missing_leg_is_incomplete_rather_than_clean():
    from margin_book_audit.audit import read
    result = read({"meta": {"schema_version": 1}, "payload": {}})
    assert result.exit_code == INCOMPLETE
    assert not result.complete


def test_a_predicted_breach_ranks_with_a_realised_one():
    """Ranking the prediction lower would be this package deciding a forecast
    is worth less than an observation, which is the desk's call."""
    assert floor_for_finding("forecast_breach:margin_balance") == \
        floor_for_finding("below_critical_threshold:margin_balance")
