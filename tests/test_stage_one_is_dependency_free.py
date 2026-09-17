"""Stage one answers with the engine made unimportable.

A BRIDGE THAT CANNOT RUN ITS FIRST STAGE WITHOUT THE ENGINE HAS ITS LAYERING
BACKWARDS. *Does the thing exist at all* is the question the engine cannot be
asked, so it has to be answerable before the engine is present -- and the only
way to know that is to make it absent and run.

ASSERTED BY BLOCKING THE IMPORT, not by reading the import lines. A module that
imports the engine lazily inside a function passes a source scan and fails here,
which is the failure worth catching.
"""

from __future__ import annotations

import builtins
import importlib
import json
import sys

import pytest

from conftest import CORPUS

STAGE_ONE = ["margin_book_audit.records", "margin_book_audit.coverage",
             "margin_book_audit.forecaster", "margin_book_audit.model",
             "margin_book_audit.adapter", "margin_book_audit.floors",
             "margin_book_audit.report"]


@pytest.fixture
def engine_forbidden(monkeypatch):
    real_import = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name == "arbiter_engine" or name.startswith("arbiter_engine."):
            raise ImportError(f"blocked for this test: {name}")
        return real_import(name, *args, **kwargs)

    for module in list(sys.modules):
        if module.startswith("arbiter_engine") or module.startswith("margin_book_audit"):
            monkeypatch.delitem(sys.modules, module, raising=False)
    monkeypatch.setattr(builtins, "__import__", guarded)
    yield


def test_every_stage_one_module_imports(engine_forbidden):
    for name in STAGE_ONE:
        importlib.import_module(name)


def test_the_whole_classification_path_runs(engine_forbidden):
    records = importlib.import_module("margin_book_audit.records")
    coverage = importlib.import_module("margin_book_audit.coverage")
    model = importlib.import_module("margin_book_audit.model")

    accounts = records.read_register(json.loads((CORPUS / "register.json").read_text()))
    feed = records.read_feed(json.loads((CORPUS / "feed.json").read_text()))
    manifest = model.partition(accounts)
    included = [a for a in accounts if a.account_id in set(manifest.included)]
    result = coverage.classify(included, feed)

    assert result.expected == 6
    assert result.counts == {"scorable": 4, "unscorable": 1, "absent": 1}


def test_the_guard_actually_blocks(engine_forbidden):
    """Without this the file proves only that nothing tried to import it."""
    with pytest.raises(ImportError):
        importlib.import_module("arbiter_engine")
