"""Which outcome floors at which exit code, and why each number was chosen.

THE SHARED CORE DELIBERATELY DOES NOT CARRY THIS. `presence_audit.exit_contract`
owns the three codes and the compose rule -- maximum over the legs, so the worst
leg wins -- and stops there, because which finding or decline deserves which
code is a domain judgement. It depends on what the axiom means here, how often
it fires on a healthy book, and what a false alarm costs a desk. A default made
once by whoever wrote the first vertical would be inherited by everyone after
them without anybody deciding.

So this table is ours, every row has a reason, and the reasons are about margin
books rather than about software.
"""

from __future__ import annotations

from typing import Dict, Iterable, Mapping, Tuple

try:  # pragma: no cover - exercised by the dependency-free test
    from presence_audit.exit_contract import CLEAN, FINDINGS, INCOMPLETE, compose
except ImportError:  # pragma: no cover
    CLEAN, FINDINGS, INCOMPLETE = 0, 1, 2

    def compose(*codes: int) -> int:
        return max((int(c) for c in codes), default=CLEAN)


#: A decline is *the engine could not judge this*, and a floor answers whether a
#: desk should care. THE KEYS ARE NOT INVENTED: the engine publishes
#: `subenvelope.VOCABULARIES` as a CLOSED set per discipline, and
#: `tests/test_every_decline_has_a_floor.py` asserts this table covers the
#: `forecasts` and `shadow` members exactly. The first version of this file was
#: written from imagination and missed three of the six reasons the forecasts
#: leg actually emits -- every one of them fell through to INCOMPLETE, so the
#: corpus run reported a broken audit for a book that was merely incomplete.
DECLINE_FLOORS: Dict[str, int] = {
    # ---- expected on a healthy book -------------------------------------
    # Not enough history yet, or nothing to compare against. A desk starting
    # this up on Monday should not see a red gate all week.
    "insufficient_samples": CLEAN,
    "no_current_value": CLEAN,
    "precondition_unmet": CLEAN,
    "not_applicable": CLEAN,
    # EVERY FORECAST PASSES THROUGH THIS STATE. `ungradeable` is a record whose
    # outcome has not been observed yet, which on an hourly horizon is true of
    # everything issued in the last hour. Flooring it higher would make a
    # correct run red on every cycle. The COUNT is still reported, because a
    # growing one means outcomes are not being recorded at all.
    "ungradeable": CLEAN,

    # ---- a declaration nobody completed ---------------------------------
    # Cheap to fix, and it means a check the desk believes is running is not.
    "no_threshold": FINDINGS,
    "missing_property": FINDINGS,
    "missing_role": FINDINGS,
    "no_rule_for_role": FINDINGS,
    "missing_config": FINDINGS,
    "missing_entity_type": FINDINGS,
    "wrong_indicator_type": FINDINGS,
    "no_report_probability": FINDINGS,
    "tail_not_declared": FINDINGS,
    # `no_tolerance` was floored here until the engine withdrew it in 0.1.18.
    # It named a point prediction with no declared tolerance, and the engine's
    # forecast contract takes three shapes that all become quantiles -- a mean
    # without a sigma is refused before any decline exists. So the member had
    # no producer, and the rule below caught the floor the moment it went:
    # a floor for a reason that cannot happen reads as coverage and is not.
    # It comes back if a point-forecast shape ever lands.

    # ---- the coverage gap this package exists to report ------------------
    # The register said a forecast was expected here and none arrived. This is
    # the finding, not a technicality.
    "forecast_missing": FINDINGS,

    # ---- the control working, and the engine saying so -------------------
    # `not_a_producers_submission` arrives with engine 0.2 and it fires on THIS
    # package's own doing. `--self-forecast` files the reference forecaster's
    # rows with a `source=` for exactly one reason: to keep the eight shadow
    # axioms off them, because a reference that can fail the audit it is a
    # control inside is not a control. 0.2 names that set-aside instead of
    # performing it silently, which is an improvement and is not a gap in the
    # book -- so CLEAN. The count still rides in the report, and a run where it
    # is zero with `--self-forecast` on would mean the set-aside stopped
    # happening, which is the failure this floor must not hide.

    "not_a_producers_submission": CLEAN,

    # ---- a producer problem ----------------------------------------------
    # The feed and the model file disagree about what is being sent.
    "model_unknown": FINDINGS,
    "stale_forecast": FINDINGS,

    # ---- PROVISIONAL, and said so rather than quietly picked -------------
    # `partially_checked` means some subjects were judged and some were not.
    # Whether that is worth a desk's morning depends on WHICH subjects, and
    # this package has not yet run against a book where it fires. FINDINGS is
    # the middle code and the safe direction: it does not claim the run broke,
    # and it does not claim the book is clean. Settle it by measuring, on a
    # real book, how often it fires and on what.
    "partially_checked": FINDINGS,

    # ---- the audit itself did not complete -------------------------------
    # Never conflated with a finding: a gate reporting a broken run as a
    # healthy book is worse than one that fails.
    "checker_error": INCOMPLETE,
    "internal_error": INCOMPLETE,
    "undefined_for_values": INCOMPLETE,
}

#: Findings, by the prefix of their problem type. A forecast breach and a
#: realised breach both floor at FINDINGS: the desk acts on either, and ranking
#: the prediction lower would be this package deciding that a forecast is worth
#: less than an observation -- which is the desk's call and depends on the model.
FINDING_FLOORS: Tuple[Tuple[str, int], ...] = (
    ("forecast_breach:", FINDINGS),
    ("below_critical_threshold:", FINDINGS),
    ("above_critical_threshold:", FINDINGS),
    ("conservation_violation:", FINDINGS),
    ("homeostasis_deviation:", FINDINGS),
)

DEFAULT_FINDING_FLOOR = FINDINGS
DEFAULT_DECLINE_FLOOR = INCOMPLETE

#: Indicators whose absence is a COLD START, not an incomplete declaration.
#:
#: FOUND BY RUNNING, and it moved a real number. `missing_property` floors at
#: FINDINGS because a bound whose source never arrived is a check the desk
#: believes is running and is not -- that reasoning is right and stays. But the
#: forecaster's calibration figures are absent for a different reason: the
#: engine omits `coverage_90` and `pinball_loss` until something has MATURED and
#: been scored, deliberately, because a coverage of 0.0 for a model nobody has
#: graded reads as catastrophic miscalibration. On an hourly horizon that is
#: true of every forecast issued in the last hour, so a desk running this for
#: the first time would see a red gate for an hour and learn to ignore it.
#:
#: The same argument the `ungradeable` row already makes, one indicator further
#: in. Named indicators rather than a blanket softening of the reason, because
#: the reason is right everywhere else.
WARMING_UP_INDICATORS: Tuple[str, ...] = ("coverage_90", "pinball_loss",
                                          "graded_n")


def floor_for_decline(reason: str, indicator: str = "") -> int:
    """The exit code a decline floors at, and why `indicator` is a parameter.

    A reason alone was not enough to answer with once the forecaster was
    actually fed: `missing_property` on a margin requirement and
    `missing_property` on a coverage rate nobody has scored yet are the same
    word for a declaration gap and a cold start. The second is expected on
    every first run and must not floor a gate.
    """
    if (reason == "missing_property"
            and str(indicator) in WARMING_UP_INDICATORS):
        return CLEAN
    return DECLINE_FLOORS.get(reason, DEFAULT_DECLINE_FLOOR)


def floor_for_finding(problem_type: str) -> int:
    for prefix, code in FINDING_FLOORS:
        if problem_type.startswith(prefix):
            return code
    return DEFAULT_FINDING_FLOOR
