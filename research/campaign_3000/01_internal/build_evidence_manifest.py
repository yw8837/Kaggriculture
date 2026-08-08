from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[2]
OUTPUT = ROOT / "evidence_manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def record(path: Path) -> dict[str, Any]:
    return {
        "path": path.resolve().relative_to(REPO_ROOT.resolve()).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def preserve_created_at_if_unchanged(
    output_path: Path, manifest: dict[str, Any]
) -> dict[str, Any]:
    """Keep the manifest byte-stable when its evidence set is unchanged."""
    if not output_path.is_file():
        return manifest
    existing = json.loads(output_path.read_text(encoding="utf-8"))
    candidate = dict(manifest)
    candidate["created_at_utc"] = existing.get("created_at_utc")
    return existing if candidate == existing else manifest


def main() -> None:
    files = []
    for path in sorted(ROOT.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_file() or path == OUTPUT:
            continue
        files.append(record(path))
    files.append(record(ROOT / "replays_raw" / ".gitignore"))

    inventory_path = ROOT / "replay_inventory.jsonl"
    inventory_rows = [
        json.loads(line)
        for line in inventory_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    integrity = json.loads((ROOT / "replay_integrity_report.json").read_text(encoding="utf-8"))
    if integrity["inventory"]["sha256"] != sha256(inventory_path):
        raise ValueError("replay inventory changed after integrity verification")
    if integrity["raw_replays"]["failed"] != 0:
        raise ValueError("replay integrity report contains failures")

    raw_replays = [
        {
            "path": row["path"],
            "episode_id": int(row["episode_id"]),
            "bytes": int(row["bytes"]),
            "sha256": row["sha256"],
            "source_url": row["source_url"],
            "retrieved_at_utc": row["retrieved_at_utc"],
        }
        for row in inventory_rows
    ]
    output = {
        "schema_version": 1,
        "created_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "scope": "Kaggriculture campaign_3000 internal submission/LB/replay evidence",
        "files": files,
        "file_count": len(files),
        "raw_replays": raw_replays,
        "raw_replay_count": len(raw_replays),
        "raw_replay_bytes": sum(row["bytes"] for row in raw_replays),
        "raw_replay_hash_verification": {
            "report_path": "research/campaign_3000/01_internal/replay_integrity_report.json",
            "verified": integrity["raw_replays"]["verified"],
            "failed": integrity["raw_replays"]["failed"],
            "inventory_sha256": integrity["inventory"]["sha256"],
        },
        "artifact_status_overrides": {
            "research/campaign_3000/01_internal/inventory_manifest.json": "HISTORICAL_INITIAL_PARTIAL_BEFORE_429_REPAIR",
            "research/campaign_3000/01_internal/collection_errors.jsonl": "APPEND_ONLY_INITIAL_429_ERRORS",
            "research/campaign_3000/01_internal/repair_manifest.json": "AUTHORITATIVE_REPAIR_STATUS_FOR_FIVE_INITIAL_FAILURES",
            "research/campaign_3000/01_internal/our_submissions.json": "AUTHORITATIVE_CURRENT_22_SUBMISSION_INVENTORY",
            "research/campaign_3000/01_internal/our_episode_inventory.jsonl": "AUTHORITATIVE_CURRENT_1017_EPISODE_METADATA_ROWS",
        },
        "external_read_only_sources": [
            {
                "path": "C:/Users/최용우/Desktop/Kaggriculture",
                "status": "DIRTY_EXTERNAL_WORKTREE_READ_ONLY",
                "index": "research/campaign_3000/01_internal/local_source_map.json",
            },
            {
                "path": "research/campaign_3000/02_public_meta",
                "status": "SEPARATE_PUBLIC_META_LANE_READ_ONLY_JOIN",
                "join": "research/campaign_3000/01_internal/leaderboard_public_join.json",
            },
        ],
    }
    output = preserve_created_at_if_unchanged(OUTPUT, output)
    output_text = json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != output_text:
        OUTPUT.write_text(output_text, encoding="utf-8", newline="\n")
    print(json.dumps(record(OUTPUT), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
