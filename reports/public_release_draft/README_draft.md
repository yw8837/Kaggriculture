# Kaggriculture Agent | Early Expansion & Mixed-Farm Baseline

This is a readable, reproducible Kaggriculture starting agent for players who want to move beyond
a single-crop opening without starting from a large optimizer. The source is one standalone
`main.py` file and uses only the Python standard library.

## Strategy at a glance

| Phase | Public baseline behavior | Main trade-off |
|---|---|---|
| Opening, days 0-4 | Starts a fixed crop and herd plan while preserving working capital. | Fixed targets are easy to understand but do not react to the opponent. |
| Expansion, days 5-18 | Conditionally buys up to two additional land quadrants when its budget buffer permits. | Land increases capacity but competes with animals, seeds, and labor for cash. |
| Production | Runs mixed crops, cow/sheep slots, a wheat feed reserve, and up to twelve hands. | Simple labor sizing can overpay when little useful work remains. |
| Late horizon | Harvests held output, sells inventory, and returns carried goods near the end. | End-game and near-capacity routing are intentionally basic. |

## Agent contract

`agent(obs)` returns the three required action channels: `farmer`, `hands`, and `market`. The policy
is deterministic and requires no internet access or external data.

## How to evaluate a change

1. Run baseline and challenger on the same seed list in both seats.
2. Score the full 720-turn horizon.
3. Keep development and confirmation seed sets separate.
4. Record failures, invalid actions, match outcomes, and money deltas.
5. Report runtime percentiles and the slowest call.
6. Inspect land timing, cash, labor, carried inventory, shed inventory, and end-game actions.

## Reproducible package

- Archive: `public_expansion_baseline.tar.gz`
- Member: root `main.py` only
- Source SHA-256: `BD32AEFDC00B1F0A41746EBACC4FCBF0AFF32AC061363179F15371B9ACE9A5C0`
- Archive SHA-256: `967A899A2BE149FF676B025E955AEDE2C42C0720C0A868428770A9B818F1144D`

The notebook verifies the source bytes and fixes gzip/tar metadata so identical source produces
identical archive bytes.

## Limitations and reuse

The policy has fixed crop and herd targets, no opponent conditioning, simple labor sizing, and
basic late-horizon and inventory rules. It is a public learning baseline, not a leaderboard
promise or the current private competition agent.

No standalone reuse license has been selected. Check the applicable Kaggle terms before reusing
the source elsewhere.
