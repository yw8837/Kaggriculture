# Kaggriculture Strong Expansion Baseline

A readable starting agent for Kaggriculture that demonstrates three useful ideas:

1. buy productive land early instead of staying on the starting quadrant;
2. combine mixed crops with a cow/sheep herd and reserve wheat for feed;
3. hire extra hands to work the expanded farm in parallel.

The package contains one standalone file, `main.py`, and uses only the Python standard library.
It can be inspected directly or packaged as a root-level Kaggriculture agent.

## What this baseline intentionally does not include

- opponent-specific adaptation;
- dynamic crop or herd optimization;
- advanced task assignment;
- robust near-capacity inventory routing;
- a private end-game policy.

It is a public learning baseline, not the current private competition agent. No leaderboard rating
is promised: early ratings depend on the changing opponent pool and match history.

For reliable comparisons, run both agents on the same seeds in both seats, record failures and
runtime, and inspect the full 720-turn horizon.

## Reproducible package

- File: `Kaggriculture - Strong Expansion Baseline.tar.gz`
- Member: root `main.py` only
- Source SHA-256: `BD32AEFDC00B1F0A41746EBACC4FCBF0AFF32AC061363179F15371B9ACE9A5C0`
- Archive SHA-256: `967A899A2BE149FF676B025E955AEDE2C42C0720C0A868428770A9B818F1144D`

License: no standalone reuse license has been selected yet.
