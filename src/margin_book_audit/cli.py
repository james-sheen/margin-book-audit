"""`margin-book-audit <register.json> <feed.json>`.

NO EXCEPTION PATH ESCAPES THE CONTRACT. Everything below funnels into an exit
code from the shared vocabulary: a traceback delivered as a successful result is
the transport reporting on itself, and a gate reading it would pass.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from typing import Optional, Sequence

from . import ENGINE_RANGE, __version__
from .floors import CLEAN, INCOMPLETE


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
                   help="add this package's reference forecaster to the feed")
    p.add_argument("--version", action="version",
                   version=f"margin-book-audit {__version__} "
                           f"(engine {ENGINE_RANGE})")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    from .adapter import from_predictions, from_records
    from .coverage import classify, unregistered
    from .forecaster import predict
    from .model import build_model, partition
    from .records import load, read_feed, read_register
    from .report import build, render, to_json

    from .records import parse_timestamp
    at = parse_timestamp(args.as_of) if args.as_of else None
    if args.as_of and at is None:
        print(f"--as-of {args.as_of!r} is not an ISO-8601 instant",
              file=sys.stderr)
        return INCOMPLETE

    try:
        accounts = read_register(load(args.register))
        records = read_feed(load(args.feed)) if args.feed else []
    except (OSError, ValueError) as exc:
        print(f"could not read input: {exc}", file=sys.stderr)
        return INCOMPLETE

    manifest = partition(accounts)
    included = [a for a in accounts if a.account_id in set(manifest.included)]

    rows, _refused = from_records(records)
    if args.self_forecast:
        now = at or datetime.utcnow()
        predictions = [p for p in
                       (predict(a.account_id, a.history) for a in included)
                       if p is not None]
        rows += from_predictions(predictions, issued_at=now.isoformat(),
                                 horizon_s=3600.0)
        records = records + read_feed({"forecasts": rows[len(records):]})

    coverage = classify(included, records)
    stray = unregistered(accounts, records)

    if args.coverage_only:
        from .audit import Result
        report = build(coverage, Result(), manifest, stray)
        print(to_json(report) if args.json else render(report))
        return CLEAN

    try:
        from arbiter_engine.api import EngineSession, check
        from .audit import feed, read
    except ImportError as exc:
        print(f"the engine is not installed: {exc}\n"
              f"install the extra: pip install 'margin-book-audit[engine]'",
              file=sys.stderr)
        return INCOMPLETE

    session = EngineSession()
    session.load_model(build_model(
        models=sorted({r.model_id for r in records if r.usable})))
    for account in included:
        session.add_entity(account.account_id, "Account", {
            "margin_balance": account.balance,
            "margin_requirement": account.requirement})
        if account.history:
            session.add_observations(
                account.account_id, "margin_balance", list(account.history))

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
    from arbiter_engine.clock import as_of
    frame = as_of(at) if at is not None else nullcontext()
    with frame:
        feed(session, rows, coverage, at=at)
        result = read(check(session))
    engine_version = ""
    try:
        from importlib.metadata import version as _v
        engine_version = _v("arbiter-engine")
    except Exception:  # pragma: no cover - metadata absent in a source tree
        pass
    report = build(coverage, result, manifest, stray,
                   engine_version=engine_version)
    print(to_json(report) if args.json else render(report))
    return result.exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
