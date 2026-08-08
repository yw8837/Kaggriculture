# Suggested Commands
- Install: uv sync --all-groups.
- Tests: .\.venv\Scripts\python.exe -m pytest -q.
- Lint tracked project scopes: .\.venv\Scripts\python.exe -m ruff check src tests research/campaign_3000. Avoid `ruff check .` when ignored third-party reference clones are present.
- Inspect batch/runtime CLI before freezing arguments: python -m kaggriculture_lab.evaluation.runner --help and python -m kaggriculture_lab.evaluation.runtime --help.
- Shared worktrees may need git -c safe.directory=<absolute-worktree> -C <absolute-worktree>.
- Use PowerShell native file commands and rg for repository search.
