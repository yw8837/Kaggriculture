# Kag_03 — premium-preemption horizon 4,3,2,1

Status: materialized implementation-freeze input. No fresh reserved seed, Kaggle action, submission, or promotion action was performed.

## Exact control and single delta

- Control: `research/campaign_3000/06_candidates/snapshots/tetsu_v16.py`
- Control: 27,244 bytes, SHA-256 `997E6BFC5234534E246E945BC61C87858EBF997AB85B0A5C9427DD4ED710F1B6`
- Candidate: 27,994 bytes, SHA-256 `9910E3332150698834AD792B6D9FAC66DE8AFE8DD905CB2FC672E9DAE9145A0C`

The only action-semantic replacement is:

```python
for horizon in (3, 2, 1):
# becomes
for horizon in (4, 3, 2, 1):
```

No new observation, route, repayment, liquidation, threshold, fallback, order quantity, or opponent/seed/replay branch is added. The remaining additions are action-neutral counters and runner hooks: `calls`, `preemptions`, and `horizon4_preemptions` via `kag03_metrics`, `get_metrics`, `rescue_metrics`, and `reset_rescue_metrics`.

## Evidence boundary

The historical reused-seed direct screen was 32–0 against exact Kag_01/Tetsu v16, mean margin `+985.8125`, with 410 successful horizon-four triggers. The exact production panel was 154–0–6 over five opponents, mean margin `+6288.2625`, with 1,144 horizon-four preemptions. Both use already-consumed seeds `50000–50015`; they are selection diagnostics, not fresh promotion evidence.

The prior SELL-order sorter and proactive WEED repair are rejected and not the production `main.py`. Their outcomes and hashes are retained in `research/campaign_3000/13_cycle_20260810/05_autoresearch/final_selection.json` and the variant-screen evidence.

## Materialization

`main.py` and `freeze_receipt.json` were deterministically regenerated from exact pinned-control bytes using `src/kaggriculture_lab/research/kag03_preempt_horizon.py`. The builder-produced receipt records both source hashes, the tuple replacement, compile result, and zeroed metrics hooks. Removing the metrics instrumentation and restoring the tuple yields exact control bytes.
