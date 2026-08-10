# Historical market/preemption variant screen

This is selection evidence only. It used only the already-used seeds 50000-50015,
both seats, default scenario, and the exact Tetsu v16 opponent. It opens no fresh
pool and supplies no promotion, SaveRun, submission, or publication authority.

Control: `research/campaign_3000/06_candidates/snapshots/tetsu_v16.py`, SHA-256
`997E6BFC5234534E246E945BC61C87858EBF997AB85B0A5C9427DD4ED710F1B6`.
Every row has 32 valid games and zero framework failures. `Trigger` is the sum of
the candidate's action-neutral mechanism counter over the 32 games (`reordered`
for SELL permutations, `trigger` for a successful premium-preemption execution).

| Variant | Source SHA-256 | W/T/L | Score | Mean margin | Trigger | Result |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| old inventory-desc SELL slots | `9034026D6872109C9AF6BD5582F65446312F0D109654BE388A17D8F8A186FE36` | 0/0/32 | 0.00000 | -2007.31250 | 462 | FAIL |
| quantity-desc SELL slots | `9A26F77FF6E5A715552FBE1DF2AC9C7590088AD766991D4C971F5BEB75BF246E` | 4/0/28 | 0.12500 | -580.56250 | 372 | FAIL |
| inventory-asc SELL slots | `8868B6EBC3C9E156DDEE74813F0040F3B0261120844EB6A4C4C1AE23637BE35C` | 0/0/32 | 0.00000 | -2936.43750 | 708 | FAIL |
| quote-times-quantity SELL slots | `472F09AA25C780B93EA4F320C261E93A9459BB22EB408B7BD5FED5A4744CA5BC` | 6/0/26 | 0.18750 | -216.31250 | 382 | FAIL |
| preempt horizons 1,2,3 | `789C4144C1371F87842735C5A35C38BDB192A619CAC3C17CA5DC5CA1FD4DCBF5` | 0/32/0 | 0.50000 | 0.00000 | 456 | FAIL |
| preempt fraction 1.0 | `89E9AB25A52AA05A799544B9E85009DAA24B04B5DB9BA235A9C94E1F1BD7C004` | 0/32/0 | 0.50000 | 0.00000 | 456 | FAIL |
| preempt max batch 15 | `771F457D82826C7F4F364DF96A83AE730BD4A9D949FF5E7AB0C5B56541238C93` | 0/22/10 | 0.34375 | -35.68750 | 456 | FAIL |
| preempt horizons 4,3,2,1 | `598F739B47BE129FF632E4DB9A41B70C5D232DA9E34C4078090D2BC13D1AF2C5` | 32/0/0 | 1.00000 | +985.81250 | 410 | PASS #1 |
| preempt horizons 5,4,3,2,1 | `BFE3775D3BAA899F709A7DA117EEEE3782C103C40EFD0C2CB03A9161179ABA32` | 32/0/0 | 1.00000 | +966.12500 | 410 | PASS #2 |
| seat0-only horizons 4,3,2,1 | `D1BE82F47D257D6F142A40A8636EDB312B87974B9927366F8809A2767844B76F` | 16/16/0 | 0.75000 | +492.90625 | 433 | PASS, outside top two |

The bounded selection rule keeps at most two variants with score greater than
0.5 and positive mean margin. It therefore retains the 4-turn and 5-turn
prepend variants. The 4-turn variant is preferred: it is the smaller delta and
has the larger observed mean margin on this reused diagnostic.

The 4-turn result is not a seat artifact: seat 0 and seat 1 are each 16/0/0
with identical mean margin +985.8125; every individual margin is positive
(minimum +275, maximum +2274). The 5-turn result is likewise 16/0/0 per seat,
with individual margins from +255 to +2253.

Canonical summary:
`screen_summary.json`, SHA-256
`F738423F448B6CCC5662172B0F9B22F18B660D210FA99C1F90BABBCE45686466`.
Raw report hashes and exact delta descriptions are embedded in that summary;
the materialization manifest is `variant_manifest.json`.
