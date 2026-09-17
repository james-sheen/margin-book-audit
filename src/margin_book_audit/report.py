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
          reference: Mapping[str, Any] = None) -> Dict[str, Any]:
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
        "reference": dict(reference or {}),

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
    if not report["complete"]:
        lines.append(f"  reason              {report['incomplete_reason']}")
    return "\n".join(lines)


def to_json(report: Mapping[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True, default=str)
