# Current campaign state — 2026-08-01 KST

## Live state verified from Kaggle API/CLI

- Competition submissions: exactly 2, refs 55137246 and 55137248, both COMPLETE.
- Scores at the latest recorded query: 1068.0 and 1069.1; team rank 24 at 1069.1.
- Top three at that query: 1406.8, 1287.7, 1270.0.
- Each submission inventory contains 18 PUBLIC + 1 VALIDATION COMPLETE episodes. The complete
  snapshot and its hash are registered in `submissions/ledger.jsonl`.
- Fa_01 has a private COMPLETE Save & Run but failed sealed revalidation and is not a competition
  submission. Fa_02 has no kernel Save & Run and no competition submission.

## Candidate and audit state

- `final_day_labor` is the current formal local champion.
- Historical Fa_01/Fa_02 evidence is NO-GO history and cannot be reused for promotion.
- New candidate A and B development, sealed-strength, and robustness pools are registered in
  `configs/fa_ab_seed_registry.json`.
- Separate-auditor verdict remains REJECTED. No new sealed-strength or robustness seed may be
  opened until a frozen development evidence handoff is accepted.
- A 1200+ ladder score is a design target, not a verified result or guarantee.

## Stale project AGENTS.md exception

Project `AGENTS.md` still contains the closed Kaggle 403/rules blocker. The global instruction
forbids editing an AGENTS file during the active session, so it was deliberately left unchanged.
Mandatory next-session startup action: correct that stale blocker before other project work.
