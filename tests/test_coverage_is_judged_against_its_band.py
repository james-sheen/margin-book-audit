"""A desk's coverage is judged against what chance explains, not a fixed 0.05.

The generated model declared `coverage_90` under HOMEOSTASIS with a tolerance of
0.05. A rate is k of n graded forecasts, and with six or fewer it cannot land
within 0.05 of 0.90 -- so the third audit of a clean book, the first whose
figures carry a grade, exited 1 on `homeostasis_setpoint:coverage_90` for a
producer at three graded and one at one, however well calibrated either was.
From engine 0.2.37 the forecaster's figures carry `coverage_90_band`, how far
chance alone carries the rate at that count, and the model takes its tolerance
from it.

EVERY NUMBER HERE IS SYNTHETIC: the later registers continue each account's
last move, a bench for the mechanism and not a claim about any book.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta

from conftest import CORPUS, needs_engine
from margin_book_audit.cli import main
from margin_book_audit.floors import CLEAN, FINDINGS
from margin_book_audit.model import build_model

COVERED = {"acct_01", "acct_02", "acct_03", "acct_04"}
STEP = timedelta(minutes=75)


def test_the_model_takes_its_tolerance_from_the_band():
    model = build_model()
    assert "tolerance: {from_property: coverage_90_band}" in model
    assert "name: coverage_90_band" in model
    assert "tolerance: 0.05" not in model


def _audits(capsys, tmp_path, width=None):
    """Three audits of the covered accounts, 75 minutes apart, on one ledger.

    Every producer re-sends at each instant, centred where the account now is;
    `width` replaces each interval's half-width, so a narrow one misses."""
    register = json.loads((CORPUS / "register.json").read_text())
    feed = json.loads((CORPUS / "feed.json").read_text())
    register["accounts"] = [a for a in register["accounts"] if a["id"] in COVERED]
    feed["forecasts"] = [f for f in feed["forecasts"] if f["entity_id"] in COVERED]
    at = datetime.fromisoformat(register["as_of"].replace("Z", "+00:00")).replace(tzinfo=None)
    steps = int(STEP.total_seconds() // register["history_interval_s"])
    ledger = tmp_path / "book.sqlite"
    runs = []
    for run in range(3):
        if run:
            at += STEP
            for account in register["accounts"]:
                history = account["history"]
                move = (history[-1] - history[-1 - steps]) / steps
                added = [round(history[-1] + move * k, 2) for k in range(1, steps + 1)]
                account["history"] = history[steps:] + added
                account["margin_balance"] = added[-1]
        balance = {a["id"]: a["margin_balance"] for a in register["accounts"]}
        register["as_of"] = feed["as_of"] = at.isoformat() + "Z"
        sent = copy.deepcopy(feed)
        for record in sent["forecasts"]:
            record["issued_at"] = register["as_of"]
            centre = balance[record["entity_id"]]
            if "quantiles" in record:
                half = width if width is not None else (record["quantiles"]["q95"]
                                                        - record["quantiles"]["q50"])
                record["quantiles"] = {"q05": centre - half, "q50": centre, "q95": centre + half}
            else:
                record["mean"] = centre
                if width is not None:
                    record["sigma"] = width / 1.645
        paths = (tmp_path / f"register{run}.json", tmp_path / f"feed{run}.json")
        paths[0].write_text(json.dumps(register))
        paths[1].write_text(json.dumps(sent))
        code = main([str(paths[0]), str(paths[1]), "--as-of", register["as_of"],
                     "--ledger", str(ledger), "--json"])
        runs.append((code, json.loads(capsys.readouterr().out)))
    return runs


def _coverage_findings(report):
    return sorted(f"{f['entity_id']}|{f['problem_type']}" for f in report["checked"]["findings"]
                  if "coverage_90" in f["problem_type"])


@needs_engine
def test_a_clean_book_audited_three_times_stays_clean(capsys, tmp_path):
    runs = _audits(capsys, tmp_path)
    assert [code for code, _ in runs] == [CLEAN, CLEAN, CLEAN], [
        (code, _coverage_findings(report)) for code, report in runs]
    graded = runs[2][1]["forecasters"]["garch_v3"]
    assert graded["graded_n"] >= 1 and "coverage_90_band" in graded


@needs_engine
def test_a_desk_whose_intervals_miss_is_named_at_its_third_audit(capsys, tmp_path):
    code, report = _audits(capsys, tmp_path, width=0.5)[2]
    assert code == FINDINGS
    assert "garch_v3|homeostasis_setpoint:coverage_90" in _coverage_findings(report)
