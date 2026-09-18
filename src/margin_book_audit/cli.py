"""`margin-book-audit <register.json> <feed.json>`.

NO EXCEPTION PATH ESCAPES THE CONTRACT. Everything below funnels into an exit
code from the shared vocabulary: a traceback delivered as a successful result is
the transport reporting on itself, and a gate reading it would pass.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from typing import Optional, Sequence

from . import ENGINE_RANGE, __version__
from .floors import CLEAN, INCOMPLETE

#: How far ahead the reference forecaster and the engine's projection both
#: look. One literal, because these two numbers have to agree: the reference
#: is filed as a yardstick for the projection, and a yardstick measured over a
#: different span is not one. It was written out twice.
REFERENCE_HORIZON_S = 3600.0


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="margin-book-audit",
        description="Which forecasts a margin book expected, and which can be "
                    "scored. Bridges a desk's forecast feed to arbiter-engine.")
    p.add_argument("register", help="book register JSON")
    p.add_argument("feed", nargs="?", help="forecast feed JSON (optional)")
    p.add_argument("--json", action="store_true", help="emit the full artifact")
    p.add_argument("--coverage-only", action="store_true",
                   help="stage one only; never imports the engine")
    p.add_argument("--as-of", metavar="ISO8601",
                   help="evaluate at this instant instead of now. A staleness "
                        "rule and a lookback window are both measured from "
                        "NOW, so a run on the wall clock gives a different "
                        "answer every hour and a fixture built on one is a "
                        "time bomb. Corpus runs pass this; live runs do not.")
    p.add_argument("--self-forecast", action="store_true",
                   help="run this package's reference forecaster beside the "
                        "desk's, on the pairs the desk already covered. It "
                        "cannot close a coverage hole -- a reference that "
                        "filled in for an absent producer would be this "
                        "package answering its own question.")
    p.add_argument("--expected-from", metavar="MODEL_ID", action="append",
                   default=[],
                   help="a producer that owes a forecast for EVERY account. "
                        "Repeatable. Nothing is inferred: being in the feed is "
                        "permission to send one, not a debt, and without this "
                        "the forecaster's expected-against-issued balance "
                        "declines rather than being invented.")
    p.add_argument("--version", action="version",
                   version=f"margin-book-audit {__version__} "
                           f"(engine {ENGINE_RANGE})")
    return p



def _history_note(book) -> dict:
    """What the register said about WHEN its readings were taken.

    Reported rather than assumed, and reported even when it is fine, because
    the interesting value is the empty one: a register with no
    `history_interval_s` carries numbers and not a series, and this package
    will not invent a spacing for somebody else's book. Without this line a
    reader could not tell a book whose history was fed from one whose history
    was silently dropped.
    """
    if book.history_is_placeable:
        return {"placed": True,
                "as_of": book.as_of.isoformat(),
                "interval_s": float(book.history_interval_s)}
    missing = [name for name, value in (("as_of", book.as_of),
                                        ("history_interval_s",
                                         book.history_interval_s)) if not value]
    return {
        "placed": False,
        "missing": missing,
        "reason": ("the register carries readings with no times, so they were "
                   "not fed: a list of numbers is not a series, and spacing "
                   "them by a guess would put this package's assumption about "
                   "sampling into a desk's own history"),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    from .adapter import from_predictions, from_records
    from .coverage import classify, unregistered
    from .forecaster import MODEL_ID, predict
    from .model import build_model, partition
    from .records import load, read_book, read_feed
    from .report import build, render, to_json

    from .records import parse_timestamp
    at = parse_timestamp(args.as_of) if args.as_of else None
    if args.as_of and at is None:
        print(f"--as-of {args.as_of!r} is not an ISO-8601 instant",
              file=sys.stderr)
        return INCOMPLETE

    try:
        book = read_book(load(args.register))
        records = read_feed(load(args.feed)) if args.feed else []
    except (OSError, ValueError) as exc:
        print(f"could not read input: {exc}", file=sys.stderr)
        return INCOMPLETE

    accounts = list(book.accounts)
    manifest = partition(accounts)
    included = [a for a in accounts if a.account_id in set(manifest.included)]

    # STAGE ONE IS ABOUT THE DESK'S FEED AND NOTHING ELSE.
    #
    # `--self-forecast` used to append this package's own predictions to
    # `records` BEFORE classifying, so the reference model answered for the
    # desk. Measured on the corpus: `acct_05` (the producer sent an unusable
    # record) and `acct_06` (the producer sent nothing) both became `scorable`,
    # coverage read 6 of 6, and the audit exited CLEAN. A package whose first
    # paragraph refuses to count what arrived and call it the total was filling
    # its own denominator.
    #
    # The reference is now fed BESIDE the desk's forecasts and only for pairs
    # the desk already covered, which is what a comparison is. It cannot reach
    # a pair that is absent or unscorable, so it can never close a hole -- and
    # the off-by-k slice that used to build it is gone with the slice.
    coverage = classify(included, records)
    stray = unregistered(accounts, records)

    rows, _refused = from_records(records)
    reference_rows = []
    if args.self_forecast:
        issued = at or book.as_of or datetime.now(timezone.utc).replace(tzinfo=None)
        # THE HORIZON IN STEPS, which is what `predict` scales by and what the
        # CLI never passed. `steps_ahead` defaulted to 1, so the filed
        # quantiles were ONE-STEP residuals -- fifteen minutes on this corpus
        # -- carried under a one-hour label, with the record's own
        # `assumptions` list naming the square-root scaling its producer had
        # not applied. Measured on the shipped corpus: every interval exactly
        # half the width the stated assumption implies.
        #
        # NOT FED AT ALL when the interval is unknown, rather than guessed. A
        # register that does not say how far apart its readings are cannot say
        # how many steps an hour is, and an undated register is already not
        # fed for the same reason -- a yardstick whose scale is invented is
        # worse than no yardstick, because the comparison still prints.
        interval_s = book.history_interval_s
        if interval_s:
            steps = REFERENCE_HORIZON_S / float(interval_s)
            predictions = [p for p in
                           (predict(a.account_id, a.history, steps_ahead=steps)
                            for a in included)
                           if p is not None]
            reference_rows = from_predictions(
                predictions, issued_at=issued.isoformat(),
                horizon_s=REFERENCE_HORIZON_S)

    if args.coverage_only:
        from .audit import Result
        report = build(coverage, Result(), manifest, stray,
                       history=_history_note(book))
        print(to_json(report) if args.json else render(report))
        return CLEAN

    try:
        from arbiter_engine.api import (
            EngineSession, check, feed_model_figures, project,
        )
        from .audit import feed, read, read_projection
        from .model import FORECASTER_TYPE
    except ImportError as exc:
        print(f"the engine is not installed: {exc}\n"
              f"install the extra: pip install 'margin-book-audit[engine]'",
              file=sys.stderr)
        return INCOMPLETE

    # THE REFERENCE IS NOT A PRODUCER, and saying it was is what let it fail
    # the audit. `models:` is the engine's allow-list of ids that may submit;
    # the reference is now filed under its own `source`, so the engine keeps it
    # out of the producer population entirely and `model_unknown` cannot be
    # raised against it. Adding it here would declare a desk model that never
    # owes anything and never sends anything as a producer.
    producers = {r.model_id for r in records if r.usable}
    session = EngineSession()
    session.load_model(build_model(models=sorted(producers),
                                   expected_from=sorted(set(args.expected_from))))
    for account in included:
        session.add_entity(account.account_id, "Account", {
            "margin_balance": account.balance,
            "margin_requirement": account.requirement})
        # TIMESTAMPED, OR NOT FED AT ALL. `add_observations` with bare readings
        # stamps them ending at the wall clock, so under `--as-of` every
        # reading landed after the instant being evaluated and the window
        # axioms saw the subject's own future. `Register.stamped` places them
        # from what the document says; when the document says nothing, there is
        # no series here and `_history_note` reports that instead.
        stamped = book.stamped(account)
        if stamped:
            session.add_observations(
                account.account_id, "margin_balance", stamped)

    # C2's second half. A generated model is an output; this reads it back
    # through the engine before anything is audited against it.
    from .model import ModelUnreadable, read_back
    try:
        proof = read_back(session)
    except ModelUnreadable as exc:
        print(f"the generated model could not be proofread: {exc}", file=sys.stderr)
        return INCOMPLETE
    broken = {k: v for k, v in proof.items()
              if v and k in ("unreachable_declarations", "dropped_declarations")}
    if broken:
        print(f"the generated model does not hold up: {broken}", file=sys.stderr)
        return INCOMPLETE

    from contextlib import nullcontext
    from arbiter_engine.api import as_of
    frame = as_of(at) if at is not None else nullcontext()
    with frame:
        fed = feed(session, rows, coverage, at=at)
        if reference_rows:
            reference_fed = feed(session, reference_rows, coverage,
                                 at=at, source=MODEL_ID)
        else:
            reference_fed = {}
        # THE FORECASTER IS AN ENTITY LIKE ANY OTHER, which is the claim the
        # generated model has been making with nobody to back it: it declared a
        # `ForecastModel` type with six indicators and this never created one,
        # so CONSERVATION, HOMEOSTASIS, MONOTONICITY and RESPONSIVENESS were
        # declared over a type with no instances and evaluated nothing. The
        # engine writes the figures; the TYPE NAME is this package's word,
        # because a domain-free core cannot hold one.
        figures = feed_model_figures(session, FORECASTER_TYPE, at=at)
        # THE `dynamics:` BLOCK IS A DECLARATION, AND A DECLARATION NOTHING
        # RUNS IS A CHECK THE DESK BELIEVES IS RUNNING. The generated model has
        # declared `local_level` with a `report_above` and a lookback from the
        # first commit, and this never called the verb that reads them -- so
        # the hour ahead of a margin book, which is the only reason a floor
        # read off the account is interesting, went unasked every cycle.
        #
        # AFTER the reference is fed, not before: `project` files its own
        # forecast and its own random walk, and running it first would put the
        # engine's records in the ledger before the producers' with nothing
        # gained.
        projection = read_projection(
            project(session, horizon_s=REFERENCE_HORIZON_S))
        result = read(check(session))
        calibration = dict(session.ledger.calibration())
    engine_version = ""
    try:
        from importlib.metadata import version as _v
        engine_version = _v("arbiter-engine")
    except Exception:  # pragma: no cover - metadata absent in a source tree
        pass
    report = build(coverage, result, manifest, stray,
                   engine_version=engine_version,
                   history=_history_note(book),
                   forecasters=figures,
                   calibration=calibration,
                   projection=projection,
                   reference={"fed": int(reference_fed.get("filed", 0)),
                              # WHOSE it is. `forecasters` is keyed by model
                              # id and this package's own reference sat in it
                              # unmarked, beside the desk's producers, as
                              # though a desk had sent it.
                              "model_id": MODEL_ID if reference_rows else None,
                              "yardsticks": int(fed.get("baselines", 0))
                                            + int(reference_fed.get("baselines", 0))})
    print(to_json(report) if args.json else render(report))
    return result.exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
