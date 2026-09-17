"""Readings with no times are not fed, and the report says they were not.

WHERE THEY LANDED BEFORE. `add_observations` with bare readings stamps them
ending at the WALL CLOCK. Run with `--as-of 2026-09-17T09:35`, all forty of the
corpus's readings landed between 15:08 and 15:47 -- hours AFTER the instant
being evaluated -- and the engine returned every one of them inside a one-hour
window. Each reading a window axiom saw was from the subject's own future, and
nothing in the output said so. The reproducibility test passed throughout,
because the artifact carries no timestamps.

WHY NOT JUST PICK A SPACING. Because the spacing is a fact about how a desk
samples its own book, and this package does not have it. `history_interval_s`
is what a register has to say for its readings to be placeable; without it the
series is not fed and `not_established.history` says which key was missing.
Guessing would put an assumption of ours inside somebody else's history, where
nobody would ever look for it.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

from conftest import AS_OF, CORPUS, needs_engine
from margin_book_audit.cli import main
from margin_book_audit.records import load, read_book

pytestmark = needs_engine

AT = datetime.fromisoformat(AS_OF)


def _report(capsys, register):
    main([str(register), str(CORPUS / "feed.json"),
          "--as-of", AS_OF, "--json"])
    return json.loads(capsys.readouterr().out)


@pytest.fixture
def undated(tmp_path):
    book = json.loads((CORPUS / "register.json").read_text())
    book.pop("history_interval_s", None)
    path = tmp_path / "undated.json"
    path.write_text(json.dumps(book))
    return path


class TestAPlacedHistoryIsPlacedCorrectly:

    def test_the_corpus_declares_its_spacing(self):
        book = read_book(load(str(CORPUS / "register.json")))
        assert book.history_is_placeable

    def test_every_reading_lands_at_or_before_the_documents_instant(self):
        book = read_book(load(str(CORPUS / "register.json")))
        for account in book.accounts:
            for when, _value in book.stamped(account):
                assert when <= book.as_of

    def test_no_reading_lands_after_the_evaluation_instant(self):
        """The defect, as the one thing that must never be true again."""
        book = read_book(load(str(CORPUS / "register.json")))
        for account in book.accounts:
            for when, _value in book.stamped(account):
                assert when <= AT, (
                    f"{account.account_id} carries a reading stamped {when}, "
                    f"after the instant being evaluated")

    def test_the_readings_are_spaced_as_the_register_says(self):
        book = read_book(load(str(CORPUS / "register.json")))
        account = next(a for a in book.accounts if len(a.history) > 2)
        stamps = [when for when, _ in book.stamped(account)]
        gaps = {(b - a) for a, b in zip(stamps, stamps[1:])}
        assert gaps == {timedelta(seconds=book.history_interval_s)}

    def test_the_last_reading_is_the_documents_own_instant(self):
        book = read_book(load(str(CORPUS / "register.json")))
        account = next(a for a in book.accounts if a.history)
        assert book.stamped(account)[-1][0] == book.as_of

    def test_the_report_says_it_was_placed(self, capsys):
        report = _report(capsys, CORPUS / "register.json")
        history = report["not_established"]["history"]
        assert history["placed"] is True
        assert history["interval_s"] == 900.0


class TestAnUndatedHistoryIsNotFed:

    def test_nothing_is_stamped(self, undated):
        book = read_book(load(str(undated)))
        assert not book.history_is_placeable
        assert all(book.stamped(a) == [] for a in book.accounts)

    def test_the_report_names_the_missing_key(self, capsys, undated):
        history = _report(capsys, undated)["not_established"]["history"]
        assert history["placed"] is False
        assert history["missing"] == ["history_interval_s"]

    def test_the_run_still_completes(self, capsys, undated):
        """Not being able to place a history is a fact to report, not a broken
        audit: coverage is answerable without any history at all."""
        report = _report(capsys, undated)
        assert report["complete"] is True
        assert report["exit_code"] == 1     # the two coverage gaps, as before

    def test_the_projection_declines_rather_than_fitting_on_nothing(
            self, capsys, undated):
        projection = _report(capsys, undated)["projection"]
        assert projection["checked"].get("forecasts_issued", 0) == 0
        assert projection["not_checked"], (
            "no series could be fitted and nothing said why")
