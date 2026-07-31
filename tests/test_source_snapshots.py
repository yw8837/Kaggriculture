from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_frozen_source_snapshot_manifest_hashes_every_input() -> None:
    manifest = json.loads(
        Path("experiments/source_snapshots/fa_ab_manifest.json").read_text(encoding="utf-8")
    )
    parent = Path(manifest["parent"]["source"])
    assert _sha256(parent) == manifest["parent"]["sha256"]

    for family in ("candidate_A", "candidate_B"):
        section = manifest[family]
        assert _sha256(Path(section["builder"])) == section["builder_sha256"]
        for snapshot in section["snapshots"].values():
            path = Path(snapshot["path"])
            assert _sha256(path) == snapshot["sha256"]
            compile(path.read_bytes(), path.as_posix(), "exec")

    evaluation = manifest["evaluation"]
    for path_key, hash_key in (
        ("runner", "runner_sha256"),
        ("development_config", "development_config_sha256"),
        ("scenario_config", "scenario_config_sha256"),
    ):
        assert _sha256(Path(evaluation[path_key])) == evaluation[hash_key]

    frozen_seed_registry = subprocess.run(
        [
            "git",
            "show",
            f"{evaluation['seed_registry_frozen_commit']}:{evaluation['seed_registry']}",
        ],
        check=True,
        capture_output=True,
    ).stdout
    assert hashlib.sha256(frozen_seed_registry).hexdigest().upper() == evaluation[
        "seed_registry_sha256"
    ]

    parent_bytes = parent.read_bytes()
    assert Path(
        manifest["candidate_A"]["snapshots"]["A0"]["path"]
    ).read_bytes() == parent_bytes
    assert Path(
        manifest["candidate_B"]["snapshots"]["B0"]["path"]
    ).read_bytes() == parent_bytes
