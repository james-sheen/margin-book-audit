"""Stage one exits 1 on an unscorable or absent pair, as the full audit does.

`--coverage-only` returned 0 whatever coverage said. On the shipped corpus it
reported one pair unscorable and one absent -- each, by the table this package
opens with, something the producer or whoever owns coverage must fix -- and
exited 0, where the full audit exits 1 on the same two pairs. An excluded
account and a forecast for an account nobody registered stay reported and
unfloored, as they are in the full audit.
"""

import json

import pytest

from conftest import AS_OF, CORPUS, needs_engine
from margin_book_audit.cli import main
from margin_book_audit.floors import CLEAN, FINDINGS

REGISTER = json.loads((CORPUS / "register.json").read_text())
FEED = json.loads((CORPUS / "feed.json").read_text())


def _book(tmp_path, drop=()):
    """The shipped corpus without the named accounts, and without their
    forecasts -- one left behind would be a forecast for an unregistered
    account, a third thing to report."""
    register = dict(REGISTER, accounts=[a for a in REGISTER["accounts"]
                                        if a["id"] not in drop])
    feed = dict(FEED, forecasts=[f for f in FEED["forecasts"]
                                 if f["entity_id"] not in drop])
    (tmp_path / "register.json").write_text(json.dumps(register))
    (tmp_path / "feed.json").write_text(json.dumps(feed))
    return tmp_path / "register.json", tmp_path / "feed.json"


def _run(capsys, register, feed, *extra):
    code = main([str(register), str(feed), "--as-of", AS_OF, "--json", *extra])
    return code, json.loads(capsys.readouterr().out)


def test_the_shipped_corpus_reports_its_two_gaps(capsys):
    code, report = _run(capsys, CORPUS / "register.json", CORPUS / "feed.json",
                        "--coverage-only")
    assert report["not_established"]["coverage"] == {
        "scorable": 4, "unscorable": 1, "absent": 1}
    assert code == FINDINGS and report["exit_code"] == FINDINGS
    assert report["complete"] is True


@pytest.mark.parametrize("drop, state", [
    (("acct_06",), "unscorable"),            # acct_05's forecast lacks its q95
    (("acct_05",), "absent"),                # acct_06 has none
], ids=["unscorable alone", "absent alone"])
def test_either_gap_alone_is_a_finding(tmp_path, capsys, drop, state):
    code, report = _run(capsys, *_book(tmp_path, drop), "--coverage-only")
    assert report["not_established"]["coverage"][state] == 1
    assert sum(report["not_established"]["coverage"].values()) == 5
    assert code == FINDINGS


def test_every_pair_scorable_is_clean_with_exclusions_and_a_stray_reported(
        tmp_path, capsys):
    code, report = _run(capsys, *_book(tmp_path, ("acct_05", "acct_06")),
                        "--coverage-only")
    established = report["not_established"]
    assert established["coverage"] == {"scorable": 4, "unscorable": 0, "absent": 0}
    assert {e["account_id"] for e in established["excluded_from_model"]} == {
        "acct_07", "acct_08"}
    assert established["forecast_for_unregistered_account"] == ["acct_99"]
    assert code == CLEAN and report["exit_code"] == CLEAN


def test_the_terminal_line_says_so(capsys):
    assert main([str(CORPUS / "register.json"), str(CORPUS / "feed.json"),
                 "--as-of", AS_OF, "--coverage-only"]) == FINDINGS
    assert capsys.readouterr().out.startswith("exit 1  (complete)")


@needs_engine
@pytest.mark.parametrize("drop", [(), ("acct_05", "acct_06")],
                         ids=["the shipped corpus", "every pair scorable"])
def test_stage_one_agrees_with_the_full_audit(tmp_path, capsys, drop):
    register, feed = _book(tmp_path, drop)
    stage_one, _ = _run(capsys, register, feed, "--coverage-only")
    full, _ = _run(capsys, register, feed)
    assert stage_one == full
