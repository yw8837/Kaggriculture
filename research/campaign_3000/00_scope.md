# Kaggriculture 3000+ campaign scope

- Opened UTC: `2026-08-08T17:43:27.6369579Z`
- Worktree: `work/campaign_3000`
- Base commit: `72b12208dd8faf78df267738b017ec3a049334ea`
- Branch: `agent/campaign-3000`
- Independent auditor task: `019fb8b8-7758-7860-9304-39eb4f06c65c`
- Initial audit state: `HOLD`

## Objective

Produce the strongest evidence-backed private Kaggriculture candidate feasible, targeting a live rating of at least 3000. This is a target, not a guarantee. Rank and rating are external noisy signals; local promotion requires paired, both-seat, fresh-seed and adversarial evidence.

## Naming directive (supersedes the historical Fa convention)

- The next two completed production artifacts are `Kag_01 - Short Description.tar.gz` and `Kag_02 - Short Description.tar.gz`.
- Later production artifacts continue as `Kag_XX` in upload order.
- Existing `Fa_*`, `bot_*`, `Ge_*`, and unnumbered artifacts remain immutable historical records and are not renumbered.

## Authority

- Authorized now: local reads, web/API read-only research, code, tests, simulation, Git commits/pushes to the private evidence repository.
- After exact independent-audit PASS: perform only the separately frozen upload/publication payload explicitly covered by the user's instruction and audit verdict.
- Competition submission is excluded unless the user explicitly says to submit.
- Browser write/control is excluded unless separately required and authorized.

## Population definitions

1. **Our submission inventory**: every Kaggriculture competition submission returned by the authenticated Kaggle API/CLI at the snapshot UTC, plus every observable episode row and replay ID. Missing historical or private fields remain `UNVERIFIED`.
2. **Leaderboard top 25**: ranks 1–25 in one pinned public leaderboard snapshot. Each row records rank, team, rating, retrieval UTC, visible public Code/Discussion and replay availability. No inaccessible private strategy is inferred.
3. **Public Code inventory**: all competition-linked public notebooks returned by the chosen Kaggle listing/API pagination until an empty page or documented API boundary, deduplicated by ref+version. A UI sort view is not called the whole population unless its pagination is exhausted.
4. **Discussion inventory**: all competition discussion topics returned through every accessible page at the snapshot UTC, deduplicated by topic ID.
5. **Models inventory**: all competition-linked model objects discoverable through an official Kaggle endpoint. If no usable endpoint exists, record `UNVERIFIED`, not zero.
6. **External corpus**: saved English/Korean query families covering official simulator/source, GitHub code/issues, finished bot competitions/hackathons, papers, formulas, engineering columns and community discussions. Completion means diminishing new mechanisms across a second pass, never literal internet exhaustiveness.

## Required provenance per retained source

- Retrieval UTC, URL/ref/ID, author/owner, version/commit where available.
- Raw saved bytes or normalized response plus SHA-256.
- Authority class: official, primary research, verified implementation, discussion, anecdote.
- Exact mechanism, applicability, failure mode, and falsifying local experiment.
- `EXECUTED`, `READ_ONLY`, `REPRO_FAILED`, or `UNVERIFIED` status.

## Tool state at start

- `agent-reach doctor --json`: GitHub, Exa, generic web, YouTube available; Reddit and X unavailable because no backend is installed/authenticated.
- `insane-search`: engine module installed; referenced first-run `setup/setup.sh` is absent from this installation. Use the engine only for a concrete blocked URL and preserve output.
- `/context7`: `mcporter list --json` exposes a healthy two-tool server. Library resolution was executed for the official Kaggle CLI; retain the exact query/document output before claiming substantive use.
- `/serena`: `mcporter list --json` exposes a healthy 23-tool server. `initial_instructions` and project activation were executed, but the stdio wrapper currently loses active-project state between calls; symbolic source inspection remains `PARTIAL` until an explicit-project invocation or persistent session succeeds.
- Platform approvals: current execution profile is unrestricted filesystem/network with approval policy `never`; routine local commands should not prompt.
- Harness limitation: Claude `TeamCreate`/`opus` are unavailable in this Codex runtime. Equivalent subordinate lanes use Codex multi-agent tools and shared files; they are not independent auditors.

## Experiment boundary

- One candidate equals one bounded causal hypothesis.
- Development, confirmation, robustness and adversarial pools are disjoint and machine registered before opening.
- Public replay, LB and old seed evidence may generate hypotheses but cannot serve as fresh promotion evidence.
- Exact source/opponent/config/tool hashes and start receipts are mandatory.
- No external action before exact frozen independent-audit PASS.
