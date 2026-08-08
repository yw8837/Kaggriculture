# Local private-release packaging

This directory builds two deterministic, local-only payloads:

- `Kag_01 - Tetsu v16 Exact.tar.gz`
- `Kag_02 - Kaito v22 Price Impact.tar.gz`

Run from the campaign workspace root:

```powershell
.\.venv\Scripts\python.exe research\campaign_3000\07_release\build_release.py
```

The ignored `local_build/` directory receives each archive, a private
Save & Run notebook, `kernel-metadata.json`, `prepush.json`, and a root release
manifest. The builder performs no Kaggle/API/network operation. It does not
push, run, submit, or publish anything.

Both exact `main.py` inputs, the complete Apache-2.0 `LICENSE`, source snapshot
receipt, tracked official GetKernel response envelopes, raw official notebook
sources, and later candidate-page license captures are hash-pinned in this
worktree. The earlier cutoff page hashes remain timestamped attestations because
their bodies were not archived. The tracked post-run bundles are never copied
into the Kaggle payload. The builder reruns the pinned production result
validator over their receipts/raw rows and rejects local paths, usernames, or
credential markers in every payload member and generated release file.

The default build honestly records `PENDING_FINAL_GIT_FREEZE`. After a clean
tracked commit exists, rebuild with `--final-freeze-commit <exact HEAD>` and
then run `--verify-only --final-freeze-commit <exact HEAD>`. Final mode requires
the exact clean HEAD, proves every tracked release input byte-exact at that
commit, and deterministically rebuilds the complete output before accepting a
receipt. A later HEAD or altered output is rejected as stale.

Every generated local receipt has `external_action_gate.status=HOLD`.
`Kag_01` has a tracked strict development `PASS`. `Kag_02` has a tracked strict
`NO_GO`; only its performance-screen/package boundary may be described as
`EXPLORATORY_PACKAGE_GATE_PASS_NON_PROMOTION_AUDITOR_RELEASE_PENDING`.
It is not promotion, champion, confirmation, robustness, or competition-submit
evidence. An independent-auditor exact per-slot private SaveRun release and the
final Git freeze remain mandatory before any external action. Only a later
separate auditor release may use
`EXPLORATORY_PRIVATE_SAVERUN_READY_NON_PROMOTION` for `Kag_02`.

Before any separately authorized external action, inspect
`IP_RULES_PROVENANCE.md`, `AUDIT_READY_CLAIMS.md`, the pinned
`TETSU_IP_VERDICT.md`, and the generated `prepush.json` files. After a private
Save & Run, the resulting archive must be downloaded and compared to the local
archive SHA-256 before any further decision.
