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
        "Kaggriculture | Strong Expansion Baseline",
        "kaggriculture",
    )
    notebook = json.loads(Path(result["notebook"]).read_text(encoding="utf-8"))
    metadata = json.loads(Path(result["metadata"]).read_text(encoding="utf-8"))

    assert metadata["is_private"] is False
    assert metadata["competition_sources"] == ["kaggriculture"]
    assert [cell["id"] for cell in notebook["cells"]] == [
        "public-strategy-overview",
        "readable-agent-source",
        "deterministic-package",
    ]
    assert "def agent(obs):" in "".join(notebook["cells"][1]["source"])
    assert result["source_sha256"] in "".join(notebook["cells"][2]["source"])
    assert "not our current private competition agent" in "".join(
        notebook["cells"][0]["source"]
    )
