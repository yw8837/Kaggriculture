# Kaggriculture Strategy | Replay Agents, Sell Guards & Engine Drift

What can a fixed replay teach us after stronger adaptive agents exist? Quite a lot—if we treat it
as a controlled baseline rather than a magic score recipe.

I am sharing a fully visible Kaggriculture agent that replays a 719-action public trajectory and
adds two small observation-aware safety layers: hand-count normalization and impossible-sell
guards. The companion Code writes the exact source, runs focused probes, and builds a deterministic
root-`main.py` archive.

Companion Code: [Kaggriculture Agent | Fixed Trace + Safe Selling](https://www.kaggle.com/code/yw8837/kaggriculture-fixed-trace-safety-baseline)

If you want a shorter reactive starting point instead, my earlier
[Kaggriculture Strong Expansion Baseline](https://www.kaggle.com/code/yw8837/kaggriculture-strong-expansion-baseline)
is a useful comparison.

## The core pattern: an open-loop plan with a closed-loop guard

A replay policy chooses action `t` from a schedule recorded at turn `t`. It is deterministic,
fast, and unusually easy to audit. It also assumes that the live game still resembles the source
game.

The public agent keeps that limitation visible. It does not add a hidden optimizer or opponent
model. It only repairs two interface-level assumptions:

1. **Live hand count.** The scheduled hand-action list is truncated or padded with `PASS` to match
   the hands that actually exist in the observation.
2. **Sell feasibility.** Before sending market orders, the agent predicts shed stock after
   same-turn `DROP` and `PICKUP` actions. Sequential `SELL` orders are then clamped to the stock
   that remains.

The ordering matters. Checking only the shed at the start of the turn misses deposits that happen
before the market phase. It can also overlook a pickup that removes stock before a scheduled sale.

This “plan plus guardrail” pattern is broadly useful. Keep the policy legible, identify the state
assumption most likely to drift, and validate at the action boundary.

## Why I am not putting a score in the title

This exact source is intentionally an older, weaker learning baseline. In a local screen pinned to
`kaggle-environments==1.32.6`, it lost all 32 both-seat games against the two stronger exact-source
references reserved for the private agents. It also lost all 80 games in a broader five-public-agent
screen. Those are direct local results on eight consumed development seeds—not a prediction of a
future Kaggle rating.

There is also an older remote submission record with a similar identity, but the historical upload
bytes are unavailable. A filename and remote rating do not prove that today's shared source is the
same artifact. So this release makes no leaderboard-score claim. Its expected public rating is
unknown.

That distinction is worth preserving in every competition:

- a source hash proves artifact identity;
- a local paired result describes a specific test matrix;
- a remote score describes whatever bytes were actually uploaded at that time;
- none of those automatically becomes a general strength estimate.

## Engine drift can reverse the story

The most surprising lesson came from an exact same-cell engine diagnostic. Across 20 games, moving
from Kaggle Environments 1.32.2 to 1.32.6 changed every final reward tuple and changed 16 of 20
win/tie/loss outcomes. The only resolved default configuration change was the town-center sell
interval moving from 12 to 24.

The sample is deliberately small and uses consumed seeds. It does not promote an agent. It does
show why a result without the engine version and resolved configuration is incomplete.

For a reproducible comparison, I recommend recording:

- exact package version and environment-source hash;
- resolved configuration, including defaults;
- source hashes for both agents;
- the seed list and both physical seats;
- full 720-turn completion and terminal statuses;
- raw rewards, money margins, lower tail, and runtime percentiles.

## A practical experiment ladder

This baseline is most useful when one change answers one question:

1. Remove the sell guard. How often do impossible or wasteful sales appear?
2. Keep the route fixed but add a state-drift detector. Which observation should trigger fallback?
3. Replace only final-day liquidation. Does terminal inventory fall without harming earlier cash?
4. Add price-aware order sizing while preserving the farm route. Does the effect survive both seats?
5. Repeat identical cells under two pinned engine versions. Can you explain every changed outcome?

Run baseline and challenger on the same cells, then keep a separate confirmation set. Do not tune
on the confirmation seeds, and do not average away a new crash or catastrophic tail.

## Provenance and limitations

The trajectory was independently regenerated from attributed public replay episode `89256171`
(team `radiant-allomancer`, player `0`). The upstream notebook is
[Kaggriculture Frontier Lab | High-Score + Visuals](https://www.kaggle.com/code/prvsiyan/kaggriculture-frontier-lab-high-score-visuals)
by PRVSIYAN, with Apache-2.0 displayed on Kaggle. The source keeps that attribution and identifies
the added hand normalization and sell guards.

Known limitations are intentional:

- the 719-step plan is open-loop and opponent-blind;
- it is tied to one public trajectory;
- safety guards repair legality and feasibility, not strategy;
- the large literal schedule is harder to modify than a compact reactive policy;
- behavior can drift sharply when environment defaults change;
- no public or private leaderboard rating is promised.

If you fork it, please keep the attribution and publish the exact source hash, engine version,
seeds, seats, and failures with your result. I would especially like to see clean guard ablations or
engine-drift explanations—share them in the comments so we can compare mechanisms, not anecdotes.

