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
2. Analyze the exact previous submissions named by the user for the current cycle. The list is
   dynamic: never hard-code Kag_01/Kag_02, silently substitute the latest two, or reuse a list
   from an older cycle. Bind every named submission to its exact artifact, Kaggle version,
   submission ID, score/rating timeline, episodes, replays, and retrieval cutoff before using it
   as evidence.
3. Design the next user-requested `Kag_XX` candidates only after the research and named-previous-
   submission analysis are connected to each candidate by a written evidence-to-delta bridge.
   Perform simulator inspection, paired both-seat experiments, held-out and adversarial
   validation, runtime checks, deterministic packaging, and independent review.
4. Discussion or public Code publication is a separate workflow and is not implied by research,
   candidate production, upload, Save & Run, or competition submission. Perform it only when the
   user explicitly requests that publication in the current task.
5. Private Save & Run is the default stopping point. Competition submission happens only when
   the user explicitly says to submit.

## Mandatory baseline checklist for every candidate cycle

This checklist is a blocking contract, not optional background reading. It applies again whenever
the user requests more candidates (Kag_03/04, Kag_05/06, and so on).

### Cycle inputs

- Record the new candidate slots requested by the user.
- Record the exact list of previous submissions that the user names for additional analysis.
  Do not infer, expand, replace, or permanently hard-code that list.
- Record one current retrieval cutoff in UTC and preserve older snapshots instead of overwriting
  them.

### A. Internal and competition research

- Inventory our submissions and identify defects: exact artifact/source hashes, Kaggle IDs and
  versions, score/rating history, episode counts, replay availability, runtime/failure evidence,
  and unresolved provenance.
- Capture the current leaderboard top 1–25 row by row with retrieval time, team, score, public
  Code/Discussion linkage, submission/episode/replay availability, and an explicit `UNVERIFIED`
  value wherever private data cannot be observed.
- Enumerate the current competition populations for public Code, Discussion, and Models. Save the
  pagination/terminal condition, IDs/URLs/versions/hashes, deduplication rule, and distinguish
  static inspection, remote claims, local execution, and reproduction.
- Research completed algorithmic-agent competitions and hackathons. Extract the winning
  mechanism, constraints, failure modes, and a falsifiable Kaggriculture adaptation; a link list
  alone does not pass.

### B. External research

- Search broad English and Korean sources: official documentation and issues, papers, columns,
  Google/Naver, GitHub, hackathons, competition write-ups, and other relevant platforms available
  through the configured tools.
- Use Agent-Reach for broad/current discovery and Insane Search for a specific blocked or
  WAF-protected source. Record every query, backend, time, success/failure, source authority,
  retained mechanism, and coverage limitation.
- Continue until the recorded query families are covered and a further pass reaches diminishing
  useful mechanisms. Never translate this bounded stop rule into a literal “entire internet”
  claim.

### C. User-specified previous-submission analysis

For every previous submission named by the user in the current cycle:

- Verify exact local and remote identity before comparing performance.
- Analyze all available episode metadata and a provenance-pinned replay population. Separate full
  population facts from recent or selected replay samples.
- Compare both seats, opponent and opponent-family results, time/rating trajectory, wins/losses/
  ties, money and margin distributions, lower quantiles, farmer/hands/market traces, cash and
  inventory curves, expansion, labor, crops, herd, storage, terminal behavior, failures, invalid
  actions, and runtime.
- Compare the same mechanisms with current top-25 and public-code evidence. State selection bias,
  unmatched-opponent limits, rating path dependence, and anything that cannot be inferred.
- Produce a per-submission defect table and retain/retire decision. A positive aggregate that hides
  a losing opponent lane is not a pass.

### D. Research-to-design bridge

Before implementing a new candidate, write one row containing:

`source -> verified finding -> observed previous-submission defect -> one bounded code delta -> expected causal metric -> regression risk -> falsifier -> fresh evaluation lane`.

- Every candidate has exactly one primary hypothesis and an immutable control.
- If a candidate direction differs from the prioritized research hypothesis, record why the old
  direction was rejected or deferred and what original evidence supports the replacement.
- No candidate may be described as research-derived when this bridge is absent.

### E. Evaluation and completion

- Freeze source, builder, runner, engine, opponents, scenarios, seeds, receipts, gate, and runtime
  contract before fresh execution.
- Use fresh paired cells, both seats, diverse deduplicated opponent families, uncertainty or
  bootstrap intervals, per-opponent results, worst case/lower quantile, invalid/failure/runtime
  checks, and a causal/action-diff witness showing that the new mechanism actually fired.
- A candidate intended to improve on a named previous submission must beat that exact control on
  the preregistered direct lane; non-inferiority alone is not an improvement claim.
- Confirmation and robustness plans are designed only after development passes, remain sealed
  until then, and use fresh disjoint evidence.
- Each checklist row ends as `PASS`, `PARTIAL`, `UNVERIFIED`, or `NOT_APPLICABLE` with original
  evidence. The cycle is complete only when every required row is `PASS`; partial artifacts do not
  add up to completion.
- Send the final frozen evidence to the separate independent auditor for verification. An internal
  child-agent review is supporting QA only.

### Required skill and tool evidence

- For every skill/tool the user names for the cycle, record `USED`, `UNAVAILABLE`, or `NOT_USED`
  plus the exact output/evidence and reason. Never count reading a skill file as using it.
- The recurring campaign routes are Harness, UltraQA, Autoresearch, Agent-Reach, Insane Search,
  Context7, Serena, Learner/Skillify, and memory consolidation when a supported memory store is
  present. Self-improve may run only after its mandatory repository/benchmark trust contract is
  satisfied; do not fake that gate.

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
