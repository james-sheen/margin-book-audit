"""Stage one: does the forecast exist at all, and can it be scored?

THIS STAGE HAS NO DEPENDENCY ON THE ENGINE, and that is the layering the method
asks for rather than an accident of what got written first. It answers the
question the engine cannot be asked -- *is there anything here* -- and a bridge
that needs the engine installed to answer it has its layering backwards.
`tests/test_stage_one_is_dependency_free.py` asserts it by making the engine
unimportable and running this whole path.

THREE WAYS, NEVER A BOOLEAN. A pair that was expected to carry a forecast is
`scorable`, `unscorable` or `absent`, and the middle one is the one a boolean
destroys. A record that arrived malformed is evidence of a producer bug; no
record at all is evidence of a gap in coverage. Folding them tells a desk to
go looking in the wrong place, and once folded the distinction cannot be
recovered downstream -- by then the record is simply not in the set.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from .records import Account, ForecastRecord

SCORABLE = "scorable"
UNSCORABLE = "unscorable"
ABSENT = "absent"

#: Every state a pair can be in. Closed, so a caller can enumerate the report
#: without discovering a fourth state in production.
STATES: Tuple[str, str, str] = (SCORABLE, UNSCORABLE, ABSENT)


@dataclass(frozen=True)
class Pair:
    """One (account, property) the register said should carry a forecast."""

    account_id: str
    prop: str
    state: str
    model_ids: Tuple[str, ...] = ()
    reason: str = ""


@dataclass(frozen=True)
class Coverage:
    pairs: Tuple[Pair, ...]

    def by_state(self, state: str) -> Tuple[Pair, ...]:
        return tuple(p for p in self.pairs if p.state == state)

    @property
    def counts(self) -> Dict[str, int]:
        return {state: len(self.by_state(state)) for state in STATES}

    @property
    def expected(self) -> int:
        """The DENOMINATOR, and the reason this stage exists.

        *371 forecasts received* is not a measurement until something says out
        of how many. Counting what arrived and calling that the total is the
        shape the whole method exists to refuse.
        """
        return len(self.pairs)


def classify(accounts: Sequence[Account], records: Sequence[ForecastRecord],
             prop: str = "margin_balance") -> Coverage:
    """Pair the register against the feed, three ways.

    The register is the population. A record naming an account the register does
    not carry is NOT silently promoted into the denominator -- it is reported by
    `unregistered` below, because a forecast for something that does not exist
    is a different problem from a forecast that did not arrive.
    """
    filed: Dict[str, List[ForecastRecord]] = {}
    for record in records:
        if record.prop == prop:
            filed.setdefault(record.account_id, []).append(record)

    pairs: List[Pair] = []
    for account in accounts:
        if not account.forecast_expected:
            continue
        mine = filed.get(account.account_id, [])
        if not mine:
            pairs.append(Pair(account.account_id, prop, ABSENT,
                              reason="no record named this account"))
            continue
        usable = [r for r in mine if r.usable]
        if usable:
            pairs.append(Pair(account.account_id, prop, SCORABLE,
                              model_ids=tuple(sorted({r.model_id for r in usable}))))
        else:
            reasons = sorted({r.unusable or "unstated" for r in mine})
            pairs.append(Pair(account.account_id, prop, UNSCORABLE,
                              model_ids=tuple(sorted({r.model_id for r in mine})),
                              reason=", ".join(reasons)))
    return Coverage(tuple(pairs))


def unregistered(accounts: Sequence[Account],
                 records: Sequence[ForecastRecord]) -> Tuple[str, ...]:
    """Accounts a forecast names that the register does not carry.

    Reported rather than folded into the denominator. A model forecasting a
    closed account is a real finding about the model; counting it as coverage
    would make a stale subscriber list look like diligence.
    """
    known = {a.account_id for a in accounts}
    return tuple(sorted({r.account_id for r in records
                         if r.account_id and r.account_id not in known}))
