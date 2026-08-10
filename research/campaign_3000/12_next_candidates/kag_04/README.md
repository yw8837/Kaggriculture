# Kag_04 - Tetsu v16 Opening Sheep Bias

Status: **MATERIALIZED IMPLEMENTATION-FREEZE INPUT / NOT EVALUATED / HOLD**. `main.py` is 31,455 bytes with SHA-256 `797E2BFED6F17964CB08E3B1A77D72A978BDB8EE2C9EA9E7E552A454DA20F191`. Construction evidence records compile, guarded rewrite, base immutability, and `rescue_metrics` (`applied=1`) smoke PASS. No seed evaluation, package, or Kaggle action is evidenced here.

Kag_04 is an Apache-2.0-page-mapping-inference derivative of exact Tetsu v16, not clean-room work. The required base is `research/campaign_3000/06_candidates/snapshots/tetsu_v16.py`, SHA-256 `997E6BFC5234534E246E945BC61C87858EBF997AB85B0A5C9427DD4ED710F1B6`. Before packaging, preserve the attribution chain documented in `07_release/TETSU_IP_VERDICT.md` and provide Apache-2.0 license text.

The only delta is guarded opening sheep bias:

- Own placed/held animals must total zero.
- Base market must contain exactly one `BUY_ANIMAL COW 2`, exactly one `BUY_ANIMAL SHEEP 2`, and no other animal purchase.
- It changes only those quantities to `COW 1` and `SHEEP 3`.
- Total animal quantity stays four. Market length, every other order, farmer, and hands are preserved.
- Any malformed or ambiguous shape, or any own animal, returns the exact base-action object.

The runtime reads only the current own/public farm structure, own shed, and base market shape. It does not use step/day, seeds, replays, opponents, identity, price/price-impact, forecasts, SELL ordering, or Kag_03 behavior. Counters expose `calls`, `applied`, and each fallback class through `kag04_metrics()`, `get_metrics()`, and `rescue_metrics()`; `reset_rescue_metrics()` resets then returns a snapshot.

The materialization command used for this frozen input was:

```text
python -m kaggriculture_lab.candidates.kag04_sheep_first --base research/campaign_3000/06_candidates/snapshots/tetsu_v16.py --output research/campaign_3000/12_next_candidates/kag_04/main.py --receipt research/campaign_3000/12_next_candidates/kag_04/materialized_receipt.json
```

The canonical receipt is `materialized_receipt.json`. Any source change requires a new receipt and complete S/E re-freeze. Fresh-seed evaluation still requires the separately recorded OPEN authority. Packaging additionally requires the attribution and license files.
