"""The two files this package reads, and what it refuses to infer from them.

A BOOK REGISTER says what exists: the accounts, their current balances, and the
requirement each one is held to. A FORECAST FEED says what somebody predicted.
Neither is produced here and neither is trusted -- a record that cannot be used
is CARRIED with the reason rather than dropped, because stage one's whole job is
telling *absent* apart from *present and unreadable*, and a reader that folds
them cannot recover the difference later.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

#: The two levels a distributional record cannot be scored without. The engine
#: enforces this again on its own side; stating it here is what lets stage one
#: answer without the engine installed.
REQUIRED_QUANTILES: Tuple[str, str] = ("q05", "q95")


def parse_timestamp(raw: Any) -> Optional[datetime]:
    """An ISO-8601 stamp, or None. Never raises on a caller's data."""
    if isinstance(raw, datetime):
        return raw if raw.tzinfo is None else raw.astimezone(timezone.utc).replace(tzinfo=None)
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is None else \
        parsed.astimezone(timezone.utc).replace(tzinfo=None)


@dataclass(frozen=True)
class Account:
    """One account in the book. `requirement` is None when the register did not
    carry one -- which is a fact to report, not a zero to assume."""

    account_id: str
    balance: Optional[float] = None
    requirement: Optional[float] = None
    forecast_expected: bool = True
    history: Tuple[float, ...] = ()


@dataclass(frozen=True)
class ForecastRecord:
    """One prediction, exactly as the feed stated it.

    `unusable` is the reason stage one could not score it, or None. A record
    with a reason is still a record: it was PRESENT, and reporting it as absent
    would credit the desk with a gap it does not have and hide a producer bug.
    """

    model_id: str
    account_id: str
    prop: str
    issued_at: Optional[datetime]
    horizon_s: Optional[float]
    quantiles: Mapping[str, float] = field(default_factory=dict)
    samples: Tuple[float, ...] = ()
    mean: Optional[float] = None
    sigma: Optional[float] = None
    unusable: Optional[str] = None
    raw: Mapping[str, Any] = field(default_factory=dict)

    @property
    def usable(self) -> bool:
        return self.unusable is None


def _number(raw: Any) -> Optional[float]:
    if isinstance(raw, bool) or raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if value == value and value not in (float("inf"), float("-inf")) else None


def read_register(payload: Any) -> List[Account]:
    """Accounts from a register document. Unreadable rows are skipped by id."""
    rows = payload.get("accounts") if isinstance(payload, Mapping) else payload
    accounts: List[Account] = []
    for row in rows or []:
        if not isinstance(row, Mapping):
            continue
        account_id = str(row.get("id") or row.get("account_id") or "").strip()
        if not account_id:
            continue
        history = tuple(
            value for value in (_number(v) for v in row.get("history") or ())
            if value is not None)
        accounts.append(Account(
            account_id=account_id,
            balance=_number(row.get("margin_balance")),
            requirement=_number(row.get("margin_requirement")),
            forecast_expected=bool(row.get("forecast_expected", True)),
            history=history))
    return accounts


def read_feed(payload: Any) -> List[ForecastRecord]:
    """Forecast records, each carrying its own reason when it cannot be scored.

    THE REASONS ARE STAGE ONE'S, not the engine's. They answer *can this be
    scored at all*, which is askable with nothing installed; the engine's own
    vocabulary answers *was it scored, and against what*, and the two are
    reported separately so a desk can tell a producer bug from a modelling gap.
    """
    rows = payload.get("forecasts") if isinstance(payload, Mapping) else payload
    out: List[ForecastRecord] = []
    for row in rows or []:
        if not isinstance(row, Mapping):
            continue
        quantiles = {
            str(k): v for k, v in (row.get("quantiles") or {}).items()
            if _number(v) is not None}
        quantiles = {k: float(v) for k, v in quantiles.items()}
        samples = tuple(
            value for value in (_number(v) for v in row.get("samples") or ())
            if value is not None)
        mean, sigma = _number(row.get("mean")), _number(row.get("sigma"))
        issued_at = parse_timestamp(row.get("issued_at"))
        horizon_s = _number(row.get("horizon_s"))

        reason: Optional[str] = None
        account_id = str(row.get("entity_id") or row.get("account_id") or "").strip()
        if not account_id:
            reason = "no_account_named"
        elif issued_at is None:
            reason = "no_issue_time"
        elif horizon_s is None or horizon_s <= 0:
            reason = "no_horizon"
        elif quantiles:
            if not all(level in quantiles for level in REQUIRED_QUANTILES):
                reason = "required_quantiles_absent"
        elif len(samples) >= 2:
            pass
        elif mean is not None and sigma is not None and sigma > 0:
            pass
        else:
            reason = "no_distribution"

        out.append(ForecastRecord(
            model_id=str(row.get("model_id") or "").strip() or "unnamed",
            account_id=account_id, prop=str(row.get("property") or "margin_balance"),
            issued_at=issued_at, horizon_s=horizon_s, quantiles=quantiles,
            samples=samples, mean=mean, sigma=sigma, unusable=reason, raw=dict(row)))
    return out


def load(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)
