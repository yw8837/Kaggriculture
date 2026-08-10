# Evidence comparison: Kag_01 and Kag_02

## Scope and evidence classes

`FACT` means a value parsed from a hash-pinned local artifact. `INFERENCE`
means a limited conclusion from those facts. `UNKNOWN` means this capture has
no evidence and makes no substitute claim.  This report is a comparison, not a
promotion decision or an independent audit.

| Field | Kag_01 | Kag_02 |
| --- | --- | --- |
| Exact local candidate | `tetsu_v16.py`, 27,244 bytes, `997E6BFC…710F1B6` | `kaito_v22.py`, 18,609 bytes, `62FB5A5F…657147A` |
| Frozen development candidate identity | exact SHA unchanged at start/end | exact SHA unchanged at start/end |
| Local seed range / seats | 50,000–50,015; both seats | 53,000–53,015; both seats |
| Environment / episode length | default, 720 steps | default, 720 steps |
| Local strict result | `PASS` | `NO_GO` |
| Remote private Save & Run | v1, `COMPLETE`, private, internet off | v1, `COMPLETE`, private, internet off |
| Remote archive | 19,099 bytes, `184F687C…001BF9E16`; equals approved | 17,360 bytes, `37EA53D3…FC4DD974C`; equals approved |
| Archive `main.py` | 27,244 bytes, `997E6BFC…710F1B6` | 18,609 bytes, `62FB5A5F…657147A` |
| Classification | `STRICT_DEVELOPMENT_PASS_PRIVATE_SAVERUN` | `EXPLORATORY_PRIVATE_SAVERUN_READY_NON_PROMOTION` |
| Competition rating / score time series | `UNKNOWN`: no competition submission | `UNKNOWN`: no competition submission |

The remote timestamps (`2026-08-08T23:42:15.120Z` and
`2026-08-08T23:45:30.623Z`) are only locally observed Save & Run times. The
raw live `GetKernel` envelopes were not retained and a later read returned a
different mutable time, so they are not a rating or an authoritative live time
series.

## Frozen local development results (`FACT`)

These two grids are not head-to-head: seeds differ and the opponent sets differ.
In particular, their overall numbers must not be read as a paired Kag_01 vs
Kag_02 effect.

| Metric | Kag_01 | Kag_02 |
| --- | ---: | ---: |
| Valid / raw games | 128 / 128 | 128 / 128 |
| Wins–losses–ties | 122–6–0 | 32–96–0 |
| Match score (95% seed-cluster bootstrap) | 0.953125 [0.90625, 1.0] | 0.25 [0.25, 0.25] |
| Candidate mean final money | 81,905.539 | 71,188.586 |
| Mean final-money margin | +7,623.484 | +2,185.141 |
| Median / p10 margin | +1,975.5 / +273 | -4,059.5 / -7,880 |
| Runtime p99 / max seconds | 7.0324 / 7.0360 | 7.2486 / 7.2773 |
| Sum of per-game elapsed seconds | 756.975 | 799.772 |
| Row `error` / hidden abnormal status | 0 / 0 | 0 / 0 |
| Candidate metrics rows | 0 | 0 |

### Opponent and economy comparison (`FACT`)

Each opponent has 16 seeds x 2 seats = 32 games. Money and margin are final
game values, not a cash time series.

| Slot | Opponent | W–L | Candidate mean | Opponent mean | Mean margin |
| --- | --- | ---: | ---: | ---: | ---: |
| Kag_01 | Boatlee v14 | 32–0 | 81,283.375 | 80,264.938 | +1,018.438 |
| Kag_01 | Fa04 g1 | 32–0 | 88,486.750 | 63,966.469 | +24,520.281 |
| Kag_01 | Kaito v22 | 30–2 | 76,997.344 | 72,567.562 | +4,429.781 |
| Kag_01 | Ray c45 exact | 28–4 | 80,854.688 | 80,329.250 | +525.438 |
| Kag_02 | Tetsu v16 | 0–32 | 68,124.312 | 73,298.938 | -5,174.625 |
| Kag_02 | Boatlee v14 | 0–32 | 68,289.812 | 73,136.438 | -4,846.625 |
| Kag_02 | Fa04 g1 | 32–0 | 79,928.906 | 56,267.469 | +23,661.438 |
| Kag_02 | Ray c45 exact | 0–32 | 68,411.312 | 73,310.938 | -4,899.625 |

Seat aggregate is balanced in game count, but it does not make the two slots
comparable: Kag_01 margin is +7,616.266 (seat 0) and +7,630.703 (seat 1);
Kag_02 is +1,965.328 (seat 0) and +2,404.953 (seat 1). `INFERENCE`: the
Kag_02 `NO_GO` is supported by three 0–32 opponent records, including the
exact Kag_01 control, rather than by a one-seat artifact.

## Actions, episode/replay, and alignment

`FACT`: Kag_01's source calls weed repair, repayment shift, SELL ranking,
preemption, and terminal liquidation. Kag_02 calls weed repair plus in-place
existing-SELL impact ranking. These are source-structure observations, not a
measurement of their executed action count.

