from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Build deterministic submission archives")
    parser.add_argument(
        "--candidates", default="fast_expansion,cow_tilt", help="comma-separated names"
    )
    parser.add_argument("--source-root", type=Path, default=Path("artifacts/candidates"))
    parser.add_argument("--output-root", type=Path, default=Path("dist"))
    args = parser.parse_args()

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
