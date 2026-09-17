"""The generated model declares a `ForecastModel`. Something has to create one.

DECLARED AND NEVER INSTANTIATED. `build_model` emitted a `ForecastModel` type
with six indicators -- CONSERVATION over expected-against-issued, HOMEOSTASIS
over two calibration figures, MONOTONICITY over the graded count, RESPONSIVENESS
over the age -- and the CLI never added an entity of that type, never called
`feed_model_figures`, never called `project`, and never read `calibration()`.
Four axiom declarations over a type with no instances: evaluated nothing,
reported nothing, and looked exactly like four checks passing.

AND WIRING IT UP FOUND A FALSE FINDING IN THE ENGINE. `forecasts_expected` was
derived from `models:`, which is an ALLOW-LIST -- the guide says so on the line
beside it. So both permitted producers were charged with all six accounts and
CONSERVATION reported them 50% and 83% short of a debt nobody had declared. A
desk naming five permitted models would have had four of them delinquent by
construction. `expected_from:` is now the obligation and `models:` stays
permission; absent an obligation the figure is absent and the axiom declines.

THE TYPE NAME IS THIS PACKAGE'S WORD. The engine takes it as an argument and
contains no such name anywhere, because a type name compiled into a domain-free
core is a domain word in the one place the project refuses to put one.
"""

from __future__ import annotations

import json

import pytest

from conftest import AS_OF, CORPUS, needs_engine
from margin_book_audit.cli import main
from margin_book_audit.model import FORECASTER_TYPE

pytestmark = needs_engine


def _report(capsys, *extra):
    main([str(CORPUS / "register.json"), str(CORPUS / "feed.json"),
          "--as-of", AS_OF, "--json", *extra])
    return json.loads(capsys.readouterr().out)


class TestTheProducersAreMeasured:

    def test_each_producer_in_the_feed_gets_figures(self, capsys):
        forecasters = _report(capsys)["forecasters"]
        assert set(forecasters) == {"garch_v3", "lstm_v1"}

    def test_the_issued_count_is_what_the_feed_carried(self, capsys):
        forecasters = _report(capsys)["forecasters"]
        assert forecasters["garch_v3"]["forecasts_issued"] == 3.0
        assert forecasters["lstm_v1"]["forecasts_issued"] == 1.0

    def test_the_engines_own_yardstick_is_not_a_producer(self, capsys):
        """`baseline_rw` is the reference the engine files beside every
        forecast. Monitoring it as a forecaster puts the ruler on the chart."""
        assert "baseline_rw" not in _report(capsys)["forecasters"]

    def test_an_unscored_calibration_figure_is_absent_not_zero(self, capsys):
        """A `coverage_90` of 0.0 for a model nobody has graded reads as
        catastrophic miscalibration, and an axiom would fire on it."""
        garch = _report(capsys)["forecasters"]["garch_v3"]
        assert "coverage_90" not in garch
        assert "pinball_loss" not in garch


class TestAnObligationIsDeclaredAndNeverInferred:

    def test_without_expected_from_no_producer_owes_anything(self, capsys):
        forecasters = _report(capsys)["forecasters"]
        assert all("forecasts_expected" not in f for f in forecasters.values())

    def test_and_no_conservation_finding_is_invented(self, capsys):
        findings = _report(capsys)["checked"]["findings"]
        assert not [f for f in findings
                    if f["problem_type"].startswith("conservation_violation:")]

    def test_declaring_it_makes_the_check_run(self, capsys):
        report = _report(capsys, "--expected-from", "garch_v3")
        assert report["forecasters"]["garch_v3"]["forecasts_expected"] == 6.0

    def test_and_a_producer_that_is_short_is_reported(self, capsys):
        """garch_v3 owes six and filed three."""
        findings = _report(capsys, "--expected-from",
                           "garch_v3")["checked"]["findings"]
        short = [f for f in findings
                 if f["problem_type"].startswith("conservation_violation:")]
        assert [f["entity_id"] for f in short] == ["garch_v3"]

    def test_a_producer_nobody_named_is_still_not_charged(self, capsys):
        report = _report(capsys, "--expected-from", "garch_v3")
        assert "forecasts_expected" not in report["forecasters"]["lstm_v1"]


class TestTheDeclaredDynamicsAreActuallyRun:

    def test_the_projection_leg_reaches_the_artifact(self, capsys):
        projection = _report(capsys)["projection"]
        assert projection["checked"].get("series_seen", 0) > 0

    def test_a_series_was_projected(self, capsys):
        projection = _report(capsys)["projection"]
        assert projection["checked"].get("forecasts_issued", 0) > 0, (
            f"nothing was projected; declines were "
            f"{[d['reason'] for d in projection['not_checked']]}")

    def test_the_floor_it_projects_against_is_the_accounts_own(self, capsys):
        """`lower_critical: {from_property: margin_requirement}`. Before the
        engine's resolver reached `project`, every account declined
        `no_threshold` here and no projection could ever report a breach."""
        projection = _report(capsys)["projection"]
        assert not [d for d in projection["not_checked"]
                    if d["reason"] == "no_threshold"
                    and d.get("property") == "margin_balance"]

    def test_a_projected_breach_does_not_floor_the_exit_code(self, capsys):
        """Reported, not gated. A probability about an hour that has not
        happened must not page a desk the way a balance does."""
        from margin_book_audit.audit import read_projection
        assert "exit_code" not in read_projection({"checked": {}})


class TestTheCalibrationBlockIsPresentEvenWhenEmpty:

    def test_it_is_reported(self, capsys):
        """An absent calibration block and one full of nulls read the same to
        a human and mean opposite things to a gate."""
        calibration = _report(capsys)["calibration"]
        assert "confirm_rate" in calibration

    def test_nothing_has_been_scored_in_a_single_run(self, capsys):
        """Every forecast here is an hour from maturing, so a rate would be a
        rate over nothing."""
        assert _report(capsys)["calibration"]["confirm_rate"] is None
