"""A control that can fail the run it is measuring inside is not a control.

`--self-forecast` files this package's own EWMA beside the desk's forecasts so
the two can be compared. The engine could not tell whose they were: an outside
record carried no source, so the reference's predictions were a producer's
submission as far as every count and every axiom was concerned. The eight
shadow axioms then ran over THEM.

MEASURED, on a book with three accounts, every pair covered and every balance
above its requirement. Without the flag: `exit 0`, `findings 0`. With it, and
nothing else changed: `exit 1`, `findings 6` -- three `forecast_breach` at
`high`, and three `forecast_below_critical_threshold` at **critical**, about
accounts whose real balance was above the line. A desk reading that report sees
six findings against its book and no indication that all six came from a toy
model this package shipped.

THE FIX IS ENGINE-SIDE, because it had to be: the findings carry no model id,
so nothing downstream could attribute them. `ingest_forecasts` now takes a
`source`, and a record filed with one is kept out of the producer counts and out
of the shadow pass -- exactly as the engine's own projections already were.

WHAT MUST NOT REGRESS WITH IT: the reference is still FILED and still RACED, so
it remains measurable. Silencing it by not feeding it would have passed the
first assertion here and destroyed the feature.
"""

from __future__ import annotations

import json

import pytest

from conftest import needs_engine
from margin_book_audit.cli import main
from margin_book_audit.forecaster import MODEL_ID

pytestmark = needs_engine

AS_OF = "2026-09-17T09:35:00"
BOOK_AS_OF = "2026-09-17T09:30:00Z"

#: Chosen so the desk and the reference DISAGREE. The series declines, so the
#: EWMA lands near 877.7k with a narrow band; the requirement sits just above
#: that and comfortably below the desk's own floor. Any book where both agree
#: cannot show this defect, which is why the corpus never did.
REQUIREMENT = 878_000.0


def _clean_book(tmp_path):
    accounts, forecasts = [], []
    for n in (1, 2, 3):
        account = f"acct_{n:02d}"
        start, end = 1_000_000.0, 880_000.0
        history = [round(start + (end - start) * i / 39.0
                         + ((i % 5) - 2) * 400.0, 2) for i in range(40)]
        accounts.append({"id": account, "margin_balance": history[-1],
                         "margin_requirement": REQUIREMENT,
                         "history": history})
        forecasts.append({
            "model_id": "garch_v3", "issued_at": BOOK_AS_OF,
            "entity_id": account, "property": "margin_balance",
            "horizon_s": 3600, "assumptions": ["stationary_vol_1d"],
            "quantiles": {"q05": 900000.0, "q50": 920000.0, "q95": 940000.0}})

    register = tmp_path / "register.json"
    feed = tmp_path / "feed.json"
    register.write_text(json.dumps({"as_of": BOOK_AS_OF,
                                    "history_interval_s": 900,
                                    "accounts": accounts}))
    feed.write_text(json.dumps({"as_of": BOOK_AS_OF, "forecasts": forecasts}))
    return register, feed


def _run(tmp_path, capsys, *extra):
    register, feed = _clean_book(tmp_path)
    code = main([str(register), str(feed), "--as-of", AS_OF, "--json", *extra])
    return code, json.loads(capsys.readouterr().out)


class TestACleanBookStaysClean:

    def test_the_book_is_clean_to_begin_with(self, tmp_path, capsys):
        """The control for the control. Without this, a test asserting exit 0
        with the flag would pass just as well on a book that could never fail.
        """
        code, report = _run(tmp_path, capsys)
        assert code == 0
        assert report["checked"]["findings"] == []

    def test_switching_the_reference_on_does_not_change_the_verdict(
            self, tmp_path, capsys):
        code, report = _run(tmp_path, capsys, "--self-forecast")
        findings = report["checked"]["findings"]
        assert code == 0, (
            "the reference forecaster raised the exit code of a clean book: "
            + json.dumps([f.get("problem_type") for f in findings]))
        assert findings == []


class TestAndItIsStillAnEntrant:
    """The half that a naive fix would break."""

    def test_the_reference_is_still_filed(self, tmp_path, capsys):
        _, report = _run(tmp_path, capsys, "--self-forecast")
        assert report["reference"]["fed"] == 3

    def test_the_reference_is_still_raced_against_a_random_walk(
            self, tmp_path, capsys):
        _, without = _run(tmp_path, capsys)
        _, with_flag = _run(tmp_path, capsys, "--self-forecast")
        assert with_flag["reference"]["yardsticks"] > without["reference"]["yardsticks"], (
            "the reference stopped getting a yardstick, so it is no longer "
            "being measured -- which is the whole point of feeding it")

    def test_the_report_says_whose_the_reference_is(self, tmp_path, capsys):
        _, report = _run(tmp_path, capsys, "--self-forecast")
        assert report["reference"]["model_id"] == MODEL_ID

    def test_the_reference_is_not_listed_among_the_producers(
            self, tmp_path, capsys):
        """It used to be, unmarked, and that was the complaint.

        `forecasters` carries PRODUCER figures -- how old the last submission
        is, how many arrived against what was owed. None of those questions
        have an answer for a model this package runs itself at the instant of
        the audit, and a row there invited a reader to hold the reference to a
        desk's obligations. It is described in `reference` instead, by name.
        """
        _, report = _run(tmp_path, capsys, "--self-forecast")
        assert MODEL_ID not in report["forecasters"], (
            "this package's own reference is being reported as one of the "
            "desk's producers")
        assert "garch_v3" in report["forecasters"], (
            "the desk's actual producer must still be reported")
