from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from collect_kaggle_inventory import normalize_episode
from kaggle.api.kaggle_api_extended import KaggleApi

ROOT = Path(__file__).resolve().parent


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def main() -> None:
    path = ROOT / "our_submissions.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    episode_path = ROOT / "our_episode_inventory.jsonl"
    existing = [json.loads(line) for line in episode_path.read_text(encoding="utf-8").splitlines() if line]
    by_id = {int(row["episode_id"]): row for row in existing}
    api = KaggleApi()
    api.authenticate()
    repaired = []
    errors = []
    for submission in payload["submissions"]:
        if int(submission["episode_count"]) != 0:
            continue
        submission_id = int(submission["ref"])
        episodes = None
        for attempt in range(5):
            try:
                episodes = api.competition_list_episodes(submission_id)
                break
            except Exception as exc:  # noqa: BLE001
                # Retry heterogeneous Kaggle API failures and record the final one.
                if attempt == 4:
                    errors.append(
                        {
                            "at_utc": utc_now(),
                            "operation": "competition_list_episodes_retry",
                            "submission_id": submission_id,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        }
                    )
                else:
                    time.sleep(2**attempt)
        if episodes is None:
            continue
        normalized = [normalize_episode(row, submission_id=submission_id, team_id=16630689) for row in episodes]
        for row in normalized:
            by_id[int(row["episode_id"])] = row
        public = [row for row in normalized if row["type"] == "EPISODE_TYPE_PUBLIC"]
        submission.update(
            {
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
        repaired.append({"submission_id": submission_id, "episodes": len(normalized)})
        time.sleep(1)

    payload["repair_observed_at_utc"] = utc_now()
    payload["repair_status"] = "COMPLETE" if not errors else "PARTIAL"
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    path.write_bytes(raw)
    rows = sorted(by_id.values(), key=lambda row: (int(row["submission_id_queried"]), int(row["episode_id"])))
    episode_raw = b"".join(
        (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for row in rows
    )
    episode_path.write_bytes(episode_raw)
    error_path = ROOT / "repair_errors.jsonl"
    error_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in errors),
        encoding="utf-8",
    )
    result: dict[str, Any] = {
        "repaired_at_utc": utc_now(),
        "repaired": repaired,
        "errors": errors,
        "our_submissions_sha256": sha256(raw),
        "our_submissions_bytes": len(raw),
        "our_episode_inventory_sha256": sha256(episode_raw),
        "our_episode_inventory_bytes": len(episode_raw),
        "our_episode_inventory_rows": len(rows),
    }
    (ROOT / "repair_manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
