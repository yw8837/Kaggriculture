# Ray C45 engine-screen addendum

This is a separate addendum to `research/campaign_3000/05_engine_screen`. The parent evidence
and its manifest SHA `A819E229...D48` remain unchanged.

The exact candidate is `dist/campaign_3000_public_agents/ray_c45.py`, SHA-256
`6CC3B69E...78F73`. Its file docstring says C45 while its embedded `__version__` says
`C64_HORIZON25`; the exact path and full SHA in `screen_config.json` define what was run.

Notebook provenance is `raykkretzschmar/kaggriculture-rank-your-agent` version 10,
Apache-2.0. The notebook inventory observed best score 2927.4 at version 9; that remote
notebook observation is context, not a local score claim.

Seeds `23000-23007` are explicitly `CONSUMED_SCREEN`, promotion-ineligible historical
development seeds. Ray is run on both seats against tetsu, kaito v22, boatlee V14, and frozen
Fa04 G1 under `kaggle-environments==1.32.6`: 16 cells/opponent, 64 total. No fresh seed or
external action is authorized.

## Result

Verdict: `ADDENDUM_SCREEN_EXECUTED_NON_PROMOTION`. All 64 cells were valid `DONE/DONE`;
runner failures and hidden abnormal statuses were both zero. Source, cell-registry, and installed
environment snapshots were identical at phase start/end.

| Opponent | Games | W-T-L | Match score | Mean margin | Game runtime p95 (s) |
|---|---:|---:|---:|---:|---:|
| tetsu adaptive | 16 | 0-0-16 | 0.00000 | -643.375 | 7.703 |
| kaito v22 price impact | 16 | 14-0-2 | 0.87500 | +4,109.375 | 6.560 |
| boatlee V14 | 16 | 0-0-16 | 0.00000 | -579.500 | 6.888 |
| Fa04 G1 | 16 | 16-0-0 | 1.00000 | +25,621.375 | 6.516 |
| overall | 64 | 30-0-34 | 0.46875 | +7,126.969 | 7.632 |

The positive overall mean margin is dominated by the large Fa04 G1 lane; it must not be read as
an overall win-rate or promotion signal. Whole-game runtime includes engine plus both agents.

Evidence hashes:

- `cell_registry.json`: `B6F2A9D16345625B72FAB7DD05A1E886D6D085DA29B1B20F0F8C74BBE1E215FD`
- `receipts/engine_1.32.6.completed.json`: `2E36DE392B8F0F7AEE751FE4DE6FE28D2A60E1E4FF4364E9CB32BF89E3B75C0D`
- `raw/ray_c45_exact.json`: `39672F7A9E4A6C09C8A9FCF8ADC44B678FC8D3C17E200995A317D329C331AA3A`
- `raw_games.json`: `45A2E19913B4D2AD2001255B06962D29E975556CB7EAA317FF730E73C31998FF`
- `summary.json`: `991FA149FE4ACBF38F82814A2D5FACA28F02188732CCFEEFEE565FB28018932A`

The final manifest digest is stored in `manifest.sha256`.
