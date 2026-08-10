# Kag_03 — conservative terminal-market SELL ordering

Status: local construction only. No seed evaluation, Kaggle action, Save & Run, commit, or
promotion claim has been made.

## Control and hypothesis

- Exact control: `research/campaign_3000/06_candidates/snapshots/tetsu_v16.py`
- Control SHA-256: `997E6BFC5234534E246E945BC61C87858EBF997AB85B0A5C9427DD4ED710F1B6`
- Hypothesis: when Tetsu v16 has already emitted several independently legal terminal-inventory
  SELLs, placing the most visibly glut-exposed product in the earlier existing SELL slot can
  improve the lockstep market matchup. This is a falsifiable hypothesis, not an expected gain.

Kag_03 does **not** create terminal liquidation. The control's existing liquidation and all of
its farmer and hand decisions remain authoritative. Kag_03 only ranks already-emitted SELL
slots, including any SELLs the control itself emits near its own terminal branch.

## Allowed mutation and guard

The one permitted mutation is a permutation of existing unique `SELL` orders. It ranks them by:

1. descending observable public market inventory;
2. descending existing requested quantity;
3. product name and original position as deterministic ties.

The candidate never changes the farmer, hands, list size, a non-SELL position, a SELL product,
or a SELL quantity. The delta code, after the control action is produced, does not read a horizon,
day, step, seat, episode, opponent identity, or opponent-private state to decide a mutation.
The focused static test parses only that generated overlay suffix (not the retained control prefix)
and permits direct observation access only to `private` and `market`; direct, `.get`, `getattr`,
and simple aliases are rejected for step/day/hour/player/seat/seed/episode/replay/team/opponent.

It returns the exact control action without a mutation if the action or observation is malformed,
there are fewer than two SELLs, a SELL is ambiguous (duplicate product), its quantity is not a
positive exact integer, availability/inventory is missing, a SELL exceeds observed shed stock,
an unknown market order occurs, the list exceeds ten entries, a no-op ranking results, or any
exception occurs. It never repairs, adds, deletes, clamps, or resizes an order.

## Counters

The generated candidate exposes `kag03_metrics()` for delta-only observability:

| Counter | Meaning |
| --- | --- |
| `calls` | wrapper invocations |
| `reordered` | accepted SELL-slot permutations |
| `no_op` | legal action had fewer than two SELLs or was already ranked |
| `rejected_malformed` | incomplete/unknown action or observation shape |
| `rejected_ambiguous` | duplicate SELL product |
| `rejected_illegal` | SELL amount/inventory cannot be proven legal |
| `rejected_resize` | more than ten orders or a failed permutation-shape assertion |
| `exception_fallback` | caught delta exception |

Counters never alter an action.

### Optional evaluator extraction

After a self-contained `main.py` is loaded, an evaluator may call the generic optional
`get_metrics()` function once after an episode. It returns the same snapshot as
`kag03_metrics()` and accepts no observation, seat, seed, or opponent argument. The existing
runner-compatible names are also present: `rescue_metrics()` returns the snapshot and
`reset_rescue_metrics()` zeroes only the counters before returning the zeroed snapshot. No runner
change is required: a loader that already retains the candidate namespace can use
`namespace.get("get_metrics", lambda: {})()`; the current runner can discover its two rescue hook
names directly. Callers that do not inspect a hook preserve the normal `agent(obs)` interface.

## Nonclaims

- No local game, revenue, score, runtime, or leaderboard improvement is claimed.
- A requested SELL is not proof that its full quantity is accepted by the engine.
- Public inventory does not reveal simultaneous opponent order quantity or order identity.
- This candidate has not cleared any development, validation, robustness, packaging, or
  promotion gate.

## Reproducible local build

```powershell
@'
from pathlib import Path
from kaggriculture_lab.candidates.kag03_terminal_market import build_file

print(build_file(
    Path("research/campaign_3000/06_candidates/snapshots/tetsu_v16.py"),
    Path("research/campaign_3000/12_next_candidates/kag_03/main.py"),
))
'@ | .\.venv\Scripts\python.exe -
```

## Materialized freeze

- Self-contained input: `main.py`
- Candidate SHA-256: `9034026D6872109C9AF6BD5582F65446312F0D109654BE388A17D8F8A186FE36`
- Candidate bytes: `33206`
- Control SHA-256 / bytes: `997E6BFC5234534E246E945BC61C87858EBF997AB85B0A5C9427DD4ED710F1B6` /
  `27244`
- Receipt: `freeze_receipt.json` (`kag03_terminal_market_freeze.v1`), recording a successful
  `compile(..., "<kag03_freeze>", "exec")` and zero initial/reset/generic metrics for
  `kag03_metrics`, `get_metrics`, `rescue_metrics`, and `reset_rescue_metrics`.

This freeze validates construction and hooks only; it is not a seed, game, performance, or
promotion result.
