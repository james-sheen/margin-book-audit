# Changelog

Notable changes to `margin-book-audit`.

## [Unreleased]

**Nothing this package filed had ever been graded.** Every forecast a run files
matures an hour after the instant it audits, and the engine's default ledger
dies with the process -- measured on the shipped corpus, 22 recorded, 22
pending, 0 graded.

### Added

- **`--ledger PATH`** keeps what a run files in a SQLite ledger, so the next
  audit of the same book grades every record whose hour has passed, against
  that later register's own history. The text report prints one CRPS line per
  graded model, ordered by name, with its count and whose it is.
- **`--learner`** files the engine's reference producer, a damped-trend
  smoother, beside the desk's forecasts as a second yardstick: fed only for the
  pairs the desk covered, filed under its own `source`, scored and never judged.

### Fixed

- **Two sentences described an engine this package never ran on.** The README
  said no run could score anything because the engine had no durable ledger; it
  has had one as a supported name since 0.2.6. The README and `report.py` said
  the engine files one random walk per forecast; it files one per pair and
  instant, and answers the rest `already_filed` -- measured on 0.2.4 and 0.2.9.

### Changed

- **The engine floor is 0.2.7**, the first release carrying the learner.
  Measured: 5 tests fail against 0.2.6, all of them the learner's.

## [0.1.3] — 2026-09-18

**A fourth review of the engine, with one finding on this side.** It was
confirmed and the review's arithmetic was exactly right: the filed interval was
half the width its own record claimed.

### Fixed

- **The reference forecaster's stated horizon scaling was never applied.**
  `predict` scales its residual quantiles by `sqrt(steps_ahead)` and the record
  it files says so -- `independent_increments_sqrt_horizon_scaling` is in its
  `assumptions` list. The CLI called `predict(account_id, history)` and filed
  the result at `horizon_s=3600`, so `steps_ahead` stayed at its default of 1
  and the quantiles were ONE-STEP residuals under a one-hour label. Measured on
  the shipped corpus, whose `history_interval_s` is 900: an hour is four steps,
  and every filed interval came out at exactly half the width the assumption
  implies -- ratio 2.0000 across every account.

  The existing test compared `predict(steps_ahead=1)` against
  `steps_ahead=9` directly and passed throughout, because the defect was never
  in the scaling. Nothing passed the argument. The new test goes through
  `cli.main` and asserts the filed width against the declared interval.

  **A register with no `history_interval_s` now files no reference at all**,
  rather than one scaled by a guess. This package already refuses to spread
  undated readings across an invented spacing; inventing the SCALE of the
  yardstick is the same invention one step along.

### Changed

- **Every engine call now goes through `arbiter_engine.api`.** This package
  imported `arbiter_engine.forecast` and `arbiter_engine.clock` -- deep paths
  the engine says may move without a major version -- while declaring a `<0.2`
  ceiling that reads as a promise about all of 0.1. Nothing was broken; the
  guarantee was. The engine re-exported the three names onto `api` in 0.1.18,
  which is what the floor now buys, and a new test fails on any import reaching
  past `arbiter_engine.__all__`.

- **`no_tolerance` is no longer floored.** The engine withdrew the reason in
  0.1.18 -- it had no producer -- and this package's own rule caught the stale
  row immediately: a floor for a reason that cannot happen reads as coverage
  and is not.

- **Floor `arbiter-engine>=0.1.18,<0.2`**, measured: this suite against 0.1.17
  fails 47 tests. The comment in `pyproject.toml` now also says HOW the figure
  was taken, because `battery/probe_pin.py` -- the oracle -- cannot produce it
  while the floor names a version the index does not carry.

## [0.1.2] — 2026-09-18

**A second review, and the one finding it filed as untested was real.** It was
also worse than filed: the review predicted a `forecast_breach` at `high`, and
what the run produced was that plus a `forecast_below_critical_threshold` at
severity **critical**.

### Fixed

- **The reference forecaster could fail the audit it is a control inside.**
  `--self-forecast` files this package's own EWMA so the desk's model can be
  compared against something. The engine could not tell whose those records
  were — an outside forecast carries no source — so the eight shadow axioms ran
  over the reference's own predictions and reported the results against the
  book. Measured on a clean three-account book, every pair covered and every
  balance above its requirement: without the flag `exit 0` and `findings 0`;
  with it, and nothing else changed, `exit 1` and `findings 6`. Three of those
  were `critical`, naming accounts whose real balance was above the line.

  **There is no fix on this side of the boundary**, which is why the floor
  moves: the findings carry no model id, so nothing here can attribute them.
  `arbiter-engine` 0.1.17 takes a `source=` on `ingest_forecasts`, and a record
  filed with one is kept out of the producer counts and out of the shadow pass.
  The reference is still filed and still raced against a random walk, so it
  remains measurable — silencing it by not feeding it would have fixed the exit
  code and destroyed the feature.

- **The reference was reported as one of the desk's producers.** It sat in
  `forecasters` keyed by model id with nothing marking it, beside `garch_v3`.
  Those are producer figures — how old the last submission is, how many arrived
  against what was owed — and none of those questions have an answer for a model
  this package runs itself at the instant of the audit. It is described in
  `reference` now, which carries `model_id`, and it is no longer declared in the
  generated model's `models:` allow-list, because it is not a producer.

