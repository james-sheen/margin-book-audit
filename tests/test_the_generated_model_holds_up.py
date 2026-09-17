"""A generated model is an output, and nothing else proofreads it.

READ IT BACK THROUGH THE ENGINE, not by eye. The first version of `build_model`
interpolated `models:` two columns short; the document was still YAML-shaped and
the loader raised a parser error eight lines below the mistake. Worse than a
raise is the version that LOADS: a declaration the engine cannot reach is never
evaluated, and a check nobody runs looks exactly like a check that found
nothing.
"""

from __future__ import annotations

import pytest

from conftest import needs_engine
from margin_book_audit.model import FORECASTER_TYPE, build_model, partition, \
    read_back
from margin_book_audit.records import Account

pytestmark = needs_engine


def _loaded(**kwargs):
    from arbiter_engine.api import EngineSession
    session = EngineSession()
    session.load_model(build_model(**kwargs))
    return session


def test_the_model_loads_with_no_models_declared():
    assert read_back(_loaded())["dropped_declarations"] == []


def test_the_model_loads_with_models_declared():
    """The interpolation that was broken. Two ids, so the join is exercised."""
    proof = read_back(_loaded(models=["garch_v3", "lstm_v1"]))
    assert proof["dropped_declarations"] == []
    assert proof["unreachable_declarations"] == []


def test_nothing_it_declares_is_unreachable():
    """A declaration that provably cannot fire is a check the desk believes is
    running and is not."""
    assert read_back(_loaded(models=["garch_v3"]))["unreachable_declarations"] == []


def test_every_field_it_writes_is_read_by_something():
    assert read_back(_loaded(models=["garch_v3"]))["unread_fields"] == []


def test_the_forecaster_type_is_declared_so_the_monitor_has_somewhere_to_land():
    assert FORECASTER_TYPE in read_back(_loaded())["indicators"]


def test_the_read_back_is_looking_at_a_real_page():
    """THE ASSERTIONS ABOVE ARE ALL `== []`, and an empty list is what a dict
    lookup against the wrong level returns. This is what stops them being
    vacuous: the proof must actually carry the model it claims to have read."""
    proof = read_back(_loaded(models=["garch_v3"]))
    assert proof["entity_types"], "the read-back found no entity types at all"
    assert proof["indicators"], "the read-back found no indicators at all"


def test_a_relocated_key_is_refused_rather_than_read_as_clean(monkeypatch):
    """A proofreader that cannot find the page must not report a clean page.

    This is the regression: the keys live under `model`, the first version read
    them from the top of the payload, and three empty lists came back on every
    call. Moving them again must go RED here rather than reporting a clean
    model by finding nothing.
    """
    import arbiter_engine.api as engine_api
    from margin_book_audit.model import ModelUnreadable

    class Envelope:
        def to_dict(self):
            # The keys moved back to the top, where they used to be read from.
            return {"payload": {"unreachable_declarations": [],
                                "unread_fields": [],
                                "model": {"entity_types": ["Account"]}}}

    monkeypatch.setattr(engine_api, "model_describe", lambda _s: Envelope())
    with pytest.raises(ModelUnreadable):
        read_back(_loaded())


def test_no_model_block_at_all_is_refused(monkeypatch):
    import arbiter_engine.api as engine_api
    from margin_book_audit.model import ModelUnreadable

    class Envelope:
        def to_dict(self):
            return {"payload": {}}

    monkeypatch.setattr(engine_api, "model_describe", lambda _s: Envelope())
    with pytest.raises(ModelUnreadable):
        read_back(_loaded())
