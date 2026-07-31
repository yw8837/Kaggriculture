# cow_tilt — GO, promoted champion for initial ladder probe

## Mechanism

Keep the verified fast-expansion policy but shift the mature herd from six cows/three sheep
to seven cows/two sheep. The initial one-cow/two-sheep opening remains unchanged, isolating
the expansion composition as the ablation.

## Evidence

- Source SHA-256: `6CDE0002281620BAED323D0EDA5DBF48A6D0B7C4B8A3564BC951A757805E621E`
- Initial paired probe: 45/48 wins; 13/16 against `fast_expansion`, 16/16 against each public
  strong opponent; mean 88,233.96; minimum 70,176.
- Fresh seeds 100–115 versus `fast_expansion`: 19/32 wins, mean margin +913.41.
- Validation: 48/48 wins, 0 failures; mean 98,912.35; minimum 85,527.
- Holdout: 48/48 wins, 0 failures; mean 90,703.25; minimum 65,422.
- Adversarial seeds 9000–9003: 3/8 against `fast_expansion`; self-play 4/4 by each seat side,
  zero failures, mean 89,257.75.
- Timed official game: 719 calls; p50 0.5945 ms, p95 1.9243 ms, max 38.1695 ms.
- Deterministic archive SHA-256:
  `73F15AECDD3CC786D755540C71D1E6035AD8D4435E813A02E56E923C8F791A86`;
  4,311 bytes; only root `main.py`.

## Uncertainty and verdict

Combined direct comparison is 35–21, but the clustered uncertainty is still material and the
adversarial slice favors the secondary. No local evaluation can reproduce hidden top-three
decision logic. This is therefore a GO for an authorized ladder probe, not proof of expected
top-three placement.

The numeric promotion threshold was not pre-registered before early tuning; it is recorded as
a process limitation. The untouched holdout, zero crashes, isolated animal-mix ablation, and
reproducible packaging are sufficient for the already-authorized first two submissions.
