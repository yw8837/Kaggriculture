# Fa_02 research sequence - no promoted artifact

Status: all tested Fa_02 challengers rejected; no private Save & Run and no competition
submission.

## Original hypothesis

The first Fa_02 hypothesis reused empty cells after a fixed premium crop's latest viable
planting day. It selected wheat or carrot from expected mature yield, observed price, and seed
cost while preserving the overflow-routing parent.

The registered development screen passed 36-28 with mean margin +212.47. The untouched v1
sealed gate then separated the apparent gain from the parent mechanism:

| Opponent | Record | Match score | Cluster bootstrap 95% | Mean margin | Verdict |
|---|---:|---:|---:|---:|---|
| `final_day_labor` | 40-24 | 0.625 | [0.515625, 0.71875] | +1,012.53 | PASS |
| `overflow_drop` parent | 30-34 | 0.46875 | [0.390625, 0.546875] | -339.22 | FAIL |

The source `38F094...BF9C` therefore received a NO-GO under the result-before-change rule.
The result is consistent with the rotation displacing higher-value work in the fixed ten-worker
schedule, but task completion and movement were not instrumented, so that causal explanation is
not established.

## Bounded-workload repair

On one shared exploratory pool (seeds 17000-17015, both seats), the number of rotated nearby
cells was intended to be the only varied mechanism:

| Cap | Parent record | Parent mean margin |
|---:|---:|---:|
| 1 | 15-17 | -7.41 |
| 2 | 17-15 | +23.91 |
| 4 | 15-17 | -114.59 |
| 6 | 15-17 | -165.25 |

The raw result JSON files retain each evaluated source hash, but the intermediate generated
source bodies were later overwritten and cannot all be byte-reproduced from the final builder.
This limits the cap sweep to exploratory evidence. The selected final cap-two source itself was
separately pinned and reproducibly rebuilt for the sealed v2 gate below.

Cap two was selected, deterministically packaged, and registered in Git commit `8cdc280`
before opening new seeds. Source SHA-256 was
`F1CA36F2D43083379D6F5E89E7D15A935D6512E86ED4CFBEFEF0F5D59A1BCBF7`; the 5,394-byte
archive SHA-256 was
`DD3ABEB21A31AFDA56430ADB3555CB4A7CEBBFB24A33FFEC52447CBF30D59850`.

The 192-game v2 sealed result was:

| Opponent | Required | Observed | Verdict |
|---|---|---|---|
| Formal champion match score | >= 0.60 | 0.59375 (57-39) | FAIL |
| Formal champion cluster lower | > 0.50 | 0.479167 | FAIL |
| Formal champion mean margin | >= +300 | +759.03 | PASS |
| Parent match score | >= 0.50 | 0.53125 (51-45) | PASS |
| Parent mean margin | >= 0 | +6.23 | PASS |
| Failures | 0 | 0 | PASS |

Missing the match-score threshold by one win did not authorize changing the threshold. The
confidence-bound failure independently rejects promotion.

## Replay-derived terminal-carry counterexample

Top-replay research found several strong agents with zero final carry, so a separate challenger
returned loaded workers during the last 24 turns while empty workers continued normal work. The
registered cap experiment had already failed, so this was a fresh exploratory direction, not a
post-hoc repair to its sealed score.

The 24-turn version lost 3-61 with mean margin -3,456.66 on seeds 21000-21015. A direct final-state
inspection at seed 21000 showed both challenger and parent already ended with zero shed goods and
zero carried inventory, while the challenger lost 88,045 to 93,458. The result is consistent with
lost productive work and does show that this inspected game had no final-carry problem, but action
counts were not measured. The 36/48-turn variants were killed without evaluation because they
apply the already falsified intervention even earlier.

## Decision

No Fa_02 candidate passed every registered promotion condition. No Fa_02 artifact was uploaded to
Kaggle, no Save & Run was created, and no competition submission was made. `final_day_labor`
remains the formal local champion. The next numbered artifact must come from a materially new
mechanism, with engine-parity tests and terminal production/sale scheduling ahead of more crop
target tuning.
