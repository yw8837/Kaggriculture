from __future__ import annotations

import hashlib
import json
import tarfile
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DESKTOP = Path(r"C:\Users\최용우\Desktop\Kaggriculture")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def file_record(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "path": path.relative_to(DESKTOP).as_posix(),
        "bytes": len(raw),
        "sha256": sha256(raw),
        "absolute_path_utf8": path.resolve().as_posix(),
    }


def archive_record(path: Path, sources_by_hash: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    record = file_record(path)
    try:
        with tarfile.open(path, mode="r:gz") as archive:
            members = [member for member in archive.getmembers() if member.isfile()]
            record["members"] = []
            for member in members:
                handle = archive.extractfile(member)
                raw = b"" if handle is None else handle.read()
                member_record = {
                    "name": member.name,
                    "bytes": len(raw),
                    "sha256": sha256(raw),
                }
                if Path(member.name).name == "main.py":
                    member_record["local_source_matches"] = sources_by_hash.get(member_record["sha256"], [])
                record["members"].append(member_record)
            record["tar_status"] = "PARSED"
    except Exception as exc:  # noqa: BLE001
        # Record any archive reproduction failure instead of dropping provenance.
        record["tar_status"] = "REPRO_FAILED"
        record["tar_error"] = f"{type(exc).__name__}: {exc}"
    return record


def main() -> None:
    submissions = json.loads((ROOT / "our_submissions.json").read_text(encoding="utf-8"))["submissions"]
    source_paths = list((DESKTOP / "artifacts" / "candidates").glob("**/main.py"))
    source_paths.extend((DESKTOP / "v24_agents").glob("**/*.py"))
    source_paths.extend((DESKTOP / "experiments" / "source_snapshots").glob("**/*.py"))
    source_index = []
    sources_by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in sorted({path.resolve() for path in source_paths}):
        record = file_record(path)
        source_index.append(record)
        sources_by_hash[record["sha256"]].append(record)

    archive_paths = list((DESKTOP / "dist").glob("**/*.tar.gz"))
    archive_paths.extend((DESKTOP / "kaggle_runs").glob("**/*.tar.gz"))
    archives_by_name: dict[str, list[Path]] = defaultdict(list)
    for path in sorted({path.resolve() for path in archive_paths}):
        archives_by_name[path.name].append(path)

    rows = []
    for submission in submissions:
        filename = submission["fileName"]
        candidates = [archive_record(path, sources_by_hash) for path in archives_by_name.get(filename, [])]
        rows.append(
            {
                "submission_id": int(submission["ref"]),
                "submitted_at": submission["date"],
                "file_name": filename,
                "public_score_at_snapshot": submission["publicScore"],
                "local_filename_matches": candidates,
                "mapping_status": "LOCAL_FILENAME_MATCH_ONLY_UPLOAD_BYTES_UNAVAILABLE"
                if candidates
                else "UNVERIFIED_NO_LOCAL_FILENAME_MATCH",
                "warning": (
                    "Kaggle API does not expose uploaded artifact bytes. A local same-named archive, even with an exact "
                    "source match, is not proof that the historical upload used those bytes. Reused filenames are ambiguous."
                ),
            }
        )

    provenance_files = []
    for relative in (
        "OPERATING_ORDERS.md",
        "docs/BOT_DESIGN_SPEC.md",
        "docs/current_state_2026-08-02.md",
        "docs/current_state_2026-08-02_night.md",
        "experiments/ledger.jsonl",
        "submissions/ledger.jsonl",
    ):
        path = DESKTOP / relative
        if path.exists():
            provenance_files.append(file_record(path))

    payload = {
        "schema_version": 1,
        "observed_at_utc": datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "desktop_repository": {
            "path": DESKTOP.as_posix(),
            "mode": "READ_ONLY_DIRTY_EXTERNAL_WORKTREE",
            "warning": "No files in this worktree were modified by this collector.",
        },
        "source_index_count": len(source_index),
        "source_index": source_index,
        "provenance_files": provenance_files,
        "submissions": rows,
    }
    output = ROOT / "local_source_map.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    raw = output.read_bytes()
    print(
        json.dumps(
            {
                "output": output.as_posix(),
                "bytes": len(raw),
                "sha256": sha256(raw),
                "source_index_count": len(source_index),
                "mapped_submissions": sum(bool(row["local_filename_matches"]) for row in rows),
                "unmapped_submissions": sum(not row["local_filename_matches"] for row in rows),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
