# Campaign 3000 independent-auditor handoff draft

Verdict: `HOLD_PENDING_EXACT_FREEZE_AND_SEPARATE_AUDIT`.

This package is an internal evidence handoff to the separate user-owned auditor task
`019fb8b8-7758-7860-9304-39eb4f06c65c`. It is not an independent-auditor verdict. The author is
an in-tree subordinate evidence packager and claims no authority to open further seeds, push a
second SaveRun, submit, or publish. It records two already authorized private SaveRuns; it does
not authorize any new external action.

## Freeze boundary

Git HEAD is still changing, so the machine handoff intentionally keeps all exact freeze fields at
`PENDING_FREEZE`:

- `freeze.start_git_head`
- `freeze.end_git_head`
- `freeze.implementation_commit`
- `freeze.execution_commit`
- `freeze.remote_ref`
- `freeze.tracked_status`
- `pending_bindings[candidate_execution_binding].sha256`

The pending binding path is
`research/campaign_3000/06_candidates/execution_binding.json`. Draft verification requires the
placeholders. The tracked 09 template is frozen in implementation commit S and must remain
unchanged in execution commit E. Final values live only in ignored
`dist/campaign_3000/audit_handoff_final.json`. Final verification requires 40-hex commits,
`start_git_head=S`, `end_git_head=E`, remote-ref equality to E, a clean worktree, current HEAD equal
to E, an exact hash-matched execution binding, and exactly that binding path as the S-to-E diff.

## Research populations and provenance limits

| Population | Observed evidence | Exact boundary |
|---|---:|---|
| Our submissions | 22 submissions; 1,017 episode-metadata rows; 44 selected unique raw replays | Authenticated API snapshot at `2026-08-08T17:50:15.385Z`; historical uploaded bytes remain unverified |
| Leaderboard top 25 | 25 rows; 4,166 episode-metadata rows; 45 selected unique raw replays | First 25 official API rows at the same snapshot; no private-strategy inference |
| Public Code | 155 refs, pages `100 + 55 + 0`; 0 failed rows | Current ref/version population; 61 source calls succeeded and 94 were rate-limited; public code was not executed |
| Discussions | 57 topics, pages `20 + 20 + 17 + 0`; 0 failed rows | Declared total plus terminal empty page, deduplicated by topic ID |
| GitHub | 256 rows | Union of saved repository and issue/PR query families, not exhaustive GitHub coverage |
| Models | 1 search row; 1 current v8 model statically analyzed | Four published files were inventoried and the 6,431-byte checkpoint was inspected without unpickling. The published 10→64→4 interface is incompatible with its checkpoint and lacks a Kaggriculture encoder/action decoder, so it is unused. No official competition filter exists; population remains `UNVERIFIED_NOT_ZERO_CLAIM`. |
| External methods | 35 retained sources from 28 query events | 31 `VERIFIED`, 1 `VERIFIED_LIMITED`, 3 `VERIFIED_LOCAL`; diminishing-return stop, not exhaustive internet coverage |

The replay integrity report rehashed all 89 selected raw replays: 44 from our submission cohort and
45 unique leaderboard episodes. It recorded zero failures. The public-source negative lineage scan
is not proof of absence: 94 of 155 current source requests were rate-limited, and generated or
compressed schedules may evade literal AST extraction.

## Tool and skill evidence

| Tool or skill | Status | Claim boundary |
|---|---|---|
| Agent-Reach | `EXECUTED_READ_ONLY_WITH_LIMITS` | Doctor and saved queries ran; X/Reddit unavailable; Exa later hit 429 |
| Insane Search | `EXECUTED_ONE_BLOCKED_URL_REPRO_FAILED` | One Kore URL returned empty extracted text and supplied no retained mechanism |
| Context7 | `EXECUTED_READ_ONLY` | Official Kaggle CLI and SciPy assignment documentation were queried |
| Serena | `EXECUTED_READ_ONLY_WITH_STATE_LIMITATION` | Collector and market-MPC symbols were inspected; initial stdio project state did not persist |
| `oh-my-claudecode:autoresearch` | `EXECUTED_SELECTION_ONLY_NON_PROMOTION` | Produced a selection-readiness result; remote `2927.4` was not a local result |
| `oh-my-claudecode:self-improve` | `NOT_EXECUTED_MANDATORY_TRUST_GATE` | No autonomous self-modification result is admitted before the exact frozen state passes separate audit |

