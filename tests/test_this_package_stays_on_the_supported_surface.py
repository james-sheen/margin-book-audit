"""Every engine name this package imports is one the engine promises to keep.

`arbiter_engine.__all__` is the supported surface, and the engine's README says
plainly that a path outside it may move without a major version. This package
declares `arbiter-engine>=0.1.18,<0.2` -- a ceiling that reads as *anything in
the 0.1 line will work* -- while importing `arbiter_engine.forecast` and
`arbiter_engine.clock`, neither of which is in `__all__`. The ceiling was
asserting a promise the engine had not made.

Nothing had broken. That is exactly why it needed a test: the failure mode is a
minor release moving a module this package reads, and the first thing anyone
would look at is the ceiling that says it should have been fine.

WHAT THIS DOES NOT DO is forbid deep imports forever. If one becomes necessary,
this test is the place to record it -- with the reason -- so the decision is
made once and visibly rather than by whoever writes the next import.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from conftest import needs_engine

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "src" / "margin_book_audit"

#: Deep paths this package is knowingly allowed to import, each with the reason
#: it could not be spelled through a supported name. Empty, and that is the
#: point: every engine call this package makes now goes through `api`.
SANCTIONED_DEEP_IMPORTS: dict[str, str] = {}


def _engine_imports():
    """Every `arbiter_engine...` import in the package, as (module, file)."""
    found = []
    for path in sorted(SOURCE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] == "arbiter_engine":
                    found.append((node.module, path.name))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] == "arbiter_engine":
                        found.append((alias.name, path.name))
    return found


class TestTheImportsAreAllSupported:

    def test_the_package_imports_the_engine_at_all(self):
        """Non-vacuity. Every assertion below is over a list, and an empty one
        satisfies them all -- so a refactor that renamed the package would turn
        this file into a guard measuring nothing."""
        assert _engine_imports(), (
            "no engine imports found; either the package stopped using the "
            "engine or this test stopped being able to see them")

    @needs_engine
    def test_every_imported_module_is_a_supported_name(self):
        import arbiter_engine

        supported = set(arbiter_engine.__all__)
        stray = []
        for module, filename in _engine_imports():
            parts = module.split(".")
            if len(parts) == 1:
                continue                       # the root package itself
            if parts[1] in supported:
                continue
            if module in SANCTIONED_DEEP_IMPORTS:
                continue
            stray.append(f"{module} ({filename})")
        assert not stray, (
            f"these imports reach past `arbiter_engine.__all__`: {stray}. The "
            f"engine does not promise them across a minor release, so this "
            f"package's `<0.2` ceiling does not cover them. Either use the "
            f"`api` re-export, or record the path in "
            f"SANCTIONED_DEEP_IMPORTS with the reason.")

    @needs_engine
    def test_the_names_taken_from_api_actually_exist(self):
        """The count is not the promise; the names are. A supported MODULE can
        still be imported for a member that moved within it."""
        from arbiter_engine import api

        missing = []
        for path in sorted(SOURCE.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
            for node in ast.walk(tree):
                if (isinstance(node, ast.ImportFrom)
                        and node.module == "arbiter_engine.api"):
                    for alias in node.names:
                        if not hasattr(api, alias.name):
                            missing.append(f"{alias.name} ({path.name})")
        assert not missing, f"named on `api` and not there: {missing}"


class TestTheSanctionedListIsHonest:

    def test_it_names_only_paths_actually_imported(self):
        """A sanctioned entry for an import nobody makes is a permission that
        outlives its reason -- the same dead-member shape the engine's own
        decline vocabularies were pruned for."""
        imported = {module for module, _ in _engine_imports()}
        stale = sorted(set(SANCTIONED_DEEP_IMPORTS) - imported)
        assert not stale, (
            f"{stale} are sanctioned here and imported nowhere; drop the entry")
