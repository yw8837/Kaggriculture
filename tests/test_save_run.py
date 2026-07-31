from __future__ import annotations

import json
from pathlib import Path

import pytest

from kaggriculture_lab.candidates.package import package
from kaggriculture_lab.candidates.save_run import prepare_save_run


def test_prepare_save_run_preserves_verified_artifact(tmp_path: Path) -> None:
    source = tmp_path / "main.py"
    source.write_text("def agent(obs):\n    return {}\n", encoding="utf-8")
    artifact = tmp_path / "Fa_01 - Test Agent.tar.gz"
    packaged = package(source, artifact)

    run_dir = tmp_path / "run"
    result = prepare_save_run(
        artifact,
        run_dir,
        "yw8837/fa-01-test-agent",
        "Fa_01 Test Agent",
        "kaggriculture",
    )
    notebook = json.loads(
        (run_dir / "Fa_01 - Test Agent.ipynb").read_text(encoding="utf-8")
    )
    metadata = json.loads((run_dir / "kernel-metadata.json").read_text(encoding="utf-8"))
    assert result["artifact_sha256"] == packaged["archive_sha256"]
    assert metadata["is_private"] is True
    assert metadata["competition_sources"] == ["kaggriculture"]
    assert [cell["id"] for cell in notebook["cells"]] == [
        "strategy-overview",
        "emit-verified-artifact",
    ]
    assert packaged["archive_sha256"] in "".join(notebook["cells"][1]["source"])


def test_prepare_save_run_rejects_unnumbered_artifact(tmp_path: Path) -> None:
    artifact = tmp_path / "agent.tar.gz"
    artifact.write_bytes(b"not an archive")
    with pytest.raises(ValueError, match="Fa_XX"):
        prepare_save_run(
            artifact,
            tmp_path / "run",
            "yw8837/agent",
            "Agent",
            "kaggriculture",
        )
