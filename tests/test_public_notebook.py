from __future__ import annotations

import json
from pathlib import Path

from kaggriculture_lab.candidates.public_notebook import prepare_public_notebook


def test_prepare_public_notebook_is_readable_and_public(tmp_path: Path) -> None:
    source = tmp_path / "main.py"
    source.write_text("def agent(obs):\n    return {}\n", encoding="utf-8")

    result = prepare_public_notebook(
        source,
        tmp_path / "run",
        "yw8837/kaggriculture-strong-expansion-baseline",
        "Kaggriculture Agent | Early Expansion & Mixed-Farm Baseline",
        "kaggriculture",
    )
    notebook = json.loads(Path(result["notebook"]).read_text(encoding="utf-8"))
    metadata = json.loads(Path(result["metadata"]).read_text(encoding="utf-8"))

    assert metadata["is_private"] is False
    assert metadata["competition_sources"] == ["kaggriculture"]
    assert [cell["id"] for cell in notebook["cells"]] == [
        "public-strategy-overview",
        "strategy-timeline",
        "agent-api-contract",
        "readable-agent-source",
        "evaluation-checklist",
        "deterministic-package",
        "package-verification-and-limitations",
    ]
    assert "def agent(obs):" in "".join(notebook["cells"][3]["source"])
    assert result["source_sha256"] in "".join(notebook["cells"][5]["source"])
    notebook_text = "\n".join("".join(cell["source"]) for cell in notebook["cells"])
    normalized_text = " ".join(notebook_text.split())
    assert "not a leaderboard promise" in normalized_text
    assert "days 5-18" in notebook_text
    assert "`farmer`" in notebook_text
    assert "same seed list in both seats" in notebook_text
    assert "full 720-turn horizon" in notebook_text
    assert "only root `main.py`" in notebook_text
    assert "no standalone reuse license" in notebook_text
    assert 'OUTPUT_NAME = "public_expansion_baseline.tar.gz"' in notebook_text
    assert "info.mtime = 0" in notebook_text
    for forbidden in (
        "Fa_01",
        "Fa_02",
        "final_day_labor",
        "overflow_safe",
        "submission_ref",
        "replay_sha256",
        "KAGGLE_API_TOKEN",
    ):
        assert forbidden not in notebook_text
