# Evidence index

This index routes portfolio, solution, and report claims to reproducible evidence. Raw large files
remain ignored locally; hashes and conclusions are tracked.

## Ground truth and research

- Rules, metric, actions, timing, limits: `docs/problem_spec.md`
- Sources, pins, hashes, coverage limits: `docs/source_manifest.md`
- Facts versus inference: `docs/assumptions.md`
- Durable user scope and authority: `CAMPAIGN_DIRECTIVE.md`
- Evaluation and publication workflow: `WORKFLOW.md`
- Fixed seed/opponent partitions: `configs/evaluation_splits.json`

## Experiments and candidates

- Immutable experiment/audit log: `experiments/ledger.jsonl`
- Initial candidate reports: `reports/fast_expansion.md`, `reports/cow_tilt.md`
- Intermediate champion report: `reports/final_day_labor.md`
- Fa_01 report and sealed NO-GO: `reports/Fa_01_overflow_safe_inventory.md`
- Fa_01 sealed registration: `configs/Fa_01_sealed_revalidation.json`
- Fa_02 registered hypotheses and final NO-GO: `configs/Fa_02_hypothesis.json`,
  `configs/Fa_02_sealed_validation.json`, `configs/Fa_02_sealed_validation_v2.json`,
  `reports/Fa_02_horizon_aware_crop_rotation.md`
- Current formal champion/candidate state: `artifacts/champion/manifest.json`

## External state

- Competition submissions and episode outcomes: `submissions/ledger.jsonl`
- Public Discussion/Code identity and hashes: `publications/ledger.jsonl`
- Public release gate and initial exception: `docs/public_release_policy.md`
- Private record repository: `https://github.com/yw8837/Kaggriculture`

## Milestones

- `43d5efe`: durable campaign directive
- `milestone/fa-01-save-run-v2`: verified Fa_01 private Save & Run bytes
- `6f60a8d`: Discussion/Code release and preregistered Fa_01 sealed gate
- `75a2ab5`: honest Fa_01 NO-GO and preregistered Fa_02 development hypothesis
- `8cdc280`: capped Fa_02 sealed-v2 registration and full research archive

## Claims that are not yet supported

- A stable 1200-level private agent
- A measured rating for the public baseline
- Final top-three placement
- Complete coverage of every web source or final competition meta

These remain targets, not portfolio results.
