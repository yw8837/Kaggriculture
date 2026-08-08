from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


def read_json(name: str) -> Any:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def read_jsonl(name: str) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in (ROOT / name).read_text(encoding="utf-8").splitlines()
        if line
    ]


def write_json(name: str, value: Any) -> None:
    (ROOT / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def replay_requests_by(cohort: str) -> dict[int, list[dict[str, Any]]]:
    output: dict[int, list[dict[str, Any]]] = {}
    for replay in read_jsonl("replay_inventory.jsonl"):
        for request in replay.get("requested_by") or []:
            if request.get("cohort") != cohort:
                continue
            identity = int(
                request.get("team_id")
                if cohort == "leaderboard_top25"
                else request["submission_id_queried"]
            )
            output.setdefault(identity, []).append(
                {
                    "episode_id": int(replay["episode_id"]),
                    "target_seat": int(request["target_seat"]),
                    "seed": int(replay["seed"]),
                    "sha256": replay["sha256"],
                    "bytes": int(replay["bytes"]),
                    "path": replay["path"],
                    "source_url": replay["source_url"],
                    "retrieved_at_utc": replay["retrieved_at_utc"],
                }
            )
    for rows in output.values():
        rows.sort(key=lambda row: (row["target_seat"], row["episode_id"]))
    return output


def main() -> None:
    created_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    leaderboard = read_json("leaderboard_top25.json")
    comparative = read_json("comparative_metrics.json")
    top_performance = {
        int(row["team_id"]): row
        for row in comparative["full_top25_episode_performance"]["teams"]
    }
    top_replays = replay_requests_by("leaderboard_top25")
    public_join_path = ROOT / "leaderboard_public_join.json"
    public_join = (
        {
            int(row["team_id"]): row
            for row in json.loads(public_join_path.read_text(encoding="utf-8"))["rows"]
        }
        if public_join_path.is_file()
        else {}
    )
    top_rows = []
    for row in leaderboard["rows"]:
        team_id = int(row["team_id"])
        top_rows.append(
            {
                "rank": int(row["rank"]),
                "team_id": team_id,
                "team_name": row["team_name"],
                "leaderboard_score": float(row["score"]),
                "leaderboard_submission_date": row["submission_date"],
                "public_submissions": row["public_submissions"],
                "highest_scoring_submission_episode_performance": top_performance[team_id],
                "sampled_public_replays": top_replays.get(team_id, []),
                "episode_metadata_status": row["episode_availability"]["metadata"],
                "public_code": public_join.get(team_id, {}).get("code", row["public_code"]),
                "public_discussion": public_join.get(team_id, {}).get(
                    "discussion", row["public_discussion"]
                ),
                "public_models": public_join.get(team_id, {}).get("models", row["public_models"]),
            }
        )
    write_json(
        "leaderboard_top25_provenance.json",
        {
            "schema_version": 1,
            "created_at_utc": created_at,
            "leaderboard_observed_at_utc": leaderboard["observed_at_utc"],
            "population": leaderboard["population"],
            "limitations": [
                "Rank and score are a time-bounded API snapshot and can change after observation.",
                "Exactly two public replay requests per team were selected; shared matches reduce 50 requests to 45 unique raw episodes.",
                "Private source is unavailable. Public Code/Discussion/Model fields remain UNVERIFIED until the separate public inventory is joined.",
            ],
            "rows": top_rows,
        },
    )

    submissions = read_json("our_submissions.json")
    our_performance = {
        int(row["submission_id"]): row
        for row in comparative["full_our_episode_performance"]["submissions"]
    }
    local_map = {
        int(row["submission_id"]): row
        for row in read_json("local_source_map.json")["submissions"]
    }
    our_replays = replay_requests_by("our_submissions")
    our_rows = []
    for submission in submissions["submissions"]:
        submission_id = int(submission["ref"])
        mapping = local_map[submission_id]
        our_rows.append(
            {
                "submission_id": submission_id,
                "file_name": submission["fileName"],
                "submitted_at_utc": submission["date"],
                "status": submission["status"],
                "public_score": float(submission["publicScore"]),
                "episode_inventory": {
                    "total": int(submission["episode_count"]),
                    "public_complete": int(submission["public_episode_count"]),
                    "validation": int(submission["validation_episode_count"]),
                    "seat_counts": submission["seat_counts"],
                },
                "public_episode_performance": our_performance[submission_id],
                "sampled_public_replays": our_replays.get(submission_id, []),
                "local_source_mapping": mapping,
                "upload_byte_identity": "UNVERIFIED_KAGGLE_HISTORICAL_UPLOAD_BYTES_UNAVAILABLE",
            }
        )
    write_json(
        "our_submission_provenance.json",
        {
            "schema_version": 1,
            "created_at_utc": created_at,
            "api_observed_at_utc": submissions["observed_at_utc"],
            "team_id": submissions["account_team_id"],
            "team_name": submissions["account_team_name"],
            "submission_count": len(our_rows),
            "naming_directive": {
                "future": "Kag_XX - Short Description.tar.gz",
                "historical_only_prefixes": ["Fa_", "Ge_", "bot_"],
            },
            "limitations": [
                "Local source/archive matches are filename-and-current-byte candidates only; Kaggle does not expose the historical uploaded archive bytes.",
                "Repeated filenames may represent distinct historical upload bytes despite matching the same current local archive.",
                "Two sampled replays per submission are descriptive and selection-biased; use the full public episode metadata performance for W-D-L summaries.",
            ],
            "rows": our_rows,
        },
    )


if __name__ == "__main__":
    main()
