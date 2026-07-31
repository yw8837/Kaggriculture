# Fa candidate gate record — 2026-08-01

## Fa_01 — Final-Day Labor

- Independent audit: `A_RESULT_PASS`, then private Save & Run release and post-run verification PASS.
- Frozen evaluation: 1,024 paired cells, 0 failures, 0 invalid actions.
- Paired match delta: `+0.1640625`, seed-cluster CI `[0.1435547, 0.1855469]`.
- Paired money delta: `+3974.911`, CI `[3904.620, 4046.362]`, p10 `+1671.3`.
- Sensitivity excluding the cow-tilt control/self-related lane remained positive: match delta `+0.08203125`; money delta `+4011.8008`.
- Kaggle kernel: `yw8837/fa-01-final-day-labor`, version 1, private, COMPLETE.
- Downloaded archive SHA-256: `59281C6434D6D48C429DDC7950266A1083454978A0425D143480E9BB75559670`.
- Competition submission: none.

## Rejected Fa_02 BG1 — Rescue Greedy

- Development evaluation: 160 paired cells, 0 failures, 0 invalid actions.
- Paired match delta: `0.0`, seed-cluster CI `[-0.05625, 0.05]`.
- Paired money delta: `-144.606`; direct formal margin `-331.219`.
- Disposition: `NO-GO`; confirmation and robustness pools retired unused; no Save & Run.

## Fa_02 BT1 — Last-Chance Tie-Break

- Single behavior delta: allocator key changes from `(priority, cost, y, x, i, j)` to `(priority, rank, cost, y, x, i, j)`.
- Rank 0 is restricted to an exact second-miss WATER/FEED target; priority cannot be crossed.
- Historical precheck: 720 calls, 0 invalid, 0 priority inversions, p95 `4.169 ms`, p99 `5.4232 ms`, max `5.9492 ms`.
- Local verification: 148 project tests PASS; Ruff 0; frozen manifest `14/14` hashes match.
- Seed state at this record: development `34000–34015`, confirmation `35000–35063`, robustness `36000–36031` all CLOSED.
- Status: implementation frozen; development seed opening requires independent audit.

This record does not authorize a Kaggle competition submission or public release.
