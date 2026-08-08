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
their bodies were not archived. Commit containment remains
`PENDING_FINAL_GIT_FREEZE`; a separate post-freeze receipt must prove it. The
builder does not depend on ignored `dist/` or `references/` inputs.

Every generated local receipt has `external_action_gate.status=HOLD`. Exact
development PASS results, an independent-auditor exact private SaveRun release
PASS, and the final Git freeze are mandatory before any external action.

Before any separately authorized external action, inspect
`IP_RULES_PROVENANCE.md`, `AUDIT_READY_CLAIMS.md`, the pinned
`TETSU_IP_VERDICT.md`, and the generated `prepush.json` files. After a private
Save & Run, the resulting archive must be downloaded and compared to the local
archive SHA-256 before any further decision.
