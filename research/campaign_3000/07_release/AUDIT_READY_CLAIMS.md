# Audit-ready claim list

Every `PASS` below is local and hash-scoped. External actions are `HOLD`.

| Claim | State | Evidence boundary |
|---|---|---|
| Tetsu `main.py` exact identity | PASS | SHA-256 `997E6BFC...710F1B6` |
| Kaito `main.py` exact identity | PASS | SHA-256 `62FB5A5F...57147A` |
| Full Apache-2.0 text included | PASS | member hash equals pinned license hash |
| Required attribution/notices included | PASS | marker tests plus exact attribution member hash |
| Archive member order/metadata fixed | PASS | `main.py`, `LICENSE`, `ATTRIBUTION.md`; USTAR; mode 0644; uid/gid/mtime 0 |
| Rebuild byte determinism | PASS | independent local output roots compare byte-for-byte |
| Wrapper payload identity | PASS | embedded archive and all member hashes checked before write |
| Private metadata | PASS | `is_private=true`, `enable_internet=false` |
| No wrapper network/push/submit logic | PASS | AST import allowlist and forbidden-token tests |
| Two package payloads distinct | PASS | archive hashes must not collide |
| Raw notebook to exact `main.py` extraction | PASS | tracked GetKernel envelope plus archived notebook hash and extraction cell/method |
| Candidate page Apache labels | PASS | tracked live Jina bodies, URLs, retrieval times, byte counts, and SHA-256 pins |
| Tracked post-run evidence integrity | PASS | pinned production validator replays exact receipt/raw/summary/gate chain; 256 fresh games |
| Kag_01 strict development result | PASS | 128 cells, integrity `PASS`, strict verdict `PASS`, lifecycle `CONSUMED_PASS` |
| Kag_02 strict development result | NO_GO | 128 cells, integrity `PASS`, strict verdict `NO_GO`, lifecycle `CONSUMED_NO_GO` |
| Kag_02 package-only exploratory screen | PASS / AUDITOR PENDING | `EXPLORATORY_PACKAGE_GATE_PASS_NON_PROMOTION_AUDITOR_RELEASE_PENDING`; no promotion/champion/confirmation/robustness/submission claim |
| Private-material payload scan | PASS | tar members, notebook, metadata, prepush, and manifest reject local paths, username encodings, and credential markers |
| Final Git commit containment | PENDING | local receipt says `PENDING_FINAL_GIT_FREEZE`; requires separate post-freeze receipt |
| Independent-auditor exact private SaveRun release | PENDING | a new exact per-slot auditor `PASS` is required; package readiness is not release |
| Tetsu artifact-native SPDX | NOT CLAIMED | page license plus exact-source mapping is an explicit inference |
| Tetsu v16 public score | PENDING | later page shows remote `3097.4 V16`; not local reproduction and requires independent-auditor confirmation |
| Kaito fresh local promotion | REJECTED / NOT CLAIMED | strict local development `NO_GO`; `2957.6 V2` remains captured remote page evidence only |
| Kaggle kernel slug availability | PENDING | check only immediately before an authorized push |
| Private Save & Run success | NOT RUN | no authorization and no external action performed |
| Downloaded output hash match | PENDING | requires an authorized private Save & Run |
| Competition submission/publication | NOT RUN | explicitly excluded |

Machine-readable evidence is emitted in each candidate's `prepush.json` and in
`local_build/release_manifest.json`.
