from __future__ import annotations

import tarfile
from pathlib import Path

from kaggriculture_lab.candidates.package import package


def test_package_is_deterministic(tmp_path: Path) -> None:
    source = tmp_path / "main.py"
    source.write_text("def agent(obs):\n    return {}\n", encoding="utf-8")
    first = package(source, tmp_path / "first.tar.gz")
    second = package(source, tmp_path / "second.tar.gz")
    assert first["archive_sha256"] == second["archive_sha256"]
    with tarfile.open(tmp_path / "first.tar.gz", "r:gz") as archive:
        assert archive.getnames() == ["main.py"]
