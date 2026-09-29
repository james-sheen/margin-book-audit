"""The README installs this package from where it is.

It is not on PyPI, where `pip install 'margin-book-audit[engine]'` answers 404, and the
corpus it is run on lives in the repository. So the README clones a release tag -- and
the tag it names is this version, or the next release would leave it pointing at the
last one.
"""
from __future__ import annotations

from conftest import ROOT
from margin_book_audit import __version__

README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_the_install_line_names_the_release_this_is():
    assert (f"git clone --branch v{__version__} "
            "https://github.com/james-sheen/margin-book-audit") in README
    assert "pip install 'margin-book-audit" not in README
