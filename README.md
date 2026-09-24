# margin-book-audit

**Of the forecasts a margin book expected, which arrived, which can be scored,
and whether anything is keeping score.**

A bridge from a desk's forecast feed to
[`arbiter-engine`](https://github.com/james-sheen/arbiter), built to the method
in that repository's `BRIDGES.md`.

> **Not investment advice, and not a risk system.** This reads two files a desk
> already produces and reports what an engine could and could not check. Every
> number in `corpus/` is synthetic.

## What it answers

*371 forecasts received* is not a measurement until something says out of how
many. This package gets the denominator from the **book register** — what the
desk says should be forecast — and never from the feed, because counting what
arrived and calling that the total is the one shape the method exists to refuse.

Every expected pair lands in exactly one of three states, and the middle one is
the point:

| state | meaning | who fixes it |
|---|---|---|
| `scorable` | a record arrived and can be scored | nobody |
| `unscorable` | a record arrived and cannot be used | the producer |
| `absent` | no record arrived | whoever owns coverage |

The engine reports both gaps as `forecast_missing`, because from where it sits
they are the same absence. Telling them apart is this side's job, and it is the
difference between a producer bug and a hole in coverage.

## The division

The engine owns the axioms, the closed vocabulary of reasons it refuses to
judge, and the schema results arrive in. **The domain nouns are here** — what an
account is, what a margin requirement means, how a balance moves, and what a
desk does about a breach.

A forecasting model is domain knowledge by that division, so `forecaster.py` is
in this package and nothing like it is in the engine. The reference model is an
exponentially-weighted level with the spread taken from its own residuals. **It
is not a good forecaster**, and that claim has to be earned per book — against
the random walk the engine files beside every prediction.

`--self-forecast` runs it **beside** the desk's forecasts, on the pairs the desk
already covered. It never fills one in. It used to: the predictions were added
to the feed before the coverage question was asked, so an account whose producer
sent nothing came out covered and the audit exited clean. A reference that
answers for the producer it is meant to be measured against is not a control.

**It needs `history_interval_s` and files nothing without it.** The forecast is
issued at a one-hour horizon, and how many steps an hour is depends on how far
apart the readings are — on a quarter-hourly book it is four, and the spread is
scaled by the square root of that. A register that does not say its spacing
cannot say its scaling, and a yardstick whose width is invented is worse than no
yardstick because the comparison still prints. This is the same refusal that
keeps undated readings out of the history: the package will not put its own
assumption about sampling into somebody else's book.

## Use

```bash
pip install 'margin-book-audit[engine]'
margin-book-audit register.json feed.json
```

Stage one needs no engine at all:

```bash
margin-book-audit register.json feed.json --coverage-only
```

`--as-of <ISO8601>` evaluates at a fixed instant. Staleness and lookback are
both measured from *now*, so a fixture built on the wall clock gives a different
answer every hour; the corpus runs pass it and live runs do not.

`--expected-from <model_id>` names a producer that owes a forecast for every
account. Nothing is inferred from the feed: having sent a forecast is not the
same as owing one, and the engine derived the obligation from its allow-list
until this package wired the forecaster up and watched two producers get charged
with a book neither had been asked for.

## What a register has to say

```json
{ "as_of": "2026-09-17T09:30:00Z", "history_interval_s": 900, "accounts": [...] }
```

`history` on an account is a list of numbers, and **a list of numbers is not a
series**. Without `as_of` and `history_interval_s` there is no way to place the
readings in time, so they are not fed and the report says which key was missing.
That is not fussiness: fed as bare readings they are stamped ending at the wall
clock, and a run evaluated at 09:35 was handed forty readings taken after 15:00
and treated them as the hour before.

Exit codes follow the shared contract: `0` clean, `1` something needs attention,
`2` the audit did not complete. Which decline floors at which code is a domain
judgement, so this repository keeps its own table in `floors.py` with a reason
on every row — and a test asserts the table covers the engine's published
vocabulary exactly, in both directions.

## What it cannot tell you yet

**Whether anything beat the random walk.** A forecast is scored when its horizon
passes and the outcome is observed; on an hourly horizon a single run scores
nothing, and every rate in the `calibration` block comes back null.

**And it is not only this horizon: no run of this command can score anything.**
That is worth stating flatly, because *a single run scores nothing* reads like a
thing a longer horizon or a patient operator fixes, and it is not. Every run
builds a fresh engine session, the engine's prediction ledger is in-memory, and a
grade needs the record still to be in the ledger when its horizon passes — so the
process would have to outlive the horizon, and this one exits. Feeding forecasts
that already matured does not work around it: the engine's forecasts leg declines
them `stale_forecast` against the generated model's `max_age`, because that leg
asks whether the producer is current and cannot tell a late forecast from one
brought back to be scored. So `calibration` is structurally null here, and the
block is still printed — an absent block and a null one read the same to a human
and mean opposite things to a gate. Scoring needs a resident process or a durable
ledger in the engine; neither exists today. What the run
*can* say is whether the race was set up — `reference.yardsticks` counts the
random walks the engine filed, **one per forecast it was sent**, on the same
series and the same horizon. Not one per account: with `--self-forecast` the
reference's own rows are forecasts too and each gets its own, so the number
exceeds the pair count by design. `reference.model_id` names this package's
entrant so it can be told apart from the desk's producers in `forecasters`. Reported with its nulls rather than omitted, because a missing
calibration block and one full of nulls read the same to a human and mean
opposite things to a gate.

## Evidence

The ladder is named, because *we tested it* means nothing until it is:

1. **synthetic corpus** — `corpus/`, deterministic, reaches all three states.
2. **mutated copies** — each guard is broken and the suite must go red.
3. **a live-but-safe feed** — not yet climbed.
4. **first contact with a real book** — not yet climbed.

Rungs 3 and 4 are honestly unclimbed. Nothing here has seen a real margin book.

## The pin

The engine extra is `>=0.2.4,<0.3`, and every floor this package has had was
measured rather than preferred. The binding one is now a **decline**:
`not_a_producers_submission` arrives with engine 0.2 and fires on this
package's own doing — `--self-forecast` files the reference forecaster's rows
with a `source=` precisely to keep the eight shadow axioms off them. This
package fails closed on a decline it has no floor for, so on 0.2.4 seven tests
reported a broken audit for a book that was merely being controlled. The floor
is CLEAN and it is version-coupled both ways: with the row present the suite is
red on 0.1.18, measured, because a floor for a reason the engine cannot emit
reads as coverage and is not. The pin and the floor are one change.

The previous floor was a **surface**: `api.ingest_forecasts`,
`api.feed_model_figures` and `api.as_of` only exist on the supported surface
from 0.1.18, and below it this package had to reach into
`arbiter_engine.forecast` and `arbiter_engine.clock`, which the engine says may
move without a major version. Measured then: this suite against 0.1.17 failed
47 tests. That reason still holds and is no longer the binding one.

*This paragraph said `>=0.1.16` while `pyproject.toml` said `0.1.17` — the
number is stated in three places and the test that exists to stop it drifting
compared two of them. It compares all three now.*

Earlier floors, each still true and none of them binding any more:

- **0.1.17** — `ingest_forecasts` takes no `source=`, so this package's own
  reference forecaster could not be told apart from a desk's producer, was
  judged by the shadow axioms, and took a clean book from `exit 0` to `exit 1`
  with three `critical` findings;
- **0.1.16** — `check` does not mount the `shadow` leg, so every shadow row in
  `floors.py` is unreachable and a forecast the engine refused to judge reports
  as clean; `model_describe` does not carry `dropped_declarations`, so the
  generated model's read-back finds nothing and passes for a model the loader
  rejected; and `project` reads a `{from_property:}` bound as no bound at all,
  so the floor every account is held to cannot be projected against.

`battery/probe_pin.py --sweep` re-derives the floor on any pin change; it is
measured, not read. It installs the pinned release and runs this suite — pass —
then installs the highest release below the floor and runs the same suite —
fail. The control is what makes the claim worth anything: the floor is here
because the release below it is genuinely broken for this package, not because
a design note said so.

Apache-2.0.
