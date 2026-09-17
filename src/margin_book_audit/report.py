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
          engine_version: str = "") -> Dict[str, Any]:
    leg = result.leg or {}
    checked = leg.get("checked") if isinstance(leg.get("checked"), Mapping) else {}
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
            "findings": [dict(f) for f in result.findings],
        },

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
    if not report["complete"]:
        lines.append(f"  reason              {report['incomplete_reason']}")
    return "\n".join(lines)


def to_json(report: Mapping[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True, default=str)
