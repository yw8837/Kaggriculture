# Kaggriculture public Code / Discussion / Models / GitHub inventory

Status: internal research evidence, **not** an independent-auditor verdict.  Future production names are `Kag_01`, `Kag_02`, ...; every `Fa_*`, `Ge_*`, or `bot_*` name below is historical evidence only.

## Observation window and population boundaries

- Collection started `2026-08-08T18:03:31.941559Z` and finished `2026-08-08T18:08:30.740192Z`.
- Code population: every ref returned by official `kernels_list(competition="kaggriculture", sort_by="dateRun")` through the first empty page.  Pages were 100, 55, 0; 155 refs remained after ref deduplication.  The collector fetched the **current version** and source of every ref: 155 rows, 0 source failures.
- Discussion population: every topic returned by the official competition topic API, through both the declared total and an empty page.  Pages were 20, 20, 17, 0; 57 unique topic IDs and full message trees were fetched.
- Models boundary is weaker: official `kaggle models list` has no competition filter. Text search found one model whose name contains Kaggriculture; the competition Models UI search showed no additional result. This is `UNVERIFIED`, not a claim that the competition has exactly one model.
- GitHub population: union of three repository searches through the API cap, plus issue/PR search and the exact official balance PR. Search totals were 161, 114, 34 repositories before union/deduplication and 93 issue/PR hits. The saved union contains 162 repositories, 90 pull requests, 3 issues, and the separately enriched official PR.
- Everything was read-only. Public notebooks and downloaded Python were **not executed**. Page scores, logs, and notebook claims are recorded as remote claims unless a local static check is explicitly named.

## Frozen inventories

| Artifact | Rows | Bytes | SHA-256 |
|---|---:|---:|---|
| `code_inventory.jsonl` | 155 | 328,991 | `E510D00AB0AFB35E06B90EFD8EB8CC96DA08F29D8398DF682CDDDD060A7BEEC1` |
| `discussion_inventory.jsonl` | 57 | 43,333 | `8A296AE0C70728883FA9A2506B263DA3A3907678F03FCAB5D2357DF6B348B767` |
| `model_inventory.jsonl` | 1 `UNVERIFIED` search hit | 485 | `6807E5AC0DB8B02EBE5BFF62AC764454A5CD208C3F6C8A2666934C61F8C8D60E` |
| `github_inventory.jsonl` | 256 | 196,404 | `F0C4FDE4978D196B02A94EBB9DDAA3D03C31C7A22B78928D9B417344FCB30D87` |
| `query_log.json` | query/page/tool receipts | 35,530 | `EF4247B7915DBD544C21A68D3DEA18AAA7D60E63288B7C49E454B6287CF92AAF` |

The 155 Code rows are unique by `ref`; each row pins current version, numeric ID, source SHA/bytes, metadata SHA, title, author, votes, last-run time, URL, notebook/script parse status, and—when the remote page exposed it—best score/version and license. Of 155 current pages, 67 explicitly exposed Apache-2.0 and 88 remain license `UNVERIFIED`. One ref returned by the competition listing, `aanaakaliil/notebook858a103738`, no longer carried `competitionDataSources` in its current metadata; the population inclusion is therefore tied to the saved list-page receipt. Do not copy from an `UNVERIFIED` row merely because it is public.

## Current public score frontier

These are the current Notebook page scores captured in the window, not independently reproduced local scores.

