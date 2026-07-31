# Experiment protocol

- `ledger.csv` is append-only.
- One experiment tests one hypothesis.
- Record source hash, configuration, development/held-out seeds, opponents, both-seat
  results, confidence interval, worst case, and exact diff from the immutable champion.
- A challenger is promoted only after the held-out gate passes.
- Submitted artifacts are copied to an immutable champion/submission directory and never
  edited in place.

