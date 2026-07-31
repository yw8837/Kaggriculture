# Kaggriculture top-3 campaign

Local-only research and agent development for Kaggriculture. External publication and
submission require explicit authorization.

## Reproduce

```powershell
uv sync --python 3.12
uv run pytest
uv run kg-analyze-replays --dataset references/kaggle-datasets/kaggriculture-episodes
```

The official environment is pinned to `kaggle-environments==1.32.2`. Upstream source,
public notebooks, GitHub references, and public replay data live under `references/` and
are excluded from this repository; exact provenance is recorded in
`docs/source_manifest.md`.
