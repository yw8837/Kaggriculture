# Decision log

| ID | Decision | Evidence | Revisit condition |
|---|---|---|---|
| D001 | Run Kaggriculture as the top-three campaign | Exact open simulator, two-month horizon, reproducible local games | Official rules/environment changes |
| D002 | Evaluate every matchup on identical seeds in both seats | A public seat-invariance claim was falsified locally | Only if official symmetry is proven in code/tests |
| D003 | Keep the two initial submissions unnumbered; Fa numbering starts at 01 | User naming directive | Never; filename contract is fixed |
| D004 | Publish Discussion then a current 1000-level baseline as a one-time bootstrap exception | Explicit user direction; public source is 99.78% line-similar to the unnumbered baseline and materially weaker than Fa_01 locally | No extension to Fa or later releases |
| D005 | Reject formal Fa_01 promotion while preserving its verified private Save & Run | Preregistered sealed direct gate failed 3/3 strength thresholds | New mechanism and new preregistered evidence, not threshold edits |
| D006 | Test Fa_02 as horizon-aware short-crop rotation | Official terminal cash/unsold-inventory rule; fixed plans can strand empty cells | Unbounded v1 was killed after its sealed parent ablation failed |
| D007 | Analyze several current top-user replays continuously | User directive; top meta changes and single replays are noisy | Refresh at meaningful leaderboard snapshots |
| D008 | Optimize public titles for honest discovery | User directive | Compare title/query log against views, votes, comments, forks |
| D009 | Retain the Fa_02 idea only with a two-cell workload cap | Same-seed cap sweep: cap2 was 17-15 and +23.91 vs parent; caps 1/4/6 had nonpositive margins | New untouched sealed v2 must pass every registered gate |
| D010 | Reject capped Fa_02 without Save & Run | Sealed v2 missed formal match score (0.59375 < 0.60) and cluster lower bound (0.47917 <= 0.50) | A materially new mechanism and untouched registration |
| D011 | Kill naive terminal carry drain after 24-turn variant | 3-61, mean margin -3,456.66; inspected challenger and parent both already finished with zero carried/shed goods | Revisit only as a full production/harvest/sale scheduler, not an early-return rule |
