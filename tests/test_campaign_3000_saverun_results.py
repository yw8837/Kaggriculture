from __future__ import annotations

import hashlib
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
DELIVERY_PATH = (
    PROJECT_ROOT
    / "research"
    / "campaign_3000"
    / "11_saverun_results"
    / "auditor_deliveries.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_private_saverun_receipts_are_exact_and_non_submitting() -> None:
    receipt = _load(RECEIPT_PATH)

    assert receipt["schema_version"] == 2
    assert receipt["state"] == "PRIVATE_SAVERUNS_COMPLETE_VERIFIED"
    assert receipt["recorded_against_git_head_scope"] == (
        "PRE_RUN_APPROVED_PACKAGE_FREEZE_ONLY_NOT_POSTRUN_LEDGER_COMMIT"
    )
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
    delivery_payload = DELIVERY_PATH.read_bytes()
    assert receipt["auditor_delivery_receipt"] == {
        "path": "research/campaign_3000/11_saverun_results/auditor_deliveries.json",
        "bytes": len(delivery_payload),
        "sha256": hashlib.sha256(delivery_payload).hexdigest().upper(),
    }
    assert receipt["independent_auditor_release"] == {
        "task_id": "019fb8b8-7758-7860-9304-39eb4f06c65c",
        "host_id": "local",
        "verdict": "RELEASE",
        "scope": "EACH_EXACT_SLOT_PRIVATE_SAVERUN_RELEASE",
        "delivery": {
            "purpose": "private_saverun_release",
            "turn_id": "019fe3bb-78c0-75f1-960b-85f8f837f913",
            "item_id": "item-523",
            "raw_message_utf8_bytes": 3430,
            "raw_message_sha256": (
                "4B37240CFF50B20473172709ABB28601200BDF317B94A19E3009361BDD49AF24"
            ),
        },
        "slots": {"Kag_01": "RELEASE", "Kag_02": "RELEASE"},
    }
    assert receipt["independent_auditor_postrun"] == {
        "task_id": "019fb8b8-7758-7860-9304-39eb4f06c65c",
        "host_id": "local",
        "verdict": "COMPLETE_VERIFIED",
        "scope": "Kag_01 and Kag_02 private Save & Run version 1",
        "method": (
            "live read-only kernel metadata/status plus remote Output API bytes rehashed "
            "in memory"
        ),
        "delivery": {
            "purpose": "private_saverun_postrun",
            "turn_id": "019fe3c6-65de-7351-b35a-3fb15ba9d279",
            "item_id": "item-530",
            "raw_message_utf8_bytes": 1244,
            "raw_message_sha256": (
                "98ACB6BA5084F4377925DB29A86D7AA968E3EDEF6FC876A6D3A4D58104D873A2"
            ),
        },
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
    expected_local_times = {
        "Kag_01": "2026-08-08T23:42:15.120000Z",
        "Kag_02": "2026-08-08T23:45:30.623000Z",
    }
    for slot, entry in slots.items():
        assert entry["version"] == 1
        assert entry["worker_status"] == "KernelWorkerStatus.COMPLETE"
        assert entry["visibility"] == "private"
        assert entry["internet"] is False
        assert entry["second_push_authorized"] is False
        assert "kaggle_last_run_time_utc" not in entry
        assert entry["locally_observed_push_or_complete_time_utc"] == (
            expected_local_times[slot]
        )
        assert entry["time_observation_provenance"] == {
            "source": "main-agent local monitoring record during the authorized SaveRun",
            "raw_kaggle_getkernel_envelope_retained": False,
            "limitation": (
                "This is not asserted as a stable live GetKernel lastRunTime; Kaggle returned "
                "a different mutable value on a later independent read."
            ),
        }
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
        "auditor_verdict": "HOLD",
        "publication_authorized": False,
        "discussion": "HOLD",
        "public_code": "HOLD",
        "delivery": {
            "purpose": "publication_review",
            "turn_id": "019fe3dd-fd97-7462-bed3-4b781297412e",
            "item_id": "item-541",
            "raw_message_utf8_bytes": 2207,
            "raw_message_sha256": (
                "9198BD647A0D08D383F0C529ABEE6B61D5B637ABC9BD9EB0FE83C4B78B805A7D"
            ),
        },
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


def test_auditor_final_message_text_and_delivery_identity_are_sha_bound() -> None:
    delivery = _load(DELIVERY_PATH)
    receipt = _load(RECEIPT_PATH)

    assert delivery["schema_version"] == 1
    assert delivery["artifact_kind"] == (
        "campaign_3000_independent_auditor_final_message_text_receipts_v1"
    )
    assert delivery["canonical_text_definition"] == (
        "Exact final agentMessage text Unicode string encoded as UTF-8 without BOM and with no "
        "appended trailing newline; SHA-256 is uppercase hexadecimal over those bytes."
    )
    assert delivery["identity_source"] == (
        "Main task read_thread observation of the separate user-owned auditor task; full "
        "read_thread envelopes were not retained in this tracked file."
    )
    assert delivery["auditor_task"] == {
        "thread_id": "019fb8b8-7758-7860-9304-39eb4f06c65c",
        "host_id": "local",
        "role": "independent_auditor",
    }

    expected = {
        "private_saverun_release": {
            "turn_id": "019fe3bb-78c0-75f1-960b-85f8f837f913",
            "item_id": "item-523",
            "bytes": 3430,
            "sha256": "4B37240CFF50B20473172709ABB28601200BDF317B94A19E3009361BDD49AF24",
            "effect": "EXACT_ONE_TIME_PRIVATE_SAVERUN_RELEASE_ONLY",
        },
        "private_saverun_postrun": {
            "turn_id": "019fe3c6-65de-7351-b35a-3fb15ba9d279",
            "item_id": "item-530",
            "bytes": 1244,
            "sha256": "98ACB6BA5084F4377925DB29A86D7AA968E3EDEF6FC876A6D3A4D58104D873A2",
            "effect": "COMPLETE_VERIFIED_CLOSURE_NO_NEW_EXTERNAL_AUTHORITY",
        },
        "publication_review": {
            "turn_id": "019fe3dd-fd97-7462-bed3-4b781297412e",
            "item_id": "item-541",
            "bytes": 2207,
            "sha256": "9198BD647A0D08D383F0C529ABEE6B61D5B637ABC9BD9EB0FE83C4B78B805A7D",
            "effect": "DISCUSSION_HOLD_PUBLIC_CODE_HOLD_NO_PUBLICATION_AUTHORITY",
        },
    }
    deliveries = {entry["purpose"]: entry for entry in delivery["deliveries"]}
    assert set(deliveries) == set(expected)
    for purpose, pinned in expected.items():
        entry = deliveries[purpose]
        raw = entry["raw_message_text"].encode("utf-8")
        assert not entry["raw_message_text"].endswith(("\r", "\n"))
        assert len(raw) == pinned["bytes"] == entry["raw_message_utf8_bytes"]
        assert hashlib.sha256(raw).hexdigest().upper() == pinned["sha256"]
        assert entry["raw_message_sha256"] == pinned["sha256"]
        assert entry["turn_id"] == pinned["turn_id"]
        assert entry["item_id"] == pinned["item_id"]
        assert entry["phase"] == "final_answer"
        assert entry["authorized_effect"] == pinned["effect"]

    assert "one-time PRIVATE Save & Run" in deliveries["private_saverun_release"][
        "raw_message_text"
    ]
    assert "COMPLETE_VERIFIED" in deliveries["private_saverun_postrun"][
        "raw_message_text"
    ]
    assert deliveries["publication_review"]["raw_message_text"].startswith(
        "판정: Discussion `HOLD`, public Code `HOLD`."
    )
    assert receipt["publication"]["publication_authorized"] is False


def test_development_close_remains_separate_from_completed_saveruns() -> None:
    lifecycle = _load(LIFECYCLE_PATH)
    assert lifecycle["state"] == "DEVELOPMENT_CLOSED"
    assert lifecycle["fresh_games_executed"] == 256
    assert lifecycle["slots"]["Kag_01"]["development"]["status"] == "CONSUMED_PASS"
    assert lifecycle["slots"]["Kag_02"]["development"]["status"] == "CONSUMED_NO_GO"
    assert lifecycle["external_actions"] == "HOLD"
