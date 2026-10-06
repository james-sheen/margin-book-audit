"""A register with no readable account is never a clean book, in either stage.

Stage one printed `exit 0 (complete)` over zero pairs expected, for a register
holding no accounts and for one whose every row named none. The full audit did
refuse -- on the engine's missing `forecasts` leg, which is true and three steps
removed from the cause. And the rows it could not read were skipped without a
word, so nothing downstream could tell a short book from a small one.
"""

import copy
import json

import pytest

from conftest import AS_OF, CORPUS, needs_engine
from margin_book_audit.cli import main
from margin_book_audit.floors import FINDINGS, INCOMPLETE
from margin_book_audit.records import (read_book, read_feed, read_feed_rows,
                                       read_register, read_register_rows)

REGISTER = json.loads((CORPUS / "register.json").read_text())
FEED = CORPUS / "feed.json"


def _register(tmp_path, accounts):
    path = tmp_path / "register.json"
    path.write_text(json.dumps(dict(REGISTER, accounts=accounts)))
    return path


def _nameless():
    rows = copy.deepcopy(REGISTER["accounts"])
    for row in rows:
        row.pop("id", None)
        row.pop("account_id", None)
    return rows


def _run(capsys, register, *extra, feed=FEED):
    code = main([str(register), str(feed), "--as-of", AS_OF, "--json", *extra])
    return code, json.loads(capsys.readouterr().out)


class TestStageOneRefusesAnEmptyBook:

    def test_no_accounts_at_all(self, tmp_path, capsys):
        code, report = _run(capsys, _register(tmp_path, []), "--coverage-only")
        assert code == INCOMPLETE and report["exit_code"] == INCOMPLETE
        assert report["complete"] is False
        assert "the register holds no accounts" in report["incomplete_reason"]

    def test_rows_none_of_which_names_an_account(self, tmp_path, capsys):
        code, report = _run(capsys, _register(tmp_path, _nameless()),
                            "--coverage-only")
        assert code == INCOMPLETE
        reason = report["incomplete_reason"]
        assert f"holds {len(REGISTER['accounts'])} row(s) and none is a " \
               f"readable account" in reason
        assert "accounts[0] names no account" in reason
        assert len(report["not_established"]["unread_rows"]["register"]) == \
            len(REGISTER["accounts"])

    def test_the_terminal_line_says_so_too(self, tmp_path, capsys):
        assert main([str(_register(tmp_path, [])), str(FEED), "--as-of", AS_OF,
                     "--coverage-only"]) == INCOMPLETE
        out = capsys.readouterr().out
        assert "exit 2  (INCOMPLETE)" in out and "holds no accounts" in out

    def test_the_shipped_book_is_unchanged(self, capsys):
        """The control: stage one on a real book still completes -- and reports
        the corpus's unscorable and absent pair as findings, as the full audit
        does."""
        code, report = _run(capsys, CORPUS / "register.json", "--coverage-only")
        assert code == FINDINGS and report["complete"] is True
        assert report["not_established"]["unread_rows"] == {"register": [],
                                                            "feed": []}


@needs_engine
class TestTheFullAuditNamesTheBook:

    def test_it_is_the_register_not_the_forecasts_leg(self, tmp_path, capsys):
        code, report = _run(capsys, _register(tmp_path, []))
        assert code == INCOMPLETE
        assert "holds no accounts" in report["incomplete_reason"]
        assert "forecasts` leg" not in report["incomplete_reason"]

    def test_the_shipped_book_is_unchanged(self, capsys):
        code, report = _run(capsys, CORPUS / "register.json")
        assert code == FINDINGS and report["complete"] is True


class TestUnreadRowsAreCountedNotDropped:

    def test_a_partly_unreadable_register_names_each_row(self, tmp_path, capsys):
        rows = REGISTER["accounts"][:6] + ["not-a-row", {"margin_balance": 1.0}]
        code, report = _run(capsys, _register(tmp_path, rows), "--coverage-only")
        assert code == FINDINGS, "the six readable accounts still audit, gaps and all"
        assert report["not_established"]["unread_rows"]["register"] == [
            "accounts[6] is str, not an object",
            "accounts[7] names no account (no `id` or `account_id`)"]

    def test_the_summary_line_counts_them(self, tmp_path, capsys):
        rows = REGISTER["accounts"][:6] + ["not-a-row"]
        main([str(_register(tmp_path, rows)), str(FEED), "--as-of", AS_OF,
              "--coverage-only"])
        assert "  register unread     1 -- accounts[6] is str" in \
            capsys.readouterr().out

    def test_a_feed_row_that_is_not_an_object_is_counted(self, tmp_path, capsys):
        feed = json.loads(FEED.read_text())
        feed["forecasts"] = feed["forecasts"] + [42]
        path = tmp_path / "feed.json"
        path.write_text(json.dumps(feed))
        _, report = _run(capsys, CORPUS / "register.json", "--coverage-only",
                         feed=path)
        assert report["not_established"]["unread_rows"]["feed"] == [
            f"forecasts[{len(feed['forecasts']) - 1}] is int, not an object"]

    def test_the_readers_keep_their_signatures(self):
        rows = REGISTER["accounts"] + [None]
        accounts, unread = read_register_rows({"accounts": rows})
        assert read_register({"accounts": rows}) == accounts
        assert unread == [f"accounts[{len(rows) - 1}] is NoneType, not an object"]
        assert read_book({"accounts": rows}).unread == tuple(unread)
        feed = json.loads(FEED.read_text())
        assert read_feed(feed) == read_feed_rows(feed)[0]