The 03 lane explicitly says it did not run self-improve and cannot proxy-claim another lane's skill
use. The exact status above preserves that trust boundary.

## Candidate decision and adverse evidence

### Kag_01 — Tetsu v16

- Exact source SHA-256:
  `997E6BFC5234534E246E945BC61C87858EBF997AB85B0A5C9427DD4ED710F1B6`.
- Consumed 1.32.6 screen: 64 games, 62 wins, 2 losses, match score `0.96875`, mean margin
  `+3314.28125`, zero failures.
- Against exact public Fa04 G1: 16/16 wins, mean margin `+25621.375`.
- Rationale: strongest consumed five-agent screen plus a separate conditional IP path.
- Fresh sealed development: 128 valid games, 122 wins and 6 losses, match score `0.953125`,
  seed-cluster bootstrap 95% interval `[0.90625, 1.0]`, mean margin `+7623.484375`; strict `PASS`.
- Private SaveRun version 1 is `COMPLETE_VERIFIED`; the downloaded remote archive is byte-exact
  with approved SHA-256 `184F687C474933A7215DB97E8C5A5F823AE79233EEA42D04B70EABC001BF9E16`.

Limits: these are consumed, promotion-ineligible seeds. The cutoff `2703.1` observation is v15,
not exact v16. A later tracked live page displays `3097.4` for v16, but its claim gate is pending
independent-auditor confirmation and it is not a local result, promotion result, or forecast. The
release spec still makes no public v16 score claim. The 9,297-byte route is shared derivative
lineage, not clean-room work.

### Kag_02 — Kaito v22 price impact

- Exact source SHA-256:
  `62FB5A5F66F0011092A2B51E3192879BA583D5D815D761F176091C615657147A`.
- Consumed 1.32.6 screen: 64 games, 14 wins, 50 losses, match score `0.21875`, mean margin
  `-3232.6875`, zero failures.
- Against exact public Fa04 G1: 16/16 wins, mean margin `+24159.25`.
- Rationale: exact notebook/version/license/remote-score mapping and route-lineage diversity.
- Fresh sealed development: 128 valid games, 32 wins and 96 losses, match score `0.25`, bootstrap
  interval `[0.25, 0.25]`, mean margin `+2185.140625`; strict `NO_GO`.
- Private SaveRun version 1 is `COMPLETE_VERIFIED` only as
  `EXPLORATORY_PRIVATE_SAVERUN_READY_NON_PROMOTION`; it is not promotion evidence.

Adverse evidence must stay visible: Ray beat Kaito 14-2 in the consumed addendum. Kaito was chosen
for mapping quality and diversity, not because it had the stronger local screen. Remote `2957.6 V2`
is context only, not fresh promotion evidence or a forecast.

### Ray fallback and public separation

Ray C45 is a hash-pinned fallback/opponent at
`6CC3B69E487052A8DEDC1A90D0D1296BA38577349E8D3BA8147E583605378F73`.
Its 64-cell consumed screen was 30-34 with mean margin `+7126.96875`; its C45 docstring conflicts
with an embedded `C64_HORIZON25` marker.

The public draft source is exact Fa04 G1 at
`81159A18DF3CD1A5CAABE5EDBBA0A597561775F77A49465FA39DF6802A706922`.
It lost all 80 games in the five-agent screen and all 16 direct games against each designated
private source. This proves only exact local separation on selected consumed seeds. The exact
public source has no claimed or expected rating, and historical score `1317.1` is not mapped to
these bytes.

## Post-run seed lifecycle

| Slot | Phase | Range | Count | State |
|---|---|---:|---:|---|
| Kag_01 | development | 50000–50015 | 16 | `CONSUMED_PASS`, 128 games |
| Kag_01 | confirmation | 51000–51063 | 64 | `CLOSED`, unopened, unconsumed, 0 games |
| Kag_01 | robustness | 52000–52031 | 32 | `CLOSED`, unopened, unconsumed, 0 games |
| Kag_02 | development | 53000–53015 | 16 | `CONSUMED_NO_GO`, 128 games |
| Kag_02 | confirmation | 54000–54063 | 64 | `RETIRED_UNUSED`, 0 games |
| Kag_02 | robustness | 55000–55031 | 32 | `RETIRED_UNUSED`, 0 games |

