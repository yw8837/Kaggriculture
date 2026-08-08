# Local release verification receipt

Run from the campaign workspace root on 2026-08-09 KST. No Kaggle push, Save &
Run, submission, publication, or other external mutation was performed.

Status: `PENDING_FINAL_GIT_FREEZE`. External action gate: `HOLD`. This local
receipt does not claim that the worktree bytes are contained in a final commit.

## Commands and raw outcomes

```text
> .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests\test_campaign_3000_release_package.py
...........................                                              [100%]
27 passed in 3.14s

> .\.venv\Scripts\python.exe -m ruff check research\campaign_3000\07_release\build_release.py tests\test_campaign_3000_release_package.py
All checks passed!

> build_release.py --output-root research\campaign_3000\07_release\local_build  # twice
first_build_files=9
second_build_files=9
byte_differences=0
```

The focused test builds into two independent temporary output roots and compares
every generated file byte-for-byte. It also validates exact source snapshots,
archive names/members/metadata/hashes, complete pinned LICENSE identity,
exact attribution hashes plus markers, archived official notebook extraction,
tracked GetKernel envelope-to-raw-source identity, tracked live page license and
score boundaries, explicit `RuntimeError` wrapper guards, private/no-internet
metadata, exact 06 plan semantics and mandatory development/auditor
prerequisites, and external-action HOLD. Safety tests reject project
root/ancestor, `src`, `tests`, Git metadata, frozen-input ancestors, symlink,
and non-owned nonempty output roots before mutation. Atomicity tests preserve an
old output byte-for-byte after both an injected second-candidate build failure
and an injected staging-to-output `os.replace` failure. A first PowerShell
hash-map attempt used an unavailable framework method and produced no valid
comparison; the compatible rerun above is the reported evidence. Earlier
provisional 06 pins were discarded; the final 06 manifest is re-pinned below.

## Generated local-only outputs

| File | Bytes | SHA-256 |
|---|---:|---|
| `Kag_01 - Tetsu v16 Exact.tar.gz` | 19,099 | `184F687C474933A7215DB97E8C5A5F823AE79233EEA42D04B70EABC001BF9E16` |
| `Kag_01 - Tetsu v16 Exact.ipynb` | 33,912 | `0C8D17DA3266804597EA753A401FDEAE8AAF4E04CDE305C2E7F9C6FF61CDF895` |
| Kag_01 `kernel-metadata.json` | 428 | `F58F72FDC99FB5FB828732EF93546F0285F02024643884D88EAFCAF768B98746` |
| Kag_01 `prepush.json` | 5,560 | `EA3E19D1F2C81639DBD67510C4DF768DCC08BB3D8E5D71285DF67D08FE39DF55` |
| `Kag_02 - Kaito v22 Price Impact.tar.gz` | 17,360 | `37EA53D3046E3D1DA914F8A89C6F4BB02E240E1BB85857BDA149273FC4DD974C` |
| `Kag_02 - Kaito v22 Price Impact.ipynb` | 31,126 | `01003AADA83D0688DB40A01B19D4886871EE0A2317A5F8F897E82FB78130A431` |
| Kag_02 `kernel-metadata.json` | 449 | `A32152D8D2DA2BE06D08C7F2C01C401BA84EA7B4BC8E69F189110FC54A3EDCFA` |
| Kag_02 `prepush.json` | 5,612 | `8B29E422AD10408FE7F226374971CF16B4D47EF4EAB83CEDBEFDCCC64EB27C27` |
| `release_manifest.json` | 6,998 | `D2F7E361C2AD233A2528BD5C22CBED2A36EE35E24353176569D6DECFAD21DB72` |

## Archive members

| Candidate | Member | SHA-256 |
|---|---|---|
| Kag_01 | `main.py` | `997E6BFC5234534E246E945BC61C87858EBF997AB85B0A5C9427DD4ED710F1B6` |
| Kag_01 | `LICENSE` | `1EB85FC97224598DAD1852B5D6483BBCF0AA8608790DCC657A5A2A761AE9C8C6` |
| Kag_01 | `ATTRIBUTION.md` | `3685283A43DF0B5352041EA24BC1E531CE706D0F722C22BB1D07DC71F362101F` |
| Kag_02 | `main.py` | `62FB5A5F66F0011092A2B51E3192879BA583D5D815D761F176091C615657147A` |
| Kag_02 | `LICENSE` | `1EB85FC97224598DAD1852B5D6483BBCF0AA8608790DCC657A5A2A761AE9C8C6` |
| Kag_02 | `ATTRIBUTION.md` | `A13EDD083A33082DD781B7A1EDD75306C868C743E12082CF4623F5B4BF970BD9` |

