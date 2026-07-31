# Kaggriculture end-to-end operating playbook

Read `CAMPAIGN_DIRECTIVE.md` before starting or resuming campaign work. It records the binding
publication order, Fa naming, research scope, repository requirements, and independent-auditor
rule that must survive context compaction and handoffs.

This playbook exists to make the campaign evidence-driven and reproducible. It does not guarantee a top-3 finish; it prevents avoidable process failures and forces every major decision through explicit gates.

## Required project artifacts

Create and maintain these before serious optimization:

- `docs/problem_spec.md`: rules, metric, state, actions, horizon, constraints, and open questions.
- `docs/source_manifest.md`: every material source, access date, authority level, finding, and design impact.
- `docs/assumptions.md`: facts, inferred mechanics, estimates, and unresolved assumptions kept separate.
- `configs/evaluation_splits.json`: fixed development, validation, holdout, adversarial seeds, and opponent sets.
- `experiments/ledger.jsonl`: immutable record of every local and Kaggle candidate.
- `artifacts/champion/manifest.json`: current champion code/config/output hashes and evidence report.
- `reports/<candidate>.md`: paired results, confidence intervals, regressions, ablations, and verdict.
- `submissions/ledger.jsonl`: exact Kaggle artifact hash, notebook version, description, result, and lesson.

Do not invent evidence to fill these files. Unknown values stay explicitly unknown.

## Stage 0 — Scope and authority

1. Restate the concrete objective, current phase, and next verifiable outcome.
2. Identify permitted local actions and external actions requiring user approval.
3. Check the competition deadline, rules acceptance, submission allowance, hardware/runtime limits, and prohibited techniques.
4. Create a live plan. At most one implementation step may be in progress.

Gate: scope, authority, and blockers are explicit. If accepting rules, uploading, submitting, publishing, or browser control is required, obtain permission first.

## Stage 1 — Ground-truth acquisition

Collect and pin:

1. Competition rules, metric, agent interface, runtime limits, submission format, and evaluation protocol.
2. Official environment source, tests, example agents, version, and commit.
3. Competition data and checksums after the user accepts the rules.
4. Public leaderboard snapshot and submission limits as context only.

Prefer official pages, source code, and tests over descriptions. Resolve disagreements by running the pinned environment or reading the implementing code.

Gate: `docs/problem_spec.md` cites the source or test for every material rule.

## Stage 2 — Broad research and mechanism extraction

Run several independent lanes in parallel when useful:

- Official environment mechanics and hidden edge cases.
- Kaggle discussions, notebooks, datasets, and high-quality public agents.
- Current top-user replays across multiple leaderboard snapshots, users, seeds, and both seats;
  retain raw episodes/IDs/hashes and extract turn-level economic and action trajectories.
- GitHub implementations, forks, issues, commits, and benchmark harnesses.
- Related farming/economic simulators, planning competitions, market games, and finished competition solutions.
- Relevant methods: finite-horizon planning, MPC, MCTS, dynamic programming, task allocation, opponent modelling, robust optimization, bandits, and policy ensembles.

Routing:

- Agent-Reach: broad/current web and platform research.
- Insane Search: blocked, dynamic, WAF-protected, or specific URL extraction.
- Local source inspection: `rg`, tests, commit history, and executable probes.
- Web technical research: primary sources and official documentation only when available.

For every retained source record:

- URL/repository and commit or access date.
- Authority: official, primary research, verified implementation, discussion, or anecdote.
- Exact mechanism learned.
- Expected benefit and failure mode.
- Which local experiment can falsify it.

Research is complete only when the source manifest exists, major query families are covered, contradictions are resolved or logged, and another search pass produces diminishing useful mechanisms. Never call a handful of searches “full research.”

Gate: prioritized mechanism backlog with evidence and falsification tests, not a list of copied solutions.

## Stage 3 — Formal problem model

Write the simulator as an explicit decision problem:

- Observable state and any partial observability.
- Legal actions, action budget, ordering, and timing.
- Reward/cash/net-worth objective and terminal effects.
- Resource flows, build/plant/harvest/sell cycles, travel costs, and bottlenecks.
- Market impact, competition, opponent interference, and stochastic variables.
- Finite 720-turn horizon and end-game liquidation behavior.
- Runtime, memory, serialization, and failure semantics.

Build small executable probes for ambiguous mechanics. Do not design a policy on prose assumptions that can be tested in code.

Gate: important assumptions are either source-backed, experimentally verified, or explicitly marked unresolved.

## Stage 4 — Reproducible baseline

1. Pin dependencies and environment commit.
2. Run official tests and a minimal smoke game.
3. Reproduce built-in and public baseline agents across fixed seeds.
4. Confirm deterministic replay where the environment promises determinism.
5. Record crashes, invalid actions, timeouts, and metric definitions.

Required evidence:

- Exact commands and exit codes.
- Environment and agent hashes.
- Seed/opponent matrix.
- Raw result artifact plus compact summary.

Gate: a clean command reproduces the baseline distribution. If not, optimization is blocked until the mismatch is explained.

## Stage 5 — Evaluation design before tuning

Create immutable partitions:

- Development seeds/opponents: rapid iteration.
- Validation set: promotion decisions.
- Holdout set: rare milestone checks, never routine tuning.
- Adversarial set: hostile market paths, maps, opponent archetypes, and resource shocks.

Use paired comparisons on identical scenarios. Report:

- Mean and median score/reward.
- Confidence intervals or bootstrap intervals.
- Win rate and pairwise delta distribution.
- Worst case, lower quantile, variance, crash/invalid-action rate, and runtime.
- Performance by opponent archetype and scenario family.

