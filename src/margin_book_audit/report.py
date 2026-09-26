"""Three ways, so silence is impossible.

CHECKED, DECLINED, NOT ESTABLISHED. A report with two of those has a hole
exactly where the interesting cases live: a pair that was never fed reads as a
pair that passed, and an audit that cannot say *I did not look at this* is
indistinguishable from one that looked and found nothing.

THE ENGINE'S OWN STRINGS ARE QUOTED VERBATIM. Paraphrasing machine output is how
two copies of a remedy drift apart -- the desk reads our wording, the engine
emits its own, and by the time they disagree nobody can tell which was right.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Sequence

from .audit import Result
from .coverage import ABSENT, SCORABLE, STATES, UNSCORABLE, Coverage
from .model import Manifest


def build(coverage: Coverage, result: Result, manifest: Manifest,
          unregistered: Sequence[str] = (), *,
          engine_version: str = "",
          history: Mapping[str, Any] = None,
          forecasters: Mapping[str, Any] = None,
          calibration: Mapping[str, Any] = None,
          projection: Mapping[str, Any] = None,
          reference: Mapping[str, Any] = None,
          learner: Mapping[str, Any] = None,
          ledger: str = None,
          producers: Sequence[str] = ()) -> Dict[str, Any]:
    leg = result.leg or {}
    checked = leg.get("checked") if isinstance(leg.get("checked"), Mapping) else {}
    shadow = result.shadow or {}
    return {
        "exit_code": result.exit_code,
        "complete": result.complete,
        "incomplete_reason": result.incomplete_reason,
        "engine": {"version": engine_version,
                   "schema_version": result.schema_version},

        # CHECKED -- with the denominator beside it, never a bare count of what
        # arrived. `expected` comes from the register; `received` from the feed.
        "checked": {
            "pairs_expected": coverage.expected,
            "engine_counts": dict(checked),
            "shadow_counts": dict(shadow.get("checked") or {}),
            "findings": [dict(f) for f in result.findings],
        },

        # THE FORECASTER, AS AN ENTITY. Six figures the engine computed from its
        # own books: how many forecasts each producer owed and issued, how many
        # have been scored, and how old the newest one is. Present even when
        # thin, because a producer with `graded_n` absent has not been measured
        # -- a different statement from a producer measured and found wanting,
        # and the two must not share a blank.
        "forecasters": {k: dict(v) for k, v in (forecasters or {}).items()},

        # WHAT THE SCORES ARE SO FAR, NULLS INCLUDED. A forecast on an hourly
        # horizon is ungradeable until the hour is up, so a single run scores
        # nothing and every rate below is null. Reported anyway: an absent
        # calibration block and one full of nulls read the same to a human and
        # mean opposite things to a gate.
        "calibration": dict(calibration or {}),

        # THE COMPARISON THE HEADLINE QUESTION NEEDS. `yardsticks` counts the
        # random walks the engine filed beside the forecasts it was sent.
        # Whether anything beat one cannot be answered until those mature; this
        # says whether the race was set up at all.
        #
        # It is ONE PER PAIR AND INSTANT, NOT ONE PER FORECAST. The engine files
        # a random walk beside the first forecast it receives for a pair and
        # answers every later one `already_filed`, so the reference and the
        # learner race the walk the desk's forecast already got. This comment
        # said the opposite until 2026-09-26, and no engine this package has
        # admitted behaved that way -- measured on 0.2.4 and 0.2.9. `model_id`
        # names whose reference it was, so a reader of `forecasters` can tell
        # this package's entrant from the desk's producers.
        "reference": dict(reference or {}),

        # THE SECOND YARDSTICK, the engine's own reference producer, filed only
        # when asked. `reason` is present whenever it filed nothing: an absent
        # learner and one that ran and found nothing to forecast must not
        # share a blank.
        "learner": dict(learner or {}),

        # WHO EACH SCORED MODEL IS, so a reader does not have to know which
        # ids were the desk's. `ledger` is null when nothing this run filed
        # outlives it -- which is why a single run's scores are all null.
        "scored": {
            "ledger": ledger,
            "producers": list(producers),
            "reference": (reference or {}).get("model_id"),
            "learner": (learner or {}).get("model_id"),
        },

        # WHERE THE BOOK IS HEADING, reported and NOT folded into the exit
        # code. A projected breach is a probability about an hour that has not
        # happened; a desk paged for one has been paged for a forecast. Its own
        # denominator travels with it, because the interesting number is how
        # many series could not be projected at all.
        "projection": dict(projection or {}),

        # DECLINED -- the engine looked and refused, with its reason verbatim.
        "declined": [dict(d) for d in result.declines],

        # NOT ESTABLISHED -- nobody looked, and this is the leg that makes the
        # other two honest.
        "not_established": {
            "coverage": coverage.counts,
            "absent": [p.account_id for p in coverage.by_state(ABSENT)],
            "unscorable": [{"account_id": p.account_id, "reason": p.reason,
                            "model_ids": list(p.model_ids)}
                           for p in coverage.by_state(UNSCORABLE)],
            "excluded_from_model": manifest.as_dict()["excluded"],
            "forecast_for_unregistered_account": list(unregistered),
            "history": dict(history or {}),
        },
    }


def render(report: Mapping[str, Any]) -> str:
    """A short human summary. The JSON above is the artifact; this is the line
    a desk reads in a terminal."""
    counts = report["not_established"]["coverage"]
    checked = report["checked"]
    lines = [
        f"exit {report['exit_code']}  "
        f"({'complete' if report['complete'] else 'INCOMPLETE'})",
        f"  pairs expected      {checked['pairs_expected']}",
        f"  scorable            {counts.get(SCORABLE, 0)}",
        f"  unscorable          {counts.get(UNSCORABLE, 0)}",
        f"  absent              {counts.get(ABSENT, 0)}",
        f"  findings            {len(checked['findings'])}",
        f"  declined            {len(report['declined'])}",
    ]
    history = report["not_established"].get("history") or {}
    if history and not history.get("placed"):
        absent = ", ".join(history.get("missing") or ["?"])
        lines.append(f"  history             not placed in time ({absent} absent)")
    reference = report.get("reference") or {}
    if reference.get("yardsticks"):
        lines.append(f"  yardsticks filed    {reference['yardsticks']}")
    projection = report.get("projection") or {}
    if projection.get("checked"):
        lines.append(f"  projected breaches  "
                     f"{len(projection.get('findings') or [])} of "
                     f"{projection['checked'].get('forecasts_issued', 0)} "
                     f"series projected")
    learner = report.get("learner") or {}
    if learner and not learner.get("fed"):
        lines.append(f"  learner             filed nothing -- {learner.get('reason', '?')}")
    lines.extend(_score_lines(report))
    if not report["complete"]:
        lines.append(f"  reason              {report['incomplete_reason']}")
    return "\n".join(lines)


def _score_lines(report: Mapping[str, Any]) -> List[str]:
    """What the ledger has graded so far, one line per model, with its count.

    ORDERED BY NAME, NOT BY SCORE. The engine scores producers and does not
    rank them, and neither does this: a lower CRPS is a closer forecast of what
    happened, and the count beside it says how much happened.

    NOTHING GRADED IS SAID IN WORDS, never as a zero. Every forecast a run files
    matures after the instant it audits, so one run on its own grades nothing,
    and a zero would read as a measurement.
    """
    calibration = report.get("calibration") or {}
    if not calibration:
        return []
    scored = report.get("scored") or {}
    recorded = int(calibration.get("recorded") or 0)
    graded = int(calibration.get("confirmed") or 0) + int(calibration.get("falsified") or 0)
    if not graded:
        later = ("audit this book again after they mature, against the same --ledger"
                 if scored.get("ledger") else
                 "nothing filed here outlives this run; pass --ledger PATH")
        return [f"  graded              none of {recorded} filed -- each matures "
                f"after the instant audited; {later}"]
    extra = [f"{n} {state}" for state, n in
             (("pending", int(calibration.get("pending") or 0)),
              ("ungradeable", int(calibration.get("ungradeable") or 0))) if n]
    lines = [f"  graded              {graded} of {recorded} filed"
             + (f" ({', '.join(extra)})" if extra else "")]
    roles = {model: "desk" for model in scored.get("producers") or ()}
    if scored.get("reference"):
        roles[scored["reference"]] = "this package's reference"
    if scored.get("learner"):
        roles[scored["learner"]] = "the engine's learner"
    for model, row in sorted((calibration.get("by_model") or {}).items()):
        if row.get("crps_approx") is None:
            continue
        role = f", {roles[model]}" if model in roles else ""
        lines.append(f"  crps {row['crps_approx']:<14.6g} {model} (n={row.get('n')}{role})")
    return lines


def to_json(report: Mapping[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True, default=str)
