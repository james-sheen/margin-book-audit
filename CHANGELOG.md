# Changelog

Notable changes to `margin-book-audit`.

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
