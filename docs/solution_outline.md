# Kaggriculture solution outline

## Objective

Maximize terminal bank over a 720-turn two-player farming economy. Unsold inventory has zero terminal
value, market orders interact simultaneously, premium products can crash to a $1 price floor, and
the shed discards inventory past capacity.

## Evaluation architecture

1. Pin the official simulator and run its tests.
2. Extract public agents without executing arbitrary notebook cells.
3. Play paired games on identical seeds in both seats.
4. Separate development, validation, holdout, adversarial, and sealed promotion seeds.
5. Record win score, cash distribution, lower tail, failures, runtime, source hash, and deterministic
   archive hash.
6. Keep leaderboard ratings as noisy external evidence, never the local tuning objective.

## Strategy tracks

- Finite-horizon cash planning: value actions by realized terminal bank, not static ROI or inventory.
- Market-impact-aware selling: reproduce the official one-unit simultaneous transition and town
  demand before optimizing order timing and size.
- Global worker/task allocation: assign by marginal cash minus travel, deadline, switching, and
  displaced-task cost.
- Robust opponent conditioning: switch away from a strong default only with calibrated evidence.
- Macro search: use MCTS/rollouts only above a deterministic worker scheduler and only when the
  exact simulator/runtime gate supports it.

## Current candidate history

- Initial unnumbered agents established expansion and cow-heavy baselines.
- `final_day_labor` fixed final-day labor and remains the formal local champion.
- Fa_01 added overflow routing and produced a byte-verified private Save & Run, but failed its later
  preregistered sealed direct gate and was not submitted.
- Fa_02 tested a different finite-horizon crop-rotation hypothesis. Both unbounded and capped
  versions failed untouched sealed gates, and a replay-derived early carry drain failed 3-61.
  No Fa_02 Save & Run was created; these remain negative evidence, not a production agent.

## Publication strategy

Public material is useful, commented, reproducible, and weaker than private production work. Titles
front-load Kaggriculture and the concrete search intent without claiming unmeasured scores. Exact Fa
and final production code stays private.
