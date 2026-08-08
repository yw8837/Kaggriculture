# IP, rules, and provenance record

Evidence cutoff: `2026-08-08T18:53:47Z`. This record supports local preparation
of private Save & Run payloads only. It is not legal advice and authorizes no
Kaggle push, run, submission, or publication.

## Official rules and environment sources

- Competition rules: <https://www.kaggle.com/competitions/kaggriculture/rules>
  - Captured UTF-8 response: 37,141 bytes; SHA-256
    `6E08C28F5EEA043B17FEBAAE43D724A8BFE9E69C34587417EFF7B9C9255E76BD`.
  - Verified statements: at most five submissions per day and two final
    submissions; public Competition Code shared through a competition notebook
    is deemed licensed under an OSI-approved license without a commercial-use
    restriction; open-source code used in a submission must meet that standard;
    public sharing must not violate third-party rights.
  - The rules separately label winner deliverables `CC-BY 4.0` and Competition
    Data access/use `Apache 2.0`. Those labels are not, by themselves, licenses
    for either packaged agent.
- Pinned official environment source:
  <https://github.com/Kaggle/kaggle-environments/tree/bded87b0d7879078c726a93a4884d044f79c4eed/kaggle_environments/envs/kaggriculture>
- Pinned repository license:
  <https://github.com/Kaggle/kaggle-environments/blob/bded87b0d7879078c726a93a4884d044f79c4eed/LICENSE>
  - Worktree-pinned local full text (commit containment pending final Git
    freeze): `research/campaign_3000/07_release/LICENSE`
  - SHA-256:
    `1EB85FC97224598DAD1852B5D6483BBCF0AA8608790DCC657A5A2A761AE9C8C6`

## Candidate decision

### Kag_01 — Tetsu v16 exact

Verdict: `CONDITIONAL_PASS_PRIVATE_SAVERUN_ONLY`.

- Official page:
  <https://www.kaggle.com/code/tetsutani/adaptive-farming-strategy-for-kaggriculture>
- Kernel id/version: `129434690` / `16`; public at cutoff.
- API notebook source SHA-256:
  `81DA966E92F9889836E22142FD7A60CEBEAEE81CB3C52661AA286AC8C727BAF9`.
- Exact packaged `main.py` SHA-256:
  `997E6BFC5234534E246E945BC61C87858EBF997AB85B0A5C9427DD4ED710F1B6`.
- Verified: a later tracked live notebook-page capture displays Apache License
  2.0; tracked official GetKernel response envelopes bind the API source,
  current version, kernel id, competition source, and exact extracted bytes.
  The original cutoff page digest remains an append-only timestamped
  attestation whose body was not archived.
- Inference: the page-level Apache statement covers the cell-14 v16 artifact.
  The artifact has no embedded SPDX declaration, so this remains an explicit
  mapping inference, not an artifact-native license fact.
- Required lineage: Boatlee v4 and Flex v42 refs/source and agent hashes, common
  route SHA-256
  `EDC3163ED477B6F9EF70FA8F7A212A4F8179C4FA281008D400EDF6EE488906C2`,
  and Boatlee's Kakuteki, mrgrishninsb, public V23, price-impact ordering, and
  frontier-cleanup notices are preserved in `ATTRIBUTION_TETSU.md`.
- Score boundary: the original cutoff record said `2703.1 V15` belonged to
  v15. A later tracked live page capture shows `3097.4 V16` with
  `scriptVersionId=341040786`; this is
  `LIVE_REMOTE_PAGE_SCORE_V16_NOT_LOCAL_REPRODUCTION`. The package still makes
  no 3097.4 claim until an independent auditor confirms that evidence.

The immutable evidence gate is `TETSU_IP_VERDICT.md`, SHA-256
`DA8764985D0EFCFC63867DB673E242D82B9D72CFE7495BFCB932A2DD6F0DF721`.

### Kag_02 — Kaito v22 price impact exact

Verdict: `PASS_PRIVATE_SAVERUN_PACKAGE` subject to unchanged hashes and notices.

- Official page:
  <https://www.kaggle.com/code/kaitofukami/44-46-strict-future-top-30-v22-price-impact>
- Kernel id/version: `129916747` / `2`; public at cutoff.
- API notebook source SHA-256:
  `BE57F757AAAAFA37A1AAB1EB5FE827925144EC7F3825A6236053329C15F2E859`.
- Exact packaged `main.py` SHA-256:
  `62FB5A5F66F0011092A2B51E3192879BA583D5D815D761F176091C615657147A`.
- Verified: a tracked live page capture has the Apache-2.0 label, and tracked
  official GetKernel response plus raw notebook bind the exact API source and
  extracted output mapping. The cutoff page digest is retained as a timestamped
  attestation whose body was not archived. Upstream route/mechanism citations
  are retained in `ATTRIBUTION_KAITO.md`.
- Score boundary: `2957.6 V2` is a captured remote public score, not a fresh
  local promotion result or future-performance guarantee.

## Fallback

Ray C45 remains a non-selected, hash-pinned fallback/evaluation opponent:
`6CC3B69E487052A8DEDC1A90D0D1296BA38577349E8D3BA8147E583605378F73`.
Its page/source evidence is Apache-2.0, but its C45 filename/docstring and
embedded `C64_HORIZON25` version identity must be disclosed if selected later.

## Claim boundary

The local package builder may claim exact-byte identity, deterministic archive
construction, inclusion of full license and attribution, private/no-internet
metadata, and absence of network/push/submit code. It may not claim a completed
Kaggle Save & Run, output download/hash match, submission, publication, fresh
promotion test, legal clearance beyond the evidence above, or future score.

The exact candidate bytes are present and worktree-hash-pinned under
`07_release/source/`; commit containment is `PENDING_FINAL_GIT_FREEZE`.
`source/SNAPSHOT_RECEIPT.json` binds them to the source-notebook and extraction
hashes. `evidence/raw/RECEIPT.json` binds tracked official GetKernel response
envelopes, the archived raw notebooks, extraction cell/method, and exact
`main.py` bytes. `evidence/official_capture_receipts.json` preserves the cutoff
attestations and binds later tracked candidate-page bodies that contain the live
Apache labels; neither record authorizes an external action.