The preregistration collision scan reserved 224 disjoint seeds while all pools were closed. The
audited development opening then consumed exactly 256 games: 128 per candidate. The exact close
lifecycle is `DEVELOPMENT_CLOSED` at
`3A535E485F1B14870E03380D3672F3CD899051A45F3EB4B9FB4D5094F7B2785D`. Kag_01 later pools
remain `CLOSED/HOLD`; Kag_02 later pools are `RETIRED_UNUSED/HOLD`. No further seed authority is
created by this handoff.

## Tetsu conditional IP terms

The exact verdict is `CONDITIONAL_PASS_PRIVATE_SAVERUN_ONLY`, not legal advice and not authority
for a Kaggle call. Every condition is blocking:

1. `main.py` remains byte-exact at `997E...F1B6`; any edit reopens review.
2. The archive includes the complete Apache-2.0 `LICENSE`.
3. `ATTRIBUTION.md` preserves Tetsu, Boatlee, Flex, Kakuteki, mrgrishninsb, public V23,
   frontier-cleanup, exact refs/hashes, and common-route hash
   `EDC3163ED477B6F9EF70FA8F7A212A4F8179C4FA281008D400EDF6EE488906C2`.
4. Notebook metadata remains `is_private=true` and `enable_internet=false`.
5. The wrapper only emits the prebuilt payload; it cannot submit, publish, access the network,
   rebuild, or alter the agent.
6. Pre-push checks confirm members and hashes, compile `main.py`, prove deterministic rebuilds,
   and show zero external actions.
7. Any mismatch, missing notice, later license contradiction, or v15-as-v16 score claim returns the
   verdict to `HOLD`.

The artifact-specific license conclusion is explicitly a page-level Apache-2.0 plus exact
source/extraction mapping inference. No artifact-native SPDX statement is claimed. The cutoff page
digest is only a timestamped attestation because its body was not archived. A later tracked page at
`7247E047A8CE43BE59DAB9886DED9A5B8832E3D14F69925A1894A3B5EEC5B19B` is locally
hash-verifiable and displays Apache-2.0; the auditor must not silently treat it as the missing cutoff
body.

## External-action boundary

Observed external actions: **2**, both private SaveRuns. Kag_01 and Kag_02 version 1 are
`COMPLETE_VERIFIED` in `11_saverun_results/remote_receipts.json`; both are private,
internet-disabled, and their remote archives equal the approved local bytes. Kag_02 remains
exploratory/non-promotion. The read-only competition-submission snapshot remained exactly 22, so
neither SaveRun created a competition submission. No publication or browser-control action was
observed. The separate auditor task's release, postrun, and publication-HOLD final messages are
preserved with exact thread/host/turn/item identity and canonical UTF-8 text hashes in
`11_saverun_results/auditor_deliveries.json`; the latest publication verdict remains `HOLD`.

If later authorized and freshly audited, the fixed public action order is:

1. Discussion: `Kaggriculture Strategy | Replay Agents, Sell Guards & Engine Drift`.
2. Kaggle Code: `Kaggriculture Agent | Fixed Trace + Safe Selling`.

Both actions are disabled now. Competition submission is separately
`FORBIDDEN_ABSENT_EXACT_USER_PHRASE`. No exact authorizing phrase has been observed; inference,
paraphrase, private Save & Run authority, Code push authority, or publication authority cannot be
treated as competition-submission authority.

## Current QA claims

Pinned command-output claims are 489 project tests at the final private-package freeze, 493
project tests after the SaveRun/publication evidence update, 81 official-environment tests,
91 candidate-freeze tests before post-run close, 38 private-release
tests, 10 public-release tests, and 4 focused SaveRun-receipt tests, with scoped Ruff passing.
These strings are not a self-authenticating CI attestation; remote CI check count remains zero.

## Hash anchors

