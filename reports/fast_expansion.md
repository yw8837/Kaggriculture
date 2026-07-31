# fast_expansion — GO for initial ladder probe

## Mechanism

Reconstruct the public top-ladder opening: ten daily hands, initial cow/sheep mix, strawberry-
heavy compounding, and land purchases around days 5–18. Unlike the public cow baseline, it
can use three quadrants and maintains six cows plus three sheep.

## Evidence

- Source SHA-256: `406BC82979637A42F2848382AD5E0248C403BBB346D09CF93859DC2D5761F25C`
- Development: 96/96 wins, 0 failures; mean 90,396.67; minimum 64,533.
- Validation: 48/48 wins, 0 failures; mean 97,048.60; minimum 84,845.
- Holdout: 48/48 wins, 0 failures; mean 90,275.48; minimum 68,523.
- Timed official game: 719 calls; p50 0.5585 ms, p95 1.4975 ms, max 33.5731 ms.
- Deterministic archive SHA-256:
  `2ECB98759CA02AB28C83C88832DB8DDFEEDDD7E2E4A7B80EA9BD0F1292251484`;
  4,314 bytes; only root `main.py`.

## Uncertainty and regression

The public opponent pool does not contain the hidden source of current top-three agents.
Against the promoted seven-cow variant over seeds 0–7, 100–115, and 9000–9003, this policy
loses 21–35 overall. It remains the secondary because it wins the adversarial 9000–9003 slice
5–3 and provides a different product mix.

The numeric promotion threshold was not pre-registered before early tuning; this weakens the
statistical claim. The clean holdout, zero failures, ablation against the public cow baseline,
and exact hashes support a limited initial ladder probe—not a top-three guarantee.
