# Assumption register

## Source-backed facts

- Final bank determines an episode win; coin margin does not change the ladder update.
- Only the latest two submissions stay active and enter final evaluation.
- The simulator is seeded, but the seed is hidden from agents.
- Labor is Fibonacci-priced per day, land is progressively priced, and market inventory is
  shared between players.

## Measured facts

- Local runtime resolves Python 3.12.13 and `kaggle-environments==1.32.2`.
- Project tests pass 7/7 and the official simulator suite passes 67/67 against the installed
  package. Public baseline reproduction beyond the smoke pair is still pending.
- The public replay snapshot is Apache-2.0 and locally hash-pinned.
- Seat swapping is not outcome invariant in the official engine. Harvest Pulse versus starter
  at seed 0 reproducibly scored 46,540 from seat 0 and 44,350 from seat 1.

## Active hypotheses

1. Fast expansion wins only when land purchase is coupled to enough same-day labor and
   seed/feed liquidity; land alone creates idle capital.
2. High-crew task allocation is a larger early edge than fine-grained crop selection.
3. Premium-product batching must be opponent-aware because synchronized dumping collapses
   price and may reverse a nominal ROI advantage.
4. Two deliberately different policies (crop compounder and animal/crop hybrid) will cover
   non-transitive opponent matchups better than two nearby parameter variants.
5. The top-ladder opening is causally strong, but only its public actions—not its hidden
   source or decision rules—were available. Our reconstruction can still miss adaptations.

## Unresolved

- Exact Kaggle agent CPU/RAM/disk limits beyond `actTimeout=1`.
- How representative the current replay crawl is of the final field.
- Whether the current top three share one strategy or exploit different matchups.
- Numeric promotion thresholds; these remain unset until baseline variance is measured.