| Page score | Ref / current version | Votes | License | Current source SHA prefix |
|---:|---|---:|---|---|
| 2957.6 | `kaitofukami/44-46-strict-future-top-30-v22-price-impact` v2 | 99 | Apache-2.0 | `BE57F757AAAA` |
| 2927.4 | `raykkretzschmar/kaggriculture-rank-your-agent` v10 | 9 | Apache-2.0 | `C9D5EB18E836` |
| 2755.9 | `anasriaz/kaggriculture` v2 | 40 | Apache-2.0 | `4F5C4E0E472C` |
| 2753.4 | `kaitofukami/159-160-vs-frontier-v20-weed-slip-recovery` v2 | 72 | Apache-2.0 | `FDE3B799DF21` |
| 2636.1 | `andrewsokolovsky/kaggriculture` v11 | 12 | Apache-2.0 | `C5ACAEB64680` |
| 2530.5 | `kaitofukami/41-49-future-unseen-v19-replication-to-control` v1 | 18 | Apache-2.0 | `777DC0E9B5E5` |
| 2517.1 | `ravi123a321at/177-180-fresh-top-30-v21-1-conditional-memory` v1 | 1 | Apache-2.0 | `814D9A1F008E` |
| 2491.7 | `web3cainiao/kaggriculture-v21-tactical-memory` v2 | 6 | Apache-2.0 | `7213C8738280` |
| 2477.0 | `boatlee/v13-r3-top-meta-order-safe-premium-control` v5 | 13 | Apache-2.0 | `8D9EB13340C3` |
| 2440.2 | `navazshfathi/notebook76f6a59396` v1 | 2 | Apache-2.0 | `EB1A230E8265` |
| 2414.6 | `dimong4/kaggriculture` v5 | 5 | Apache-2.0 | `D5079E518E2D` |
| 2391.0 | `romantamrazov/kaggriculture-hamburger` v23 | 123 | Apache-2.0 | `21B03BAB1B34` |
| 2346.6 | `prvsiyan/kaggle-frontier-lab-strategy-improvement` v7 | 56 | Apache-2.0 | `49AE3D628B16` |
| 2332.1 | `navazshfathi/177-180-fresh-top-30-v21-1-conditional-memory` v2 | 2 | Apache-2.0 | `8FD23E9C1068` |
| 2270.5 | `llccqq624/kaggriculture-top-5-meta-ensemble` v2 | 7 | Apache-2.0 | `64C4534E0F2E` |
| 1956.0 | `kaitofukami/v15-top5-robust-market-gate` v1 | 2 | Apache-2.0 | `902DB4FB52F8` |
| 1935.6 | `debmalya84/kaggriculture-route-refresh-price-impact` v5 | 0 | Apache-2.0 | `27F3164D51BD` |

The highest captured score below these was 1461.7. Scores can change after this snapshot.

## Actual output inspection, separate from Notebook claims

For every current page-score row at or above 1900, plus the current `fleongg/...2830-4...` page whose score was not exposed to the reader, the exact current Kernel output was downloaded. Results:

- 18/18 output downloads succeeded; 89 files, 9,533,154 bytes.
- Exact manifest: `kernel_output_manifest.jsonl`, 61,163 bytes, SHA `F72D9C5FECB8CA4213BBE07F76E5549C1FE1923C3655918E72C43C45CD5359AA`.
- Version/source/license join: `kernel_output_provenance.jsonl`, 15,325 bytes, SHA `43B4DF2E2E36551373F04A78E8310C1311C82F94931C6FF16A25EE18414CC3B0`; it binds every output receipt to the exact Code ID/current version/source hash observed immediately before the output scan.
- 18/18 deployed `main.py` files parsed with Python AST. No imported public module and no public agent call was executed.
- Static result: `kernel_static_analysis.jsonl`, 24,427 bytes, SHA `BD4AF58185A718F436756093F0C2713831A5632B30C7BAA8F3D9F627E39CE256`.
- Three byte-identical deployed-agent clone groups were found:
  - `62FB5A5F...`: the 2957.6 Kaito v22 output and 2755.9 Anas output.
  - `D9DC24CE...`: Ravi and Navaz conditional-memory outputs.
  - `00E8AB59...`: the Hamburger and Navaz fixed Tran-policy outputs.

This proves byte identity of those downloaded `main.py` outputs at observation time. It does not prove which private leaderboard submission each participant currently runs.
The downloaded third-party files remain ignored local research inputs under `raw/kernel_outputs/`; only their per-file manifests and static summaries are intended for Git. A clean clone must re-download the pinned public versions (if still available) before it can repeat the byte-level verifier. This limitation avoids republishing an `UNVERIFIED`-license fleong output.

### Tetsu v16 focused provenance and license boundary

