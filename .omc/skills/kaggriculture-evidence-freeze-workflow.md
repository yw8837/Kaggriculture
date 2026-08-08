---
name: kaggriculture-evidence-freeze-workflow
description: Preserve Kaggriculture stepwise failures and historical frozen blobs while evolving live evaluation tooling.
triggers:
  - runner final DONE overwrite
  - historical manifest hash mismatch after tooling update
  - frozen Kaggriculture evidence cannot reproduce
  - live runner differs from receipt runner
---

# Kaggriculture Evidence Freeze Workflow

## The insight

Kaggriculture evidence has two different truths that must never be collapsed:

1. A live runner must scan every step status because the official environment can end with `DONE` after an earlier abnormal status.
2. A historical receipt must be checked against the raw Git blob at its implementation commit, not against today's safer runner bytes.

Updating the runner and then rewriting old manifests to the new hash destroys provenance. Keeping the old runner live preserves a known failure-masking bug. The correct design is a hardened live runner plus commit-addressed historical verification.

## Recognition pattern

- A raw replay reports terminal `DONE/DONE`, yet earlier steps contain `ERROR`, `TIMEOUT`, or `INVALID`.
- `tests/test_fa04_top_trace_boundary.py`, `tests/test_fa05_trace_gate.py`, `tests/test_fa05_wool_gate.py`, or `tests/test_next_boundary.py` fail only because the current runner SHA differs from the receipt.
- A developer proposes updating an old manifest hash to make the test green.
- The same candidate/result is called reproducible even though its exact implementation commit is not used during verification.

## Approach

1. In `src/kaggriculture_lab/evaluation/runner.py`, scan the complete step sequence and retain the first abnormal status. Do not infer validity only from the terminal status.
2. Freeze new runs with the hardened live runner SHA, exact bytes, engine version, config, source/opponent hashes, and start/end receipts.
3. For historical evidence, read raw bytes with `git show <implementation_commit>:<path>` (binary output, no text decoding or `.strip()`) and hash those bytes.
4. Keep `IMMUTABLE_LOCAL_EXTERNAL` replay inputs as current-path hash checks only when they were never committed; label that limitation explicitly.
5. Never change historical manifest hashes merely because live tooling evolved. If the old freeze was unsound, retain it as historical evidence with a defect label rather than laundering it into a current freeze.
6. Run focused historical tests, the full suite, and scoped Ruff. Preserve immutable stdout/JUnit evidence only after final file bytes are fixed.

## Success criteria

- Hidden intermediate abnormal statuses make a game invalid even if terminal statuses are `DONE`.
- Historical tests pass against their original commit blobs while the live runner remains hardened.
- Old receipt hashes are unchanged.
- New execution receipts bind the current engine and runner bytes.
- No claim upgrades a historical screen into fresh promotion evidence.

## Pitfalls

- `git show` with text conversion can change CRLF/LF bytes and invalidate the proof.
- `ruff check .` can enter ignored third-party clones; lint `src`, `tests`, and owned research scopes.
- A clean current worktree does not prove a historical package used current bytes.
- Terminal `DONE` is not a substitute for scanning every step.
