# Kaggriculture campaign directive

Recorded: 2026-07-31 (Asia/Seoul)

This file is the durable user directive for the campaign. It must be read together with
`PROJECT_BRIEF.md` and `WORKFLOW.md` after any context reset or handoff.

## Terminal objective

- Target a final rank of third or better. This is judged only after the competition finishes,
  not as a same-day checklist item.
- Treat early ladder ratings as noisy evidence. Build a durable research and agent-production
  system rather than optimizing one lucky public score.

## Immediate ordered work

1. Search, archive, analyze, and cross-check Kaggle Code and Discussions, GitHub, completed
   algorithmic-agent competitions and hackathons, academic papers, official documentation,
   columns, and broad English/Korean web sources. Use Agent-Reach, Insane Search for blocked
   URLs, and available deep web search. Never claim literal exhaustive coverage without a saved
   query/source manifest.
   - Continuously collect and analyze public replays from multiple current top-ranked users and
     leaderboard snapshots. Preserve episode IDs, rank/rating snapshot, retrieval time, raw replay,
     and hashes. Compare both seats, turn/day action traces, cash and inventory curves, expansion,
     labor, crop/herd, market, storage, and end-game patterns.
   - Never generalize from one replay or one leader. Recheck mechanisms across several top users,
     seeds, seats, and time snapshots, and convert every retained pattern into a falsifiable local
     experiment without copying or publishing private production strategy.
2. Build Kag_01 and Kag_02 as two distinct private candidates. Perform pattern analysis,
   simulator inspection, paired both-seat experiments, held-out and adversarial validation,
   runtime checks, deterministic packaging, and independent review.
3. After both private Save & Runs are verified, publish the useful Discussion first and the
   deliberately weaker, commented public Code second.
4. Private Save & Run is the default stopping point. Competition submission happens only when
   the user explicitly says to submit.

## Naming and release policy

- The two initial baseline submissions remain unnumbered.
- Production filenames are `Kag_XX - Short Description.tar.gz`, starting with Kag_01.
- Keep the exact active and final production agents private.
- When the private score band is stable, continue publishing older or ablated code below it.
  The public payload must remain clearly below the two current private candidates. The current
  private research target is 3000+ on the observed ladder, but no local or remote score is
  guaranteed and exact upstream-version score claims must remain version-bound.
- Public code must be genuinely useful, well commented, and honest about being a public
  baseline rather than the current private champion.
- Treat public Discussion and Code titles as search/discovery assets. Front-load `Kaggriculture`,
  include the concrete search intent (`Agent`, `Baseline`, `Evaluation`, `Strategy`, or the main
  mechanism), and state a specific benefit without clickbait or unverified score claims. Keep a
  title/query log so later views, votes, comments, and forks can be compared honestly.

## Evidence and repository requirements

- Store raw references under `references/`; store tracked provenance and findings in source
  manifests and reports.
- Maintain immutable experiment and submission ledgers with hashes, seeds, opponents, runtime,
  failures, result, and rejected hypotheses.
- Keep the private GitHub repository suitable for a future portfolio, solution write-up, and
  technical report: evidence index, strategy cards, decision log, milestone commits/tags, and
  sanitized public exports.
- Never commit credentials, Kaggle tokens, production archives, or private Save & Run notebooks.

## Independent adversarial auditor

- A structurally independent auditor must be a separate user-owned Codex task, not a child,
  parent, or sibling in the production agent tree. Do not label an in-tree subagent independent.
- Until that separate task exists, describe any in-tree review exactly as a subordinate
  adversarial review and treat its conclusions as supporting evidence only.
- The auditor distrusts the main agent's framing and rechecks source code, simulator outputs,
  Kaggle state, hashes, claims, publication leakage, and instruction compliance from originals.
- The auditor has no permission to edit code, submit, publish, commit, or push. It reports defects
  directly to the user. Main work must not suppress or rewrite adverse findings.
- Every completed audit must receive a written disposition for each finding: `accepted`,
  `rejected with original evidence`, or `deferred with an explicit blocker`.
- Accepted findings restart the relevant research -> review -> correction -> verification -> build
  sequence. Send the resulting evidence back to the separate auditor for re-audit.
- If the auditor rejects the reworked result, preserve both positions and evidence, discuss the
  disputed decision with the user, and continue the loop until the user accepts a resolution or
  an objective blocker is recorded. Audit approval is not inferred from silence.

## User coordination

- Ask immediately when login, authorization, a material strategy choice, or any other user action
  is genuinely required. Otherwise continue autonomously through the authorized local and private
  Save & Run workflow.
