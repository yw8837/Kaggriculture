# Current evidence synthesis for Kag_03 and Kag_04

This is the 2026-08-10 bridge from current evidence to bounded candidate work.
It is not a promotion result and authorizes no Kaggle mutation.

## Decision

- Kag_01 remains the only acceptable control: it passed the sealed local gate
  and is currently 2716.1 on the UI, but its ladder rating peaked near 2818 and
  then fell. Rating path dependence makes a blind duplicate uninformative.
- Kag_02 is a negative control: local strict score 0.25 and current UI score
  1659.0. Its positive local mean margin was dominated by the weak G1 lane.
- The first Kag_03 SELL-order sort and Kag_04 animal-ratio implementations
  both lost the direct Kag_01 diagnostic 0-32 and are rejected. Actor-local
  weed repair, adjacent animal swap, and animal-buy prefix follow-ups were
  action-neutral ties and are also rejected.
- Selected Kag_03 changes only the existing premium preemption horizon tuple
  from `(3,2,1)` to `(4,3,2,1)` for both seats. Its historical reused-seed
  panel was 154-0-6 overall and 32-0 directly against Kag_01.
- Selected Kag_04 is the conservative seat portfolio: seat 0 uses
  `(4,3,2,1)`, while seat 1 remains exact `(3,2,1)`. Its reused-seed panel was
  138-16-6 overall and 16-16-0 directly against Kag_01.

## Required evaluation

Each candidate is paired against exact Kag_01/Tetsu v16 and four additional
opponents, both seats and preregistered seeds. It must beat Kag_01 directly
(`score > .5` and `mean margin > 0`). The development gate has a deliberately
loose catastrophic per-opponent guard rather than a full noninferiority claim.
Historical seeds are diagnostic only; fresh reserved seeds stay CLOSED until a
clean freeze and independent seed-open verdict.

The source evidence and limits are machine-readable in
`live_browser_snapshot.json`; the final selection and diagnostic receipts are
in `../05_autoresearch/final_selection.json`. Public Code or Discussion
creation is outside this cycle; competition submission remains a later terminal
action after the exact audit gate.
