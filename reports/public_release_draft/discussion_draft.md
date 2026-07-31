# Kaggriculture Baseline Guide | Expansion Agent & Reproducible Evaluation

I am sharing a readable Kaggriculture baseline for players who want to move beyond a single-crop
starter without jumping straight into a large optimizer.

The agent focuses on three ideas:

- early land expansion;
- a fixed mixed-crop plan plus a cow/sheep herd;
- extra hands to keep the larger farm productive.

The source is standalone and fully visible. The package contains only root `main.py`, so it is easy
to inspect, fork, and test locally.

## Known limitations

The hiring rule is deliberately simple and may overpay. Crop and herd targets are fixed, the policy
does not react to the opponent, and its late-horizon and inventory routing are intentionally basic.
This is a public learning baseline, not a current private competition agent or a guaranteed rating.

## How I recommend evaluating changes

Use the same seeds in both seats, keep development and confirmation seeds separate, record invalid
actions and runtime, and inspect the complete 720-turn horizon. A single early ladder result is not
enough to establish general strength.

I would be interested to hear which part you improve first: crop mix, herd composition, labor
sizing, or the end game.

## Fixed publication titles

- Discussion first: **Kaggriculture Baseline Guide | Expansion Agent & Reproducible Evaluation**
- Kaggle Code second: **Kaggriculture Agent | Strong Expansion Baseline**

These titles intentionally omit unverified rating claims and unstable implementation counts.