The current public Notebook [`tetsutani/adaptive-farming-strategy-for-kaggriculture`](https://www.kaggle.com/code/tetsutani/adaptive-farming-strategy-for-kaggriculture) is v16, numeric ID `129434690`. Its fetched Notebook source is 158,263 bytes, SHA `81DA966E92F9889836E22142FD7A60CEBEAEE81CB3C52661AA286AC8C727BAF9`. The exact `main.py` written by its `%%writefile` cell was statically extracted—never imported or executed—at 27,244 bytes, SHA `997E6BFC5234534E246E945BC61C87858EBF997AB85B0A5C9427DD4ED710F1B6`; static compile passed. The extraction manifest is `E949AFA4...B281` / 2,954 bytes.

This is not an independent route family. The embedded 9,297-byte Base85 route payload is byte-identical across Tetsu v16, Boatlee V14, and Flex's Adaptive Replay Agent, SHA `EDC3163ED477B6F9EF70FA8F7A212A4F8179C4FA281008D400EDF6EE488906C2`. Flex and Boatlee differ only by Boatlee's six-line explanatory docstring. Relative to Boatlee, Tetsu keeps that route and closely related weed/SELL/preemption code while extending the future-sale search from one turn to ordered horizons 3→2→1 with exact repayment. Boatlee's source explicitly attributes the field/labor route to Kakuteki and mrgrishninsb and its runtime layers to public V23/frontier work; the Tetsu source contains no exact `boatlee` or `flexonafft` name match. Therefore a production candidate based on Tetsu must be treated as a derivative of this observed chain, not clean-room work.

The license boundary is deliberately unresolved here. Tetsu is public and its metadata links it to the Kaggriculture competition, but the artifact-specific metadata/page license is `UNVERIFIED` and the page-reader license request failed. Competition-wide public-Notebook rules may supply permission, but that is a **rules-based inference**, not an artifact-specific license finding from this lane. Before any bytes are copied into `Kag_01` or another package, the exact payload needs a separate independent rules/license verdict and preserved Tetsu plus Boatlee/Flex/common-route attribution. Machine-readable evidence is in `tetsu_v16_provenance.json`; this report does not authorize reuse, Save & Run, submission, or publication.

## Discussion findings

Notable primary topics, with full message-tree hashes in the inventory:

- `733431` [Balance Changes](https://www.kaggle.com/competitions/kaggriculture/discussion/733431), 25 votes, official author `bovard`: live rollout requires `kaggle-environments >=1.32.6`; Town Center demand is now flat 1/day; shops are drawn with replacement and duplicate shop instances consume independently.
- `731215` [Daily Top Episodes Dataset](https://www.kaggle.com/competitions/kaggriculture/discussion/731215), 19 votes: public replay data is an explicit research surface.
- `733383` [Thoughts on RL vs. Deterministic Baselines](https://www.kaggle.com/competitions/kaggriculture/discussion/733383): author reports PPO/SAC difficulty from delayed rewards and zero-tolerance farm failures, and advocates deterministic logistics plus dynamic market rules. This is an author report, not a benchmark reproduced here.
- `733055` [How can the Kaggriculture engine be changed to kill the fixed-script meta?](https://www.kaggle.com/competitions/kaggriculture/discussion/733055): claims a fixed public asset route dominated the early ladder; useful as a historical hypothesis, not proof for the current rebalance.
- `733658` [Why agents make the same decisions](https://www.kaggle.com/competitions/kaggriculture/discussion/733658): observes copied deterministic public policies and warns that convergent endgames alone do not establish shared source.
- `733161` Observation timing, `733155` Terminal settlement, `733173` opponent-agnostic optimum, and `733868` code/data licensing are preserved in the complete inventory.

## Official live-engine delta

The exact primary source is merged [Kaggle/kaggle-environments PR 1394](https://github.com/Kaggle/kaggle-environments/pull/1394): head `dd71c18601f0c5c460dbed4ac74d4454db65e3bf`, merge `1fa13d78387eb3661b1e621a4f5df150e6c3b646`, merged `2026-08-07T16:42:16Z`.

The diff removes the late Town Center 2x/4x multiplier, changes its interval 12 to 24, draws shops with replacement, caps total instances at 8, and makes duplicates consume independently. The project search at collection time still showed `kaggle-environments==1.32.2`. Therefore the already-collected 1.32.2 score evidence is historical and stale against this live rule set. This was a material validity blocker, not a cosmetic dependency bump.

Current remediation is recorded separately from this lane's collection-time observation: the main project now pins exact `kaggle-environments==1.32.6` in `pyproject.toml` and `uv.lock`. The tracked engine-lane manifest identifies official commit `bded87b0d7879078c726a93a4884d044f79c4eed`, normalized engine SHA-256 `FB9215C5E21A25243E2D13E75B3D70A79CF7D78FFF150A90F1BB5EACF9BA2BCF`, and an 81/81 official-suite pass. Those tests were produced by the engine-remediation lane, not rerun or independently attested by this public-meta lane; the old 1.32.2 results still require replacement rather than relabeling.

## Models

The only text-search hit was `saitejabandaruin/kaggriculture-dqn-weights`, ID 737778, subtitle “Starter PyTorch DQN Baseline,” record SHA `2E0B5778...F9E`. Competition linkage is only name/text search, not an official competition filter. No model was executed, downloaded, or treated as competitive evidence.

## GitHub

- 162 repository rows; 156 default-branch heads and 132 READMEs were hash-pinned.
- Licenses: 141 `UNVERIFIED`, 11 MIT, 5 Apache-2.0, 2 GPL-3.0, 2 NOASSERTION, 1 CC-BY-4.0.
- Official `Kaggle/kaggle-environments`: Apache-2.0, observed head `bded87b0...`, 442 stars and 191 forks in the snapshot.
- Other visible repositories mostly had zero stars and frequently no verified license. A public URL is not reuse permission.
- `rooklift/krobus` is a replay viewer; `Beiciccc/Kaggriculture` preserves experiment notes; many broad search hits are portfolios or unrelated AI-agent repositories. Search inclusion is not a quality endorsement.

## Current top-25 identity join

Against the separately captured top-25 team display names:

- Exact current Code author/display match: `Rayk Kretzschmar` only.
  - `raykkretzschmar/kaggriculture-findings-from-zero-to-top-meta`, v15, source SHA `CBE0CABA...`, 509,282 bytes, license `UNVERIFIED`.
  - `raykkretzschmar/kaggriculture-rank-your-agent`, v10, source SHA `C9D5EB18...`, 65,117 bytes, Apache-2.0.
- `Lester Leong` to owner `fleongg` is only a plausible name/handle inference; API author display was `fle3n`. It is explicitly `UNVERIFIED_INFERENCE`.
- No exact current Code author/owner match was observed for the other 23 names. No exact-name match was observed in the 57 Discussion rows or the one unverified Model search row. Missing matches are “not observed,” not proof that those teams have no public material.

## Tool evidence

- Agent-Reach doctor was run: GitHub, Exa web search, web pages, and YouTube were available; Reddit and X were not available in the local setup.
- Exa was actually queried for Kaggriculture Code/Discussion/GitHub discovery. Its results were supplemental; official APIs define the saved population.
- Context7 resolved `/kaggle/kaggle-cli` and returned official pagination/topics/models documentation.
- Serena was actually used on `src/kaggriculture_lab/research/kaggle_inventory.py::collect_inventory` to inspect existing collector symbols before writing this campaign collector.
- Insane Search was **not invoked**: no concrete URL remained blocked after official APIs and Jina Reader. This is recorded as `NOT_INVOKED`, not claimed as successful use.

## Limits and unknowns

- This is a time-bounded snapshot of public material, not private code, hidden models, or private submissions.
- Public source was hashed and statically parsed but not executed. A successful remote log is a page claim unless the exact output download is in the 18-ref manifest.
- The 155-ref list can change immediately after the observation window.
- The top-25 identity join is sparse because team names, handles, and Notebook authors need not match.
- A literal-tape crosscheck was rate-limited for 94/155 second-pass source requests. The high-score output scan still covered 18 current outputs, but the dominant leaderboard farm-trace lineage remains unmapped rather than “absent.”
