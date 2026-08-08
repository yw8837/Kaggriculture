# CLOSED private SaveRun candidate freeze

Verdict: two exact candidates and all downstream seed pools are frozen `CLOSED`. No fresh game,
Kaggle SaveRun, upload, submission, or publication was performed.

| Slot | Exact payload | Planned archive | Development grid |
|---|---|---|---:|
| Kag_01 | Tetsu v16, `997E6BFC...F1B6` | `Kag_01 - Tetsu v16 Exact.tar.gz` | 16 seeds x 4 opponents x 2 seats = 128 |
| Kag_02 | Kaito v22, `62FB5A5F...147A` | `Kag_02 - Kaito v22 Price Impact.tar.gz` | 16 seeds x 4 opponents x 2 seats = 128 |

The exact source bytes are copied into tracked-path snapshots in this directory. Ray C45,
Boatlee v14, the other candidate, and frozen Fa04 G1 form each candidate's four-opponent pool;
the validator rejects a candidate alias or hash in its own opponent lane.

## Seed freeze

The pre-freeze collision scan enumerated repository evidence with `rg --files`, extracted JSON,
JSONL, and text seed observations, and expanded registered inclusive ranges. It found 1,692
distinct observed values with digest
`3A9183A27AC8484A5F45C055924B6A7778C9B7FEF8CC45C70F99AB82AB914CCC` and no value in any
new range.

The pre-reservation evidence scan excludes exactly these reservation-derived lifecycle prefixes:
`research/campaign_3000/06_candidates/`, `research/campaign_3000/07_release/`,
`research/campaign_3000/08_public_release/`, and `research/campaign_3000/09_audit/`. Those paths
repeat this frozen plan or its release/audit handoff and therefore cannot become retrospective
pre-reservation observations. Every other repository path remains in scope, so a newly added
prior-evidence file containing a reserved seed still fails validation.

- Kag_01: development `50000-50015`, confirmation `51000-51063`, robustness `52000-52031`.
- Kag_02: development `53000-53015`, confirmation `54000-54063`, robustness `55000-55031`.

All six ranges have `opened=false`, `consumed=false`, and `evaluated_games=0`. Development may
open only through the committed S -> E -> O authority protocol below after the separate auditor's
exact OPEN/PASS. Confirmation and robustness need their preceding strict gate plus a new exact
auditor OPEN/PASS and remain HOLD under the development receipt.

## Two different verdicts

The strict promotion gate is unchanged by upload timing: development, confirmation, and
four-scenario robustness must all pass the frozen aggregate, seed-cluster bootstrap, per-opponent,
runtime, and integrity thresholds.

Exploratory private SaveRun readiness is deliberately separate and is never a promotion claim.
After fresh development it requires all hard integrity checks, finite metrics, zero errors and
hidden abnormal statuses, runtime p99/max at most 25/30 seconds, direct candidate performance
against Fa04 G1 of at least `0.90` match score and `+10,000` mean margin, the exact license and
attribution package, and the final independent auditor release PASS. Confirmation and robustness
stay CLOSED in that path.

Tetsu's exact v16 payload is conditionally cleared only under
`research/campaign_3000/07_release/TETSU_IP_VERDICT.md` SHA-256
`DA876498...F721`: exact `main.py`, full Apache-2.0 `LICENSE`, and complete Tetsu/Boatlee/Flex/
Kakuteki/mrgrishninsb/common-route attribution are mandatory. The public `2703.1` observation is
V15, not evidence for v16. Kaito's exact v22 notebook/version/license mapping is pinned in the
candidate plan. Kaito's weak consumed local screen remains disclosed; fresh gates decide it.

## Clean two-stage S -> E binding

`execution_binding.json` freezes the future independent-auditor handoff without opening a seed.
At implementation commit S, `implementation_commit` must remain the explicit `PENDING` value;
only `binding --binding-mode implementation-freeze` accepts that placeholder. After S exists,
execution commit E must have exactly S as its sole parent and may change exactly one value on one
line in that one file: `implementation_commit` from `PENDING` to S's full lowercase Git SHA.

Execution-mode validation rejects a wrong parent, any other S-to-E file change, a dirty tracked
tree, manifest SHA/byte drift, and any current manifest input whose bytes differ from its S Git
blob. `execution_binding.json` is intentionally absent from the input manifest: including it would
make the one-line S-to-E binding self-referential and would force a second manifest change. The
validator instead proves the binding's S blob and E bytes differ only at that one value.

`lifecycle.json` is also intentionally manifest-excluded and is exact `CLOSED`/`PENDING` at S and
E. This does not weaken the S -> E invariant: E still changes only `execution_binding.json`.

## Executable development authority

The only OPEN transition is a third commit O whose sole parent is exact E and whose E -> O diff is
only `research/campaign_3000/06_candidates/lifecycle.json`. O must pin the byte count and SHA-256
of both the exact ignored receipt and the original `codex_app__read_thread` result exported with
`turnLimit=1`. The raw export must have the real `{schemaVersion, thread, page, turns}` shape,
thread id `019fb8b8-7758-7860-9304-39eb4f06c65c`, `kind=codex`, `hostId=local`, one clean
completed turn, and one `agentMessage` with `phase=final_answer`; its text must be the canonical
JSON decision. Manually invented metadata wrappers are rejected. The decision must bind
auditor task `019fb8b8-7758-7860-9304-39eb4f06c65c`, exact S and E commits, manifest, candidate
plan, engine, both candidate hashes, both seats, Kag_01 development `50000-50015`, Kag_02
development `53000-53015`, and an `OPEN` verdict for each. It must also hold every confirmation
and robustness range, hold every external action, and attest zero prior fresh games.

