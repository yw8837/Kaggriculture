# Source manifest

Access date: 2026-07-31 (Asia/Seoul).

## Official ground truth

| Source | Pin / hash | Finding and design impact |
|---|---|---|
| Kaggle competition pages via CLI 2.2.4 | `kaggriculture` | 5/day; latest 2 active/final; best displayed; no private LB; final Bradley–Terry. Sets paired win-rate evaluation. |
| Competition archive | `AC6A529D72D2D03387672286D22B1BEB7DE53312D136D4F5CAD5C2CEF9754A37` | Downloaded after user joined. Contains only official rules/interface documents. |
| Official `AGENTS.md` | `6DC2CC96A99A14EAACE43E613121E327A14DC5A3CFFBD3C424FF480F76F2D352` | Agent contract and workflow. |
| Official `README.md` | `C43A7DDFCD3FED022B5344E20DFF6789F36799FBFE94D0BDD2FF71517F35E252` | Full game mechanics and economics. |
| `Kaggle/kaggle-environments` | commit `4f6e2763e2232605aacbade443715a9e2c9ef401`, package `1.32.2` | Exact Apache-2.0 simulator/tests; final reward is bank; action timeout 1 s. |
| Official simulator test suite | 67/67 passed against the installed package | Installed and pinned source are text-identical after line-ending normalization, SHA-256 `DCD33A832EA6EF1B7E527813DDCD45CEA314DC5CCE58B5BACA0D587CEF847A44`. |
| Official GitHub history | 23 environment-path commits; no open Kaggriculture PR/issues found | Important current rules came from PRs #1199, #1145, #1142, #1135, #1108, and #1107; stale pre-rebalance economics are rejected. |

The extracted competition documents and the pinned repository copies produced no textual
`git diff --no-index` output.

## Kaggle public notebooks

The complete 13-row result returned on the access date by `kaggle kernels list
--competition kaggriculture --sort-by voteCount --page-size 100` was downloaded with
metadata under `references/kaggle-kernels/`:

1. `bovard/kaggriculture-getting-started`
2. `alexandergremyakov/harvest-pulse-adaptive-landrush-baseline`
3. `ektarr/diversified-scheduler-baseline-kaggriculture`
4. `romanrozen/strong-statr-baseline-agent-lb-950`
5. `georgymamarin/kaggriculture-visualized-what-every-crop-pays`
6. `dheerajkannaujiya/start-with-basic-simple`
7. `mpwolke/doomed-kaggliculture-harvest`
8. `chaitanyajamble/kaggriculture`
9. `romantamrazov/kaggriculture-hamburger`
10. `pavloivanin/kaggriculture-baseline`
11. `romantamrazov/kaggriculture-yumerous`
12. `georgymamarin/kaggriculture-daily-replays-the-live-meta-report`
13. `pilkwang/kaggriculture-scenario-aware-economic-policy`

Mechanisms retained for falsification: cheap labor scaling, early reinvestment/land, spatial
task assignment, price-impact-aware liquidation, diversified crops, crop/animal hybrids,
both-seat evaluation, and replay-derived opponent fingerprints. Notebook performance claims
are not treated as verified until rerun locally.

Twelve executable agents were extracted from source cells without running arbitrary notebook
cells. Every notebook and output is hash-recorded in
`artifacts/opponents/public_kaggle/manifest.json` (manifest SHA-256
`36FED180963A3D3231231FEC163F99463E3B135C22A3D3D86F1AD184DBBE6B88`).

## Competition discussions

All three topics returned by the competition API on the access date were read with their
full bodies and comments: #731215 (daily top-episode dataset), #730708 (official getting
started/Discord notice), and #731152 (seat-swap and seed-variance claim). Topic #731152's
claim that seat swapping changes nothing was falsified locally: Harvest Pulse versus starter,
seed 0, produced 46,540 from seat 0 and 44,350 from seat 1, exactly reproducibly. Evaluation
therefore retains both seats and clusters uncertainty by seed/opponent pair.

The Kaggle-owned CC0 daily replay index was downloaded, SHA-256
`90BF4694EBAA2EA4E658FC8038011253C7155755D24EE60159315E3BDEF76851`.
Its first listed daily archive contains 864 episodes and is 13.64 GB; it was not downloaded
because the smaller replay corpus below already supports the initial meta analysis.

## Public replay corpus

`georgymamarin/kaggriculture-episodes`, Apache-2.0, downloaded through the Kaggle API.
`replays.parquet` is 98,761,719 bytes with SHA-256
`FC32964A3C16FB8D02F7A4A8B4EA2DFD6076D2553412991830836D42F3FAE3AE`.
Validation self-play rows are excluded from strength analysis. Coverage is rate-limited and
lags new submissions.

Five direct top-ladder match replays were also downloaded through the official episode API:
#89119601, #89123012, #89133857, #89135836, and #89138818. Their full action/state report
has SHA-256 `57D702B9A56B291BF3DE2929A3C9FE9565DDE8846204419AB11285944A28E691`.
The corrected action-time and daily-trajectory report has SHA-256
`BD480E0962060B7BE05CC44A48C45D8715A8E8D6AC592F1070DE4F32FFE8116B`.
Observed top policies hire roughly 10–13 daily hands, usually buy two additional land
quadrants, and combine crops with animals. The then-first-place `smlcr` opening repeated
exactly across four inspected replays: one cow, two sheep, 11 melon seeds, five strawberry
seeds, one carrot seed, one wheat seed, then six day-zero hires across the first two turns.

## GitHub

Repository-name search returned 17 matches. A separate GitHub code-body search for Python
`kaggriculture` references returned 34 files; the competition-specific hits reduced to the
same official repository and already inspected solution/tooling repositories. Current-
competition repositories inspected:
`niits/kaggriculture` (`3c89b816e634653fcde40918edae5f65ff356f84`),
`rooklift/krobus` (`92d8fe09386ad349a0e71ed9aba19fdc839db270`),
`sota1111/kaggriculture-claude` (`39d46d3cad48451d6a3ad28ae058bee299308902`),
`sota1111/kaggriculture-gpt` (`4f6e594ad2377820dfcca5bc6c58aa3d4edbb6c3`),
`jcdumlao14/Kaggriculture-AI-Agent`
(`ef2442a7ea4c5e82177f79305cfbb2bc9a4098fc`), empty repositories
`ShaunTheKing/kaggriculture-tools` and `liamnewsam/kaggriculture_competition`, plus
`seshurajup/myclew` replay/vector-environment tooling.

The non-Kaggle GitHub solutions reported no SPDX license through the GitHub API, so their
code is not copied into a submission. It may only serve as read-only research or an opponent.

## Coverage limits

- Cross-platform search found no additional authoritative rules beyond official sources.
- Discord was not scraped; Kaggle explicitly describes it as public but unmonitored and asks
  that important information be kept in the competition forum.
- This manifest is a dated snapshot and will be appended when new material changes strategy.
