# Campaign 3000 independent-auditor handoff draft

Verdict: `HOLD_PENDING_EXACT_FREEZE_AND_SEPARATE_AUDIT`.

This package is an internal evidence handoff to the separate user-owned auditor task
`019fb8b8-7758-7860-9304-39eb4f06c65c`. It is not an independent-auditor verdict. The author is
an in-tree subordinate evidence packager and claims no authority to edit production code, open
seeds, push, Save & Run, submit, or publish.

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
| Models | 1 search row | No official competition filter; population remains `UNVERIFIED_NOT_ZERO_CLAIM` |
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

## All candidate seed pools are CLOSED

| Slot | Phase | Range | Count | State |
|---|---|---:|---:|---|
| Kag_01 | development | 50000–50015 | 16 | `CLOSED`, unopened, unconsumed, 0 games |
| Kag_01 | confirmation | 51000–51063 | 64 | `CLOSED`, unopened, unconsumed, 0 games |
| Kag_01 | robustness | 52000–52031 | 32 | `CLOSED`, unopened, unconsumed, 0 games |
| Kag_02 | development | 53000–53015 | 16 | `CLOSED`, unopened, unconsumed, 0 games |
| Kag_02 | confirmation | 54000–54063 | 64 | `CLOSED`, unopened, unconsumed, 0 games |
| Kag_02 | robustness | 55000–55031 | 32 | `CLOSED`, unopened, unconsumed, 0 games |

The collision scan reserved 224 seeds, found no collision, and recorded
`fresh_games_executed=0`. No pool opens without that phase's exact independent-auditor OPEN/PASS;
confirmation and robustness also require the preceding strict gate.

The exact lifecycle is `CLOSED`/`PENDING` at
`839CD70EE519C7220697500747D0EFBD2D801580E0F3132F1E56A00D82E88E6A`. The authority receipt,
raw auditor OPEN delivery, and post-O auditor-review delivery are all absent. After exact S and E,
only a lifecycle-only O commit may pin the first two files, and execution also requires the separate
post-O review. Local checks can reject malformed or mismatched exports but cannot cryptographically
prove a `read_thread` export was not fabricated; acquisition from the user-owned auditor task and
the post-O verdict remain an explicit human/host trust boundary. No gate has opened and no reserved
seed has run.

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

Observed external actions: **0**. The local release and public-release receipts record no Kaggle
push, Save & Run, submission, publication, or browser control.

If later authorized and freshly audited, the fixed public action order is:

1. Discussion: `Kaggriculture Strategy | Replay Agents, Sell Guards & Engine Drift`.
2. Kaggle Code: `Kaggriculture Agent | Fixed Trace + Safe Selling`.

Both actions are disabled now. Competition submission is separately
`FORBIDDEN_ABSENT_EXACT_USER_PHRASE`. No exact authorizing phrase has been observed; inference,
paraphrase, private Save & Run authority, Code push authority, or publication authority cannot be
treated as competition-submission authority.

## Hash anchors

| Anchor | SHA-256 |
|---|---|
| `01_internal/evidence_manifest.json` | `4A07D2AFAC7EE2F99C223AC5B4D35C07CA325363C25441109976917E1D6AE6E6` |
| `02_public_meta/source_manifest.json` | `5A6EDF659C7F8C9B0C999535F42513BC7C55D7CC231FBF5543FF66888CF8EE1B` |
| `03_external/manifest.json` | `1D2578AB7BCB44AEB9E740F874832F83CC96E4F97B758835DBC5967C17CBE893` |
| `04_synthesis/autoresearch_portfolio_result.json` | `4B289DF099A6BCAA6747B1DF3F2A3F83B587FD117C6EB7C979A60C1762A6C9C9` |
| `05_engine_screen/manifest.json` | `A819E229B8FA101730B759AE30B224D692944129B55E7A3B1BEA44ACBDC70D48` |
| `05_engine_screen_ray_c45_addendum/manifest.json` | `2449F4A771CA0F8716AE1EFCE05FB8842D310BD381895C14F162EF1DC9B812D9` |
| `06_candidates/manifest.json` | `FBF560F617788022552B2115023639F81CB49E01E67B90AACE2291DA72DECE69` |
| `06_candidates/lifecycle.json` | `839CD70EE519C7220697500747D0EFBD2D801580E0F3132F1E56A00D82E88E6A` |
| `07_release/release_spec.json` | `BBE3B7DA2C14B5C4DD752AE67C55FD1898E1B9DF613162DA7FCAEC32009680F4` |
| `07_release/evidence/raw/RECEIPT.json` | `B3F54DDD8C888665C8755B806F10094F999C63E3409130587FD94C2982759772` |
| `07_release/local_build/release_manifest.json` | `DCF7C3CD881941386480746D7BF1F505BF0F067D3021D8274B613861D48B7625` |
| `07_release/verification/VERIFICATION.md` | `33A771C1C607E8437BF43CF8121FF10C9F759927AD5AFAF41E63835E5D333E58` |
| `08_public_release/SHA256SUMS` | `D385449E9A35B4A49043DCADC5B43BD94F9522C4F5832255D0D422C3ACA83B9C` |
| `08_public_release/release_manifest.json` | `82560413B968544B03038868AC2B2C61C825E37571FB3B23EA6560C3A2AF1F9C` |
| `08_public_release/artifact/kaggriculture_fixed_trace_safety_baseline.tar.gz` | `2730084026B6C0EA68D1D54FF469E1B80D9ABF9BEF43285B15366CF13CF8ACCB` |
| `06_candidates/execution_binding.json` | `PENDING_FREEZE` |

The machine handoff records 52 exact evidence files with byte counts and SHA-256 values. The
verifier rehashes each file and also checks child hashes against the 01/02/03/05/06 source
manifests or sidecars and the 08 checksum list where available.

## Auditor challenge list

- Recompute all hashes from the frozen commit; do not trust this report's framing.
- Recheck API pagination, repair provenance, unavailable platforms, and negative-scan limits.
- Challenge the Tetsu page-license-to-cell mapping, including the unarchived cutoff body versus the
  later tracked page, and every lineage notice.
- Confirm all six pools are still unopened, all three authority artifacts are absent, and the final
  execution binding is exact.
- Treat Kaito's weak screen and Ray's 14-2 result as material adverse evidence.
- Scan public bytes for private-source leakage and enforce Discussion before Code.
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
