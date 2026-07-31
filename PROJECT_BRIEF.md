# Kaggriculture — Top-3 campaign

Decision date: 2026-07-31 (Asia/Seoul)

## Objective

Finish in the final top 3. Current public leaderboard is only an early signal; all strategy decisions must be backed by local seeded simulation, opponent diversity, and held-out scenario tests.

## Why this competition

- 167 teams at selection time.
- Current top 3: 1294.6 / 1277.7 / 1253.8. The gap from third to first is 40.8 points (3.25%).
- Five submissions per day and roughly two months remaining.
- The exact environment is open source, so most iteration can happen locally without consuming submissions.
- The game has a finite 720-turn horizon and explicit economics, making deterministic planning, simulation search, opponent modeling, and robust policy optimization practical.

Official links:

- Competition: https://www.kaggle.com/competitions/kaggriculture
- Environment source: https://github.com/Kaggle/kaggle-environments/tree/master/kaggle_environments/envs/kaggriculture
- Strong public baseline/evaluation project: https://github.com/niits/kaggriculture

## Alternatives rejected

| Competition | Evidence | Reason not selected |
|---|---:|---|
| Autonomous Agent Prediction (Beta) | 387 teams; top 3 = 0.830 / 0.829 / 0.828 | Only one submission/day and seven days left. Excellent fit, but too little recovery time for an experimental agent harness. |
| Biohub Cell Tracking | 1,811 teams; third = 0.935 | Specialized 3D/4D microscopy, large data, and a mature field make top 3 materially less likely. |
| Pokémon TCG AI Battle | 6,024 teams; third = 1152.4 | Much larger field and complex evolving card-game meta; current campaign already has 64 submissions without top-tier position. |

## Non-negotiable workflow

The durable user direction and publication order are recorded in `CAMPAIGN_DIRECTIVE.md` and
must be reread after every context reset or handoff.

1. Reproduce the official environment locally and pin its exact version/commit.
2. Establish deterministic baselines across many seeds and all built-in opponents.
3. Build a replay/metrics warehouse: end cash, cash curve, action utilization, crop/animal ROI, market impact, failure counts.
4. Separate policy development from evaluation seeds and opponent sets.
5. Use search/optimization locally; submit only candidates that clear robust promotion gates.
6. Never tune against ladder score alone. Track confidence intervals and worst-case performance.
7. Keep every submitted agent immutable with code hash, local report, and Kaggle result.

## First technical tracks

- Exact economic optimizer for build/plant/harvest/sell schedules.
- Path planning and multi-worker task allocation with action-budget constraints.
- Market-impact-aware order sizing and adversarial opponent response.
- Scenario randomization over map, market parameters, seeds, and opponent archetypes.
- Policy ensemble or opponent-conditioned switching only after stable single-policy baselines.

## Evidence captured at selection

- Kaggle API leaderboard top 10: 1294.6, 1277.7, 1253.8, 1239.3, 1204.8, 1171.0, 1145.6, 1145.4, 1142.5, 1130.3.
- Kaggle API submission allowance: 5/day.
- GitHub search found the official environment plus public baseline, validation, and evaluation repositories.
- The pinned public benchmark already contains seven runnable agents across 210 competition-mode games. Its `many_hands` and built-in `pro_tier` agents each recorded a 0.667 win rate, while policy archetypes differ sharply in reward and net-worth proxy. This gives us an immediate opponent suite and clear optimization headroom.

## Pinned references

- `references/kaggle-environments`: commit `4f6e2763e2232605aacbade443715a9e2c9ef401` (sparse checkout of Kaggriculture environment and tests).
- `references/niits-kaggriculture`: commit `3c89b816e634653fcde40918edae5f65ff356f84`.
- The account has accepted the competition rules. `kaggle competitions files kaggriculture`
  succeeds, and the official `AGENTS.md`/`README.md` are downloaded and hash-pinned under
  `competition_data/official/`. The old 403 blocker is closed.

## Mandatory lessons carried forward from PS-S6E7

The previous campaign reached 0.95306 but exposed serious process failures. These are operational constraints, not optional advice:

- Do not claim broad research or deep verification when only a narrow check was performed. Save a source manifest and raw evidence.
- Do not confuse a mathematically feasible outcome with a forecast or guarantee.
- Do not spend submissions on duplicate artifacts, weakly identified probes, or changes whose exact output diff was not checked.
- Equal rounded leaderboard scores do not prove that changed cases are neutral or correctly identified.
- A long submission history is not a substitute for held-out validation, causal reasoning, or an immutable experiment ledger.
- Preserve the strongest champion. Every challenger must have one explicit hypothesis and a clean comparison.
- Before upload, verify code hash, output hash, schema, runtime, changed behavior, and whether an identical artifact was already uploaded.
- External actions require explicit user authority. The user submits unless they clearly delegate submission.
- Prefer API/CLI. Browser control is a last resort and requires permission.
- If the evidence is insufficient, report that before consuming a submission rather than improvising confidence.

## New-task startup checklist

1. Read `AGENTS.md` and this brief completely.
2. Verify the already accepted rules and re-check the hashes of the downloaded official files.
3. Reproduce the pinned environment and public evaluation project from clean commands.
4. Create the experiment ledger, immutable champion directory, seed split, opponent split, and promotion report template before optimization.
5. Establish deterministic baseline distributions and confidence intervals.
6. Only then design challengers and local search tracks.