A naked `OPEN` string/boolean cannot authorize anything. After O, a second independent-auditor
`read_thread` export must review the exact O commit and pin the lifecycle, first raw export, and
authority-receipt hashes. Both `open`, `run`, and `gate` require that post-O verdict. Local code
cannot cryptographically prove a Codex export was not fabricated, so acquisition must be performed
by the user-owned task from the actual thread; the second auditor verdict is an explicit final
human/host trust boundary, not a claimed local signature. The validator still hard-rejects a
synthetic wrapper, wrong thread/turn/item, altered message, or missing second verdict.

`orchestrator.py run` is the only accepted reserved-seed runner. It first calls the full authority
gate, emits an immutable ignored run receipt containing the exact grid, cells, sources, authority
hashes, and child-runner argv, then invokes `authorized_runner.py`. The report gate requires that
run receipt and its SHA in both outer receipts; raw/synthetic runner output from any other path is
rejected. No current receipt, O, post-O verdict, or run receipt exists, so state remains CLOSED and
seed execution remains zero.

Immediately before and after the child run, the outer receipts measure the actually imported
`kaggle-environments` distribution and its package/core/utils/agent/Kaggriculture Python+JSON
dependency manifest, plus the live plan/gate/selection/scenario/runner/orchestrator/tool and source
hashes. Imported module paths must resolve to the selected distribution root. The three
start=end flags are derived from those measurements; they are never hard-coded receipt claims.
The runtime also requires `PYTHONPATH`, `PYTHONHOME`, `PYTHONSTARTUP`, `PYTHONINSPECT`, and
`PYTHONUSERBASE` to be absent or empty, and binds the package/core `make` callable identity,
globals, source path, AST/source hashes, and equality to the exact same-process `core.py` compile.

This is an explicit trusted-interpreter/process-memory boundary, not a sandbox proof. A privileged
host that mutates arbitrary module globals in memory after all measured startup checks is outside
what these receipts can cryptographically exclude. Such a host or interpreter compromise remains
a declared trust assumption; module/callable identity and startup-environment checks are hard
gates for the execution environment we control.
The live `kaggle_environments.make` callable must also be the exact `core.make` function, use the
core module globals and source path, and match a fresh compile of the pinned `core.py`; its
process-stable function-source and AST hashes are recorded in every runtime snapshot and raw row.
This blocks path shadowing and in-process callable replacement. The remaining explicit trust
boundary is the selected Python interpreter and host process memory itself; the evidence does not
claim cryptographic protection from an already-compromised interpreter or administrator.

Every raw row must preserve the official environment's full typed configuration and canonical
finite-JSON hash. The scrubbed configuration `seed` is exactly `null`, while the separately
resolved seed is an exact int-not-bool equal to the requested seed; `randomSeed` is forbidden.
Seed, seat, elapsed time, and both money values are type/finite checked without lossy coercion.
The hardened runner records its actual full-step abnormal-status scan in every row and recomputes
the mandatory summary counters. Strict promotion also applies nonnegative mean-margin floors to
every opponent in every phase and to every scenario in robustness, so aggregate gains cannot
average away a catastrophic lane.

## Read-only checks

```powershell
.\.venv\Scripts\python.exe research\campaign_3000\06_candidates\orchestrator.py validate
.\.venv\Scripts\python.exe research\campaign_3000\06_candidates\orchestrator.py binding --binding-mode implementation-freeze
# Only after the independent auditor creates E:
.\.venv\Scripts\python.exe research\campaign_3000\06_candidates\orchestrator.py binding --binding-mode execution
# Only after exact raw exports and lifecycle-only O:
.\.venv\Scripts\python.exe research\campaign_3000\06_candidates\orchestrator.py open --slot Kag_01 --phase development --authority-receipt dist\campaign_3000\authority\auditor_development_open.json --auditor-delivery dist\campaign_3000\authority\auditor_development_open.delivery.json --o-review-delivery dist\campaign_3000\authority\auditor_authority_o_review.delivery.json
.\.venv\Scripts\python.exe research\campaign_3000\06_candidates\orchestrator.py run --slot Kag_01 --phase development
.\.venv\Scripts\python.exe research\campaign_3000\06_candidates\orchestrator.py grid --slot Kag_01 --phase development
.\.venv\Scripts\python.exe research\campaign_3000\06_candidates\orchestrator.py grid --slot Kag_02 --phase development
.\.venv\Scripts\ruff.exe check research\campaign_3000\06_candidates\orchestrator.py research\campaign_3000\06_candidates\test_execution_binding.py tests\test_campaign_3000_candidate_freeze.py
.\.venv\Scripts\python.exe -m pytest -q research\campaign_3000\06_candidates\test_execution_binding.py tests\test_campaign_3000_candidate_freeze.py
```

`orchestrator.py open` raises while the lifecycle is CLOSED and for every confirmation,
robustness, or external-action request. Its report gate entrypoint requires a
raw report, the runner pre-run receipt, and separate outer started/completed receipts. It rejects
missing/extra/duplicate cells, wrong seeds/seats/opponents/scenarios, source/config/environment or
runner hash drift, non-finite values, non-DONE statuses, and errors hidden before terminal DONE.
