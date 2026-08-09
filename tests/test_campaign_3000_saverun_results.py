from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RECEIPT_PATH = (
    PROJECT_ROOT
    / "research"
    / "campaign_3000"
    / "11_saverun_results"
    / "remote_receipts.json"
)
LIFECYCLE_PATH = (
    PROJECT_ROOT
    / "research"
    / "campaign_3000"
    / "06_candidates"
    / "lifecycle.json"
)
PRIVATE_MANIFEST_PATH = (
    PROJECT_ROOT
    / "research"
    / "campaign_3000"
    / "08_public_release"
    / "evidence"
    / "private_release_manifest.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_private_saverun_receipts_are_exact_and_non_submitting() -> None:
    receipt = _load(RECEIPT_PATH)

    assert receipt["state"] == "PRIVATE_SAVERUNS_COMPLETE_VERIFIED"
    assert receipt["approved_package_binding"] == {
        "git_head": "b13eeb2f3b92fe51393fbce37ef21112b26af686",
        "release_manifest_path": (
            "research/campaign_3000/08_public_release/evidence/"
            "private_release_manifest.json"
        ),
        "release_manifest_bytes": 18927,
        "release_manifest_sha256": (
            "F99D31D750E1D4EAF26127308C720A6BD042E32CA3F05AFC16CDB6182925F224"
        ),
    }
    assert receipt["independent_auditor_release"] == {
        "task_id": "019fb8b8-7758-7860-9304-39eb4f06c65c",
        "verdict": "PASS",
        "scope": "EACH_EXACT_SLOT_PRIVATE_SAVERUN_RELEASE",
        "slots": {"Kag_01": "PASS", "Kag_02": "PASS"},
    }
    assert receipt["independent_auditor_postrun"] == {
        "task_id": "019fb8b8-7758-7860-9304-39eb4f06c65c",
        "verdict": "COMPLETE_VERIFIED",
        "scope": "Kag_01 and Kag_02 private Save & Run version 1",
        "method": (
            "live read-only kernel metadata/status plus remote Output API bytes rehashed "
            "in memory"
        ),
    }
    assert receipt["additional_external_action_authority"] == "HOLD"
    assert receipt["competition_submission"] == {
        "performed_by_this_release": False,
        "snapshot_at_utc": "2026-08-08T23:51:25.917Z",
        "exact_total": 22,
        "latest_ref": 55270999,
    }

    slots = {entry["slot"]: entry for entry in receipt["slots"]}
    assert set(slots) == {"Kag_01", "Kag_02"}
    assert slots["Kag_01"]["classification"] == (
        "STRICT_DEVELOPMENT_PASS_PRIVATE_SAVERUN"
    )
    assert slots["Kag_02"]["classification"] == (
        "EXPLORATORY_PRIVATE_SAVERUN_READY_NON_PROMOTION"
    )
    assert slots["Kag_02"]["strict_development_verdict"] == "NO_GO"

    expected_archives = {
        "Kag_01": (
            19099,
            "184F687C474933A7215DB97E8C5A5F823AE79233EEA42D04B70EABC001BF9E16",
        ),
        "Kag_02": (
            17360,
            "37EA53D3046E3D1DA914F8A89C6F4BB02E240E1BB85857BDA149273FC4DD974C",
        ),
    }
    expected_prepush = {
        "Kag_01": (
            17615,
            "15A034D50B9BBC417F91F185C61719100DB3F8D7D94672A9198032B78636B9DC",
        ),
        "Kag_02": (
            18225,
            "86461AEB7709E3569D55A275E80E8B1969BBAB4B7D8F25BBD31B5E933AC050F9",
        ),
    }
    for slot, entry in slots.items():
        assert entry["version"] == 1
        assert entry["worker_status"] == "KernelWorkerStatus.COMPLETE"
        assert entry["visibility"] == "private"
        assert entry["internet"] is False
        assert entry["second_push_authorized"] is False
        assert (entry["approved_prepush"]["bytes"], entry["approved_prepush"]["sha256"]) == (
            expected_prepush[slot]
        )
        assert entry["archive"]["remote_equals_approved"] is True
        assert (entry["archive"]["bytes"], entry["archive"]["sha256"]) == (
            expected_archives[slot]
        )
        assert entry["log"]["error_pattern_hits"] == 0
        assert entry["member_order"] == ["main.py", "LICENSE", "ATTRIBUTION.md"]
        assert entry["deterministic_tar_metadata"] == {
            "mode": "0644",
            "uid": 0,
            "gid": 0,
            "mtime": 0,
            "uname": "",
            "gname": "",
        }
        assert entry["main_compile"] == "PASS"

    assert receipt["publication"] == {
        "discussion": "HOLD",
        "public_code": "HOLD",
        "required_order": ["discussion", "public_code"],
    }
    assert receipt["confirmation_and_robustness"] == "HOLD"


def test_receipt_is_bound_to_the_tracked_final_private_manifest() -> None:
    import hashlib

    receipt = _load(RECEIPT_PATH)
    binding = receipt["approved_package_binding"]
    payload = PRIVATE_MANIFEST_PATH.read_bytes()
    assert len(payload) == binding["release_manifest_bytes"]
    assert hashlib.sha256(payload).hexdigest().upper() == binding["release_manifest_sha256"]

    manifest = json.loads(payload)
    candidates = {entry["sequence"]: entry for entry in manifest["candidates"]}
    slots = {entry["slot"]: entry for entry in receipt["slots"]}
    for slot, recorded in slots.items():
        approved = candidates[slot]
        assert approved["artifact"]["bytes"] == recorded["archive"]["bytes"]
        assert approved["artifact"]["sha256"] == recorded["archive"]["sha256"]
        assert approved["prepush"]["sha256"] == recorded["approved_prepush"]["sha256"]


def test_development_close_remains_separate_from_completed_saveruns() -> None:
    lifecycle = _load(LIFECYCLE_PATH)
    assert lifecycle["state"] == "DEVELOPMENT_CLOSED"
    assert lifecycle["fresh_games_executed"] == 256
    assert lifecycle["slots"]["Kag_01"]["development"]["status"] == "CONSUMED_PASS"
    assert lifecycle["slots"]["Kag_02"]["development"]["status"] == "CONSUMED_NO_GO"
    assert lifecycle["external_actions"] == "HOLD"
