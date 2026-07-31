# Fa_01 revision: fixed daily-labor sweep

Status: hypothesis killed at the registered development gate. No sealed validation, private
Save & Run, or competition submission was authorized or performed.

## Registered hypothesis

`configs/Fa_01_revision_daily_labor_development.json` fixed the hypothesis, three immutable
sources, seeds 22000-22015, both seats, two opponents, provenance requirements, and all gates
before execution. The only intended change from the overflow-safe Fa_01 parent was the ordinary
day labor target: 11, 12, or 13 hands. Final-day labor, expansion, crops, herd, market, routing,
and the overflow threshold were held fixed.

Required development gates were:

- overall match score at least 0.55;
- overall mean margin at least +300;
- parent match score at least 0.50 and parent mean margin at least zero;
- zero failed games, a start receipt, four workers, and unchanged source hashes.

## Results

Each variant ran 64 paired raw games: 16 seeds, both seats, against the formal
`final_day_labor` champion and the `overflow_drop` parent.

| Variant | Overall | Overall score | Overall margin | vs formal | Formal margin | vs parent | Parent margin | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 11 hands | 34-30 | 0.53125 | +590.42 | 16-16 | +534.63 | 18-14 | +646.22 | FAIL: overall score |
| 12 hands | 30-34 | 0.46875 | -931.20 | 17-15 | -992.75 | 13-19 | -869.66 | FAIL |
| 13 hands | 13-51 | 0.203125 | -5,408.91 | 6-26 | -5,585.19 | 7-25 | -5,232.63 | FAIL |

All 192 raw games completed without a failed agent. Every run started at Git HEAD
`674d7d6816ba89005849d3ebcc783e4bdcebe59d`, used four workers, wrote a start receipt, and
reported `sources_unchanged_during_run=true`.

Raw evidence:

| Variant | Source SHA-256 | Result SHA-256 | Start-receipt SHA-256 |
|---|---|---|---|
| 11 | `1730EB5CDA8D7122A6373EA8AF57E73E597236E84EEC081646CA542FBD0878EA` | `6AA98A10B6C8F0A7D2FDC96103D37E9AF87A4F2544F6EFF1318E4641C7B852E7` | `0BA57FD4E3DB28CF92C92A9C4EFB2A9A37FA4DC3DF8D3AFB36E7967A72C808F5` |
| 12 | `203DD3F97F248CC22A4676637BBE4660F61389B9B0F67DAE5548984006D009E7` | `9FC38ADAA741DE13B4C766E4B3661F049F90F9B3C5D70A22A7A73D6F8486D2EC` | `CA0899B4597AA39FA6ABEAA2EAF81B0D498B837ABA54A4FB955715FBEDCB85A1` |
| 13 | `13E373749958721ACFBE7E95DCDF4D5C83900F4F08FDD7808B2322CCB25925DC` | `10B6AC7414C225E90C0833B3D47318E8D94E306937DD9537155A76490D8D0541` | `D48CE0B41253BA78DE9B765F2CD2467D20B8200A94784293441AC5605BFFC22D` |

## Decision

No variant passed every registered condition, so the selection rule kills the fixed daily-labor
hypothesis. The 11-hand result had positive cash margin but did not establish reliable paired
superiority; changing the 0.55 threshold after seeing 0.53125 is not allowed. The formal champion
remains `final_day_labor`, and the old Fa_01 private Save & Run remains a rejected historical
artifact rather than the formal champion.

This result only falsifies a fixed global labor increase in this parent. It does not test
state-dependent hiring, exact task valuation, or deadline-aware worker allocation.
