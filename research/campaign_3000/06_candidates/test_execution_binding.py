from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

MODULE_PATH = Path(__file__).with_name("orchestrator.py")
SPEC = importlib.util.spec_from_file_location("candidate_freeze_orchestrator_binding", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
ORCHESTRATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ORCHESTRATOR)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2) + "\n").encode()


def _git(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _test_plan() -> dict[str, Any]:
    candidates = []
    for index, (slot, ranges) in enumerate(ORCHESTRATOR.EXPECTED_SEED_RANGES.items(), 1):
        candidates.append(
            {
                "slot": slot,
                "candidate_sha256": str(index) * 64,
                "seed_pools": {
                    phase: {
                        "start": bounds[0],
                        "end_inclusive": bounds[1],
                        "count": bounds[1] - bounds[0] + 1,
                    }
                    for phase, bounds in ranges.items()
                },
                "expected_cells": {
                    "development": 128,
                    "confirmation": 512,
                    "robustness": 1024,
                },
            }
        )
    return {
        "engine": {
            "package": "kaggle-environments",
            "version": "1.32.6",
            "environment": "kaggriculture",
        },
        "candidates": candidates,
    }


def _write_freeze_files(
    repo: Path, *, manifest_sha_override: str | None = None
) -> Path:
    input_bytes = b"candidate-v1\n"
    plan = _test_plan()
    plan_bytes = _json_bytes(plan)
    (repo / "input.txt").write_bytes(input_bytes)
    (repo / "candidate_plan.json").write_bytes(plan_bytes)
    manifest_bytes = _json_bytes(
        {
            "schema_version": 1,
            "files": [
                {
                    "path": "input.txt",
                    "bytes": len(input_bytes),
                    "sha256": _sha256(input_bytes),
                },
                {
                    "path": "candidate_plan.json",
                    "bytes": len(plan_bytes),
                    "sha256": _sha256(plan_bytes),
                },
            ],
        }
    )
    (repo / "manifest.json").write_bytes(manifest_bytes)
    binding = {
        "schema_version": 1,
        "binding_protocol": "clean_two_stage_S_to_E_v1",
        "implementation_commit": "PENDING",
        "input_manifest": {
            "path": "manifest.json",
            "bytes": len(manifest_bytes),
            "sha256": manifest_sha_override or _sha256(manifest_bytes),
        },
        "binding_path": "execution_binding.json",
        "binding_excluded_from_input_manifest": True,
        "lifecycle_path": "lifecycle.json",
        "lifecycle_excluded_from_input_manifest": True,
        "candidate_plan_path": "candidate_plan.json",
        "tracked_execution_inputs": ["input.txt", "candidate_plan.json"],
    }
    binding_path = repo / "execution_binding.json"
    binding_path.write_bytes(_json_bytes(binding))
    (repo / "lifecycle.json").write_bytes(
        _json_bytes(ORCHESTRATOR._closed_lifecycle(plan))
    )
    (repo / ".gitignore").write_bytes(b"dist/\n")
    return binding_path


def _create_two_stage_repo(
    tmp_path: Path, *, manifest_sha_override: str | None = None
) -> tuple[Path, str, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.name", "Binding Test")
    _git(repo, "config", "user.email", "binding-test@example.invalid")
    _git(repo, "config", "core.autocrlf", "false")
    binding_path = _write_freeze_files(
        repo, manifest_sha_override=manifest_sha_override
    )
    _git(
        repo,
        "add",
        ".gitignore",
        "input.txt",
        "candidate_plan.json",
        "manifest.json",
        "execution_binding.json",
        "lifecycle.json",
    )
    _git(repo, "commit", "--quiet", "-m", "S implementation freeze")
    implementation_commit = _git(repo, "rev-parse", "HEAD")
    binding_bytes = binding_path.read_bytes()
    binding_path.write_bytes(
        binding_bytes.replace(
            b'"implementation_commit": "PENDING"',
            f'"implementation_commit": "{implementation_commit}"'.encode(),
        )
    )
    _git(repo, "add", "execution_binding.json")
    _git(repo, "commit", "--quiet", "-m", "E execution binding")
    return repo, implementation_commit, _git(repo, "rev-parse", "HEAD")


def test_pending_is_accepted_only_in_implementation_freeze(tmp_path: Path) -> None:
    repo = tmp_path / "pending"
    repo.mkdir()
    binding_path = _write_freeze_files(repo)

    result = ORCHESTRATOR.validate_execution_binding(
        "implementation-freeze", repo, binding_path
    )
    assert result["status"] == "VALID_IMPLEMENTATION_FREEZE_PENDING"
    with pytest.raises(ValueError, match="full lowercase implementation commit"):
        ORCHESTRATOR.validate_execution_binding(
            "execution", repo, binding_path
        )


def test_valid_clean_two_stage_binding(tmp_path: Path) -> None:
    repo, implementation_commit, execution_commit = _create_two_stage_repo(tmp_path)
    result = ORCHESTRATOR.validate_execution_binding(
        "execution", repo, repo / "execution_binding.json"
    )
    assert result["status"] == "VALID_CLEAN_EXECUTION_BINDING"
    assert result["implementation_commit"] == implementation_commit
    assert result["execution_commit"] == execution_commit


def test_wrong_parent_is_rejected(tmp_path: Path) -> None:
    repo, _, _ = _create_two_stage_repo(tmp_path)
    _git(repo, "commit", "--quiet", "--allow-empty", "-m", "wrong execution parent")
    with pytest.raises(ValueError, match="not exactly E parent S"):
        ORCHESTRATOR.validate_execution_binding(
            "execution", repo, repo / "execution_binding.json"
        )


def test_wrong_manifest_pin_is_rejected(tmp_path: Path) -> None:
    repo, _, _ = _create_two_stage_repo(tmp_path, manifest_sha_override="0" * 64)
    with pytest.raises(ValueError, match="current manifest SHA mismatch"):
        ORCHESTRATOR.validate_execution_binding(
            "execution", repo, repo / "execution_binding.json"
        )


def test_current_input_bytes_different_from_s_are_rejected(tmp_path: Path) -> None:
    repo, _, _ = _create_two_stage_repo(tmp_path)
    _git(repo, "update-index", "--assume-unchanged", "input.txt")
    (repo / "input.txt").write_bytes(b"candidate-v2\n")
    assert _git(repo, "status", "--porcelain=v1", "--untracked-files=no") == ""
    with pytest.raises(ValueError, match="current input SHA mismatch"):
        ORCHESTRATOR.validate_execution_binding(
            "execution", repo, repo / "execution_binding.json"
        )


def test_dirty_tracked_tree_is_rejected(tmp_path: Path) -> None:
    repo, _, _ = _create_two_stage_repo(tmp_path)
    (repo / "input.txt").write_bytes(b"dirty\n")
    with pytest.raises(ValueError, match="tracked tree is dirty"):
        ORCHESTRATOR.validate_execution_binding(
            "execution", repo, repo / "execution_binding.json"
        )


def _authority_receipt(
    repo: Path, implementation_commit: str, execution_commit: str
) -> dict[str, Any]:
    plan = json.loads((repo / "candidate_plan.json").read_text(encoding="utf-8"))
    binding = json.loads((repo / "execution_binding.json").read_text(encoding="utf-8"))
    return {
        "schema_version": 1,
        "receipt_type": "INDEPENDENT_AUDITOR_EXACT_DEVELOPMENT_OPEN",
        "issued_at_utc": "2026-08-09T00:00:00Z",
        "auditor_attestation": {
            "task_id": ORCHESTRATOR.AUDITOR_TASK_ID,
            "role": "independent-auditor",
            "verdict": "OPEN",
            "scope": "EXACT_LOCAL_DEVELOPMENT_RANGES_ONLY",
        },
        "subject": {
            "execution_commit": execution_commit,
            "implementation_commit": implementation_commit,
            "input_manifest_sha256": binding["input_manifest"]["sha256"],
            "candidate_plan_sha256": _sha256((repo / "candidate_plan.json").read_bytes()),
            "engine": plan["engine"],
        },
        "authorizations": ORCHESTRATOR._exact_phase_records(
            plan, ("development",), "OPEN"
        ),
        "holds": ORCHESTRATOR._exact_phase_records(
            plan, ("confirmation", "robustness"), "HOLD"
        ),
        "prohibitions": {
            "kaggle_save_run": "HOLD",
            "upload": "HOLD",
            "competition_submission": "HOLD",
            "publication": "HOLD",
        },
        "prior_execution": {"fresh_games_executed": 0, "opened_seed_ranges": []},
    }


def _raw_read_thread_export(decision: dict[str, Any], suffix: str) -> bytes:
    raw_message = json.dumps(decision, sort_keys=True, separators=(",", ":"))
    return _json_bytes(
        {
            "schemaVersion": 1,
            "thread": {
                "id": ORCHESTRATOR.AUDITOR_TASK_ID,
                "kind": "codex",
                "hostId": "local",
                "title": "Independent auditor",
                "status": {"type": "idle"},
            },
            "page": {"hasMore": False, "cursor": None, "order": "newest_first"},
            "turns": [
                {
                    "id": f"turn-{suffix}",
                    "status": "completed",
                    "error": None,
                    "items": [
                        {
                            "type": "agentMessage",
                            "id": f"item-{suffix}",
                            "text": raw_message,
                            "phase": "final_answer",
                        }
                    ],
                }
            ],
        }
    )


def _delivery_pin(path: Path, payload: bytes, suffix: str) -> dict[str, Any]:
    export = json.loads(payload)
    raw_message = export["turns"][-1]["items"][-1]["text"]
    return {
        "path": path.as_posix(),
        "bytes": len(payload),
        "sha256": _sha256(payload),
        "thread_id": ORCHESTRATOR.AUDITOR_TASK_ID,
        "host_id": "local",
        "turn_id": f"turn-{suffix}",
        "item_id": f"item-{suffix}",
        "raw_message_sha256": _sha256(raw_message.encode()),
    }


def _commit_authority_open(
    repo: Path,
    implementation_commit: str,
    execution_commit: str,
    *,
    receipt_mutation: tuple[tuple[str | int, ...], Any] | None = None,
    naked_lifecycle: bool = False,
    extra_tracked_change: bool = False,
    synthetic_delivery: bool = False,
) -> dict[str, Path]:
    receipt = _authority_receipt(repo, implementation_commit, execution_commit)
    if receipt_mutation is not None:
        path, value = receipt_mutation
        target: Any = receipt
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
    receipt_path = repo / ORCHESTRATOR.AUTHORITY_RECEIPT_RELATIVE
    delivery_path = repo / ORCHESTRATOR.AUDITOR_OPEN_DELIVERY_RELATIVE
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    initial_decision = {
        "verdict": "OPEN",
        "auditor_attestation": receipt["auditor_attestation"],
        "subject": receipt["subject"],
        "authorizations": receipt["authorizations"],
        "holds": receipt["holds"],
        "prohibitions": receipt["prohibitions"],
        "prior_execution": receipt["prior_execution"],
    }
    delivery_bytes = (
        _json_bytes(
            {
                "schema_version": 1,
                "artifact_kind": "synthetic_manual_wrapper",
                "decision": initial_decision,
            }
        )
        if synthetic_delivery
        else _raw_read_thread_export(initial_decision, "initial")
    )
    delivery_path.write_bytes(delivery_bytes)
    delivery_pin = (
        {
            "path": ORCHESTRATOR.AUDITOR_OPEN_DELIVERY_RELATIVE,
            "bytes": len(delivery_bytes),
            "sha256": _sha256(delivery_bytes),
            "thread_id": ORCHESTRATOR.AUDITOR_TASK_ID,
            "host_id": "local",
            "turn_id": "synthetic",
            "item_id": "synthetic",
            "raw_message_sha256": _sha256(_json_bytes(initial_decision)),
        }
        if synthetic_delivery
        else _delivery_pin(
            Path(ORCHESTRATOR.AUDITOR_OPEN_DELIVERY_RELATIVE),
            delivery_bytes,
            "initial",
        )
    )
    receipt["auditor_delivery"] = delivery_pin
    receipt_bytes = _json_bytes(receipt)
    receipt_path.write_bytes(receipt_bytes)
    plan = json.loads((repo / "candidate_plan.json").read_text(encoding="utf-8"))
    lifecycle = (
        {"state": "DEVELOPMENT_OPEN"}
        if naked_lifecycle
        else ORCHESTRATOR._open_lifecycle(
            plan, execution_commit, receipt_bytes, delivery_bytes
        )
    )
    (repo / "lifecycle.json").write_bytes(_json_bytes(lifecycle))
    _git(repo, "add", "lifecycle.json")
    if extra_tracked_change:
        (repo / "input.txt").write_bytes(b"extra-change\n")
        _git(repo, "add", "input.txt")
    _git(repo, "commit", "--quiet", "-m", "O auditor authority")
    authority_commit = _git(repo, "rev-parse", "HEAD")
    review_path = repo / ORCHESTRATOR.AUDITOR_O_REVIEW_RELATIVE
    review_decision = {
        "verdict": "OPEN",
        "authority_commit": authority_commit,
        "execution_commit": execution_commit,
        "lifecycle_sha256": _sha256((repo / "lifecycle.json").read_bytes()),
        "authority_receipt_sha256": _sha256(receipt_bytes),
        "auditor_open_delivery_sha256": _sha256(delivery_bytes),
        "confirmation": "HOLD",
        "robustness": "HOLD",
        "external_actions": "HOLD",
        "fresh_games_executed": 0,
    }
    review_path.write_bytes(_raw_read_thread_export(review_decision, "review"))
    return {"receipt": receipt_path, "delivery": delivery_path, "review": review_path}


def test_exact_receipt_and_lifecycle_only_o_authorize_development(tmp_path: Path) -> None:
    repo, implementation_commit, execution_commit = _create_two_stage_repo(tmp_path)
    evidence = _commit_authority_open(repo, implementation_commit, execution_commit)
    authority = ORCHESTRATOR.validate_development_authority(
        repo,
        repo / "execution_binding.json",
        repo / "lifecycle.json",
        evidence["receipt"],
        evidence["delivery"],
        evidence["review"],
    )
    assert authority["status"] == "AUTHORIZED_DEVELOPMENT_OPEN"
    assert authority["authorized_ranges"] == {
        "Kag_01": [50000, 50015],
        "Kag_02": [53000, 53015],
    }
    opened = ORCHESTRATOR.require_open_authority(
        "Kag_01",
        "development",
        repo,
        repo / "execution_binding.json",
        repo / "lifecycle.json",
        evidence["receipt"],
        evidence["delivery"],
        evidence["review"],
    )
    assert opened["status"] == "AUTHORIZED_LOCAL_DEVELOPMENT_EXECUTION"
    assert opened["seeds"] == list(range(50000, 50016))
    assert opened["external_actions"] == "HOLD"
    for phase in ("confirmation", "robustness"):
        with pytest.raises(PermissionError, match="HOLD"):
            ORCHESTRATOR.require_open_authority(
                "Kag_01",
                phase,
                repo,
                repo / "execution_binding.json",
                repo / "lifecycle.json",
                evidence["receipt"],
                evidence["delivery"],
                evidence["review"],
            )


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("auditor_attestation", "task_id"), "wrong-task", "attestation mismatch"),
        (("subject", "execution_commit"), "0" * 40, "subject mismatch"),
        (("authorizations", 0, "slot"), "Kag_99", "slot/range/OPEN mismatch"),
        (("authorizations", 0, "seed_start"), 50001, "slot/range/OPEN mismatch"),
        (("authorizations", 0, "verdict"), "HOLD", "slot/range/OPEN mismatch"),
        (("holds", 0, "verdict"), "OPEN", "confirmation/robustness HOLD mismatch"),
    ],
)
def test_forged_authority_receipt_fields_are_rejected(
    tmp_path: Path, path: tuple[str | int, ...], value: Any, message: str
) -> None:
    repo, implementation_commit, execution_commit = _create_two_stage_repo(tmp_path)
    evidence = _commit_authority_open(
        repo,
        implementation_commit,
        execution_commit,
        receipt_mutation=(path, value),
    )
    with pytest.raises(ValueError, match=message):
        ORCHESTRATOR.validate_development_authority(
            repo,
            repo / "execution_binding.json",
            repo / "lifecycle.json",
            evidence["receipt"],
            evidence["delivery"],
            evidence["review"],
        )


