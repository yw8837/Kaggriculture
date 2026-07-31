# Main-maintained coordination mirror — not auditor-issued / not auditor-approved

**Current promotion verdict: CRITICAL REJECTED. All external actions and new seed openings are
stopped pending corrective re-audit. Submission provenance is now user-confirmed.**

This file is maintained by the production task to mirror coordination. It is not an independent
auditor report, signature, approval, or substitute for the original separate-task messages.

## Separate auditor reference

Auditor task: `019fb8b8-7758-7860-9304-39eb4f06c65c`.

This is a structurally separate, user-owned Codex task. It has read-only authority and no
permission to edit files, run Kaggle Save & Run, submit, publish, commit, or push. Findings are
not silently rewritten by the production task.

## Preliminary handoff and dispositions

| ID | Independent finding | Main disposition | Required action |
|---|---|---|---|
| F1 | The earlier query had two competition submissions, but submission 55142935 existed from 16:45:32Z before the frozen evidence handoff. | Superseded / CRITICAL; actor resolved | Historical query and claim withdrawal preserved. User confirmed a manual Kaggle UI submission; Codex did not submit it. Corrective audit remains required. |
| F2 | Old Fa_01/Fa_02 raw statistics and seat balance recompute, but pre-hardening reports lack Git HEAD/start receipts/opponent start-end hashes. Fa_02 cap-sweep sources were overwritten and current hashes differ. | Accepted | Treat these only as historical NO-GO boundaries. Never reuse them as promotion evidence. |
| F3 | All 70 refreshed replay files match the report manifest SHA-256, but the corpus is correlated and public-exposure selected; it is not an executable elite opponent suite. | Accepted | Use it only for priors and falsifiable hypotheses. Do not infer independent win rate or top-3 strength. |
| F4 | Current runner varies seed and episode length but not `marketParams` or other adversarial scenarios. The opponent pool is public/1069-lineage strength and is not a top-3 sufficient condition. | Accepted | Add configuration/scenario evaluation before sealed promotion. Describe 1200+ as a target, never a verified rating without a competition result. |
| F5 | Before sealed seeds are opened, the auditor requires a frozen commit, candidate/opponent/config hashes, development raw results, tests, and an explicit claim list. | Accepted | Send a development-only evidence package to the separate task and wait for its pass/reject verdict before sealed evaluation. |
| F6 | The 2 x 19 snapshot was correct only at 15:30:34Z and stale before the 17:01 evidence commit. | REJECTED; corrective snapshot pending audit | Preserve a new append-only three-submission snapshot with per-query UTC, dynamic counts, metadata, and SHA-256. |
| F7 | Champion resolver/core hashes pass, but active submissions and rejected Fa_01 `submitted=false` were false after 55142935. | PARTIAL PASS | Record all three refs and the unresolved Fa_01 competition submission without guessing the actor. |
| F8 | Registered seed pools and disjointness verified. | PASS | Retire unopened 24000/25000/27000/28000 pools unused; never reuse them for another hypothesis. |
| F9 | Some stale docs were fixed, but current state and prose-only test evidence were still inaccurate/unverified. | REJECTED / PARTIAL | Correct current state and require immutable test logs with SHA-256 or remote CI. |

The main task sent these dispositions directly to the auditor. Development NO-GO evidence was
accepted, but the PR/evidence promotion remains CRITICAL REJECTED. Corrective implementation and
new evidence remain unverified. No candidate is ready for Save & Run or submission.

## Corrective work awaiting independent re-audit

- Added an append-only three-submission API inventory ending 17:17:51.842Z, SHA-256
  `25BD51D99BBDA2A3BF5EA4D243D1008A0D1378BB579F63801B6CE15DED93BC7E`.
- Corrected champion external-state fields and recorded the user's confirmation that 55142935 was
  their manual Kaggle UI action, not a Codex submission or authorization for a later submission.
- Retired all unopened A/B candidate-specific pools unused and registered all proposed next pools
  CLOSED. No proposed seed was opened.
- Froze the two previously untracked public-opponent exact bytes for private reproducibility and
  marked both public-release forbidden because their source licenses were not identified.
- Corrected future aggregate/bootstrap clustering to seed, while leaving historical pair-cluster
  evidence unchanged and explicitly labeled.
- Prepared the conditionally accepted next boundary without opening a seed: exact A paired gates,
  BG1 one-delta rescue source, causal counter capture, strict paired seed-cluster analysis, and a
  historical-replay runtime PASS (p95 1.8301 ms / p99 3.5609 ms / max 4.1475 ms / invalid 0).
- Captured hash-registered local evidence: Ruff zero findings, project 108 passed, official
  simulator 67 passed. This is not remote CI and remains unverified by the separate auditor.

## Required loop

1. Freeze and commit the development implementation and registered config.
2. Run only registered development seeds and scenario suites.
3. Send original hashes, raw outputs, tests, and claims to the auditor.
4. Correct accepted defects and rerun affected development evidence.
5. Open sealed seeds only after the auditor accepts the evidence boundary.
6. Send package and private Save & Run evidence back for final re-audit.
