from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _assert_inventory_is_self_consistent(payload: dict) -> None:
    assert payload["submission_count"] == len(payload["submissions"])
    for submission in payload["submissions"]:
        inventory = submission["episode_inventory"]
        episodes = inventory["episodes"]
        assert inventory["total"] == len(episodes)
        assert inventory["public"] == sum("PUBLIC" in row["type"] for row in episodes)
        assert inventory["validation"] == sum("VALIDATION" in row["type"] for row in episodes)
        assert inventory["completed"] == sum("COMPLETED" in row["state"] for row in episodes)
        assert len(episodes) == len({episode["id"] for episode in episodes})
        assert all(
            {"id", "type", "state", "createTime", "endTime"} <= episode.keys()
            for episode in episodes
        )
        assert all("COMPLETED" in episode["state"] for episode in episodes)


def test_append_only_api_episode_inventories_are_hash_registered() -> None:
    historical_path = Path("submissions/api_inventory_2026-08-01.json")
    latest_path = Path("submissions/api_inventory_2026-08-01_critical_3sub.json")
    historical = json.loads(historical_path.read_text(encoding="utf-8"))
    latest = json.loads(latest_path.read_text(encoding="utf-8"))

    _assert_inventory_is_self_consistent(historical)
    _assert_inventory_is_self_consistent(latest)
    assert historical["submission_count"] == 2
    assert {row["ref"] for row in historical["submissions"]} == {55137246, 55137248}
    assert latest["submission_count"] == 3
    assert {row["ref"] for row in latest["submissions"]} == {
        55137246,
        55137248,
        55142935,
    }
    assert [row["episode_inventory"]["total"] for row in latest["submissions"]] == [19, 23, 9]
    assert all(row["episode_inventory"]["validation"] == 1 for row in latest["submissions"])

    ledger = [
        json.loads(line)
        for line in Path("submissions/ledger.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    registered = [row for row in ledger if row["record_type"] == "api_episode_inventory_snapshot"]
    expected = {
        historical_path.as_posix(): hashlib.sha256(historical_path.read_bytes()).hexdigest().upper(),
        latest_path.as_posix(): hashlib.sha256(latest_path.read_bytes()).hexdigest().upper(),
    }
    assert {row["snapshot_path"]: row["snapshot_sha256"] for row in registered} == expected
    historical_record = next(
        row for row in registered if row["snapshot_path"] == historical_path.as_posix()
    )
    assert "historical partial snapshots" in historical_record["note"]

    discovered = [row for row in ledger if row["record_type"] == "external_submission_discovered"]
    assert discovered[-1]["submission_ref"] == 55142935
    assert discovered[-1]["actor"] == "unknown_pending_user_confirmation"
    assert discovered[-1]["authorization_provenance"] == "unresolved"

    confirmed = [row for row in ledger if row["record_type"] == "submission_actor_confirmation"]
    assert confirmed[-1]["submission_ref"] == 55142935
    assert confirmed[-1]["actor"] == "user_manual_kaggle_ui"
    assert confirmed[-1]["authorization_provenance"] == "user_confirmed_direct_action"
    assert confirmed[-1]["submitted_by_codex"] is False
    assert confirmed[-1]["scope"].startswith("Confirms the historical actor only")


def test_champion_manifest_records_all_observed_submissions_without_guessing_actor() -> None:
    manifest = json.loads(Path("artifacts/champion/manifest.json").read_text(encoding="utf-8"))
    assert manifest["active_competition_submissions"] == [55137246, 55137248, 55142935]
    fa01 = manifest["rejected_history"][0]
    assert fa01["submitted"] is True
    assert fa01["competition_submission"]["ref"] == 55142935
    assert fa01["competition_submission"]["actor"] == "user_manual_kaggle_ui"
    assert fa01["competition_submission"]["authorization_provenance"] == "user_confirmed_direct_action"
    assert fa01["competition_submission"]["submitted_by_codex"] is False