- **`reference.yardsticks` was described as one per forecast.** It is one per
  forecast THE ENGINE WAS SENT, and with `--self-forecast` the reference's own
  rows are forecasts too, so the number exceeds the pair count by design.

### Documentation

- **Calibration is structurally unreachable from this CLI, and the README now
  says so rather than implying a longer horizon would help.** Every run builds a
  fresh engine session, the engine's ledger is in-memory, and a grade needs the
  record still to be there when its horizon passes — so the process would have
  to outlive the horizon, and this one exits. Feeding already-matured forecasts
  does not work around it: the forecasts leg declines them `stale_forecast`,
  because it asks whether the producer is current and cannot tell a late
  forecast from one brought back to be scored.

### Changed

- Engine floor `>=0.1.16` → `>=0.1.17`, measured: this suite fails 13 tests
  against 0.1.16. **The floor names an unpublished version until the engine
  ships**, which is the ordering it asserts rather than an oversight.

## [0.1.1] — 2026-09-17

**Found by running the package against a review of it that ran nothing.** Two of
the five below were filed as low-severity wording issues and turned out to
change the exit code.

### Fixed

- **The reference forecaster was answering the desk's question.**
  `--self-forecast` appended this package's own predictions to the feed BEFORE
  stage one classified it. Measured on the corpus: `acct_05`, whose producer
  sent a record that could not be scored, and `acct_06`, whose producer sent
  nothing, both came out `scorable`; coverage read 6 of 6; the run exited
  CLEAN. The first paragraph of the README says the denominator never comes
  from the feed, and the feed was being topped up from inside. The reference is
  now fed beside the desk's forecasts and only for pairs the desk already
  covered, so it cannot close a hole. The off-by-k slice that built it is gone
  with the slice.

- **A realised breach was invisible.** The exit code was composed from the
  `forecasts` leg alone, so the model's own BOUNDEDNESS declaration — the
  reason this package generates a model at all — fired at severity `critical`
  and went nowhere. An account 50,000 below its contracted requirement reported
  `findings 0`, and with coverage complete would have exited CLEAN. The
  envelope's own findings and declines, and the shadow leg's declines, are now
  read. Half the floor table was unreachable before this and is not now.

- **History was stamped at the wall clock.** `add_observations` with bare
  readings stamps them ending at NOW, so under `--as-of 09:35` all forty of the
  corpus's readings landed after 15:00 — hours after the instant being
  evaluated — and every one of them came back inside a one-hour window. A
  register now says when its readings were taken (`history_interval_s` beside
  `as_of`) or the series is not fed and the report says which key was missing.
  Spacing them by a guess would put an assumption of ours inside a desk's own
  history.

- **The generated model's read-back could not fire.** It looked for
  `dropped_declarations` under `model_describe`'s `model` block, which never
  carried the key, so the gate returned an empty list and passed for every
  model — including one with a misspelled axiom and one with an unreadable
  `{from_property:}` mapping. The key is a required proof key now, and the
  engine mounts it.

- **A record that stated its distribution twice was silently scored on one
  half**, and a record that named no producer was filed under `unnamed` — which
  then appeared in the generated `models:` list as though a model were called
  that, and pooled every anonymous record into one calibration stratum. Both
  are refused with a reason.

### Added

- **The forecaster is created and measured.** The generated model has declared a
  `ForecastModel` type with six indicators since the first commit and nothing
  ever created one, so four axiom declarations sat over a type with no
  instances. `feed_model_figures` now writes the figures and the report carries
  them per producer.

- **`--expected-from`**, naming a producer that owes a forecast for every
  account. Nothing is inferred: wiring the forecaster up found that the engine
  was deriving the obligation from `models:`, which is an allow-list, and
  charging both permitted producers with all six accounts — two
  `conservation_violation` findings at severity `high`, against a debt nobody
  had declared. Fixed in the engine; this is how a desk states the real one.

- **`project` is run**, so the `dynamics:` block the model has always declared
  is finally read. Its findings are reported and deliberately do NOT floor the
  exit code: a probability about an hour that has not happened must not page a
  desk the way a balance does.

- **A `calibration` block, nulls included**, and a count of the random walks the
  engine filed beside the forecasts it was sent. An absent calibration block and
  one full of nulls read the same to a human and mean opposite things to a gate.

### Changed

- **The engine floor is `>=0.1.16`**, and `battery/probe_pin.py --sweep`
  re-derives it. 0.1.15 does not mount the shadow leg, does not carry
  `dropped_declarations` on `model_describe`, and reads a `{from_property:}`
  bound in `project` as no bound at all.

## [0.1.0] — 2026-09-17

First cut. Not released.

### Added

- **Stage one, which needs no engine.** A book register and a forecast feed are
  paired into `scorable` / `unscorable` / `absent`, never a boolean. The
  denominator is the register.
- **A domain model and its exclusion manifest, as a pair**, with one `Account`
  type for the whole book — the requirement each account is held to is read off
  the entity through `{from_property:}`.
- **A reference forecaster**, an exponentially-weighted level with empirical
  residual quantiles. It declines rather than emitting an interval too few
  points can support.
- **A floor table covering the engine's published decline vocabulary exactly**,
  asserted in both directions so a reason the engine adds cannot fall through
  to *could not complete*.
- **`--as-of`**, so a corpus run is reproducible rather than depending on the
  hour it was started.