`UNKNOWN`: neither development `raw_report.json` stores emitted actions,
per-step inventory/cash, or a replay ID. The private Save & Runs preserve an
archive/log receipt, not competition episodes. Therefore this capture has:

- no Kag_01/Kag_02 episode IDs, opponents, or seats from Kaggle;
- no replay-derived inventory/economy trajectory;
- no action, invalid-action, reorder, fallback, or market-order count;
- no current official rating or time series.

The frozen public-replay corpus is deliberately not substituted for them:
`replay_inventory.jsonl` records 89 verified, 720-step public replays from
other submissions. Its runtime analyzer explicitly aligns action emitted at
observation `i` to recorded replay state `i + 1`, therefore compares exactly
`emitted_actions[:719]` with `recorded_actions[1:]`. Any future Kag_03/04
action comparison must preserve that 719-action/offset-1 rule; do not report
720 aligned actions.

## Failure and provenance defects

1. `FACT`: Both frozen development reports have 128 `DONE` candidate states,
   128 `DONE` opponent states, zero row errors, and zero hidden abnormal
   status failures. The runner used by this report has a stepwise scan before
   accepting the final `DONE` state.
2. `FACT`: An older local-runner defect is separately recorded: terminal
   `DONE` could overwrite an earlier `ERROR`, `TIMEOUT`, or `INVALID` state.
   Thus legacy reports with only final status cannot prove a failure-free run.
   It does not erase the later report's stepwise result, but it bars using any
   older final-status-only evidence as equivalent.
3. `FACT`: exact subprocess stderr was not saved for either development run.
   No immutable zero-stderr claim is available.
4. `FACT`: `candidate_metrics_games` is zero in both grids. There is no
   execution counter evidence for market triggers, exception fallbacks, or
   action changes.
5. `FACT`: no current API response was collected on 2026-08-10: the one
   read-only `uvx kaggle` request failed while creating its local cache before
   initialization (`os error 183`). `UNKNOWN` is not zero.

## Current-versus-local gap

| Needed comparison dimension | Frozen local evidence | 2026-08-10 current official evidence | Consequence |
| --- | --- | --- | --- |
| Kag_01/Kag_02 archive identity | remote archive and member hashes, v1 receipts | none retrieved this capture | historic runtime identity only |
| Competition submission / rating | 2026-08-08 frozen account snapshot: 22 submissions, latest ref 55270999; receipts say neither Save & Run submitted | none retrieved | cannot claim present ranking, score, or drift |
| Episode/seat/opponent | none for these two slots | none retrieved | cannot compare live episode mix or seat exposure |
| Replay actions/economy | no slot replay; 89 other replay corpus only | none retrieved | action/economy causal claim blocked |
| Runtime/failures | local 128-game grids, plus remote compilation/log pattern receipt | no current execution | historical only, not live reliability |

The old account snapshot is bounded to `2026-08-08T17:50:15.385Z`; the remote
receipt's 22-submission check is `2026-08-08T23:51:25.917Z`. Neither is a
current observation. A competition-submission response would also not prove
the status of a private Save & Run kernel.

## Actionable deltas and falsifiers

### Kag_03 — exact Kag_01 control, narrow market delta

`INFERENCE`: Kag_01 is the only defensible control for Kag_03, not Kag_02:
Kag_02 loses every evaluated game to the Tetsu control in its own grid. The
smallest eligible design is therefore a legal, observable market-only
reordering overlay with exact control fallback. It must not mutate farmer or
hands, create/delete/resize orders, use identity/seat/seed/episode/step
triggers, or turn a missing action trace into a gain claim.

Falsify/stop the candidate if any of the following occurs:

1. protected farmer/hands equality, market multiset/length preservation, or
   legal SELL-only ordering fails on any emitted action;
2. paired same-seed, same-opponent, both-seat comparison against the exact
   Kag_01 hash fails its predeclared non-inferiority floor;
3. it cannot outperform both exact control and the existing simple
   price-impact/preemption order controls on a predeclared fresh pool;
4. per-game 719-aligned action comparison shows unaccounted action changes,
   or the trigger/fallback/reorder counters are absent, invalid, or zero across
   all evaluated opportunities;
5. any stepwise `ERROR`/`TIMEOUT`/`INVALID`, illegal order, or runtime cap is
   observed.

### Kag_04 — independently bounded successor

`INFERENCE`: do not interpret Kag_02's market ranking as a positive baseline.
For any Kag_04 farm/hands proposal, freeze one observable action contract and
use Kag_01 exact control on the same seeds/opponents/both seats; do not use
Kag_02's different seed/opponent grid as an effect size. It needs the same
stepwise failure scan, protected-lane proof, per-game counters, and 719-action
alignment. It is falsified by any protected-action drift outside its declared
lane, lack of a visible trigger, paired non-inferiority failure, or a result
driven only by Fa04 while failing the route-family controls.

These are evaluation requirements, not authorization to execute a new seed
run, submit, or publish.
