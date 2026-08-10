# Primary-source mechanism addendum

Cutoff: 2026-08-10T03:15Z. This addendum supplements the 35-source frozen
external inventory; it does not claim the whole web was enumerated.

| Primary source | Verified mechanism | Kaggriculture use | Rejection / falsifier |
|---|---|---|---|
| Kaggle `kaggle-environments` repository, https://github.com/Kaggle/kaggle-environments | The official environment is locally executable and replay-renderable; engine identity must be pinned. | Keep 1.32.6 engine/config/source hashes in every diagnostic and fresh receipt. | Reject any result whose actual imported engine differs start/end. |
| Zhou et al., *Reactive Task Allocation and Planning for Quadrupedal and Wheeled Robot Teaming*, https://arxiv.org/abs/2110.08436 | Local/global reallocation repairs disturbances without rebuilding the whole plan. | Kag_03 changes only the currently disturbed actor when its live tile is a weed; the frozen Tetsu schedule remains the fallback. | No observed repair, new route drift, or worse direct Kag_01 lane falsifies it. |
| Choudhury et al., *Dynamic Multi-Robot Task Allocation under Uncertainty and Temporal Constraints*, https://arxiv.org/abs/2005.13109 | Online execution can separate individual action policies from conflict resolution. | Reserve the single actor action consumed by a weed repair and preserve all other farmer/hands actions. | Duplicate action ownership, inventory conflict, or nonlocal action differences reject it. |
| Chen et al., *Integrated Task Assignment and Path Planning for Capacitated Multi-Agent Pickup and Delivery*, https://arxiv.org/abs/2110.14891 | Capacity and actual delivery cost must inform assignment rather than a lower-bound route alone. | Kag_04 may sell only live shed stock and must preserve order cap, item quantity, non-SELL orders and terminal capacity safety. | Oversell, order-cap conflict, price-blind loss or new invalid order rejects it. |
| Kaggriculture Discussion 734000, https://www.kaggle.com/competitions/kaggriculture/discussion/734000 | Byte-identical submissions can diverge strongly because ladder ratings are path-dependent. | Require paired simulator evidence and never select by a single live rating. | A duplicate submission is not a valid experiment. |
| Kaggriculture Discussion 734033, https://www.kaggle.com/competitions/kaggriculture/discussion/734033 | Actions, not only product value, are a scarce constraint. | Count repair/liquidation action cost and measure net cash/margin, terminal inventory and weeds. | Extra actions without causal recovery reject the delta. |

The two implemented deltas remain intentionally smaller than the cited general
methods. Neither uses opponent identity, submission ID, episode ID, source
episode, seed, or a fixed replay step.
