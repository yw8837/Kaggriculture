from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kaggle.api.kaggle_api_extended import KaggleApi

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[2]


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def select_top25() -> list[dict[str, Any]]:
    leaderboard = json.loads((ROOT / "leaderboard_top25.json").read_text(encoding="utf-8"))
    episodes = read_jsonl(ROOT / "top25_episode_inventory.jsonl")
    by_submission: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for episode in episodes:
        by_submission[int(episode["submission_id_queried"])].append(episode)
    selected: list[dict[str, Any]] = []
    for row in leaderboard["rows"]:
        submissions = sorted(
            row["public_submissions"], key=lambda item: float(item.get("publicScore") or -1), reverse=True
        )
        if not submissions:
            continue
        submission_id = int(submissions[0]["id"])
        candidates = [
            episode
            for episode in by_submission[submission_id]
            if episode["type"] == "EPISODE_TYPE_PUBLIC" and episode["state"] == "COMPLETED"
        ]
        for seat in (0, 1):
            match = next((episode for episode in candidates if seat in episode["queried_team_seats"]), None)
            if match:
                selected.append(
                    {
                        "cohort": "leaderboard_top25",
                        "rank": row["rank"],
                        "team_id": row["team_id"],
                        "team_name": row["team_name"],
                        "leaderboard_score": row["score"],
                        "submission_id": submission_id,
                        "submission_public_score": submissions[0].get("publicScore"),
                        "target_seat": seat,
                        **match,
                    }
                )
    return selected


def select_ours() -> list[dict[str, Any]]:
    submissions = json.loads((ROOT / "our_submissions.json").read_text(encoding="utf-8"))["submissions"]
    episodes = read_jsonl(ROOT / "our_episode_inventory.jsonl")
    by_submission: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for episode in episodes:
        by_submission[int(episode["submission_id_queried"])].append(episode)
    selected: list[dict[str, Any]] = []
    for submission in submissions:
        submission_id = int(submission["ref"])
        candidates = [
            episode
            for episode in by_submission[submission_id]
            if episode["type"] == "EPISODE_TYPE_PUBLIC" and episode["state"] == "COMPLETED"
        ]
        for seat in (0, 1):
            match = next((episode for episode in candidates if seat in episode["queried_team_seats"]), None)
            if match:
                selected.append(
                    {
                        "cohort": "our_submissions",
                        "file_name": submission.get("fileName"),
                        "submission_public_score": submission.get("publicScore"),
                        "target_seat": seat,
                        **match,
                    }
                )
    return selected


def download(api: KaggleApi, episode_id: int, output_dir: Path) -> tuple[Path | None, str | None]:
    output = output_dir / f"episode-{episode_id}-replay.json"
    if output.exists():
        return output, None
    for attempt in range(4):
        try:
            api.competition_episode_replay(episode_id, path=str(output_dir), quiet=True)
            return output, None
        except Exception as exc:  # noqa: BLE001
            # Retry heterogeneous Kaggle transport/API failures and retain the final one.
            if attempt == 3:
                return None, f"{type(exc).__name__}: {exc}"
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cohort", choices=("top25", "ours", "both"), default="both")
    args = parser.parse_args()
    started = utc_now()
    selections = []
    if args.cohort in ("top25", "both"):
        selections.extend(select_top25())
    if args.cohort in ("ours", "both"):
        selections.extend(select_ours())

    deduplicated: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for selection in selections:
        deduplicated[int(selection["episode_id"])].append(selection)

    output_dir = ROOT / "replays_raw"
    output_dir.mkdir(parents=True, exist_ok=True)
    api = KaggleApi()
    api.authenticate()
    rows = []
    for index, (episode_id, requested_by) in enumerate(sorted(deduplicated.items()), start=1):
        path, error = download(api, episode_id, output_dir)
        if path is None:
            rows.append(
                {
                    "episode_id": episode_id,
                    "retrieved_at_utc": utc_now(),
                    "status": "REPRO_FAILED",
                    "error": error,
                    "requested_by": requested_by,
                }
            )
            continue
        raw = path.read_bytes()
        replay = json.loads(raw)
        rows.append(
            {
                "episode_id": episode_id,
                "retrieved_at_utc": utc_now(),
                "status": "EXECUTED_READ_ONLY_DOWNLOAD",
                "source_command": f"KaggleApi.competition_episode_replay({episode_id})",
                "source_url": f"https://www.kaggle.com/competitions/kaggriculture/episodes/{episode_id}",
                # Authoritative paths are relative to the campaign Git worktree.
                # Absolute Windows paths add no provenance value and are vulnerable
                # to mojibake when a downstream PowerShell JSON round-trip touches
                # the Korean user-profile segment.
                "path": path.resolve().relative_to(REPO_ROOT.resolve()).as_posix(),
                "bytes": len(raw),
                "sha256": sha256(raw),
                "replay_episode_id": replay.get("info", {}).get("EpisodeId"),
                "seed": replay.get("info", {}).get("seed"),
                "team_names": replay.get("info", {}).get("TeamNames"),
                "steps": len(replay.get("steps") or []),
                "requested_by": requested_by,
            }
        )
        if index < len(deduplicated):
            time.sleep(0.25)

    inventory_path = ROOT / "replay_inventory.jsonl"
    write_jsonl(inventory_path, rows)
    raw = inventory_path.read_bytes()
    manifest = {
        "schema_version": 1,
        "started_at_utc": started,
        "completed_at_utc": utc_now(),
        "cohort": args.cohort,
        "selection_requests": len(selections),
        "unique_episode_count": len(deduplicated),
        "downloaded": sum(row["status"] == "EXECUTED_READ_ONLY_DOWNLOAD" for row in rows),
        "failed": sum(row["status"] == "REPRO_FAILED" for row in rows),
        "inventory_path": inventory_path.as_posix(),
        "inventory_bytes": len(raw),
        "inventory_sha256": sha256(raw),
    }
    write_json(ROOT / "replay_download_manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
