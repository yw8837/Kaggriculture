# final_day_labor — promoted local champion, not submitted

## Mechanism

The submitted `cow_tilt` returned from market planning before hiring on day 29. That left only
the permanent farmer to harvest and liquidate the final day. This candidate changes only that
branch: hire ten hands during hours 0–3 on day 29, prioritize those hire orders, then keep the
existing liquidation policy. Days 0–28 and the seven-cow/two-sheep strategy are unchanged.

## Causal ablations

- Final-day 10 hands versus `cow_tilt`, seeds 0–15: 30/32 wins, mean margin +4,470.06,
  clustered 95% interval 0.84375–1.0, zero failures.
- Fresh seeds 100–115 versus `cow_tilt`: 31/32 wins, mean margin +4,291.97,
  clustered 95% interval 0.90625–1.0, zero failures.
- Delaying the expanded herd was rejected: 1/32 versus `cow_tilt`, mean margin -8,748.47.
  Combining it with final-day labor was also rejected at 3/32.
- Twelve final-day hands lost 19–29 to ten on fresh seeds 200–223; thirteen lost 14–34.
  Ten is retained rather than extrapolating that more labor is always better.

## Fixed evaluation gates

- Development: 64/64 wins, mean 104,089.11, minimum 94,282, zero failures.
- Validation: 48/48 wins, mean 104,069.73, minimum 89,731, zero failures.
- Holdout: 48/48 wins, mean 95,329.81, minimum 67,920, zero failures.
- Adversarial direct pool (`cow_tilt` and `fast_expansion`, seeds 9000–9007): 31/32 wins,
  mean margin +5,740.69, minimum 74,287, zero failures. The sole loss was one seat against
  `fast_expansion` on seed 9002; the opposite seat won.

## Safety, runtime, and packaging

- Source SHA-256: `112AF9EC28030B53CE852927CEE986834F18F0245F3A88FB2E06F423291C9F8B`.
- Replay-observation benchmark: 720 calls, zero invalid outputs; p50 0.5145 ms,
  p95 1.4787 ms, p99 1.8341 ms, maximum 2.2181 ms.
- Deterministic archive SHA-256:
  `59281C6434D6D48C429DDC7950266A1083454978A0425D143480E9BB75559670`;
  4,382 bytes; only root `main.py`; two builds were byte-identical.
- Static search found zero references to requests, urllib, sockets, subprocesses, or HTTP URLs.

## Verdict and limits

Promote as the local champion. Do not submit without fresh user authorization. The improvement
is strongly supported against the reproduced pool, but current top-three source code is not
available and the public pool is much weaker than the top ladder. This is not evidence that the
candidate itself is top-three capable; a ladder probe would still be required.
