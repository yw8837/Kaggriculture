from __future__ import annotations

import hashlib
import json
from pathlib import Path


def test_complete_api_episode_inventory_is_hash_registered() -> None:
    snapshot_path = Path("submissions/api_inventory_2026-08-01.json")
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))

    assert payload["submission_count"] == 2
    assert {row["ref"] for row in payload["submissions"]} == {55137246, 55137248}
    for submission in payload["submissions"]:
        inventory = submission["episode_inventory"]
        episodes = inventory["episodes"]
        assert inventory == {
            "total": 19,
            "public": 18,
            "validation": 1,
            "completed": 19,
            "episodes": episodes,
        }
        assert len(episodes) == len({episode["id"] for episode in episodes}) == 19
        assert all(
            {"id", "type", "state", "createTime", "endTime"} <= episode.keys()
            for episode in episodes
        )
        assert sum("PUBLIC" in episode["type"] for episode in episodes) == 18
        assert sum("VALIDATION" in episode["type"] for episode in episodes) == 1
        assert all("COMPLETED" in episode["state"] for episode in episodes)

    digest = hashlib.sha256(snapshot_path.read_bytes()).hexdigest().upper()
    ledger = [
        json.loads(line)
        for line in Path("submissions/ledger.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    registered = [row for row in ledger if row["record_type"] == "api_episode_inventory_snapshot"]
    assert registered[-1]["snapshot_sha256"] == digest
    assert "historical partial snapshots" in registered[-1]["note"]
