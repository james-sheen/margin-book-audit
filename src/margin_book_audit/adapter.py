"""Records and predictions to the engine's contract, and nothing more.

THE ADAPTER IS A TRANSLATOR, not a second opinion. It does not decide whether a
forecast is good, whether an account is in trouble, or what a probability means
-- every one of those is either the engine's judgement or the desk's. What it
does is put a record into the shape the engine's `ingest_forecasts` accepts and
hand back what it could not translate, with the reason.

ONE MALFORMED RECORD MUST NOT COST ANOTHER PRODUCER'S DATA, so nothing here
raises on a caller's row: the untranslatable are returned beside the translated.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .forecaster import MODEL_ID, Prediction
from .records import ForecastRecord


def from_records(records: Sequence[ForecastRecord]
                 ) -> Tuple[List[Dict[str, Any]], List[Tuple[str, str]]]:
    """`(contract_rows, [(model_id, reason), ...])` for a desk's own feed."""
    rows: List[Dict[str, Any]] = []
    refused: List[Tuple[str, str]] = []
    for record in records:
        if not record.usable:
            refused.append((record.model_id, record.unusable or "unstated"))
            continue
        row: Dict[str, Any] = {
            "model_id": record.model_id,
            "entity_id": record.account_id,
            "property": record.prop,
            "issued_at": record.issued_at.isoformat() if record.issued_at else None,
            "horizon_s": record.horizon_s,
        }
        if record.quantiles:
            row["quantiles"] = dict(record.quantiles)
        elif record.samples:
            row["samples"] = list(record.samples)
        else:
            row["mean"], row["sigma"] = record.mean, record.sigma
        rows.append(row)
    return rows, refused


def from_predictions(predictions: Sequence[Prediction], *, issued_at: str,
                     horizon_s: float, prop: str = "margin_balance",
                     model_id: str = MODEL_ID) -> List[Dict[str, Any]]:
    """This package's own forecaster, in the same shape as anybody else's.

    Deliberately identical: the reference model gets no privileged path into the
    engine, so a comparison between it and a desk's model is a comparison of
    forecasts and not of plumbing.
    """
    return [{
        "model_id": model_id,
        "entity_id": prediction.account_id,
        "property": prop,
        "issued_at": issued_at,
        "horizon_s": horizon_s,
        "quantiles": dict(prediction.quantiles),
        "assumptions": ["ewma_level", "empirical_residual_quantiles",
                        f"residuals_n={prediction.residuals_n}"],
    } for prediction in predictions]