def test_naked_open_string_is_rejected(tmp_path: Path) -> None:
    repo, implementation_commit, execution_commit = _create_two_stage_repo(tmp_path)
    evidence = _commit_authority_open(
        repo, implementation_commit, execution_commit, naked_lifecycle=True
    )
    with pytest.raises(ValueError, match="not exactly O parent E"):
        ORCHESTRATOR.validate_development_authority(
            repo,
            repo / "execution_binding.json",
            repo / "lifecycle.json",
            evidence["receipt"],
            evidence["delivery"],
            evidence["review"],
        )


def test_authority_o_with_extra_tracked_change_is_rejected(tmp_path: Path) -> None:
    repo, implementation_commit, execution_commit = _create_two_stage_repo(tmp_path)
    evidence = _commit_authority_open(
        repo, implementation_commit, execution_commit, extra_tracked_change=True
    )
    with pytest.raises(ValueError, match="change only lifecycle"):
        ORCHESTRATOR.validate_development_authority(
            repo,
            repo / "execution_binding.json",
            repo / "lifecycle.json",
            evidence["receipt"],
            evidence["delivery"],
            evidence["review"],
        )


def test_authority_o_must_have_exact_e_parent(tmp_path: Path) -> None:
    repo, implementation_commit, execution_commit = _create_two_stage_repo(tmp_path)
    evidence = _commit_authority_open(repo, implementation_commit, execution_commit)
    _git(repo, "commit", "--quiet", "--allow-empty", "-m", "not O")
    with pytest.raises(ValueError, match="not exactly O parent E"):
        ORCHESTRATOR.validate_development_authority(
            repo,
            repo / "execution_binding.json",
            repo / "lifecycle.json",
            evidence["receipt"],
            evidence["delivery"],
            evidence["review"],
        )


