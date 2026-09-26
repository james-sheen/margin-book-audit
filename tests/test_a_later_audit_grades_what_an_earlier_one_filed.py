"""A later audit grades what an earlier one filed, and the engine's learner is scored beside it.

NOTHING WAS EVER GRADED HERE, and the report said so in a comment nobody reads.
Every forecast a run files -- the desk's, the reference's, the engine's random
walks -- matures an hour after the instant being audited, and the default
ledger dies with the process. Measured on the shipped corpus with
`--self-forecast`: 22 recorded, 22 pending, 0 graded, every score null. So the
comparison this package exists to set up -- does the desk's model beat the
yardsticks -- had never been answered by any run of it.

`--ledger PATH` keeps what a run files; the next audit of the same book feeds a
register whose own history holds the readings those forecasts were about, and
the engine grades them. `--learner` files the engine's reference producer
beside this package's, so the desk's model is scored against something harder
than a random walk.

EVERY NUMBER HERE IS SYNTHETIC, like the corpus it starts from. The later
register continues each account's last move; it is a bench for the mechanism,
not a claim about any book, and no score below is asserted as a value.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta

import pytest

from conftest import CORPUS, needs_engine
from margin_book_audit.cli import main
from margin_book_audit.forecaster import MODEL_ID as REFERENCE

pytestmark = needs_engine

#: One register step past the hour: the forecasts filed at the first instant
#: target the hour, the ledger grades a record only once its grace has passed
#: too, and the later register's history holds a reading at the hour itself.
LATER = timedelta(minutes=75)


def _instant(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)


def _book(tmp_path):
    """The shipped corpus at its own instant, and the same book 75 minutes on."""
    register = json.loads((CORPUS / "register.json").read_text())
    feed = json.loads((CORPUS / "feed.json").read_text())
    first = _instant(register["as_of"])
    steps = int(LATER.total_seconds() // register["history_interval_s"])

    later = copy.deepcopy(register)
    later["as_of"] = (first + LATER).isoformat() + "Z"
    for account in later["accounts"]:
        history = account["history"]
        move = (history[-1] - history[-1 - steps]) / steps
        added = [round(history[-1] + move * k, 2) for k in range(1, steps + 1)]
        account["history"] = history[steps:] + added
        account["margin_balance"] = added[-1]

    later_feed = copy.deepcopy(feed)
    later_feed["as_of"] = later["as_of"]
    for record in later_feed["forecasts"]:
        record["issued_at"] = later["as_of"]

    paths = {}
    for name, doc in (("register", register), ("feed", feed),
                      ("later_register", later), ("later_feed", later_feed)):
        paths[name] = tmp_path / f"{name}.json"
        paths[name].write_text(json.dumps(doc))
    return paths, register["as_of"], later["as_of"]


def _audit(capsys, register, feed, at, *extra, text=False):
    code = main([str(register), str(feed), "--as-of", at, "--self-forecast",
                 "--learner", *extra] + ([] if text else ["--json"]))
    out = capsys.readouterr().out
    return code, (out if text else json.loads(out))


def _learner_id():
    from arbiter_engine.producers.baseline_learner import BASELINE_MODEL_ID
    return BASELINE_MODEL_ID


def _random_walk_id():
    # The engine's own name for the yardstick it files beside every forecast.
    # Read, not typed: this package must never carry a second copy of it.
    from arbiter_engine.projection.projector import BASELINE_MODEL_ID
    return BASELINE_MODEL_ID


class TestOneRunGradesNothing:

    def test_the_shipped_corpus_grades_nothing_and_says_so(self, capsys, tmp_path):
        """The measured premise, pinned: a single run's scores are all null."""
        paths, first, _ = _book(tmp_path)
        _, report = _audit(capsys, paths["register"], paths["feed"], first)
        calibration = report["calibration"]
        assert calibration["recorded"] > 0
        assert calibration["pending"] == calibration["recorded"]
        assert calibration["by_model"] == {}

    def test_the_readme_figure_is_this_run(self, capsys):
        """The README quotes the measurement; this is the measurement. A figure
        typed into prose and derived nowhere is how the old sentence -- *no run
        of this command can score anything* -- outlived the engine shipping the
        ledger that made it false."""
        import re
        from conftest import ROOT
        register = json.loads((CORPUS / "register.json").read_text())
        main([str(CORPUS / "register.json"), str(CORPUS / "feed.json"),
              "--as-of", register["as_of"], "--self-forecast", "--json"])
        calibration = json.loads(capsys.readouterr().out)["calibration"]
        readme = " ".join((ROOT / "README.md").read_text().split())
        said = re.search(r"with `--self-forecast`: (\d+) recorded, (\d+) pending, "
                         r"(\d+) graded", readme)
        assert said, "the README no longer states the measured premise"
        graded = calibration["confirmed"] + calibration["falsified"]
        assert (int(said.group(1)), int(said.group(2)), int(said.group(3))) == (
            calibration["recorded"], calibration["pending"], graded)

    def test_the_text_says_why_rather_than_printing_a_zero(self, capsys, tmp_path):
        paths, first, _ = _book(tmp_path)
        _, text = _audit(capsys, paths["register"], paths["feed"], first, text=True)
        assert "graded              none of" in text
        assert "pass --ledger PATH" in text


