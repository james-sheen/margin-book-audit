"""Present-and-scorable, present-and-unscorable, absent.

THE MIDDLE STATE IS THE ONE A BOOLEAN DESTROYS, and it is the one that tells a
desk where to look. A malformed record is a producer bug; no record at all is a
gap in coverage. Fold them and the report sends somebody to the wrong team --
and once folded the distinction cannot be recovered downstream, because by then
the record is simply not in the set.
"""

from __future__ import annotations

import json

from conftest import CORPUS
from margin_book_audit.coverage import ABSENT, SCORABLE, STATES, UNSCORABLE, \
    classify, unregistered
from margin_book_audit.model import partition
from margin_book_audit.records import read_feed, read_register


def _corpus():
    accounts = read_register(json.loads((CORPUS / "register.json").read_text()))
    feed = read_feed(json.loads((CORPUS / "feed.json").read_text()))
    manifest = partition(accounts)
    included = [a for a in accounts if a.account_id in set(manifest.included)]
    return accounts, included, feed


def test_the_three_states_are_all_reached_by_the_corpus():
    """An evidence corpus that never produces a state has not tested it."""
    _, included, feed = _corpus()
    counts = classify(included, feed).counts
    assert set(counts) == set(STATES)
    assert all(counts[state] > 0 for state in STATES), counts


def test_a_malformed_record_is_unscorable_and_not_absent():
    _, included, feed = _corpus()
    pairs = {p.account_id: p for p in classify(included, feed).pairs}
    assert pairs["acct_05"].state == UNSCORABLE
    assert "required_quantiles_absent" in pairs["acct_05"].reason
    assert pairs["acct_05"].model_ids, (
        "an unscorable pair must still name who sent it, or the producer bug "
        "has nobody to report to")


def test_a_pair_with_no_record_at_all_is_absent():
    _, included, feed = _corpus()
    pairs = {p.account_id: p for p in classify(included, feed).pairs}
    assert pairs["acct_06"].state == ABSENT
    assert pairs["acct_06"].model_ids == ()


def test_the_denominator_is_the_register_not_the_feed():
    """Counting what arrived and calling that the total is the shape the whole
    method exists to refuse."""
    _, included, feed = _corpus()
    result = classify(included, feed)
    assert result.expected == len(included)
    assert result.expected > len(result.by_state(SCORABLE))


def test_a_forecast_for_an_unregistered_account_is_reported_not_counted():
    accounts, included, feed = _corpus()
    assert unregistered(accounts, feed) == ("acct_99",)
    assert "acct_99" not in {p.account_id for p in classify(included, feed).pairs}