def test_synthetic_auditor_wrapper_is_rejected_even_when_o_pins_it(
    tmp_path: Path,
) -> None:
    repo, implementation_commit, execution_commit = _create_two_stage_repo(tmp_path)
    evidence = _commit_authority_open(
        repo,
        implementation_commit,
        execution_commit,
        synthetic_delivery=True,
    )
    with pytest.raises(ValueError, match="unmodified codex_app__read_thread"):
        ORCHESTRATOR.validate_development_authority(
            repo,
            repo / "execution_binding.json",
            repo / "lifecycle.json",
            evidence["receipt"],
            evidence["delivery"],
            evidence["review"],
        )


def test_post_o_second_auditor_delivery_is_mandatory(tmp_path: Path) -> None:
    repo, implementation_commit, execution_commit = _create_two_stage_repo(tmp_path)
    evidence = _commit_authority_open(repo, implementation_commit, execution_commit)
    evidence["review"].unlink()
    with pytest.raises(ValueError, match="raw auditor task delivery is missing"):
        ORCHESTRATOR.validate_development_authority(
            repo,
            repo / "execution_binding.json",
            repo / "lifecycle.json",
            evidence["receipt"],
            evidence["delivery"],
            evidence["review"],
        )


def test_report_gate_rejects_closed_synthetic_rows_without_authorized_run(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "synthetic.json"
    with pytest.raises(PermissionError, match="OPEN authority"):
        ORCHESTRATOR.validate_report_files(
            "Kag_01", "development", missing, missing, missing, missing
        )


def test_run_entrypoint_refuses_current_closed_reserved_seeds(tmp_path: Path) -> None:
    repo = tmp_path / "closed_run"
    repo.mkdir()
    binding_path = _write_freeze_files(repo)
    with pytest.raises(PermissionError, match="CLOSED"):
        ORCHESTRATOR.require_open_authority(
            "Kag_01",
            "development",
            repo,
            binding_path,
            repo / "lifecycle.json",
        )


def test_seed_scan_excludes_downstream_prefixes_but_detects_prior_collision(
    tmp_path: Path,
) -> None:
    downstream = {
        "research/campaign_3000/06_candidates/reservation.json": 50000,
        "research/campaign_3000/07_release/reservation.json": 51000,
        "research/campaign_3000/08_public_release/reservation.json": 52000,
        "research/campaign_3000/09_audit/reservation.json": 53000,
    }
    for relative, seed in downstream.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_json_bytes({"seed": seed}))
    prior_path = tmp_path / "research/campaign_3000/05_engine_screen/prior.json"
    prior_path.parent.mkdir(parents=True)
    prior_path.write_bytes(_json_bytes({"seed": 123}))

    before = ORCHESTRATOR.scan_observed_seeds(tmp_path)
    assert before["excluded_prefixes"] == list(ORCHESTRATOR.SCAN_EXCLUDED_PREFIXES)
    assert before["observed_seed_values"] == [123]

    new_prior_path = tmp_path / "research/campaign_3000/04_synthesis/new_prior.json"
    new_prior_path.parent.mkdir(parents=True)
    new_prior_path.write_bytes(_json_bytes({"seed": 50000}))
    after = ORCHESTRATOR.scan_observed_seeds(tmp_path)
    assert after["observed_seed_values"] == [123, 50000]
