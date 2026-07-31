# Public expansion baseline release gate

Verdict: **GO for Discussion-first public notebook release; not a private champion and not a
competition submission.** The external rating is unknown. The intended band is approximately
1050, but only the live ladder can measure it.

## Artifact identity

- Policy: `public_expansion_baseline`
- Source SHA-256: `BD32AEFDC00B1F0A41746EBACC4FCBF0AFF32AC061363179F15371B9ACE9A5C0`
- Deterministic archive SHA-256:
  `967A899A2BE149FF676B025E955AEDE2C42C0720C0A868428770A9B818F1144D`
- Archive bytes/members: 4,685 bytes; root `main.py` only
- Two independent deterministic builds produced identical archive bytes.
- The public comments do not change behavior: its Python AST is identical to evaluated
  `labor_rush` (`F4DC4D4C4002C7D4088C9B0EE14F412AE3920087C29023AC3A9D43404AB993DA`).

## Local strength and intentional separation

All comparisons use paired seeds in both seats.

| Gate | Games | Result | Failures | Mean margin |
|---|---:|---:|---:|---:|
| vs private Fa_01 mechanism, seeds 600-647 | 96 | 1-95 | 0 | -10,317.99 |
| public validation pool, seeds 100-107 | 48 | 48-0 | 0 | +66,444.00 |
| fast-expansion/cow-tilt calibration, seeds 500-507 | 32 | 8-24 | 0 | -2,280.09 |

The 95% seed-cluster bootstrap interval for match score against the private Fa_01 mechanism is
`[0.00000, 0.03125]`. This demonstrates material local separation without claiming a precise
Kaggle rating.

## Runtime and packaging

- 720 replay calls; 0 invalid outputs
- p50 0.5193 ms; p95 1.6762 ms; p99 2.3353 ms; max 2.7669 ms
- Public notebook keeps the full source readable and produces a deterministic `tar.gz` with only
  root `main.py`.

## Publication and audit disclosure

- Discussion published first: `https://www.kaggle.com/competitions/kaggriculture/discussion/731515`.
- Public Code Version 1: `https://www.kaggle.com/code/yw8837/kaggriculture-strong-expansion-baseline`.
- Kaggle status: `COMPLETE`; downloaded source/archive hashes match local bytes exactly.
- The public policy shares 445 of 446 lines with the active unnumbered `fast_expansion` baseline
  (line similarity 0.9977578). This is a deliberate initial-bootstrap exception because the user
  explicitly classified the two initial submissions as baseline code and authorized publication
  of the current 1000-level baseline. It is not a normal future rolling release.

## Honest public limitations

- The twelve-hand hiring target can overpay when marginal work is low.
- Crop and herd targets are fixed and do not condition on the opponent.
- No dedicated final-day or near-capacity inventory safeguard is present.
- This artifact must never be described as the active private champion.

## Raw evidence

- `artifacts/evaluations/public_labor_rush_vs_Fa_01.json`
- `artifacts/evaluations/public_labor_rush_validation.json`
- `artifacts/evaluations/public_probe_labor_rush.json`
- `artifacts/evaluations/public_expansion_runtime.json`
- `dist/public/manifest.json`
