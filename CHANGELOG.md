# Changelog

Notable changes to `margin-book-audit`.

## [Unreleased]

Nothing yet.

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
