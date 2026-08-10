"""Append-only, read-only official Kaggle API capture for cycle 2026-08-10.

This script never uploads, submits, publishes, or downloads replay payloads.  It records
what the authenticated Kaggle API returned at one cutoff and labels any failed endpoint
UNVERIFIED rather than treating it as an empty population.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kaggle.api.kaggle_api_extended import KaggleApi


COMPETITION = "kaggriculture"
ACCOUNT_TEAM_ID = 16630689
ACCOUNT_TEAM_NAME = "yw8837"
TOP_N = 25
HERE = Path(__file__).resolve().parent


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def as_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    raise TypeError(f"unsupported SDK object: {type(value)!r}")


def canonical_json(value: Any, *, indent: int | None = None) -> bytes:
    suffix = "\n"
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=indent) + suffix).encode("utf-8")


def write_new(path: Path, raw: bytes, *, rows: int | None = None) -> dict[str, Any]:
    if path.exists():
        raise RuntimeError(f"append-only capture target already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    output: dict[str, Any] = {
        "path": path.relative_to(HERE.parents[3]).as_posix(),
        "bytes": len(raw),
        "sha256": sha256(raw),
    }
    if rows is not None:
        output["rows"] = rows
    return output


def write_json(name: str, value: Any) -> dict[str, Any]:
    return write_new(HERE / name, canonical_json(value, indent=2))


def write_jsonl(name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    raw = b"".join(canonical_json(row) for row in rows)
    return write_new(HERE / name, raw, rows=len(rows))


def normalize_episode(raw: dict[str, Any], *, submission_id: int, team_id: int | None) -> dict[str, Any]:
    agents = raw.get("agents") or []
    seats = [index for index, agent in enumerate(agents) if team_id is not None and agent.get("teamId") == team_id]
    episode_id = int(raw["id"])
    return {
        "episode_id": episode_id,
        "submission_id_queried": submission_id,
        "create_time": raw.get("createTime"),
        "end_time": raw.get("endTime"),
        "state": raw.get("state"),
        "type": raw.get("type"),
        "queried_team_id": team_id,
        "queried_team_seats": seats,
        "replay_url": f"https://www.kaggle.com/competitions/{COMPETITION}/episodes/{episode_id}",
        "replay_endpoint": f"KaggleApi.competition_episode_replay({episode_id})",
        "replay_payload_downloaded": false,
        "replay_payload_status": "AVAILABLE_ENDPOINT_NOT_DOWNLOADED"
        if raw.get("state") == "COMPLETED"
        else "UNVERIFIED_NOT_COMPLETED",
    }


def public_completed(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row["type"] == "EPISODE_TYPE_PUBLIC" and row["state"] == "COMPLETED"]


def main() -> int:
    started = utc_now()
    api = KaggleApi()
    api.authenticate()
    errors: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []

    leaderboard_raw = [as_dict(row) for row in api.competition_leaderboard_view(COMPETITION, page_size=200)]
    outputs.append(write_json("raw/leaderboard_view.json", leaderboard_raw))
    top_rows: list[dict[str, Any]] = []
    top_episode_rows: list[dict[str, Any]] = []

    for rank, row in enumerate(leaderboard_raw[:TOP_N], start=1):
        team_id = int(row["teamId"])
        submissions: list[dict[str, Any]] = []
        try:
            team_submissions = [as_dict(item) for item in api.competition_team_submissions(team_id)]
        except Exception as exc:  # noqa: BLE001
            errors.append({"at_utc": utc_now(), "operation": "competition_team_submissions", "team_id": team_id,
                           "error_type": type(exc).__name__, "error": str(exc)})
            team_submissions = []

        for submission in team_submissions:
            submission_id = int(submission["id"])
            try:
                episodes = [as_dict(item) for item in api.competition_list_episodes(submission_id)]
            except Exception as exc:  # noqa: BLE001
                errors.append({"at_utc": utc_now(), "operation": "competition_list_episodes", "team_id": team_id,
                               "submission_id": submission_id, "error_type": type(exc).__name__, "error": str(exc)})
                episodes = []
            normalized = [normalize_episode(item, submission_id=submission_id, team_id=team_id) for item in episodes]
            top_episode_rows.extend({"leaderboard_rank_at_cutoff": rank, "team_name_at_cutoff": row.get("teamName"), **item}
                                    for item in normalized)
            completed = public_completed(normalized)
            submissions.append({
                **submission,
                "episode_inventory_status": "OBSERVED" if episodes else "UNVERIFIED_EMPTY_OR_API_FAILURE",
                "episode_count": len(normalized),
                "public_completed_episode_count": len(completed),
                "seat_counts": {"0": sum(0 in item["queried_team_seats"] for item in completed),
                                "1": sum(1 in item["queried_team_seats"] for item in completed)},
                "latest_public_episode_ids": [item["episode_id"] for item in completed[:10]],
            })
        top_rows.append({
            "rank": rank,
            "team_id": team_id,
            "team_name": row.get("teamName"),
            "score": row.get("score"),
            "submission_date": row.get("submissionDate"),
            "source_row": row,
            "public_submissions": submissions,
            "public_submission_inventory_status": "OBSERVED" if submissions else "UNVERIFIED_EMPTY_OR_API_FAILURE",
            "episode_replay_population_boundary": "Only metadata returned for current listed submissions; replay payloads were not downloaded.",
        })

    our_submissions_raw = [as_dict(row) for row in api.competition_submissions(COMPETITION, page_size=200)]
    outputs.append(write_json("raw/our_submissions.json", our_submissions_raw))
    ours: list[dict[str, Any]] = []
    our_episode_rows: list[dict[str, Any]] = []
    for submission in our_submissions_raw:
        submission_id = int(submission["ref"])
        try:
            episodes = [as_dict(item) for item in api.competition_list_episodes(submission_id)]
        except Exception as exc:  # noqa: BLE001
            errors.append({"at_utc": utc_now(), "operation": "competition_list_episodes", "submission_id": submission_id,
                           "error_type": type(exc).__name__, "error": str(exc)})
            episodes = []
        normalized = [normalize_episode(item, submission_id=submission_id, team_id=ACCOUNT_TEAM_ID) for item in episodes]
        our_episode_rows.extend(normalized)
        completed = public_completed(normalized)
        ours.append({
            **submission,
            "episode_inventory_status": "OBSERVED" if episodes else "UNVERIFIED_EMPTY_OR_API_FAILURE",
            "episode_count": len(normalized),
            "public_completed_episode_count": len(completed),
            "seat_counts": {"0": sum(0 in item["queried_team_seats"] for item in completed),
                            "1": sum(1 in item["queried_team_seats"] for item in completed)},
            "episode_ids": [item["episode_id"] for item in normalized],
        })

    exact_kag_names = {"Kag_01 - Tetsu v16 Exact.tar.gz", "Kag_02 - Kaito v22 Price Impact.tar.gz"}
    observed_names = {row.get("fileName") for row in ours}
    kag_slots = [
        {
            "slot": name.split(" - ")[0],
            "expected_competition_archive_name": name,
            "competition_submission_row_status": "OBSERVED" if name in observed_names else "NONE_OBSERVED_IN_CURRENT_AUTHENTICATED_SUBMISSION_RESPONSE",
            "claim_limit": "Absence from competition_submissions does not establish the status of any private Save & Run kernel.",
        }
        for name in sorted(exact_kag_names)
    ]

    cutoff = utc_now()
    outputs.append(write_json("leaderboard_top25.json", {
        "schema_version": 1,
        "competition": COMPETITION,
        "query_started_at_utc": started,
        "cutoff_utc": cutoff,
        "population": "First 25 rows returned by official Kaggle leaderboard API page_size=200 at this cutoff; rankings may change after it.",
        "source": {"sdk_method": "KaggleApi.competition_leaderboard_view('kaggriculture', page_size=200)",
                   "url": "https://www.kaggle.com/competitions/kaggriculture/leaderboard"},
        "rows": top_rows,
    }))
    outputs.append(write_jsonl("top25_episode_inventory.jsonl", top_episode_rows))
    outputs.append(write_json("our_submissions_inventory.json", {
        "schema_version": 1,
        "competition": COMPETITION,
        "query_started_at_utc": started,
        "cutoff_utc": cutoff,
        "account_team_id": ACCOUNT_TEAM_ID,
        "account_team_name": ACCOUNT_TEAM_NAME,
        "population": "Every row returned by the authenticated competition_submissions API with page_size=200 at this cutoff; historical uploaded archive bytes are not exposed by this API.",
        "source": {"sdk_method": "KaggleApi.competition_submissions('kaggriculture', page_size=200)",
                   "url": "https://www.kaggle.com/competitions/kaggriculture/submissions"},
        "submission_count": len(ours),
        "kag_01_kag_02_competition_submission_check": kag_slots,
        "submissions": ours,
    }))
    outputs.append(write_jsonl("our_episode_inventory.jsonl", our_episode_rows))
    outputs.append(write_jsonl("collection_errors.jsonl", errors))
    outputs.append(write_json("defect_comparison.md.json", {
        "schema_version": 1,
        "cutoff_utc": cutoff,
        "scope": "Read-only current-cycle comparison of available official metadata with the historical provenance limitation.",
        "known_defect": {
            "status": "HISTORICAL_PROVENANCE_DEFECT_RECORDED_NOT_RETESTED_THIS_CAPTURE",
            "path": "research/campaign_3000/01_internal/runner_done_overwrite_defect.json",
            "claim_limit": "This capture does not execute the local runner and cannot repair or independently reproduce the historical defect."
        },
        "comparison": {
            "prior_snapshot_cutoff_utc": "2026-08-08T17:50:15.385Z",
            "current_submission_count": len(ours),
            "current_top25_rows": len(top_rows),
            "current_top25_episode_metadata_rows": len(top_episode_rows),
            "current_our_episode_metadata_rows": len(our_episode_rows),
            "replay_payloads_downloaded": 0,
            "historical_archive_byte_identity": "UNVERIFIED_KAGGLE_API_DOES_NOT_EXPOSE_HISTORICAL_UPLOAD_BYTES",
        },
    }))
    manifest = {
        "schema_version": 1,
        "capture_kind": "OFFICIAL_KAGGLE_API_READ_ONLY_CURRENT_CYCLE",
        "command": "python research/campaign_3000/13_cycle_20260810/01_internal_live/capture_official_snapshot.py",
        "query_started_at_utc": started,
        "cutoff_utc": cutoff,
        "external_actions": {"upload": false, "save_run": false, "competition_submission": false, "publication": false,
                             "comment": false, "vote": false, "replay_payload_download": false},
        "outputs": outputs,
        "errors": len(errors),
        "limits": [
            "This is a time-bounded API snapshot, not a live or exhaustive historical record.",
            "Unavailable or failed endpoints are recorded in collection_errors.jsonl and never interpreted as zero.",
            "No raw replay payload was downloaded or analyzed in this capture.",
            "No conclusion about private Save & Run kernels follows from the competition-submissions response.",
        ],
        "python": sys.version,
    }
    write_json("capture_manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
