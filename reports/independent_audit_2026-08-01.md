# Main-maintained coordination mirror — not auditor-issued / not auditor-approved

**Current promotion verdict: REJECTED. Sealed-strength and robustness seeds remain closed.**

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
| F1 | Kaggle has exactly two competition submissions, 55137246/55137248, both COMPLETE at 1068.0/1069.1. Fa_01 is a COMPLETE kernel but not a competition submission; Fa_02 has no Save & Run or submission. | Accepted | Keep kernel, Save & Run, and competition submission states separate in every claim. |
| F2 | Old Fa_01/Fa_02 raw statistics and seat balance recompute, but pre-hardening reports lack Git HEAD/start receipts/opponent start-end hashes. Fa_02 cap-sweep sources were overwritten and current hashes differ. | Accepted | Treat these only as historical NO-GO boundaries. Never reuse them as promotion evidence. |
| F3 | All 70 refreshed replay files match the report manifest SHA-256, but the corpus is correlated and public-exposure selected; it is not an executable elite opponent suite. | Accepted | Use it only for priors and falsifiable hypotheses. Do not infer independent win rate or top-3 strength. |
| F4 | Current runner varies seed and episode length but not `marketParams` or other adversarial scenarios. The opponent pool is public/1069-lineage strength and is not a top-3 sufficient condition. | Accepted | Add configuration/scenario evaluation before sealed promotion. Describe 1200+ as a target, never a verified rating without a competition result. |
| F5 | Before sealed seeds are opened, the auditor requires a frozen commit, candidate/opponent/config hashes, development raw results, tests, and an explicit claim list. | Accepted | Send a development-only evidence package to the separate task and wait for its pass/reject verdict before sealed evaluation. |
| F6 | The submission ledger preserved only historical partial episode snapshots. | Accepted | Preserve a complete API snapshot for both submissions with 18 PUBLIC + 1 VALIDATION each, observation time, episode metadata, invariant, and content hash. |
| F7 | The champion manifest's top-level identity pointed at rejected Fa_01. | Accepted | Make `final_day_labor` the sole current identity, move Fa_01 to rejected history, and prove the packaging resolver verifies source and artifact hashes. |
| F8 | Legacy seed pools were repeatedly observed and cannot support new promotion. | Accepted | Register A 23000-23015 / 24000-24063 / 25000-25031 and B 26000-26015 / 27000-27063 / 28000-28031 with purpose and opened/consumed state. |
| F9 | Project state documents contained stale rule-acceptance, test-count, and threshold claims. | Accepted | Correct mutable state docs now. Do not edit project `AGENTS.md` mid-session; record mandatory correction for the next session. |

The main task sent these dispositions directly to the auditor. Remediation plans were accepted,
but implementation and evidence remain unverified. New candidates are not reviewed or ready.

## Required loop

1. Freeze and commit the development implementation and registered config.
2. Run only registered development seeds and scenario suites.
3. Send original hashes, raw outputs, tests, and claims to the auditor.
4. Correct accepted defects and rerun affected development evidence.
5. Open sealed seeds only after the auditor accepts the evidence boundary.
6. Send package and private Save & Run evidence back for final re-audit.