class TestALaterAuditGradesTheEarlierOne:

    def _two_audits(self, capsys, tmp_path, *extra):
        paths, first, later = _book(tmp_path)
        _audit(capsys, paths["register"], paths["feed"], first, *extra)
        return _audit(capsys, paths["later_register"], paths["later_feed"],
                      later, *extra)

    def test_the_first_run_is_graded_by_the_second(self, capsys, tmp_path):
        ledger = tmp_path / "ledger.sqlite"
        _, report = self._two_audits(capsys, tmp_path, "--ledger", str(ledger))
        calibration = report["calibration"]
        graded = calibration["confirmed"] + calibration["falsified"]
        assert graded > 0, calibration
        assert report["scored"]["ledger"] == str(ledger)

    def test_three_yardsticks_are_scored_beside_the_desk(self, capsys, tmp_path):
        """The reference, the learner and the random walk, each with a CRPS
        and a count -- and the desk's own producers beside them."""
        _, report = self._two_audits(capsys, tmp_path,
                                     "--ledger", str(tmp_path / "l.sqlite"))
        by_model = report["calibration"]["by_model"]
        for model in (REFERENCE, _learner_id(), _random_walk_id(),
                      *report["scored"]["producers"]):
            assert model in by_model, f"{model} was not graded: {sorted(by_model)}"
            assert by_model[model]["n"] > 0
            assert by_model[model]["crps_approx"] is not None

    def test_the_text_prints_one_line_per_graded_model(self, capsys, tmp_path):
        paths, first, later = _book(tmp_path)
        ledger = str(tmp_path / "l.sqlite")
        _audit(capsys, paths["register"], paths["feed"], first, "--ledger", ledger)
        _, text = _audit(capsys, paths["later_register"], paths["later_feed"],
                         later, "--ledger", ledger, text=True)
        assert f"{REFERENCE} (n=" in text and "this package's reference" in text
        assert f"{_learner_id()} (n=" in text and "the engine's learner" in text
        assert f"{_random_walk_id()} (n=" in text

    def test_without_a_ledger_the_second_run_starts_from_nothing(self, capsys, tmp_path):
        """Non-vacuity: the grading above is the ledger's doing, not the
        second register's."""
        _, report = self._two_audits(capsys, tmp_path)
        calibration = report["calibration"]
        assert calibration["confirmed"] + calibration["falsified"] == 0
        assert report["scored"]["ledger"] is None


class TestTheLearnerIsAYardstickAndNothingMore:

    def test_it_never_closes_a_coverage_hole(self, capsys, tmp_path):
        paths, first, _ = _book(tmp_path)
        code_without = main([str(paths["register"]), str(paths["feed"]),
                             "--as-of", first, "--json"])
        without = json.loads(capsys.readouterr().out)
        code_with, with_learner = _audit(capsys, paths["register"], paths["feed"], first)
        assert (with_learner["not_established"]["coverage"]
                == without["not_established"]["coverage"])
        assert with_learner["learner"]["fed"] == without["not_established"]["coverage"]["scorable"]
        assert with_learner["learner"]["forecast"] > with_learner["learner"]["fed"], (
            "the learner forecast every placed series; only the pairs the desk "
            "covered may reach the engine, or this bench cannot tell the two apart")
        assert code_with == code_without

    def test_it_cannot_fail_the_audit(self, capsys, tmp_path):
        """Set aside by source, like the reference: its forecasts are scored,
        never judged against the book."""
        paths, first, _ = _book(tmp_path)
        main([str(paths["register"]), str(paths["feed"]), "--as-of", first,
              "--self-forecast", "--json"])
        without = json.loads(capsys.readouterr().out)
        _, with_learner = _audit(capsys, paths["register"], paths["feed"], first)
        assert with_learner["exit_code"] == without["exit_code"]
        assert with_learner["checked"]["findings"] == without["checked"]["findings"]
        assert (with_learner["checked"]["shadow_counts"]
                == without["checked"]["shadow_counts"])
        # The engine's own receipt that it set them aside: every learner record
        # lands in `caller_references` -- and in `reference`, which that count
        # partitions -- and in nothing a producer is judged by.
        fed = with_learner["learner"]["fed"]
        assert fed > 0
        counts, before = (with_learner["checked"]["engine_counts"],
                          without["checked"]["engine_counts"])
        assert counts["caller_references"] - before["caller_references"] == fed
        assert counts["reference"] - before["reference"] == fed
        assert ({k: v for k, v in counts.items()
                 if k not in ("caller_references", "reference")}
                == {k: v for k, v in before.items()
                    if k not in ("caller_references", "reference")})

    def test_a_learner_with_nothing_to_read_says_why(self, capsys, tmp_path):
        paths, first, _ = _book(tmp_path)
        register = json.loads(paths["register"].read_text())
        del register["history_interval_s"]
        paths["register"].write_text(json.dumps(register))
        _, report = _audit(capsys, paths["register"], paths["feed"], first)
        assert report["learner"]["fed"] == 0
        assert "history_interval_s" in report["learner"]["reason"]
