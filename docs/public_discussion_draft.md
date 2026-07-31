# Discussion draft: Reproducible evaluation checklist

Proposed title: **[Guide] A Reproducible Evaluation Checklist for Kaggriculture Agents**

Early ladder ratings are useful, but they are noisy: the opponent pool is still changing and a
single result can hide seat or scenario effects. Here is the checklist I use before trusting a
change.

## 1. Pair every seed in both seats

Run the same two agents twice per seed and swap player 0/player 1. Keep the paired score delta,
not just an aggregate win rate. This exposes seat-sensitive policies and reduces scenario noise.

## 2. Keep development and validation scenarios separate

Use one fixed seed/opponent set while iterating, then make the promotion decision on a second
set that was not used to choose parameters. Keep a small holdout for rare milestone checks.

## 3. Record failures, tails, and runtime

Mean reward alone is not enough. Save the minimum result, lower quantile, invalid actions,
crashes, timeouts, and per-call runtime. A stronger average with a new catastrophic failure mode
is usually not a safe promotion.

## 4. Check the full finite horizon

Kaggriculture has a 720-turn horizon. Confirm that the replay reaches the expected terminal state
and inspect the end game separately. A policy that compounds well can still lose value through
unfinished work or poor liquidation near the horizon.

## 5. Audit action and storage constraints

Test market-action limits, inventory movement, and shed-capacity behavior with executable probes.
Treat prose assumptions as unresolved until the official environment or a local test confirms
them.

## 6. Package deterministically

Build an archive containing only root `main.py`, fix archive metadata, and record both source and
archive SHA-256 hashes. Rebuilding the same source should produce the same bytes.

I will publish a readable expansion baseline next. It is intended as a useful starting point,
not as a claim that one public ladder score proves general strength.
