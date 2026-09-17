"""Feed what stage one vouched for, read the leg, compose an exit code.

INGESTION IS LAYERED. Only pairs stage one classified `scorable` are fed, and
the engine's own `missing_property` decline is the belt to that brace -- two
independent reasons a bad record does not reach a verdict, because either alone
has failed somewhere before.

A SCHEMA MISMATCH IS A HARD STOP. If the envelope arrives under a version this
package has not been measured against, the run reports INCOMPLETE and says so.
Reading an unknown envelope optimistically is how a gate starts passing for a
reason that has nothing to do with the book.

NO EXCEPTION PATH ESCAPES THE CONTRACT. A traceback delivered as a successful
result is the transport reporting on itself, so everything below returns a
Result and the CLI turns that into a code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from . import ENGINE_RANGE
from .coverage import SCORABLE, Coverage
from .floors import CLEAN, FINDINGS, INCOMPLETE, compose, floor_for_decline, \
    floor_for_finding

#: The envelope version this package reads, READ FROM THE SHARED CORE rather
#: than transcribed. `presence_audit` publishes the contract constant precisely
#: so every vertical compares against one record of it; a list typed in here was
#: a second copy, and the first version of this file guessed `"1.0"` as a string
#: against an integer `1` and hard-stopped on a perfectly good envelope. A
#: constant nobody measured is worse than no check, because it fails closed on
#: the healthy case and a reader believes the version really did move.
try:  # pragma: no cover - the fallback is exercised by the dependency-free test
    from presence_audit import ENVELOPE_SCHEMA_VERSION as _SHARED_SCHEMA
except ImportError:  # pragma: no cover
    _SHARED_SCHEMA = 1

KNOWN_SCHEMA_VERSIONS = (_SHARED_SCHEMA,)


def _same_version(seen: object, known: object) -> bool:
    """Compare as strings, because the wire carries whichever the producer
    chose and `1` and `"1"` are the same claim about the same envelope."""
    return str(seen).strip() == str(known).strip()


@dataclass
class Result:
    exit_code: int = CLEAN
    schema_version: str = ""
    findings: List[Mapping[str, Any]] = field(default_factory=list)
    declines: List[Mapping[str, Any]] = field(default_factory=list)
    leg: Mapping[str, Any] = field(default_factory=dict)
    incomplete_reason: str = ""

    @property
    def complete(self) -> bool:
        return not self.incomplete_reason


def _payload(envelope: Any) -> Mapping[str, Any]:
    raw = envelope.to_dict() if hasattr(envelope, "to_dict") else envelope
    if not isinstance(raw, Mapping):
        return {}
    return raw.get("payload") if isinstance(raw.get("payload"), Mapping) else raw


def _meta(envelope: Any) -> Mapping[str, Any]:
    raw = envelope.to_dict() if hasattr(envelope, "to_dict") else envelope
    meta = raw.get("meta") if isinstance(raw, Mapping) else None
    return meta if isinstance(meta, Mapping) else {}


def feed(session: Any, rows: Sequence[Mapping[str, Any]], coverage: Coverage,
         *, at: Any = None) -> Dict[str, Any]:
    """Ingest only the rows stage one vouched for. Returns the engine's tally."""
    from arbiter_engine.forecast import ingest_forecasts

    vouched = {(p.account_id, p.prop) for p in coverage.by_state(SCORABLE)}
    eligible = [r for r in rows
                if (r.get("entity_id"), r.get("property")) in vouched]
    return dict(ingest_forecasts(session, eligible, at=at))


def read(envelope: Any) -> Result:
    """Turn one envelope into a Result, or say why it could not be read."""
    meta = _meta(envelope)
    raw_version = meta.get("schema_version")
    version = "" if raw_version is None else str(raw_version)
    if version and not any(_same_version(raw_version, known)
                           for known in KNOWN_SCHEMA_VERSIONS):
        return Result(
            exit_code=INCOMPLETE, schema_version=version,
            incomplete_reason=(
                f"envelope schema_version {version!r} is not the one this "
                f"package reads "
                f"({', '.join(str(v) for v in KNOWN_SCHEMA_VERSIONS)}); the "
                f"engine pin is {ENGINE_RANGE}"))

    payload = _payload(envelope)
    leg = payload.get("forecasts")
    if not isinstance(leg, Mapping):
        return Result(
            exit_code=INCOMPLETE, schema_version=version,
            incomplete_reason=(
                "the envelope carried no `forecasts` leg, so nothing states "
                "how many forecasts were expected; a count of what arrived is "
                "not a denominator"))

    findings = [f for f in leg.get("findings") or [] if isinstance(f, Mapping)]
    declines = [d for d in leg.get("not_checked") or [] if isinstance(d, Mapping)]
    codes = [floor_for_finding(str(f.get("problem_type") or "")) for f in findings]
    codes += [floor_for_decline(str(d.get("reason") or d.get("kind") or ""))
              for d in declines]
    # COMPOSING NOTHING IS `2` IN THE SHARED RULE, and that is right for LEGS:
    # a battery whose legs were never collected must not read as clean. What is
    # composed here is different -- the outcomes WITHIN one leg whose presence
    # was already confirmed above -- so an empty list means the leg ran and
    # reported nothing, which is the one case that genuinely is clean.
    #
    # Spelled out because it otherwise reads exactly like the failure the core
    # exists to prevent, and a reader cannot tell a considered exception from a
    # reintroduced bug by looking at the expression.
    exit_code = compose(*codes) if codes else CLEAN
    return Result(exit_code=exit_code, schema_version=version,
                  findings=findings, declines=declines, leg=dict(leg))
