# Kaggriculture project rules

Read `PROJECT_BRIEF.md` and `WORKFLOW.md` completely before any design, coding, experiment, upload, or submission.

Follow the stages and gates in `WORKFLOW.md` in order. Skipping a gate requires an explicit written reason and user approval when it changes risk or scope.

## Objective

- Target: final top 3.
- Never present the target as guaranteed. Report evidence, uncertainty, and failure risk honestly.

## Authority

- Local reading, coding, simulation, and reversible diagnostics are authorized.
- Do not submit to Kaggle, publish a notebook/dataset/discussion, accept rules, or control Chrome unless the user explicitly authorizes that exact action.
- Prefer Kaggle API/CLI. Use Chrome only after explaining why API/CLI is insufficient and receiving permission.

## Evidence contract

- Never say "completed", "verified", "searched everything", or "safe" without showing the command output, report, hash, or source manifest that proves it.
- Separate facts, model assumptions, estimates, and guesses in every decision report.
- If a source, run, or check was not performed, say so immediately.
- Re-read the original file/output for important judgments; do not rely only on summaries.

## Research gate

- For material strategy changes, record consulted sources, access date, exact relevant finding, and how it changes the design.
- "Full research" requires a saved source manifest. A few searches never qualify.
- Public solutions are inputs, not the goal. Extract reusable mechanisms and validate them locally.
- Use Agent-Reach for broad/current cross-platform research. Use Insane Search when a specific page or blocked source cannot be accessed normally.
- For large independent work, split bounded research, simulator audit, evaluation, and adversarial review across parallel agents. The primary agent must verify important claims from original sources and raw outputs.

## Experiment and promotion gate

- Maintain one immutable champion and independently reproducible challengers.
- One version equals one hypothesis. Record code hash, configuration, seeds, opponents, metrics, and exact diff from champion.
- Never upload duplicate outputs under new names. Compare artifact hashes before every upload.
- Promote only after held-out seeds and opponent sets show improvement with confidence intervals and acceptable worst-case performance.
- Leaderboard score alone cannot promote a model. Never probe the public leaderboard to infer hidden state unless identifiability is demonstrated first.
- No daily "first submission" ritual and no neutral probes. Submission budget is scarce.

## Verification before an authorized submission

1. Reproduce the candidate from a clean command.
2. Validate file/schema/runtime and competition rules.
3. Compare candidate against the immutable champion on fixed and held-out suites.
4. Check robustness, worst case, variance, and regression metrics.
5. Verify artifact hash and prove it differs from prior submissions.
6. Save a concise evidence report and submission ledger entry.
7. Ask for final user authorization if not already explicit.

## Context discipline

- Do not import PS-S6E7 row-probing tactics or stale conclusions into this simulator competition.
- When context is uncertain, stop and re-read `PROJECT_BRIEF.md`, the experiment ledger, and raw outputs.
- Keep research, implementation, evaluation, and external publishing as distinct stages.
- Maintain a live plan with at most one in-progress implementation step and give concise evidence-backed progress updates during long work.
- Do not stop at analysis when the user requested a build. Continue through implementation and proportional verification while an authorized, safe next step exists.

## Current blocker

- Competition data download returns HTTP 403 until the user accepts the Kaggriculture rules. Do not bypass this.
