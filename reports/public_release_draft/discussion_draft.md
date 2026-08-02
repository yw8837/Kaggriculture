# Kaggriculture Agent Guide | Expansion Strategy & Both-Seat Evaluation

I am sharing a readable Kaggriculture agent for players who want to study expansion without first
building a large optimizer. The companion notebook keeps the full source visible and produces a
submission-ready archive with only root `main.py`.

## What the baseline demonstrates

- conditional land expansion during days 5-18;
- a fixed mixed-crop layout and cow/sheep herd;
- a wheat reserve for daily feed;
- deterministic task assignment for a larger workforce;
- deterministic packaging with source and archive verification.

The rules are intentionally direct. That makes each decision easy to trace and gives experiments
a clear baseline.

## A useful way to test changes

For each change, run the baseline and challenger on the same seed list in both seats. Evaluate the
complete 720-turn horizon, keep development and confirmation seed sets separate, and record:

- completed games, failures, and invalid actions;
- match outcomes and money deltas;
- runtime percentiles and the slowest call;
- land timing, cash, labor, inventories, and end-game actions.

One early ladder snapshot can be useful feedback, but it is not a stable estimate of general
strength.

## Known limitations

Labor sizing can overpay, crop and herd targets are fixed, and the policy does not condition on the
opponent. Its late-horizon and near-capacity inventory rules are intentionally basic. This is a
public learning baseline, not a leaderboard guarantee or the current private competition agent.

The most informative follow-up is a one-variable experiment: change labor sizing, crop mix, herd
composition, or the end game while keeping the same paired both-seat evaluation contract.

Companion Code title: **Kaggriculture Agent | Early Expansion & Mixed-Farm Baseline**

No standalone reuse license has been selected; check the applicable Kaggle terms before reusing
the source elsewhere.
