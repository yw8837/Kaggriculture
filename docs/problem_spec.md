# Problem specification

Evidence date: 2026-07-31. Authority order is official simulator source/tests, official
competition pages, then public implementations. Unknowns are not filled by guesswork.

## Objective and leaderboard metric

- One episode is a two-player, 720-turn game: 30 days × 24 turns.
- Each episode reward is the player's final bank balance. Unsold inventory has no terminal
  value.
- Episode outcome uses only final-bank win/loss/tie. Coin margin does not affect the rating
  update.
- The ladder matches bots with similar skill ratings. Five submissions are allowed per day;
  only the latest two remain active and enter final evaluation, while the better active score
  is shown on the leaderboard.
- There is no private leaderboard. After submissions close, games continue for roughly two
  weeks and a final Bradley–Terry tournament is fit to the episode outcomes.

Design impact: local promotion targets paired win rate and opponent coverage, not maximum
cash or a single public ladder score.

## State and partial observability

The agent observes both public farms (money, board tiles, worker positions, unlocked land,
daily hire count), shared market inventory/prices, shared town shops, and its own private
shed, seeds, and carried inventories. The opponent's shed, seeds, and carried inventories are
hidden. The episode seed is also hidden from agents.

## Action budget and ordering

- The main farmer and every hired hand each issue at most one field action per turn.
- A player may queue at most 10 market orders per turn; extras are silently discarded.
- Market orders are interleaved one unit at a time across players, so order and quantity
  affect shared price impact.
- Invalid actions are silent no-ops. Agent action timeout is one second.
- Evaluation permits no network ingress or egress.

## Economy

- Start: 3,000 coins, northwest 5×5 quadrant, one farmer.
- Land: successive quadrant purchases cost 1,000 / 2,000 / 4,000.
- Daily worker hires follow `1, 1, 2, 3, 5, 8, ...` and reset each day.
- Shed capacity is 100 non-seed items; end-of-day overflow is destroyed.
- Crops: wheat, carrot, tomato, strawberry, melon. Animals: goose, cow, sheep.
- Crops must be watered and animals fed; two consecutive misses destroy the asset.
- Shared sell prices follow the official per-resource piecewise curve around inventory 10,000.
  Strawberry, melon, milk, and wool have especially severe glut collapse.
- Town demand removes goods and increases over the season. Shop unlock order is seeded and
  stochastic.

Exact crop/animal constants and price parameters remain imported from the pinned official
engine rather than duplicated in policy code where possible.

## Submission contract

A single-file submission has root `main.py` exposing `agent(obs)`. A multi-file submission is
a `.tar.gz` with `main.py` at archive root. Imports must resolve under
`/kaggle_simulations/agent/`. Packaging, import, timeout, schema, and a 720-turn self-play
validation are required before upload.

## Open questions requiring probes

- Resolved runtime resources beyond the one-second action timeout are not exposed as concrete
  values in the fetched FAQ page; do not assume CPU/RAM limits.
- The public replay corpus lags new agents and is not a complete census.
- Whether fast land expansion dominates depends on simultaneous labor, seed/feed, market
  impact, and opponent archetype; it is a falsifiable hypothesis, not a rule.

