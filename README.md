# margin-book-audit

**Of the forecasts a margin book expected, which arrived, which can be scored,
and which beat a random walk.**

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

Exit codes follow the shared contract: `0` clean, `1` something needs attention,
`2` the audit did not complete. Which decline floors at which code is a domain
judgement, so this repository keeps its own table in `floors.py` with a reason
on every row — and a test asserts the table covers the engine's published
vocabulary exactly, in both directions.

## Evidence

The ladder is named, because *we tested it* means nothing until it is:

1. **synthetic corpus** — `corpus/`, deterministic, reaches all three states.
2. **mutated copies** — each guard is broken and the suite must go red.
3. **a live-but-safe feed** — not yet climbed.
4. **first contact with a real book** — not yet climbed.

Rungs 3 and 4 are honestly unclimbed. Nothing here has seen a real margin book.

## The pin

The engine extra is `>=0.1.15,<0.2`, and the floor is a crash rather than a
preference: this package declares `loss_margin: 0` on the forecaster's
expected-against-issued balance, and on every earlier release CONSERVATION
divided by that zero and reported a model skipping two thirds of its subjects as
a broken run. `battery/probe_pin.py --sweep` re-derives the floor on any pin
change; it is measured, not read.

**Measured 2026-09-17, not reasoned about.** The sweep installs 0.1.15 and runs
this suite against it — pass. It then installs 0.1.14, the highest release below
the floor, and runs the same suite — fail. The control is what makes the claim
worth anything: the floor is here because the release below it is genuinely
broken for this package, not because a design note said so.

Apache-2.0.
