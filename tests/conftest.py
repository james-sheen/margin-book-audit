import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

CORPUS = ROOT / "corpus"

#: The instant the corpus is evaluated at. PINNED, because a staleness rule and
#: a lookback window are both measured from NOW: run on the wall clock, this
#: suite passes for the few minutes after the corpus was written and then
#: reports stale forecasts forever. A fixture whose verdict depends on the hour
#: is not a fixture.
AS_OF = "2026-09-17T09:35:00"


def engine_available() -> bool:
    try:
        import arbiter_engine  # noqa: F401
    except ImportError:
        return False
    return True


needs_engine = pytest.mark.skipif(
    not engine_available(),
    reason="the engine extra is not installed: pip install 'margin-book-audit[engine]'")
