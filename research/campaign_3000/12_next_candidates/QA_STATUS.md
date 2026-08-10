# Kag_03 / Kag_04 QA status

Current state: local construction passes; all fresh pools remain CLOSED.

## Candidate outcome so far

- Kag_03 is exact Tetsu v16 except the premium-preemption horizon tuple changes from
  `(3, 2, 1)` to `(4, 3, 2, 1)` for both seats, plus action-neutral counters.
- Kag_04 applies that same horizon extension only in seat 0; seat 1 keeps the exact control
  horizon tuple. Its counters are action-neutral.
- Historical reused-seed diagnostics selected these variants but do not promote them:
  Kag_03 beat exact Kag_01 32–0 with mean margin `+985.8125`; Kag_04 produced
  16 wins and 16 ties with mean margin `+492.90625`.
- Rejected deltas and zero-effect iterations remain recorded. No local result guarantees a
  3000 leaderboard rating.

## Integrity and tests

- Exact candidate sources: Kag_03 `9910E333...145A0C` / 27,994 bytes; Kag_04
  `3B4E4D62...27A6708` / 28,040 bytes.
- Candidate reconstruction from the pinned Tetsu control is byte-exact.
- Focused suite final rerun: `96 passed in 10.98s`.
- The first broad run produced `646 passed, 1 failed, 3 deselected`; the single failure was
  another historical Kag_01/Kag_02 child-process test that launches the bundled executable
  after its bootstrap environment has been cleared. It was not reported as a pass.
- Scoped full project rerun: `646 passed, 4 deselected in 153.90s`.
  The four explicit exclusions are the pinned historical Kag_01/Kag_02 closed-plan test and
  three historical child-process environment tests that require the project `.venv`
  interpreter layout. Current runner/gate and launcher attack coverage is in the focused suite.
- Ruff: `All checks passed!` for the runner, gate, freeze tooling, selected builders, and tests.
- Closed plan: `VALID_CLOSED_DEVELOPMENT_PLAN`, exactly 160 cells per candidate.
- The frozen PowerShell/Python launcher avoids the unusable local `.venv` uv trampoline and is
  itself one of eight exact execution inputs.
- The runner exclusively creates the actual started receipt, run-id source directory, and final
  report; binds the clean S-to-E Git authority; executes immutable candidate/opponent payloads;
  and records the actual 1.32.6 engine, six dependency files, make-callable identity, eight
  execution inputs, and per-row execution-source hashes. The gate rereads and rehashes those
  actual files and rejects missing, drifted, bool-laundered, shape-only, or self-consistently
  forged evidence.
- The final seed-collision values live only in `seed_collision_scan.json` to avoid a
  self-referential scanner receipt.

## Still required

1. Deterministic manifest and clean two-stage S/E freeze.
2. Independent-auditor exact OPEN authority.
3. Fresh development execution on the reserved pools, followed by the strict direct Kag_01 gate.
4. Package and submit only candidates that pass; then verify remote execution and submission.

No approval prompt, public Code/Discussion action, fresh seed, upload, or submission was used here.
