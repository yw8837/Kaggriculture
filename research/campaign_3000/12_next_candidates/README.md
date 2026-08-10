# Kag_03 / Kag_04 — closed implementation freeze

This pair follows the persistent campaign checklist and the named Kag_01/Kag_02 analysis. It is not an upload, competition submission, public release, or seed-opening authority.

| Slot | Single delta over exact Kag_01/Tetsu v16 | Reused-seed diagnostic only |
| --- | --- | --- |
| Kag_03 | Premium SELL preemption horizons `(3,2,1) → (4,3,2,1)` for both seats. | 5 opponents × 16 historical seeds × both seats: 154–0–6, score 0.9625, mean margin +6288.2625; direct Kag_01 32–0, +985.8125. |
| Kag_04 | Seat 0 uses `(4,3,2,1)`; seat 1 keeps exact `(3,2,1)`. | Same reused panel: 138–16–6, score 0.9125, mean margin +6193.525; direct Kag_01 16–16–0, +492.90625. |

The diagnostics reused historical seeds `50000–50015`; they are selection evidence, not fresh promotion evidence. All six new ranges remain pristine `CLOSED` with zero games:

- Kag_03: development `56000–56015`, confirmation `57000–57063`, robustness `58000–58031`.
- Kag_04: development `59000–59015`, confirmation `60000–60063`, robustness `61000–61031`.

The development panel is exact Kag_01 plus Ray, Boatlee, Kag_02/Kaito, and Fa04 G1, both seats. The gate requires the exact 160 cells, exact frozen source/environment identity, zero failures/abnormal states, complete causal metrics, overall score/margin floors, a strict direct Kag_01 win, and only a catastrophic per-opponent guard. It does **not** claim full per-opponent noninferiority or a guaranteed 3000 rating.

Before any new seed runs, regenerate the reservation scan and clean two-stage S/E freeze, then obtain the independent auditor's exact OPEN verdict. Any source mutation invalidates this freeze and requires a full re-freeze.
