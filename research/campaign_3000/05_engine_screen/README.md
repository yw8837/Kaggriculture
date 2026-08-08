# Campaign 3000 engine/public-agent screen

This directory is a local-only, non-promotion screen of five exact-byte public agents under
`kaggle-environments==1.32.6`, with a small same-cell comparison against `1.32.2`.

## Frozen scope

- Seeds `23000-23007` are explicitly `CONSUMED_SCREEN`. They are historical consumed
  development seeds from `candidates.A.development`; they are not fresh promotion evidence.
- Main engine: `1.32.6`.
- Main cells: every public agent against frozen Fa04 G1 on both seats and all eight seeds
  (80 games), plus the complete five-agent round robin on both seats and all eight seeds
  (160 games).
- Engine comparison: the 20 Fa04 cells on seeds `23000-23001` under both `1.32.2` and
  `1.32.6`.
- No upload, submission, publication, browser action, or seed opening is authorized.

The formal run uses the public files directly from `dist/campaign_3000_public_agents/*.py`.
It does not copy, regenerate, or rewrite agent bytes. Source, runner, configuration, installed
engine files, resolved environment configuration, start/end snapshots, exact cell keys, raw
runner JSON, and receipts are hash-pinned here.

## Commands

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe research\campaign_3000\05_engine_screen\run_screen.py prepare
.\.venv\Scripts\python.exe research\campaign_3000\05_engine_screen\run_screen.py run-1326
uv run --isolated --no-project --with kaggle-environments==1.32.2 python research\campaign_3000\05_engine_screen\run_screen.py run-1322
.\.venv\Scripts\python.exe research\campaign_3000\05_engine_screen\run_screen.py analyze
```

`manifest.json` and `manifest.sha256` are created only after the verification logs and this
README contain the final result. See `summary.json` and `engine_comparison.json` for metrics.

## Pre-formal compatibility probe

Before the formal receipt was created, seed `23000`, candidate seat 0 was run once per public
agent against Fa04 G1 to check import/runtime compatibility. All five returned `DONE/DONE` and
no exception. Elapsed game times were 3.927-4.742 seconds. This probe used an already-consumed
screen seed, produced no promotion claim, and is not included in any formal aggregate.

## Result

Verdict: `SCREEN_EXECUTED_NON_PROMOTION`. All 260 engine-specific cells ran. The 1.32.6
phase had 240/240 valid games, zero runner failures, and zero hidden abnormal statuses. The
isolated 1.32.2 phase had 20/20 valid games, zero runner failures, and zero hidden abnormal
statuses. Both phase receipts report unchanged source, config, cell registry, and installed
environment snapshots from start to end.

### Public agents versus Fa04 G1 on 1.32.6

| Public agent | Games | Match score | Mean margin | Game runtime p95 (s) |
|---|---:|---:|---:|---:|
| boatlee V14 | 16 | 1.00000 | +25,621.375 | 7.295 |
| flex adaptive | 16 | 1.00000 | +25,621.375 | 7.168 |
| indar route 2948-9 | 16 | 1.00000 | +22,700.500 | 7.046 |
| kaito v22 price impact | 16 | 1.00000 | +24,159.250 | 7.058 |
| tetsu adaptive | 16 | 1.00000 | +25,621.375 | 7.266 |

Boatlee, flex, and tetsu produced equal final-result vectors against G1 across these 16 cells.
That is a result-vector observation only; it does not prove action-trace or source equivalence.

### Five-agent round robin on 1.32.6

Each public agent has 64 games: four opponents x eight seeds x both seats.

| Public agent | Games | Match score | Mean margin | Game runtime p95 (s) |
|---|---:|---:|---:|---:|
| tetsu adaptive | 64 | 0.96875 | +3,314.281 | 19.938 |
| boatlee V14 | 64 | 0.59375 | +2,311.125 | 8.055 |
| flex adaptive | 64 | 0.59375 | +2,311.125 | 8.055 |
| kaito v22 price impact | 64 | 0.21875 | -3,232.688 | 19.938 |
| indar route 2948-9 | 64 | 0.12500 | -4,703.844 | 8.370 |

The runtime is whole-game wall time for both agents plus the engine. In particular, an agent's
round-robin p95 includes shared games and is not an isolated per-agent latency measurement.

### Same-cell 1.32.2 versus 1.32.6 comparison

The only resolved default configuration change was `townCenterSellInterval: 12 -> 24`.
All 20 final reward tuples changed; 16/20 win/tie/loss outcomes changed. Aggregate public-agent
match score against G1 changed from `0.20` on 1.32.2 to `1.00` on 1.32.6. Mean paired margin
delta (`1.32.6 - 1.32.2`) was `+88,477.45`.

- Boatlee, flex, indar, and tetsu changed from 0/4 wins to 4/4 wins.
- Kaito stayed at 4/4 wins, while its mean margin decreased by 8,585.5.
- The 20-cell comparison is deliberately small and uses consumed seeds; it demonstrates large
  local engine sensitivity but is not a promotion estimate.

### Evidence hashes

- `cell_registry.json`: `CC328669C935ED4D60201CBF1C94F067BC884F725A94CCD8495B68F37C9DC4AE`
- `receipts/engine_1.32.6.completed.json`: `8C04811AFF8B0FF21AF3AF3858FFF863A71F8F07ABFB2FC8D57104C943933F85`
- `receipts/engine_1.32.2.completed.json`: `C639A877E9DD1B3C7CEAE1528267A82E2D07F4A6BC5703ABE87AE91DFF5B977B`
- `raw_games.json`: `1449F6AB335BC910B57995EE4711042C052FC4B2F1D823D0333B57DF813C42DA`
- `engine_comparison.json`: `7FBC90385D085932544E693836CA4B24EC28E9AAD7A28DB9AA442E22FB46B2F6`
- `summary.json`: `193FB33CA537681E510C74C9E6ED947CD1FB0D806911BB1C93AF95AC8C50D94F`

The final manifest hash is stored in `manifest.sha256` after verification.
