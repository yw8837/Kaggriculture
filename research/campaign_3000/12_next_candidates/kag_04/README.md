# Kag_04 — Tetsu v16 seat-0 horizon-four preemption

Status: materialized implementation-freeze input. `main.py` is 28,040 bytes, SHA-256 `3B4E4D626D7F9062B5E1122198112FD4F23C2142B77962368362C4CB627A6708`, and is byte-identical to the deterministic builder output.

The only action decision delta is:

```python
for horizon in ((4, 3, 2, 1) if _seat(obs) == 0 else (3, 2, 1)):
```

Seat 0 may try the existing four-turn premium-sale horizon before the original 3/2/1 sequence. Seat 1 retains exact 3/2/1. No new order rule, route, repayment, liquidation, fallback, forecast, identity, opponent, seed, replay, or fixed-step branch is added. `calls`, `preemptions`, and `horizon4_preemptions` are action-neutral metrics only.

The source is a Tetsu v16 derivative, not clean-room work. The exact base SHA-256 is `997E6BFC5234534E246E945BC61C87858EBF997AB85B0A5C9427DD4ED710F1B6`. Preserve the conditional Apache-2.0 lineage and limitations in `research/campaign_3000/07_release/TETSU_IP_VERDICT.md`.

The reused direct screen was 16 wins, 16 ties, 0 losses, score `0.75`, mean margin `+492.90625`. The exact production panel over five opponents was 138 wins, 16 ties, 6 losses, score `0.9125`, mean margin `+6193.525`, with 572 horizon-four preemptions. These used already-consumed historical seeds and are selection diagnostics, not fresh promotion evidence.

Earlier animal quantity, adjacent swap, and animal-prefix deltas are retained only as rejected provenance. Fresh execution, packaging, submission, and external action remain forbidden pending the clean S/E freeze and independent auditor OPEN.

Materialize with:

```text
python -m kaggriculture_lab.research.kag04_seat0_horizon4 --base research/campaign_3000/06_candidates/snapshots/tetsu_v16.py --output research/campaign_3000/12_next_candidates/kag_04/main.py --receipt research/campaign_3000/12_next_candidates/kag_04/materialized_receipt.json
```
