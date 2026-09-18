"""The reference forecaster's interval has to mean the horizon it is filed at.

`predict` scales its residual quantiles by `sqrt(steps_ahead)` and says so: the
record it produces carries `independent_increments_sqrt_horizon_scaling` in its
`assumptions` list. The CLI called `predict(account_id, history)` and filed the
result at `horizon_s=3600`, so `steps_ahead` was its default of 1 and the
quantiles were ONE-STEP residuals -- fifteen minutes on the shipped corpus --
labelled as an hour. Measured: every interval exactly half the width its own
stated assumption implies.

WHY A CLI TEST AND NOT ANOTHER UNIT ONE. `predict(steps_ahead=1)` against
`predict(steps_ahead=9)` was already tested and passed throughout, because the
defect was never in the scaling -- it was that nothing passed the argument.
A unit test on an internal with the public path untested is the shape three
earlier rounds filed against this package, and this is that shape again.

Nothing downstream read the wrong number: the CLI cannot reach calibration at
all (the engine's ledger is in-memory and each run builds a fresh session), so
the mis-scaled entrant was racing and never being scored. That makes this a
correctness defect in the yardstick rather than a wrong published figure, and
it would have become one the moment the ledger persisted.
"""
from __future__ import annotations

import json
import math

import pytest

from conftest import needs_engine


def _register(interval_s, accounts=3, points=40):
    """A clean book: every balance well above its requirement."""
    return {
        "as_of": "2026-09-17T09:30:00Z",
        "history_interval_s": interval_s,
        "accounts": [
            {"id": f"acct_{n:02d}",
             "margin_balance": 1_200_000.0,
             "margin_requirement": 800_000.0,
             "history": [1_200_000.0 + ((i * 37 + n * 11) % 97) * 25.0
                         for i in range(points)]}
            for n in range(1, accounts + 1)
        ],
    }


def _feed(accounts=3):
    return [
        {"model_id": "garch_v3",
         "issued_at": "2026-09-17T09:15:00Z",
         "horizon_s": 3600.0,
         "entity_id": f"acct_{n:02d}",
         "property": "margin_balance",
         "quantiles": {"q05": 1_150_000.0, "q50": 1_200_000.0,
                       "q95": 1_250_000.0}}
        for n in range(1, accounts + 1)
    ]


def _widths_filed(tmp_path, monkeypatch, interval_s):
    """Run the CLI and capture the intervals it actually filed.

    The report does not print quantiles, so the observable is taken at the
    adapter boundary -- the last point where the prediction is still a
    prediction and before it becomes a record.
    """
    from margin_book_audit import adapter, cli

    register = tmp_path / f"register_{interval_s}.json"
    feed = tmp_path / f"feed_{interval_s}.json"
    register.write_text(json.dumps(_register(interval_s)))
    feed.write_text(json.dumps(_feed()))

    seen = []
    original = adapter.from_predictions

    def spy(predictions, **kwargs):
        captured = list(predictions)
        seen.extend(captured)
        return original(captured, **kwargs)

    monkeypatch.setattr(adapter, "from_predictions", spy)
    cli.main([str(register), str(feed), "--self-forecast",
              "--as-of", "2026-09-17T09:30:00Z", "--json"])
    return [p.quantiles["q95"] - p.quantiles["q05"] for p in seen]


@needs_engine
class TestTheIntervalWidensWithTheHorizon:

    def test_a_coarser_history_means_fewer_steps_and_a_tighter_interval(
            self, tmp_path, monkeypatch, capsys):
        """One hour is four steps of fifteen minutes and one step of an hour.
        Under the record's own assumption the first is twice as wide."""
        quarter_hourly = _widths_filed(tmp_path, monkeypatch, 900)
        capsys.readouterr()
        hourly = _widths_filed(tmp_path, monkeypatch, 3600)
        capsys.readouterr()

        assert quarter_hourly and hourly, "no reference rows were filed"
        assert len(quarter_hourly) == len(hourly)
        for wide, narrow in zip(quarter_hourly, hourly):
            assert wide == pytest.approx(narrow * math.sqrt(4.0), rel=1e-9), (
                "the filed interval did not scale with the number of steps "
                "the horizon spans; `steps_ahead` is not reaching `predict`")

    def test_the_hourly_case_is_the_unscaled_one(
            self, tmp_path, monkeypatch, capsys):
        """The anchor. With a one-hour history interval a one-hour horizon IS
        one step, so `sqrt(1) == 1` and the filed width equals the raw residual
        spread -- which is what the old code filed for EVERY interval."""
        from margin_book_audit.forecaster import predict

        hourly = _widths_filed(tmp_path, monkeypatch, 3600)
        capsys.readouterr()
        raw = []
        for account in _register(3600)["accounts"]:
            prediction = predict(account["id"], account["history"])
            assert prediction is not None
            raw.append(prediction.quantiles["q95"] - prediction.quantiles["q05"])
        assert hourly == pytest.approx(raw)


@needs_engine
class TestAnUnplaceableHistoryFilesNoReference:
    """A register with no `history_interval_s` cannot say how many steps an
    hour is. The package already refuses to spread undated readings across a
    guessed interval; inventing the SCALE of the yardstick is the same
    invention one layer along, and a yardstick nobody can interpret is worse
    than none because the comparison still prints.
    """

    def test_no_rows_are_filed_without_an_interval(
            self, tmp_path, monkeypatch, capsys):
        register = _register(900)
        del register["history_interval_s"]
        path = tmp_path / "no_interval.json"
        feed = tmp_path / "feed.json"
        path.write_text(json.dumps(register))
        feed.write_text(json.dumps(_feed()))

        from margin_book_audit import cli

        cli.main([str(path), str(feed), "--self-forecast", "--json",
                  "--as-of", "2026-09-17T09:30:00Z"])
        report = json.loads(capsys.readouterr().out)
        assert report["reference"]["fed"] == 0
        assert report["reference"]["model_id"] is None
