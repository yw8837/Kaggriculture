# Conventions
- Evidence first: immutable raw bytes and SHA-256; label observed, inferred, failed, and unverified separately.
- Each candidate is a bounded causal hypothesis. Public and leaderboard replays generate hypotheses but are never fresh promotion evidence.
- Preserve unrelated dirty user work; campaign work stays in an isolated worktree.
- Production validators use canonical JSON and explicit ValueError checks, not optimized-away assert.
- Avoid broad exception masking in agent logic; record invalid actions and failures explicitly.