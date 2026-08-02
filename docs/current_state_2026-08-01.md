# Current campaign state — 2026-08-01 KST

## Live state verified from Kaggle API/CLI

- Competition submissions observed: 3, refs 55137246, 55137248, and 55142935, all COMPLETE.
- Submission 55142935 is `Fa_01 - Overflow-Safe Inventory.tar.gz`, submitted at
  2026-07-31T16:45:32.363Z. The user confirmed they submitted it manually through the Kaggle UI;
  Codex did not submit it. This confirmation is not authorization for another submission.
- At the append-only inventory snapshot ending 2026-07-31T17:17:51.842Z, the submission scores
  were 1068.0, 1066.4, and 966.7. The per-submission COMPLETE episode counts were respectively
  19 (18 PUBLIC + 1 VALIDATION), 23 (22 + 1), and 9 (8 + 1). These are time-stamped historical
  observations, not claims about later live counts.
- At the leaderboard query begun 2026-07-31T17:18:13.333Z, the team was rank 27 at 1075.0 and
  the top three were 1412.7, 1366.3, and 1319.3.
- The old 2 x 19 snapshot remains valid only at 2026-07-31T15:30:34.914Z. It was stale by the
  171b8e9 evidence handoff and is superseded for later-state claims by the new 3-submission
  snapshot registered in `submissions/ledger.jsonl`.
- Fa_01 still has a private COMPLETE Save & Run and failed sealed revalidation, but it is also a
  competition submission as ref 55142935. Fa_02 has no kernel Save & Run or submission.

## Candidate and audit state

- `final_day_labor` is the current formal local champion.
- Historical Fa_01/Fa_02 evidence is NO-GO history and cannot be reused for promotion.
- New candidate A and B development, sealed-strength, and robustness pools are registered in
  `configs/fa_ab_seed_registry.json`.
- Submission provenance is resolved. Separate-auditor verdict remains CRITICAL REJECTED until a
  clean corrective frozen handoff passes. No Save & Run, submission, publication, or new seed may
  be opened before that pass.
- All A/B challengers are accepted as NO-GO. Their unopened candidate-specific sealed and
  robustness pools are retired unused and cannot be reassigned to another hypothesis.
- A 1200+ ladder score is a design target, not a verified result or guarantee.

## Stale project AGENTS.md exception

Project `AGENTS.md` still contains the closed Kaggle 403/rules blocker. The global instruction
forbids editing an AGENTS file during the active session, so it was deliberately left unchanged.
Mandatory next-session startup action: correct that stale blocker before other project work.
