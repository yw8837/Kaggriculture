"""Download and statically inspect current outputs of high-scoring public kernels.

Downloaded Python is never imported or executed.  Archives are read in memory only.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from map_public_tapes import DOMINANT_FARM_SHA256, _literal_tapes

ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = ROOT / "raw" / "kernel_outputs"
EXPLICIT_REFS = {"fleongg/kaggriculture-public-2830-4-v21-1-no-preemption"}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _inspect_python(data: bytes) -> dict[str, Any]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return {"static_parse": "NON_UTF8", "literal_tapes": []}
    return {"static_parse": "UTF8_STATIC_ONLY", "literal_tapes": _literal_tapes(text)}


def _inspect_tar(path: Path) -> dict[str, Any]:
    members: list[dict[str, Any]] = []
    with tarfile.open(path, mode="r:*") as archive:
        for member in archive.getmembers():
            row: dict[str, Any] = {
                "name": member.name,
                "size": member.size,
                "mode": member.mode,
                "mtime": member.mtime,
                "uid": member.uid,
                "gid": member.gid,
            }
            if member.isfile():
                handle = archive.extractfile(member)
                data = handle.read() if handle else b""
                row["sha256"] = hashlib.sha256(data).hexdigest().upper()
                if member.name.endswith(".py"):
                    row.update(_inspect_python(data))
            members.append(row)
    return {"archive_status": "STATIC_READ_ONLY", "members": members}


def _inspect_file(path: Path) -> dict[str, Any]:
    row: dict[str, Any] = {
        "relative_path": path.relative_to(OUTPUT_ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": _file_sha(path),
    }
    if path.name.endswith((".tar.gz", ".tgz", ".tar")):
        try:
            row.update(_inspect_tar(path))
        except tarfile.TarError as exc:
            row.update({"archive_status": "INVALID", "archive_error": repr(exc)})
    elif path.suffix == ".py":
        row.update(_inspect_python(path.read_bytes()))
    return row


def main() -> None:
    inventory = [
        json.loads(line)
        for line in (ROOT / "code_inventory.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    selected = sorted(
        row["ref"]
        for row in inventory
        if (isinstance(row.get("best_score"), (int, float)) and row["best_score"] >= 1900)
        or row["ref"] in EXPLICIT_REFS
    )
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    rows: list[dict[str, Any]] = []
    for ref in selected:
        target = OUTPUT_ROOT / ref.replace("/", "__")
        target.mkdir(parents=True, exist_ok=True)
        command = ["uvx", "kaggle", "kernels", "output", ref, "-p", str(target), "--force"]
        started = _utc_now()
        completed = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
        files = sorted(
            (_inspect_file(path) for path in target.rglob("*") if path.is_file()),
            key=lambda row: row["relative_path"],
        )
        rows.append(
            {
                "ref": ref,
                "command": command,
                "started_at_utc": started,
                "finished_at_utc": _utc_now(),
                "returncode": completed.returncode,
                "stdout_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest().upper(),
                "stderr_sha256": hashlib.sha256(completed.stderr.encode()).hexdigest().upper(),
                "stdout_excerpt": completed.stdout[:1000],
                "stderr_excerpt": completed.stderr[:1000],
                "files": files,
                "execution_status": "DOWNLOADED_STATIC_ONLY_NOT_EXECUTED",
            }
        )
    manifest = ROOT / "kernel_output_manifest.jsonl"
    manifest.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    matches = [
        {"ref": row["ref"], "file": file["relative_path"], "tape": tape}
        for row in rows
        for file in row["files"]
        for tape in file.get("literal_tapes", [])
        + [nested for member in file.get("members", []) for nested in member.get("literal_tapes", [])]
        if tape["dominant_match_variants"]
    ]
    print(
        json.dumps(
            {
                "refs": len(rows),
                "success": sum(row["returncode"] == 0 for row in rows),
                "files": sum(len(row["files"]) for row in rows),
                "dominant_hash": DOMINANT_FARM_SHA256,
                "dominant_matches": matches,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
