from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kaggle.api.kaggle_api_extended import KaggleApi

COMPETITION = "kaggriculture"
TOP_N = 25
OUTPUT = Path(__file__).resolve().parent


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def write_json(path: Path, value: Any) -> dict[str, Any]:
    raw = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {"path": path.as_posix(), "bytes": len(raw), "sha256": sha256(raw)}


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    raw = b"".join(canonical_bytes(row) for row in rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {"path": path.as_posix(), "bytes": len(raw), "sha256": sha256(raw), "rows": len(rows)}


def as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        return value.to_dict()
    raise TypeError(type(value))


def normalize_episode(episode: Any, *, submission_id: int, team_id: int | None) -> dict[str, Any]:
    row = as_dict(episode)
    agents = row.get("agents") or []
    team_seats = [
        index for index, agent in enumerate(agents) if team_id is not None and agent.get("teamId") == team_id
    ]
    return {
        "episode_id": int(row["id"]),
        "submission_id_queried": int(submission_id),
        "create_time": row.get("createTime"),
        "end_time": row.get("endTime"),
        "state": row.get("state"),
        "type": row.get("type"),
        "agents": agents,
        "queried_team_id": team_id,
        "queried_team_seats": team_seats,
        "replay_endpoint": f"kaggle competitions episode-replay {int(row['id'])}",
        "replay_url": f"https://www.kaggle.com/competitions/kaggriculture/episodes/{int(row['id'])}",
    }


def main() -> int:
    started = utc_now()
    api = KaggleApi()
    api.authenticate()
    errors: list[dict[str, Any]] = []

    leaderboard_raw = [as_dict(row) for row in api.competition_leaderboard_view(COMPETITION, page_size=200)]
    top = leaderboard_raw[:TOP_N]
    top_episode_rows: list[dict[str, Any]] = []
    lb_rows: list[dict[str, Any]] = []

    for rank, leaderboard in enumerate(top, start=1):
        team_id = int(leaderboard["teamId"])
        team_submissions: list[dict[str, Any]] = []
        try:
            submissions = api.competition_team_submissions(team_id)
        except Exception as exc:  # noqa: BLE001
            # Preserve heterogeneous Kaggle API failures without pretending zero results.
            errors.append(
                {
                    "at_utc": utc_now(),
                    "operation": "competition_team_submissions",
                    "team_id": team_id,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            submissions = []
        for submission in submissions:
            submission_row = as_dict(submission)
            submission_id = int(submission_row["id"])
            try:
                episodes = api.competition_list_episodes(submission_id)
            except Exception as exc:  # noqa: BLE001
                # Preserve heterogeneous Kaggle API failures without pretending zero results.
                errors.append(
                    {
                        "at_utc": utc_now(),
                        "operation": "competition_list_episodes",
                        "team_id": team_id,
                        "submission_id": submission_id,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )
                episodes = []
            normalized = [
                normalize_episode(episode, submission_id=submission_id, team_id=team_id)
                for episode in episodes
            ]
            top_episode_rows.extend(
                {"leaderboard_rank_at_snapshot": rank, "team_name": leaderboard.get("teamName"), **row}
                for row in normalized
            )
            public_completed = [
                row
                for row in normalized
                if row["type"] == "EPISODE_TYPE_PUBLIC" and row["state"] == "COMPLETED"
            ]
            team_submissions.append(
                {
                    **submission_row,
                    "episode_count": len(normalized),
                    "public_completed_episode_count": len(public_completed),
                    "seat_counts": {
                        "0": sum(0 in row["queried_team_seats"] for row in public_completed),
                        "1": sum(1 in row["queried_team_seats"] for row in public_completed),
                    },
                    "latest_public_episode_ids": [row["episode_id"] for row in public_completed[:10]],
                }
            )
        lb_rows.append(
            {
                "rank": rank,
                "team_id": team_id,
                "team_name": leaderboard.get("teamName"),
                "score": float(leaderboard["score"]),
                "submission_date": leaderboard.get("submissionDate"),
                "public_submission_inventory_status": "OBSERVED" if team_submissions else "UNVERIFIED_EMPTY_OR_API_FAILURE",
                "public_submissions": team_submissions,
                "public_code": {"status": "UNVERIFIED_PENDING_PUBLIC_INVENTORY_JOIN", "refs": []},
                "public_discussion": {"status": "UNVERIFIED_PENDING_PUBLIC_INVENTORY_JOIN", "refs": []},
                "public_models": {"status": "UNVERIFIED_PENDING_PUBLIC_INVENTORY_JOIN", "refs": []},
                "episode_availability": {
                    "metadata": "OBSERVED" if team_submissions else "UNVERIFIED",
                    "replay_download": "AVAILABLE_ENDPOINT_NOT_YET_DOWNLOADED"
                    if any(row["public_completed_episode_count"] for row in team_submissions)
                    else "UNVERIFIED",
                },
            }
        )

    our_raw = [as_dict(row) for row in api.competition_submissions(COMPETITION, page_size=200)]
    our_rows: list[dict[str, Any]] = []
    our_episode_rows: list[dict[str, Any]] = []
    for submission in our_raw:
        submission_id = int(submission["ref"])
        try:
            episodes = api.competition_list_episodes(submission_id)
        except Exception as exc:  # noqa: BLE001
            # Preserve heterogeneous Kaggle API failures without pretending zero results.
            errors.append(
                {
                    "at_utc": utc_now(),
                    "operation": "competition_list_episodes",
                    "submission_id": submission_id,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            episodes = []
        normalized = [
            normalize_episode(episode, submission_id=submission_id, team_id=16630689)
            for episode in episodes
        ]
        our_episode_rows.extend(normalized)
        public = [row for row in normalized if row["type"] == "EPISODE_TYPE_PUBLIC"]
        our_rows.append(
            {
                **submission,
                "episode_count": len(normalized),
                "public_episode_count": len(public),
                "validation_episode_count": sum(row["type"] == "EPISODE_TYPE_VALIDATION" for row in normalized),
                "completed_episode_count": sum(row["state"] == "COMPLETED" for row in normalized),
                "seat_counts": {
                    "0": sum(0 in row["queried_team_seats"] for row in public),
                    "1": sum(1 in row["queried_team_seats"] for row in public),
                },
                "episode_ids": [row["episode_id"] for row in normalized],
            }
        )

    observed = utc_now()
    outputs = []
    outputs.append(
        write_json(
            OUTPUT / "leaderboard_top25.json",
            {
                "schema_version": 1,
                "competition": COMPETITION,
                "query_started_at_utc": started,
                "observed_at_utc": observed,
                "population": "First 25 rows returned by official Kaggle leaderboard API page_size=200.",
                "source": {
                    "sdk_method": "KaggleApi.competition_leaderboard_view('kaggriculture', page_size=200)",
                    "url": "https://www.kaggle.com/competitions/kaggriculture/leaderboard",
                },
                "rows": lb_rows,
            },
        )
    )
    outputs.append(write_jsonl(OUTPUT / "top25_episode_inventory.jsonl", top_episode_rows))
    outputs.append(
        write_json(
            OUTPUT / "our_submissions.json",
            {
                "schema_version": 1,
                "competition": COMPETITION,
                "query_started_at_utc": started,
                "observed_at_utc": observed,
                "account_team_id": 16630689,
                "account_team_name": "yw8837",
                "source": {
                    "sdk_method": "KaggleApi.competition_submissions('kaggriculture', page_size=200)",
                    "url": "https://www.kaggle.com/competitions/kaggriculture/submissions",
                },
                "submission_count": len(our_rows),
                "submissions": our_rows,
            },
        )
    )
    outputs.append(write_jsonl(OUTPUT / "our_episode_inventory.jsonl", our_episode_rows))
    outputs.append(write_jsonl(OUTPUT / "collection_errors.jsonl", errors))
    manifest = {
        "schema_version": 1,
        "created_at_utc": utc_now(),
        "command": "python research/campaign_3000/01_internal/collect_kaggle_inventory.py",
        "python": sys.version,
        "outputs": outputs,
        "errors": len(errors),
    }
    write_json(OUTPUT / "inventory_manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
