from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path
from typing import Any


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def package(source: Path, output: Path) -> dict:
    payload = source.read_bytes()
    compile(payload, "main.py", "exec")
    output.parent.mkdir(parents=True, exist_ok=True)

    compressed = io.BytesIO()
    with (
        gzip.GzipFile(filename="", mode="wb", fileobj=compressed, mtime=0) as gz,
        tarfile.open(fileobj=gz, mode="w") as archive,
    ):
        info = tarfile.TarInfo("main.py")
        info.size = len(payload)
        info.mode = 0o644
        info.mtime = 0
        info.uid = 0
        info.gid = 0
        info.uname = ""
        info.gname = ""
        archive.addfile(info, io.BytesIO(payload))
    archive_bytes = compressed.getvalue()
    output.write_bytes(archive_bytes)

    with tarfile.open(output, "r:gz") as archive:
        members = archive.getmembers()
        if [member.name for member in members] != ["main.py"]:
            raise ValueError("archive must contain only main.py at its root")
        extracted = archive.extractfile(members[0])
        if extracted is None or extracted.read() != payload:
            raise ValueError("packaged payload differs from source")
    return {
        "source": source.as_posix(),
        "source_sha256": _sha256(payload),
        "archive": output.as_posix(),
        "archive_sha256": _sha256(archive_bytes),
        "archive_bytes": len(archive_bytes),
        "members": ["main.py"],
    }


def resolve_current_champion(
    manifest_path: Path, project_root: Path, *, require_artifact: bool = True,
) -> dict[str, Any]:
    """Resolve and hash-check the manifest's one current champion identity."""
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    current = payload.get("current_champion")
    if not isinstance(current, dict):
        raise TypeError("champion manifest must define current_champion object")
    required = {"identity", "source", "source_sha256", "artifact", "artifact_sha256"}
    missing = sorted(required - current.keys())
    if missing:
        raise ValueError(f"current_champion is missing fields: {missing}")

    source = (project_root / current["source"]).resolve()
    artifact = (project_root / current["artifact"]).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"champion source not found: {source}")
    source_sha256 = _sha256(source.read_bytes())
    if source_sha256 != current["source_sha256"]:
        raise ValueError("current champion source SHA-256 mismatch")
    artifact_sha256 = None
    if require_artifact:
        if not artifact.is_file():
            raise FileNotFoundError(f"champion artifact not found: {artifact}")
        artifact_sha256 = _sha256(artifact.read_bytes())
        if artifact_sha256 != current["artifact_sha256"]:
            raise ValueError("current champion artifact SHA-256 mismatch")
    return {
        "identity": current["identity"],
        "source": source,
        "source_sha256": source_sha256,
        "artifact": artifact,
        "artifact_sha256": artifact_sha256,
        "expected_artifact_sha256": current["artifact_sha256"],
    }


def package_registered_champion(manifest_path: Path, project_root: Path) -> dict[str, Any]:
    """Package exactly the current manifest identity and verify its registered artifact hash."""
    resolved = resolve_current_champion(manifest_path, project_root, require_artifact=False)
    record = package(resolved["source"], resolved["artifact"])
    if record["archive_sha256"] != resolved["expected_artifact_sha256"]:
        raise ValueError("packaged current champion artifact SHA-256 mismatch")
    return {"identity": resolved["identity"], **record}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build deterministic submission archives")
    parser.add_argument(
        "--candidates", default="fast_expansion,cow_tilt", help="comma-separated names"
    )
    parser.add_argument("--source-root", type=Path, default=Path("artifacts/candidates"))
    parser.add_argument("--output-root", type=Path, default=Path("dist"))
    parser.add_argument("--champion-manifest", type=Path)
    parser.add_argument("--project-root", type=Path, default=Path("."))
    args = parser.parse_args()

    if args.champion_manifest:
        print(json.dumps(package_registered_champion(args.champion_manifest, args.project_root)))
        return

    records = []
    for name in (part.strip() for part in args.candidates.split(",")):
        if not name:
            continue
        records.append(
            {
                "name": name,
                **package(
                    args.source_root / name / "main.py",
                    args.output_root / f"{name}.tar.gz",
                ),
            }
        )
    manifest = {"schema_version": 1, "artifacts": records}
    manifest_path = args.output_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