| Anchor | SHA-256 |
|---|---|
| `01_internal/evidence_manifest.json` | `4A07D2AFAC7EE2F99C223AC5B4D35C07CA325363C25441109976917E1D6AE6E6` |
| `02_public_meta/source_manifest.json` | `4080781AEBA0B088197CDD0B38651E0D7044AAD45C9552586A5795A2931CE86F` |
| `03_external/manifest.json` | `1D2578AB7BCB44AEB9E740F874832F83CC96E4F97B758835DBC5967C17CBE893` |
| `04_synthesis/autoresearch_portfolio_result.json` | `4B289DF099A6BCAA6747B1DF3F2A3F83B587FD117C6EB7C979A60C1762A6C9C9` |
| `05_engine_screen/manifest.json` | `A819E229B8FA101730B759AE30B224D692944129B55E7A3B1BEA44ACBDC70D48` |
| `05_engine_screen_ray_c45_addendum/manifest.json` | `2449F4A771CA0F8716AE1EFCE05FB8842D310BD381895C14F162EF1DC9B812D9` |
| `06_candidates/manifest.json` | `1A2765982DB4FD3EC648BD9A68CC4F331761BF100E63950E02F57463BCCBCA9C` |
| `06_candidates/lifecycle.json` | `3A535E485F1B14870E03380D3672F3CD899051A45F3EB4B9FB4D5094F7B2785D` |
| `07_release/release_spec.json` | `662937F95BF52BB3E765C14F14A36681FC82AE1D7A49EBF58280550B7C0DCC2D` |
| `07_release/evidence/raw/RECEIPT.json` | `B3F54DDD8C888665C8755B806F10094F999C63E3409130587FD94C2982759772` |
| `07_release/local_build/release_manifest.json` | `F99D31D750E1D4EAF26127308C720A6BD042E32CA3F05AFC16CDB6182925F224` |
| `07_release/verification/VERIFICATION.md` | `577F47A9E4C9276D2579C49F2FC3F934A82B2C08DBA620D91E33CCA2F332A39D` |
| `08_public_release/SHA256SUMS` | `D78D451382D9E6361C508805691B00B7070114572E4D7AD324C1E140D5A75B1E` |
| `08_public_release/release_manifest.json` | `855A4E297305AA2B3F6BB6B816DA7F1140AEEEB15903C80197576A52054EBA72` |
| `08_public_release/artifact/kaggriculture_fixed_trace_safety_baseline.tar.gz` | `5DBD64463878A52ED7C47C8D60BCA3AE9FAC7E29B775E7FADB08F0CC7670A8B6` |
| `10_results/kag_01_development/evidence_manifest.json` | `712DEBADB1BAE4247687B788A1986AB2B90DF32A52F390AB2BBD5213A5A2B09A` |
| `10_results/kag_02_development/evidence_manifest.json` | `F9E9C7629B6EA95D989712D1F8ED685835DC8120D31292FD51B33E414F82FD7D` |
| `11_saverun_results/auditor_deliveries.json` | `E6DBF2F0656FF71FE63CDF050635896367D2C844F554A8EE4A37DCC6DFBED972` |
| `11_saverun_results/remote_receipts.json` | `B5D361741F193CB1AA72194090B9AFB3C6825278541E02C82874300EE2922871` |
| `06_candidates/execution_binding.json` | `PENDING_FREEZE` |

The machine handoff records 57 exact evidence files with byte counts and SHA-256 values. The
verifier rehashes each file and also checks child hashes against the 01/02/03/05/06 source
manifests or sidecars and the 08 checksum list where available.

## Auditor challenge list

- Recompute all hashes from the frozen commit; do not trust this report's framing.
- Recheck API pagination, repair provenance, unavailable platforms, and negative-scan limits.
- Challenge the Tetsu page-license-to-cell mapping, including the unarchived cutoff body versus the
  later tracked page, and every lineage notice.
- Recheck all 256 development games, both gate verdicts, and the closed/retired later pools.
- Recheck both private SaveRun COMPLETE receipts, exact remote archives, and submission count 22.
- Treat Kaito's weak screen and Ray's 14-2 result as material adverse evidence.
- Scan public bytes for private-source leakage and enforce Discussion before Code.
- Keep Discussion and public Code HOLD until a separate exact publication verdict.
- Reject competition submission unless the exact authorizing user phrase is recorded.

## Verification commands

Draft state:

```powershell
.\.venv\Scripts\python.exe research\campaign_3000\09_audit\verify_handoff.py
```

Final frozen state only:

```powershell
.\.venv\Scripts\python.exe research\campaign_3000\09_audit\verify_handoff.py `
  --final `
  --final-state dist\campaign_3000\audit_handoff_final.json
```

The ignored overlay must contain the tracked template hash, exact S/E/remote fields, clean status,
and exact execution-binding hash. `--final` is expected to fail until E exists and the remote ref is
equal to E. It never requires or permits replacing the tracked template placeholders after S.
