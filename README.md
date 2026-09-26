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

# score the desk against both yardsticks, an audit at a time
margin-book-audit register.json feed.json --self-forecast --learner --ledger book.sqlite
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

## Scoring the desk against the yardsticks

**One run scores nothing.** A forecast is scored when its horizon passes and the
outcome is observed, and every forecast a run files -- the desk's, the
reference's, the engine's own -- matures an hour after the instant it audits.
Measured on the shipped corpus at its own `as_of`, with `--self-forecast`: 22
recorded, 22 pending, 0 graded, every rate null. The `calibration` block is printed anyway, because an
absent block and a null one read the same to a human and mean opposite things to
a gate.

**`--ledger PATH` keeps them for the next audit.** The engine's prediction ledger
lives in memory unless it is handed a file, so without this flag nothing a run
files outlives the process. With it, the next audit of the same book -- a later
register, run against the same file -- grades every record whose hour has
passed, and the text report prints one line per graded model:

```
  graded              N of M filed (K pending)
  crps <score>        <model id> (n=<count>, <whose it is>)
```

The reading a record is graded against comes from that later register's own
`history`, so the register has to reach back to the hour being graded; a
forecast whose outcome no later register covers comes back `ungradeable` and is
counted as that, never scored. The lines are ordered by name. This package does
not rank the models, for the reason the engine does not: a lower CRPS is a closer
forecast of what happened, and the count beside it says how much happened.

*This section said until 2026-09-26 that no run of this command could score
anything, because scoring needed a durable ledger in the engine and none existed.
The engine has carried one as a supported name since 0.2.6, and nothing here
used it.*

**`--learner` adds a second yardstick.** A random walk is the right floor and a
poor opponent: anything that notices a balance is going somewhere beats one, so a
desk model scored only against it has shown almost nothing. The learner is the
engine's own reference producer, a damped-trend smoother fitted to each account's
history, and it is held to the reference's rules -- fed only for the pairs the
desk already covered, and filed under its own `source`, so the engine scores it
and never judges the book by it. It lives at a module path the engine does not
promise across a minor release; if that path moves, the report says the learner
filed nothing and why, and the audit is unaffected.

**The random walk is one per pair, not one per forecast.** `reference.yardsticks`
counts the random walks the engine filed: one beside the first forecast it
receives for a pair at an instant, and `already_filed` for every later forecast
of the same pair, so the reference and the learner are raced against the walk the
desk's forecast already got. This paragraph said the opposite until 2026-09-26,
and it was not true of any engine this package has admitted -- measured on 0.2.4
and on 0.2.9, the reference's rows come back `already_filed`. `reference.model_id`
and `learner.model_id` name this package's two entrants, so they can be told
apart from the desk's producers in `forecasters` and `calibration`.

## Evidence

The ladder is named, because *we tested it* means nothing until it is:

1. **synthetic corpus** — `corpus/`, deterministic, reaches all three states.
2. **mutated copies** — each guard is broken and the suite must go red.
3. **a live-but-safe feed** — not yet climbed.
4. **first contact with a real book** — not yet climbed.

Rungs 3 and 4 are honestly unclimbed. Nothing here has seen a real margin book.

## The pin

The engine extra is `>=0.2.7,<0.3`, and every floor this package has had was
measured rather than preferred. The binding one is now **the learner**:
`--learner` files the engine's reference producer, which first shipped in
0.2.7. Measured against 0.2.6, the release below: 5 tests fail, every one of
them a test of the learner, while the durable-ledger half of the same change
passes there. Not 0.2.9: that release fixed grading through a durable
*observation* store, and this package keeps only the ledger durable -- each
audit's readings come from its own register, and the same two-audit bench
grades identically on 0.2.7 and 0.2.9.

Before that the binding floor was 0.2.4, and it was a **decline**:
`not_a_producers_submission` arrives with engine 0.2 and fires on this
package's own doing — `--self-forecast` files the reference forecaster's rows
with a `source=` precisely to keep the eight shadow axioms off them. This
package fails closed on a decline it has no floor for, so on 0.2.4 seven tests
reported a broken audit for a book that was merely being controlled. The floor
is CLEAN and it is version-coupled both ways: with the row present the suite is
red on 0.1.18, measured, because a floor for a reason the engine cannot emit
reads as coverage and is not. The pin and the floor are one change.

Before that it was a **surface**: `api.ingest_forecasts`,
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
