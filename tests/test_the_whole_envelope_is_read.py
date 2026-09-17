"""An audit of a margin book has to be able to say an account is under its margin.

IT COULD NOT. The exit code was composed from the `forecasts` leg alone, so the
model's own BOUNDEDNESS declaration -- `lower_critical: {from_property:
margin_requirement}`, the reason this package generates a model at all -- was
evaluated by the engine, fired at severity `critical`, and went nowhere.
Measured on the corpus with one balance moved below its requirement: the engine
reported `below_critical_threshold:margin_balance`, this package reported
`findings 0`, and with coverage complete the run exited CLEAN.

That is not a narrower audit. The README says the question is coverage, and it
is -- but the model declares a floor, the floor is checked, and a package that
asks the engine a question and then discards the answer has not narrowed its
scope; it has hidden a result it went and fetched.

THREE POPULATIONS, and the two that were missing are the ones with teeth:

  - the FORECASTS leg -- did the producer send what was expected;
  - the SHADOW leg -- what the eight axioms make of the forecast itself. Every
    shadow row in this package's floor table was unreachable until the engine
    stopped discarding that leg, and half the table is shadow rows;
  - the ENVELOPE's own findings and declines -- what is true of the book now.
"""

from __future__ import annotations

import json

import pytest

from conftest import AS_OF, CORPUS, needs_engine
from margin_book_audit.cli import main

pytestmark = needs_engine

REQUIREMENT_GAP = 50_000.0


@pytest.fixture
def breached(tmp_path):
    """The corpus, with one account pushed under its contracted requirement."""
    book = json.loads((CORPUS / "register.json").read_text())
    for account in book["accounts"]:
        if account["id"] == "acct_01":
            account["margin_balance"] = (account["margin_requirement"]
                                         - REQUIREMENT_GAP)
    path = tmp_path / "breached.json"
    path.write_text(json.dumps(book))
    return path


def _report(capsys, register=None, *extra):
    main([str(register or CORPUS / "register.json"),
          str(CORPUS / "feed.json"), "--as-of", AS_OF, "--json", *extra])
    return json.loads(capsys.readouterr().out)


class TestARealisedBreachIsReported:

    def test_the_finding_reaches_the_artifact(self, capsys, breached):
        findings = _report(capsys, breached)["checked"]["findings"]
        assert any(f["problem_type"].startswith("below_critical_threshold:")
                   and f["entity_id"] == "acct_01" for f in findings), findings

    def test_it_carries_the_engines_own_severity(self, capsys, breached):
        findings = _report(capsys, breached)["checked"]["findings"]
        breach = [f for f in findings
                  if f["problem_type"].startswith("below_critical_threshold:")]
        assert breach[0]["severity"] == "critical"

    def test_a_healthy_book_reports_no_such_finding(self, capsys):
        """The control. A test that only asserts a finding appears would pass
        against a package that reported one for every account."""
        findings = _report(capsys)["checked"]["findings"]
        assert not [f for f in findings
                    if f["problem_type"].startswith("below_critical_threshold:")]

    def test_it_floors_the_exit_code_on_its_own(self, capsys, breached, tmp_path):
        """With the feed complete there is nothing else to be red about, so
        this is the assertion the old behaviour failed: the run exited 0."""
        book = json.loads(breached.read_text())
        # Expect a forecast only where the feed carries a USABLE one. A record
        # that arrived and cannot be scored still leaves the pair uncovered --
        # which is the distinction this package exists to keep, and getting it
        # wrong here would leave a `forecast_missing` in the run and make the
        # assertion below pass for the wrong reason.
        from margin_book_audit.records import load, read_feed
        usable = {r.account_id for r in read_feed(load(str(CORPUS / "feed.json")))
                  if r.usable}
        for account in book["accounts"]:
            account["forecast_expected"] = account["id"] in usable
        register = tmp_path / "covered.json"
        register.write_text(json.dumps(book))
        report = _report(capsys, register)
        assert not [d for d in report["declined"]
                    if d["reason"] == "forecast_missing"], (
            "this fixture is meant to have no coverage gap left")
        assert report["exit_code"] == 1


class TestTheShadowLegIsRead:

    def test_its_denominator_is_reported(self, capsys):
        counts = _report(capsys)["checked"]["shadow_counts"]
        assert counts.get("entities", 0) > 0, (
            "the shadow leg carries no denominator, so either the engine is "
            "not mounting it or this package is not reading it")

    def test_a_shadow_decline_can_reach_the_exit_code(self):
        """The floor table has a row for every member of the engine's shadow
        vocabulary, and until the engine stopped discarding that leg not one of
        them could ever match."""
        from arbiter_engine.subenvelope import VOCABULARIES
        from margin_book_audit.floors import DECLINE_FLOORS

        shadow_only = set(VOCABULARIES["shadow"]) - set(VOCABULARIES["forecasts"])
        assert shadow_only <= set(DECLINE_FLOORS)


class TestTheAxiomDeclinesAreRead:

    def test_a_check_that_could_not_run_is_reported(self, capsys):
        """The population the floor table was written for. Fourteen rows, and
        before this none of them could fire."""
        declines = _report(capsys)["declined"]
        assert any(d.get("axiom") for d in declines), (
            "no axiom-level decline reached the artifact")

    def test_a_cold_calibration_figure_does_not_floor_the_gate(self, capsys):
        """`coverage_90` is absent until something has matured and been scored,
        which on an hourly horizon is true of every first run. Flooring
        `missing_property` there would give a desk a red gate for an hour and
        teach them to ignore it."""
        from margin_book_audit.floors import CLEAN, FINDINGS, floor_for_decline

        assert floor_for_decline("missing_property", "coverage_90") == CLEAN
        assert floor_for_decline("missing_property", "margin_requirement") == FINDINGS