Do not pick numeric promotion thresholds until baseline variance is measured. Once chosen, record them before evaluating the challenger.

Gate: evaluation protocol and promotion rule are fixed before challenger tuning.

## Stage 6 — Hypothesis-driven design

Each challenger gets one primary hypothesis containing:

- Mechanism and expected causal effect.
- Exact code/config surface to change.
- Metrics that should move if the hypothesis is true.
- Likely regressions and safety guard.
- Minimum useful effect and kill criteria.
- Required compute and experiment budget.

Maintain diverse tracks rather than many cosmetic variants of one idea:

- Exact economic scheduling/optimization.
- Path planning and multi-worker allocation.
- Market-impact-aware action sizing.
- Opponent modelling and response.
- Robust/receding-horizon control.
- End-game planning.
- Policy switching or ensembles only after strong single policies exist.

Gate: candidate is distinguishable from prior artifacts and can be falsified locally.

## Stage 7 — Minimal implementation

1. Preserve user and parallel-agent edits.
2. Make the smallest change that tests the hypothesis.
3. Keep randomness seeded and configuration explicit.
4. Add structured logs for decisions, failures, and resource flows.
5. Avoid unrelated refactors.
6. Record code/config hash before running evaluation.
7. Preserve every named variant source or a reproducible generator revision; do not reuse a
   mutable default path for multiple experimental variants.
8. Write a pre-run receipt containing start time, Git HEAD, workers, seeds, source/opponent
   paths and hashes. The final report must include the receipt hash and matching end hashes.

Gate: lint/static checks, focused unit tests, and a smoke simulation pass.

## Stage 8 — Verification matrix

Run in increasing cost order:

1. Interface/schema and import checks.
2. Unit tests for economic calculations and action legality.
3. Determinism/replay test.
4. Integration games against simple built-ins.
5. Paired development evaluation.
6. Validation evaluation.
7. Ablation: remove the new mechanism and confirm the effect disappears.
8. Stress/adversarial scenarios.
9. Runtime, memory, timeout, crash, and invalid-action checks.
10. Rule/compliance and packaging audit.

For every batch, require `sources_unchanged_during_run=true`. Treat a missing start receipt,
source hash mismatch, overwritten variant, or absent worker count as invalid provenance even if
the score looks favorable.

Investigate conflicting signals. Do not average away a severe regression or explain it after the fact without a new test.

Gate: `reports/<candidate>.md` contains raw artifact references, metrics, uncertainty, regressions, and a GO/NO-GO verdict.

## Stage 9 — Champion promotion

Promote only when all are true:

- Pre-registered validation rule passes.
- No unacceptable worst-case, crash, timeout, or opponent-specific regression.
- Improvement survives paired analysis and an ablation.
- Code/config/output hashes are unique and recorded.
- A clean reproduction command succeeds.

The previous champion remains immutable and recoverable. A leaderboard increase does not retroactively validate a broken local process.

## Stage 10 — Authorized Kaggle save-run or submission

Only after explicit authorization:

- Kaggriculture production candidates use `Fa_XX - Short Description.tar.gz`, starting at
  `Fa_01`; the two unnumbered initial baseline submissions remain outside this sequence.
- Default authority stops after a successful private Save & Run. A competition submission
  requires the user to say to submit it explicitly.
- Keep the record repository private. Any later public notebook or Discussion must use a
  separately verified, slightly weaker public baseline and state honestly that it is not the
  current private champion. Never publish the exact active or final production artifact.

1. Build from the promoted immutable artifact.
2. Verify entrypoint, dependencies, file size, runtime, network restrictions, and output schema.
3. Compare hash against every prior upload to prevent duplicates.
4. Save-run and inspect complete logs and output artifacts.
5. Provide the user with exact notebook/version/output and the evidence report.
6. Submit only if the user delegated submission; otherwise stop at the verified artifact.

Browser control requires separate permission when API/CLI cannot perform the action.

## Stage 11 — Post-result learning

After a Kaggle result:

- Append the exact result to the immutable submission ledger.
- Compare local expectation with ladder outcome.
- Diagnose mismatch as a new hypothesis; never rewrite old evidence.
- Update confidence in mechanisms, not individual lucky scores.
- Do not immediately create another version merely because daily submissions remain.

## Red-team questions before every major claim

- What direct evidence supports this claim?
- What did we not inspect or run?
- Could this be leakage, overfitting, seed selection, duplicated output, or rounded-score noise?
- Is the comparison paired and reproducible?
- Which assumption, if false, reverses the decision?
- Does the worst-case behavior remain acceptable?
- Is this genuinely new behavior or only a renamed artifact?
- Am I reporting a feasible outcome as though it were probable?

## Stop and escalate conditions

Stop and tell the user immediately when:

- Rules or required authority are missing.
- Official behavior contradicts the current model.
- Baseline reproduction fails.
- Evaluation integrity or seed separation is compromised.
- The artifact duplicates a prior upload.
- A candidate only looks good through leaderboard feedback.
- The requested external action was not explicitly authorized.

Hard work, slow runs, or uncertainty are not blockers. Continue with safe local analysis while useful work remains.

## Reporting format

Every milestone report should lead with:

1. Outcome/verdict.
2. Raw evidence: commands, outputs, hashes, metrics, and source links.
3. What remains uncertain or unverified.
4. Exact next action and why it is the highest-value step.

Do not make the user infer whether something actually ran or merely was planned.
