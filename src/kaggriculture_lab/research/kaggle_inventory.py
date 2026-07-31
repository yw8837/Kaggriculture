from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _run_json(command: list[str]) -> list[dict[str, Any]]:
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    output = completed.stdout
    start = output.find("[")
    if start < 0:
        raise ValueError(f"Kaggle CLI returned no JSON array: {command!r}")
    payload = json.loads(output[start:])
    if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
        raise TypeError(f"Kaggle CLI returned an unexpected payload: {command!r}")
    return payload


def collect_inventory(competition: str) -> dict[str, Any]:
    started_at = _utc_now()
    submissions_command = [
        "kaggle",
        "competitions",
        "submissions",
        competition,
        "--page-size",
        "200",
        "--format",
        "json",
        "-q",
    ]
    submissions = _run_json(submissions_command)
    inventory_rows: list[dict[str, Any]] = []
    source_commands = [" ".join(submissions_command)]

    for submission in sorted(submissions, key=lambda row: int(row["ref"])):
        ref = int(submission["ref"])
        episodes_command = [
            "kaggle",
            "competitions",
            "episodes",
            str(ref),
            "--format",
            "json",
            "-q",
        ]
        episodes = _run_json(episodes_command)
        episodes_observed_at = _utc_now()
        source_commands.append(" ".join(episodes_command))
        normalized = [
            {
                "id": int(episode["id"]),
                "createTime": episode.get("createTime"),
                "endTime": episode.get("endTime"),
                "state": episode.get("state"),
                "type": episode.get("type"),
            }
            for episode in episodes
        ]
        inventory_rows.append(
            {
                "ref": ref,
                "fileName": submission.get("fileName"),
                "date": submission.get("date"),
                "description": submission.get("description", ""),
                "status": submission.get("status"),
                "publicScore": submission.get("publicScore", ""),
                "privateScore": submission.get("privateScore", ""),
                "episodes_observed_at_utc": episodes_observed_at,
                "episode_inventory": {
                    "total": len(normalized),
                    "public": sum("PUBLIC" in str(row["type"]) for row in normalized),
                    "validation": sum("VALIDATION" in str(row["type"]) for row in normalized),
                    "completed": sum("COMPLETED" in str(row["state"]) for row in normalized),
                    "episodes": normalized,
                },
            }
        )

    return {
        "schema_version": 2,
        "query_started_at_utc": started_at,
        "observed_at_utc": _utc_now(),
        "competition": competition,
        "source_commands": source_commands,
        "submission_count": len(inventory_rows),
        "submissions": inventory_rows,
        "note": (
            "Read-only Kaggle API inventory. Counts are historical observations at each "
            "episodes_observed_at_utc, not claims about later live state."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--competition", default="kaggriculture")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = collect_inventory(args.competition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output), "observed_at_utc": payload["observed_at_utc"]}))


if __name__ == "__main__":
    main()
