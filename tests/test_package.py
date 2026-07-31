from __future__ import annotations

import json
import tarfile
from pathlib import Path

from kaggriculture_lab.candidates.package import (
    package,
    package_registered_champion,
    resolve_current_champion,
)


def test_package_is_deterministic(tmp_path: Path) -> None:
    source = tmp_path / "main.py"
    source.write_text("def agent(obs):\n    return {}\n", encoding="utf-8")
    first = package(source, tmp_path / "first.tar.gz")
    second = package(source, tmp_path / "second.tar.gz")
    assert first["archive_sha256"] == second["archive_sha256"]
    with tarfile.open(tmp_path / "first.tar.gz", "r:gz") as archive:
        assert archive.getnames() == ["main.py"]


def test_manifest_resolver_packages_only_registered_current_identity(tmp_path: Path) -> None:
    source = tmp_path / "formal.py"
    rejected = tmp_path / "rejected.py"
    artifact = tmp_path / "current.tar.gz"
    source.write_text("def agent(obs):\n    return {'current': 1}\n", encoding="utf-8")
    rejected.write_text("def agent(obs):\n    return {'rejected': 1}\n", encoding="utf-8")
    expected = package(source, artifact)
    artifact.unlink()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({
            "current_champion": {
                "identity": "formal",
                "source": "formal.py",
                "source_sha256": expected["source_sha256"],
                "artifact": "current.tar.gz",
                "artifact_sha256": expected["archive_sha256"],
            },
            "rejected_history": [{"source": "rejected.py"}],
        }),
        encoding="utf-8",
    )

    built = package_registered_champion(manifest, tmp_path)
    resolved = resolve_current_champion(manifest, tmp_path)

    assert built["identity"] == "formal"
    assert resolved["source"] == source
    assert resolved["artifact"] == artifact
    with tarfile.open(artifact, "r:gz") as archive:
        payload = archive.extractfile("main.py")
        assert payload is not None
        assert payload.read() == source.read_bytes()
