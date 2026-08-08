# Public-meta mechanisms and implications for Kag_01 / Kag_02

Status: internal synthesis from primary public pages plus static inspection of exact downloaded outputs. It is not an independent-auditor verdict, a score guarantee, or permission for any external action.

## What the current public frontier actually deploys

The dominant public architecture is not a general end-to-end planner:

1. A replay-derived, usually open-loop farm/labor route supplies most actions.
2. Small observable-state repairs protect that route: hand-count alignment, WEED recovery, shed/SELL clamping, and terminal liquidation.
3. A narrow market overlay tries to win mirror-like matchups by reordering, preempting, or advancing already-planned premium SELLs.
4. Newer versions add route memories, nearest-route selection, a small mirror classifier, or a small ensemble while keeping the base farm route intact.

That structure is supported by the exact deployed source, not just page titles:

| Captured page score | Deployed source evidence | Mechanism | Important limitation |
|---:|---|---|---|
| 2957.6 and 2755.9 | exact same `main.py` SHA `62FB5A5F...` | “fit-only trajectory”; identity-free WEED repair; price-impact ranking of existing SELL slots | docstring says ordinary turns never create/delete/resize market orders; these are a byte-identical clone group |
| 2927.4 | `6CC3B69E...` | stable Kakuteki/mrgrishninsb field route; two-turn premium preemption; debt repayment; price-impact rank; terminal cleanup | near-clone gate and narrow premium list, not general MPC |
| 2753.4 | `231CF97F...` | public-farm distance + small learned mirror probability; hybrid/two-route control; WEED-slip recovery; front-run market | classifier threshold is frozen and route-centered |
| 2636.1 | `0827987D...` | stable shared route plus same-turn/premium preemption and repayment | still route-first; candidate variants differ mostly in market frontloading |
| 2530.5 | `9F18C729...` | replay opening plus observation-only task scheduler, four experts, learned market model and closed-loop wrapper | closest public collision to a scheduler, but source surface is large and it is not evidence of exact bounded scarce-resource matching |
| 2517.1 and 2332.1 | exact same `D9DC24CE...` | fit-only route plus nearest Top-30 route memory; reorders existing SELL set | byte-identical clone group; ordinary SELL creation is forbidden by its own contract |
| 2491.7 / unscored fleong page | `630125B3...` / `94711062...` | fit-only medoid, 30-route market hazard memory, one-turn preemption | fleong and web3 versions differ mainly in threshold, not architecture |
| 2477.0 | `6F529020...` | replay-derived route; hand/WEED/shed guards; premium preemption/repayment | explicitly trace-based; no general production replanning |
| 2440.2 and 2391.0 | exact same `00E8AB59...` | fixed Tran H Hoang episode 89674601 route plus terminal/cashflow repairs | byte-identical deployed output despite different Notebook research surfaces |
| 2414.6 | `D895047B...` | fixed public Tran trace with soil/front/cashflow/terminal overlays | literal 720-action tape remains the production backbone |
| 2346.6 | `4694C435...` | visible-state router over seven public Syouya/zero-waste duels | routing among fixed expert routes, not generating a new joint plan |
| 2270.5 | `7E88738B...` | loads multiple agents, route distance and market mix | ensemble/selection rather than a single interpretable planner |
| 1956.0 | `EB68BBE2...` | replay opening, task scheduler and gated market interference | the broad “robust market” label already exists publicly |
| 1935.6 | `C47FC1F...` | fresh episode 90525850 open-loop route plus safe market, mirror tiebreak, endgame pull, floor guard, WEED repair | explicitly 719-turn open-loop core |

The detailed source paths, hashes, definitions, constants, and docstrings are in `kernel_static_analysis.jsonl`. These agents were not run locally.

## Convergence, copying, and the current LB replay evidence

The separate leaderboard lane observed dominant farm hash `FC37F8688680DA949DB44C9444DCB9541488B4E10D9F432CC42648D6423F1B26` across 19/25 current top teams and 78/100 samples. That independently supports route convergence, while market traces vary more often.

Public lineage crosscheck:

- Early PRVSIYAN Frontier V12 episode 89256171/player0 is not the same farm tape under literal, prepend-None, or append-None alignment.
- Eighteen current high-score outputs, 89 files, and 20 literal tapes yielded zero exact FC37 matches.
- A second current-source pass completed only 61/155 refs before Kaggle returned 429; 15 literal tapes yielded zero match.
- Several current routes are compressed or generated and evade literal AST extraction.

Therefore the correct result is `FC37 lineage UNMAPPED`, not “the source is Frontier V12” and not “no public source exists.” The exact negative-scan boundaries and hashes are in `lineage_summary.json`.

## Mechanisms that look real versus crowded

### Crowded / should not be sold as novel

- Replay mining, fixed routes, route freshness, and route medoids.
- Identity-free public-farm distance and mirror/near-clone detection.
- WEED-slip repair, hand alignment, safe SELL clamps, and terminal liquidation.
- Price-impact SELL ordering, premium preemption, repayment debt, and order-slot safety.
- Route memory, nearest-route selection, and small route ensembles.
- Generic “robust market,” “adaptive market,” “closed loop,” or “MPC” labels without an exact new control contract.

### Underexploited or not exactly observed in the inspected frontier

