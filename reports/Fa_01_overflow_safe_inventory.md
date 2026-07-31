# Fa_01 - Overflow-Safe Inventory

Status: private Save & Run complete; not submitted.

## Hypothesis and mechanism

The prior champion could finish a day with more goods in the shed plus worker inventories than
the 100-item shed can retain. Fa_01 reserves a ten-item buffer: once combined stock reaches 90,
loaded workers return to a shed tile and drop before taking ordinary farm tasks. The final-day
ten-hand liquidation fix and all earlier expansion, crop, and livestock decisions are preserved.

The production source adds eight audit comments. Its AST is identical to the evaluated source:

- Evaluated source SHA-256: `58C20426E4B32ED538E2E846D6579E43DC18F8802661FFE4364A5219E9B55196`.
- Commented production source SHA-256:
  `0AF2CC152748DD8539A1190675CBBFA7D70A90EF55EA009642EB3BDF473DAE3C`.
- `ast.dump(..., include_attributes=False)` equality: `True`.

## Direct and fixed gates

- Direct versus `final_day_labor`, seeds 300-315: 19-13, mean margin +485.34,
  clustered 95% interval 0.40625-0.78125, zero failures.
- Fresh confirmation versus `final_day_labor`, seeds 400-431: 44-20, mean margin +1,037.39,
  clustered 95% interval 0.5625-0.796875, zero failures.
- Combined direct result: 63-33 (65.625%), weighted mean margin +853.37, zero failures.
- Validation: 48-0, mean money 103,781.58, minimum 88,087, zero failures.
- Independent confirmation: 48-0, mean money 89,890.15, minimum 69,061, zero failures.
- Adversarial versus submitted `cow_tilt` and `fast_expansion`: 28-4 (87.5%),
  mean margin +5,176.31, minimum 74,901, zero failures.

The direct threshold was written only after all 96 direct games were available. The direct result
is therefore post-selection exploratory evidence, **not preregistered promotion evidence**.
Validation, adversarial, confirmation, runtime, and packaging ran later, but they do not repair
that ordering defect.

An adversarial audit also exposed regressions hidden by saturated win counts:

- Validation money versus the previous champion: 104,069.73 to 103,781.58 (mean -288.15),
  with 21 games higher and 27 lower.
- Adversarial money versus the previous champion: mean -600.06, with 13 games higher,
  18 lower, and one tied; the win record moved from 31-1 to 28-4.

These regressions require a new sealed-seed gate before formal champion promotion.

## Sealed revalidation (registered before opening results)

The statistical thresholds and seeds were committed and pushed in `6f60a8d` before execution.
Fa_01 received a **NO-GO**; thresholds were not edited after the result.

| Gate | Required | Observed | Result |
|---|---:|---:|---|
| Direct match score, 128 both-seat games | >= 0.58 | 0.578125 (74-54) | FAIL |
| Direct seed-cluster bootstrap 95% lower | > 0.50 | 0.4765625 | FAIL |
| Direct mean margin | >= +500 | +445.39 | FAIL |
| Direct failures | 0 | 0 | PASS |
| Safety match-score delta vs previous | >= -0.03 | +0.02344 | PASS |
| Safety mean-money delta vs previous | >= -250 | +663.30 | PASS |
| Safety p10-money delta vs previous | >= -1,000 | -648.90 | PASS |
| Safety failures | 0 | 0 | PASS |

The safety panel improved on average (118-10 versus the previous champion's 115-13), but the
direct gate failed all three strength thresholds. A 0.001875 miss on match score is still a miss;
the lower confidence bound and margin also failed independently. Formal promotion is rejected.

## Runtime, archive, and private Save & Run

- Runtime replay: 720 calls, zero invalid outputs; p50 0.5317 ms, p95 1.5169 ms,
  p99 1.9439 ms, maximum 2.7367 ms.
- Numbered artifact: `Fa_01 - Overflow-Safe Inventory.tar.gz`.
- Deterministic archive SHA-256:
  `1B52522D0CD55536F1C45B73F5FC5A37A27CF924A218FA009D1D1786B72F53D1`;
  4,894 bytes; root `main.py` only; two builds were byte-identical.
- Kaggle private kernel: `yw8837/fa-01-overflow-safe-inventory`, Version 2, status `COMPLETE`.
- Downloaded Kaggle output: 4,894 bytes with the same archive SHA-256; no error,
  traceback, failed-run, or missing-cell-ID warning contexts in the Version 2 log.

## Verdict and limits

Fa_01 remains a verified private Save & Run artifact, but its formal champion promotion is
**rejected** by the preregistered sealed gate. `final_day_labor` remains the formal local champion.
Fa_01 is not a Kaggle competition submission. Nothing here establishes a future 1200 rating or
final top-three placement; those remain campaign targets requiring further research and ladder
evidence.