All archives use ordered USTAR members `main.py`, `LICENSE`,
`ATTRIBUTION.md`, mode `0644`, and zero mtime/uid/gid with empty user/group
names. Gzip mtime and embedded filename are also fixed to zero/empty.

## Worktree-pinned input hashes

| Input | SHA-256 |
|---|---|
| `build_release.py` | `F31DAFF27A7EEF2FB4EE34E56F7DB060CFB549B0D42611717528C6832D8FC9DF` |
| `release_spec.json` | `BBE3B7DA2C14B5C4DD752AE67C55FD1898E1B9DF613162DA7FCAEC32009680F4` |
| `source/tetsu_v16_main.py` | `997E6BFC5234534E246E945BC61C87858EBF997AB85B0A5C9427DD4ED710F1B6` |
| `source/kaito_v22_main.py` | `62FB5A5F66F0011092A2B51E3192879BA583D5D815D761F176091C615657147A` |
| `LICENSE` | `1EB85FC97224598DAD1852B5D6483BBCF0AA8608790DCC657A5A2A761AE9C8C6` |
| `TETSU_IP_VERDICT.md` | `DA8764985D0EFCFC63867DB673E242D82B9D72CFE7495BFCB932A2DD6F0DF721` |
| `source/SNAPSHOT_RECEIPT.json` | `A07E93F0FB1BD93BD2F248924D9DFD6F7F2DB5F908776E732743E7B72EB8981C` |
| `evidence/official_capture_receipts.json` | `83C1E27A39B9B7582022CC5AB7F5F337BCF5F06CCD770538AD6513F861A19558` |
| `evidence/raw/RECEIPT.json` | `B3F54DDD8C888665C8755B806F10094F999C63E3409130587FD94C2982759772` |
| Tetsu raw v16 notebook | `81DA966E92F9889836E22142FD7A60CEBEAEE81CB3C52661AA286AC8C727BAF9` |
| Kaito raw v2 notebook | `BE57F757AAAAFA37A1AAB1EB5FE827925144EC7F3825A6236053329C15F2E859` |
| Tetsu tracked GetKernel envelope | `70ADF63DCDEB41504A63C6056258CA77C9D09F86FB8101A2EE00A82C1D4434FB` |
| Kaito tracked GetKernel envelope | `8C782EE8D07629523F0675341AE876FBE5680CD145ED3315E0CCFEE23E5391CC` |
| Tetsu tracked live page | `7247E047A8CE43BE59DAB9886DED9A5B8832E3D14F69925A1894A3B5EEC5B19B` |
| Kaito tracked live page | `215183C1DF46AA58D6A4F2BD76644E1E16488DD7A513679493E2F282B36125C1` |
| `06_candidates/candidate_plan.json` | `7167430237ACFF5846C8DFD6F948DC846BC5DB3BCBFCE973505DF3E86A0D33C8` |
| `06_candidates/gate_config.json` | `F9E82C8F1EE992FB2F82B3EB8DE476410A0695E05C06C35AD951A21AAE8750DB` |
| `06_candidates/manifest.json` | `FBF560F617788022552B2115023639F81CB49E01E67B90AACE2291DA72DECE69` |
| `tests/test_campaign_3000_release_package.py` | `CEB1E570C00BD63B114831BF35031D795E6FBBE6D6DBE9C36C3E94C1571363A3` |

The immutable `TETSU_IP_VERDICT.md` retains its historical cutoff-era `dist/`
path wording because the closed 06 plan pins its exact SHA-256. Clean-clone
verification does not follow those historical paths: the builder instead pins
the tracked `07_release/source`, raw notebook, GetKernel envelope, page capture,
and receipt paths. The fallback now points to the tracked 06 Ray C45 snapshot.
