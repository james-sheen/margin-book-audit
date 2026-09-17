"""`--self-forecast` is a second entrant, not a stand-in.

WHAT IT DID INSTEAD. The predictions were appended to the feed BEFORE stage one
classified it, so this package's own model answered the question this package
exists to ask. Measured on the corpus: `acct_05`, whose producer sent a record
that could not be scored, and `acct_06`, whose producer sent nothing, both came
out `scorable`; coverage read 6 of 6; the audit exited CLEAN. The README's first
paragraph says the denominator never comes from the feed, and the feed was being
topped up from inside.

It also carried an off-by-k. The slice that rebuilt the records started at
`len(records)` against a list built from `rows`, which excludes the unusable --
so on a corpus with one unusable record the first account's own reference
prediction fell out of the set entirely. That bug is gone with the slice: there
is no rebuild any more, because the reference never enters the register's
population at all.

WHAT IT DOES NOW. The reference is fed BESIDE the desk's forecasts and only for
pairs the desk already covered, which is what a comparison is. It cannot reach
an absent or unscorable pair, so it can never close a hole.
"""

from __future__ import annotations

import json

import pytest

from conftest import AS_OF, CORPUS, needs_engine
from margin_book_audit.cli import main
from margin_book_audit.forecaster import MODEL_ID

pytestmark = needs_engine


def _report(capsys, *extra):
    main([str(CORPUS / "register.json"), str(CORPUS / "feed.json"),
          "--as-of", AS_OF, "--json", *extra])
    return json.loads(capsys.readouterr().out)


class TestCoverageIsTheDesksAlone:

    def test_the_states_are_identical_with_and_without_it(self, capsys):
        without = _report(capsys)["not_established"]
        with_it = _report(capsys, "--self-forecast")["not_established"]
        assert with_it["coverage"] == without["coverage"]
        assert with_it["absent"] == without["absent"] == ["acct_06"]
        assert ([u["account_id"] for u in with_it["unscorable"]]
                == [u["account_id"] for u in without["unscorable"]]
                == ["acct_05"])

    def test_an_absent_producer_stays_absent(self, capsys):
        report = _report(capsys, "--self-forecast")
        assert "acct_06" in report["not_established"]["absent"]

    def test_the_run_does_not_turn_clean(self, capsys):
        """The whole of the defect in one number: it exited 0."""
        assert _report(capsys, "--self-forecast")["exit_code"] == 1

    def test_the_engine_is_still_told_a_forecast_is_missing(self, capsys):
        report = _report(capsys, "--self-forecast")
        missing = {d.get("entity") for d in report["declined"]
                   if d["reason"] == "forecast_missing"}
        assert missing == {"acct_05", "acct_06"}


class TestTheReferenceStillRuns:
    """A fix that simply dropped the flag would pass every assertion above."""

    def test_it_reaches_the_engine(self, capsys):
        report = _report(capsys, "--self-forecast")
        assert report["reference"]["fed"] > 0

    def test_it_is_declared_as_a_permitted_producer(self, capsys):
        """Otherwise the engine declines `model_unknown` against us."""
        report = _report(capsys, "--self-forecast")
        assert not [d for d in report["declined"]
                    if d["reason"] == "model_unknown"]

    def test_it_reaches_every_pair_the_desk_covered(self, capsys):
        report = _report(capsys, "--self-forecast")
        scorable = report["not_established"]["coverage"]["scorable"]
        assert report["reference"]["fed"] == scorable

    def test_a_yardstick_is_filed_for_each_forecast(self, capsys):
        """The engine's random walk, on the same series and horizon. Without
        it *beat a random walk* has nothing on the other side."""
        plain = _report(capsys)["reference"]["yardsticks"]
        both = _report(capsys, "--self-forecast")["reference"]["yardsticks"]
        assert plain == 4
        assert both == 8

    def test_its_own_assumption_travels_with_its_records(self):
        """The square-root-of-horizon scaling is only right if the increments
        are independent -- a claim about margin balances this package cannot
        make and is therefore obliged to state where a scorer will see it."""
        from margin_book_audit.adapter import from_predictions
        from margin_book_audit.forecaster import Prediction

        rows = from_predictions(
            [Prediction("acct_01", {"q05": 1.0, "q50": 2.0, "q95": 3.0}, 40)],
            issued_at=AS_OF, horizon_s=3600.0)
        assert any("independent_increments" in a
                   for a in rows[0]["assumptions"])
