# Decision log

## Iteration 0001 — Tetsu v16 + Kaito v22

- Evaluation: `F3D6A16C59428E688F3A8978F75134363BA328ABDAF30F8877EA75A7C47CA047`
- Result: `pass=false`, score `0.0`.
- Decision: reject for immediate release readiness. Tetsu was strongest in the consumed-seed current-engine screen, but its exact Notebook license and remote score are unverified. Keep it as a separately audited research candidate, not as a byte-copy production payload.

## Iteration 0002 — Kaito v22 + Ray C45

- Evaluation: `179BEDC67B85F218108C9FEE2A8EAAC80C37594905FAF91F8CC88C4898EB0464`
- Result: `pass=true`, score `2927.4`.
- Decision: stop on the explicit first-pass terminal condition. Both exact artifacts have captured Apache-2.0 provenance, public scores at or above 2900, and 16/16 wins against frozen G1 on the consumed-seed 1.32.6 screen.
- Boundary: this only selects the release-ready portfolio. Fresh local gates, exact package provenance, independent audit and remote verification remain mandatory.