- A small, bounded, polynomial joint worker-task allocator whose only action delta is on verified scarce-unit/resource contention states, with a formal priority-preservation fallback.
- A finite, declared shop-demand uncertainty set for the **new >=1.32.6 with-replacement town distribution**, evaluating the next 1–2 days and committing only the first action.
- Causal opportunity logging that distinguishes a proposed action from an executed/reconciled rescue, and compares against exact fixed-route control on the same state.
- Dynamic response to duplicate-shop composition. The old fixed-market overlays were built for a very different Town Center/shop process.

“Not exactly observed” is limited to 18 high-score deployed outputs plus current-page source metadata; it is not a patent or global novelty claim.

Tetsu v16 deserves a separate lineage warning if it is considered as a `Kag_01` base. Its exact extracted agent (`997E6BFC...F1B6`) uses the same 9,297-byte compressed route payload (`EDC3163E...06C2`) as Boatlee V14 and Flex, then extends the closely related one-turn preemption logic to ordered 3→2→1 horizons with repayment. That is potentially useful behavior, but it is not an independent route or an attribution-free source. Its artifact-specific license is `UNVERIFIED`; any competition-rules permission remains an inference for the independent auditor to decide before exact-byte reuse.

## Kag_01 implication: bounded joint assignment

The public frontier provides a strong protected control: keep the route and market byte-exact unless a narrowly defined worker/resource contention is proven. A credible `Kag_01` delta should:

- use a polynomial matching/flow/auction procedure bounded far below the per-step budget;
- preserve the formal route’s priority class before optimizing distance/value inside that class;
- reserve shared WHEAT, carried animals, shed access, and unique worker capability explicitly;
- fall back to the exact route if feasibility or a priority-preservation certificate fails;
- log candidate opportunity, changed final assignment, emitted action, completed outcome, and any stranded higher-priority task separately;
- compare directly against the 2957-style route family and against non-route schedulers.

Collision warning: `kaitofukami/...v19-replication-to-control` already contains an observation-only `_build_tasks` / `_assign_actions` scheduler, and `sidhaarthshree/a-reactive-agent-with-optimal-task` explicitly teaches task assignment. The candidate is differentiated only if its scarce-resource, priority-preserving bounded contract and evaluation are materially distinct—not by saying “optimal assignment.”

## Kag_02 implication: rebalance-aware scenario control

The broad market-overlay space is saturated, but the official rebalance creates a concrete new uncertainty problem:

- Town Center demand changed from 12-turn ticks with late 2x/4x multipliers to a flat one unit every 24 turns.
- Eight shop instances are now sampled with replacement; duplicate demand stacks and product coverage is no longer guaranteed.
- Current public overlays largely optimize price impact against fixed/replay-derived demand paths.

A credible `Kag_02` delta should therefore be an exact finite-scenario first-action controller:

- scenario state is observable current shops plus admissible next unlock/town-consumption trajectories under >=1.32.6;
- horizon is only 1–2 days and computation is bounded;
- objectives report worst-case and expected cash/inventory feasibility, with the first action committed and replanning next step;
- no identity, team, episode, seed, or private-path branch;
- exact fallback to the protected route when scenario disagreement, order-cap risk, shed overflow, or runtime cap occurs;
- it must beat simple price-impact reorder/preemption controls, not only weak baselines.

This is narrower and more falsifiable than the crowded “robust market” label. The inspected public code already includes `v15-top5-robust-market-gate`, `v13-r3 ... premium-control`, `v22 price-impact`, tactical memory, and route-refresh price impact; broad similarity is unavoidable.

## Test and evidence consequences

1. The engine upgrade identified during collection has now been applied by the main engine lane: exact package `1.32.6`, official commit `bded87b0d7879078c726a93a4884d044f79c4eed`, normalized engine SHA-256 `FB9215C5E21A25243E2D13E75B3D70A79CF7D78FFF150A90F1BB5EACF9BA2BCF`, with 81/81 official tests recorded in the tracked project evidence. This public-meta lane did not run that suite; all earlier 1.32.2 money/scenario evidence remains historical and must not be promoted.
2. Do not use current public Notebook scores as local benchmark reproduction. Use exact downloaded output SHA and both seats on the same seeds/config.
3. Separate route-family opponents from genuinely distinct external opponents; clone-heavy aggregates can overstate coverage.
4. Reserve fresh development/confirmation/robustness pools before viewing results and use seed-cluster inference, not game-row independence.
5. Report protected-lane bit equality, invalid/failure count, runtime p95/p99/max, and per-opponent deltas.
6. Treat public replay/code as hypothesis-generation and opponent construction. It is not fresh promotion evidence.
7. Preserve Apache-2.0 license and attribution only for exact reused bytes; `UNVERIFIED` pages and most GitHub repositories are not safe reuse sources.

## Public content implication

If a public Code/Discussion piece is later prepared, it should teach a deliberately weaker, already-audited historical mechanism rather than disclose `Kag_01`/`Kag_02` production bytes. A useful SEO title can truthfully center on “Kaggriculture 1.32.6 Town Rebalance,” “Replay-Route Baseline,” or “Price-Impact Safety,” but page-score claims must cite the exact version and observation time. No publication is authorized by this report.
