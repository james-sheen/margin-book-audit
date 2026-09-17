"""The bridge end to end, at a pinned instant, against the real engine.

PINNED, AND THAT IS NOT A DETAIL. Staleness and lookback are both measured from
NOW. Run on the wall clock this file passes for a few minutes after the corpus
was written and then reports four stale forecasts forever -- a suite that goes
red by the clock rather than by the code. The sibling engine repository shipped
exactly that bug in a test that compared a frozen projection against a
wall-clock recomputation, and it went red two hours after it was written.
"""

from __future__ import annotations

import json

import pytest

from conftest import AS_OF, CORPUS, needs_engine
from margin_book_audit.cli import main

pytestmark = needs_engine


def _run(*extra):
    return main([str(CORPUS / "register.json"), str(CORPUS / "feed.json"),
                 "--as-of", AS_OF, *extra])


def test_the_run_completes_and_reports_findings(capsys):
    code = _run()
    capsys.readouterr()
    assert code == 1, "two pairs carry no usable forecast; that is a finding"


def test_the_artifact_separates_a_producer_bug_from_a_coverage_gap(capsys):
    _run("--json")
    report = json.loads(capsys.readouterr().out)

    # The ENGINE says `forecast_missing` for both, because from where it sits
    # they are the same absence. Stage one is what tells them apart.
    reasons = {(d["reason"], d["entity"]) for d in report["declined"]}
    assert ("forecast_missing", "acct_05") in reasons
    assert ("forecast_missing", "acct_06") in reasons

    not_established = report["not_established"]
    assert not_established["absent"] == ["acct_06"]
    unscorable = {u["account_id"]: u["reason"] for u in not_established["unscorable"]}
    assert "acct_05" in unscorable and "quantiles" in unscorable["acct_05"]


def test_the_denominator_comes_from_the_register(capsys):
    _run("--json")
    report = json.loads(capsys.readouterr().out)
    counts = report["checked"]["engine_counts"]
    assert counts["expected"] == 6
    assert counts["received"] == 4
    assert counts["expected"] > counts["received"], (
        "a denominator equal to what arrived is not a denominator")


def test_exclusions_are_named_with_reasons(capsys):
    _run("--json")
    report = json.loads(capsys.readouterr().out)
    excluded = {e["account_id"]: e["reason"]
                for e in report["not_established"]["excluded_from_model"]}
    assert set(excluded) == {"acct_07", "acct_08"}
    assert all(reason.strip() for reason in excluded.values()), (
        "an exclusion without a reason is indistinguishable from an omission")


def test_two_runs_at_the_same_instant_agree(capsys):
    _run("--json")
    first = capsys.readouterr().out
    _run("--json")
    assert capsys.readouterr().out == first


def test_the_pin_is_not_vacuous(capsys):
    """If the instant made no difference, the pin proves nothing. Run the same
    corpus far enough past the declared `max_age` and the verdict must move."""
    _run("--json")
    fresh = json.loads(capsys.readouterr().out)
    main([str(CORPUS / "register.json"), str(CORPUS / "feed.json"),
          "--as-of", "2026-09-17T18:00:00", "--json"])
    stale = json.loads(capsys.readouterr().out)
    assert {d["reason"] for d in stale["declined"]} != \
        {d["reason"] for d in fresh["declined"]}
    assert "stale_forecast" in {d["reason"] for d in stale["declined"]}
