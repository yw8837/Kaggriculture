# Research index

Snapshot date: 2026-07-31. These are evidence snapshots, not claims of historical
exhaustiveness. Private notebooks, deleted material, Discord, the full 13.6 GB daily
dataset, and arbitrary renamed repositories were outside the observable set.

## Stored reports

- `kaggle_public_landscape_2026-07-31.md`
  - 56,830 bytes; SHA256
    `1EC4E6C64684BDDA5F0A1F019917AF69842A9E8812627552F26C2751E2270EF9`.
  - Live top-six snapshot, a URL/SHA-256 manifest for 22 public replay payloads / 31 seat
    observations, 14 public Code entries, three Discussions, three Datasets,
    official-engine history, GitHub searches, query log, limitations, and proposed
    falsification tests.
  - Five raw replay payloads remain in the local `references/top-replays` cache and three
    overlap this 22-episode manifest. The remaining URLs and hashes are re-downloadable but are
    not a fully local immutable snapshot.
- `related_methods_landscape_2026-07-31.md`
  - 38,636 bytes; SHA256
    `DAC7097BCD3407EDBC202BC2EF5983600EA26FD712004F309634BC67F6558D55`.
  - Twenty-one retained primary or near-primary sources covering successful and
    failed competition bots, shrinking-horizon planning, economic MPC, assignment,
    simultaneous-action search, market impact, opponent modelling, and robustness.

## Evidence-backed campaign findings

1. The live top six did not share one build. Their public replays showed materially
   different expansion timing, crew size (11-15), crop portfolios, and herd mixes.
   The recurring pattern was aggressive land, large crews, animals, and deliberate
   liquidation; it is a prior to test, not a policy to clone.
2. The strongest clean endgame observation was smlcr finishing with zero carried
   inventory in all six retained replays. Several other top policies stranded
   fertilizer, milk, wheat, or wool. A terminal-liquidation ablation therefore has
   higher priority than further fixed crop tuning.
3. The pinned official engine and its README conflict on the fed-and-cared bonus:
   executable code adds `+1`, while prose says `+2`. Calculations must follow pinned
   code and be guarded by a one-step parity test; prose alone is not authoritative.
4. Cross-competition evidence repeatedly favors an exact simulator, short replanning,
   marginal-value task assignment, and replay-driven ablation. It does not justify
   copying finance formulas, opponent identities, or atomic-action MCTS into this game.

## Ordered experiment backlog

1. Engine parity golden tests, especially care, market interleaving, price floor,
   town tick, land, and hire transitions.
2. Terminal liquidation at 72/48/24 turns, evaluated on paired seats with terminal
   cash, lower decile, failures, and final carry.
3. Official-market transition oracle and success-aware order queue before any learned
   market policy.
4. Marginal-cash global task assignment with travel, inventory, and deadline costs.
5. Confidence-gated opponent response only above a robust default policy.

Every item requires a registered holdout and a failure criterion before promotion.
