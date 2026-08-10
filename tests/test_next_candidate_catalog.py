"""Static guard for Kag_03/Kag_04 planning reservations."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import ClassVar

import pytest

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "research" / "campaign_3000" / "12_next_candidates" / "candidate_catalog.json"
SEED_RESERVATION = (
    ROOT / "research" / "campaign_3000" / "12_next_candidates" / "seed_reservation.py"
)
DEVELOPMENT_GATE = (
    ROOT / "research" / "campaign_3000" / "12_next_candidates" / "development_gate.py"
)


def _seed_reservation_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("test_next_seed_reservation", SEED_RESERVATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def _development_gate_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("test_next_development_gate", DEVELOPMENT_GATE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _patch_gate_documents(
    monkeypatch, gate: ModuleType, replacements: dict[Path, dict]
) -> None:
    original_load = gate._load

    def patched_load(path: Path) -> dict:
        if path in replacements:
            return copy.deepcopy(replacements[path])
        return original_load(path)

    monkeypatch.setattr(gate, "_load", patched_load)


def _report_for_exact_grid(slot: str, *, beat_tetsu: bool = False) -> dict:
    gate = _development_gate_module()
    plan = gate._load(gate.PLAN_PATH)
    cells = gate.expected_development_cells(slot)
    slot_plan = plan["slots"][slot]
    runtime_environment = gate._expected_runtime_environment_snapshot(plan["engine"])
    execution_inputs = gate._expected_execution_inputs_snapshot(plan)
    opponent_hashes = {
        item["path"]: item["sha256"] for item in plan["runner"]["opponents"]
    }
    tetsu_path = next(
        item["path"]
        for item in plan["runner"]["opponents"]
        if item["alias"] == "tetsu_v16"
    )
    effective_scenarios = {"default": {"episodeSteps": 720}}
    runtime_make_callable = {
        "package_make_is_core_make": True,
        "function_type": True,
        "globals_is_core_module": True,
        "module": "kaggle_environments.core",
        "qualname": "make",
        "source_path_matches_core": True,
        "compiled_make_count": 1,
        "ast_make_count": 1,
        "ast_function_sha256": "C" * 64,
        "function_source_sha256": "D" * 64,
        "code_equals_compiled_source": True,
        "startup_environment": {
            "PYTHONPATH": None,
            "PYTHONHOME": None,
            "PYTHONSTARTUP": None,
            "PYTHONINSPECT": None,
            "PYTHONUSERBASE": None,
        },
        "defaults_sha256": "E" * 64,
    }
    candidate_metrics_total = {
        "calls": len(cells) * 719,
        "preemptions": len(cells),
        "horizon4_preemptions": len(cells),
    }
    return {
        "execution_context_schema_version": 1,
        "runtime_environment_at_start": runtime_environment,
        "runtime_environment_at_start_sha256": gate._canonical_json_sha256(
            runtime_environment
        ),
        "runtime_environment_at_end": copy.deepcopy(runtime_environment),
        "runtime_environment_at_end_sha256": gate._canonical_json_sha256(
            runtime_environment
        ),
        "runtime_environment_unchanged_during_run": True,
        "execution_inputs_at_start": execution_inputs,
        "execution_inputs_at_start_sha256": gate._canonical_json_sha256(execution_inputs),
        "execution_inputs_at_end": copy.deepcopy(execution_inputs),
        "execution_inputs_at_end_sha256": gate._canonical_json_sha256(execution_inputs),
        "execution_inputs_unchanged_during_run": True,
        "execution_context_unchanged_during_run": True,
        "execution_gate_valid": True,
        "candidate": slot_plan["candidate_path"],
        "candidate_path": str((ROOT / slot_plan["candidate_path"]).resolve()),
        "opponents": [item["path"] for item in plan["runner"]["opponents"]],
        "sources_unchanged_during_run": True,
        "candidate_sha256": slot_plan["candidate_source_sha256"],
        "candidate_sha256_at_start": slot_plan["candidate_source_sha256"],
        "candidate_sha256_at_end": slot_plan["candidate_source_sha256"],
        "opponent_sha256_at_start": opponent_hashes,
        "opponent_sha256_at_end": dict(opponent_hashes),
        "scenario_overrides": {"default": {}},
        "effective_scenarios": effective_scenarios,
        "effective_scenarios_sha256": gate._canonical_json_sha256(effective_scenarios),
        "seeds": sorted({cell["seed"] for cell in cells}),
        "seat_policy": "both seats scored; confidence interval is clustered by seed",
        "summary": {
            "raw_games": len(cells),
            "valid_raw_games": len(cells),
            "failed_raw_games": 0,
            "hidden_abnormal_status_failures": 0,
            "candidate_metrics_games": len(cells),
            "candidate_metrics_total": candidate_metrics_total,
        },
        "games": [
            {
                **cell,
                "candidate_money": 101.0 if beat_tetsu and cell["opponent"] == tetsu_path else 100.0,
                "opponent_money": 100.0,
                "candidate_status": "DONE",
                "opponent_status": "DONE",
                "elapsed_seconds": 0.1,
                "error": None,
                "hidden_abnormal_status": None,
                "resolved_environment_seed": cell["seed"],
                "effective_configuration": {
                    "episodeSteps": 720,
                    "seed": cell["seed"],
                },
                "effective_configuration_sha256": gate._canonical_json_sha256(
                    {"episodeSteps": 720, "seed": cell["seed"]}
                ),
                "environment_configuration": plan["engine"]["environment_configuration"],
                "environment_configuration_sha256": plan["engine"][
                    "environment_configuration_sha256"
                ],
                "runtime_make_callable": runtime_make_callable,
                "candidate_metrics": {
                    "calls": 719,
                    "preemptions": 1,
                    "horizon4_preemptions": 1,
                },
            }
            for cell in cells
        ],
    }


def test_next_candidate_pools_are_closed_and_disjoint() -> None:
    catalog = _load()
    assert catalog["status"] == "CLOSED_PLANNING_NO_SEED_AUTHORITY"
    values: set[int] = set()
    for slot in catalog["slots"]:
        for pool in slot["seed_pools"].values():
            assert pool["status"] == "CLOSED"
            assert pool["opened"] is False
            assert pool["consumed"] is False
            assert pool["evaluated_games"] == 0
            current = set(range(pool["start"], pool["end_inclusive"] + 1))
            assert not values.intersection(current)
            values.update(current)
    assert len(values) == 224
    assert catalog["reservation_check"]["fresh_games_executed"] == 0


def test_development_plan_is_closed_default_only_and_exactly_160_cells_per_slot() -> None:
    gate = _development_gate_module()
    result = gate.validate_plan()

    assert result == {
        "status": "VALID_CLOSED_DEVELOPMENT_PLAN",
        "slots": ["Kag_03", "Kag_04"],
        "development_cells": {"Kag_03": 160, "Kag_04": 160},
        "future_phases": "CLOSED_NO_EVALUATION_FRAMEWORK",
    }


def test_development_plan_rejects_a_stale_builder_file_pin(monkeypatch) -> None:
    gate = _development_gate_module()
    plan = gate._load(gate.PLAN_PATH)
    plan["slots"]["Kag_03"]["builder_bytes"] += 1
    _patch_gate_documents(monkeypatch, gate, {gate.PLAN_PATH: plan})

    with pytest.raises(ValueError, match="builder source pin does not match current bytes"):
        gate.validate_plan()


def test_development_plan_rejects_catalog_builder_pin_drift(monkeypatch) -> None:
    gate = _development_gate_module()
    catalog = gate._load(gate.CATALOG_PATH)
    catalog["slots"][0]["implementation"]["builder_sha256"] = "F" * 64
    _patch_gate_documents(monkeypatch, gate, {gate.CATALOG_PATH: catalog})

    with pytest.raises(ValueError, match="catalog and execution builder pins disagree"):
        gate.validate_plan()


def test_development_plan_rejects_candidate_and_control_path_drift(monkeypatch) -> None:
    gate = _development_gate_module()
    catalog = gate._load(gate.CATALOG_PATH)
    kag03, kag04 = catalog["slots"]
    kag03["implementation"]["candidate_path"] = kag04["implementation"]["candidate_path"]
    kag03["implementation"]["control_path"] = (
        "research/campaign_3000/06_candidates/snapshots/ray_c45_exact.py"
    )
    _patch_gate_documents(monkeypatch, gate, {gate.CATALOG_PATH: catalog})

    with pytest.raises(ValueError) as exc_info:
        gate.validate_plan()
    message = str(exc_info.value)
    assert "catalog and execution candidate pins disagree" in message
    assert "catalog control path is not the frozen Tetsu control" in message


def test_development_plan_rejects_metrics_integrity_contract_drift(monkeypatch) -> None:
    gate = _development_gate_module()
    plan = gate._load(gate.PLAN_PATH)
    plan["development_gate"]["integrity"]["calls_per_game"] = 718
    _patch_gate_documents(monkeypatch, gate, {gate.PLAN_PATH: plan})

    with pytest.raises(ValueError, match="development integrity gate changed"):
        gate.validate_plan()


def test_development_plan_rejects_runtime_dependency_manifest_drift(monkeypatch) -> None:
    gate = _development_gate_module()
    plan = gate._load(gate.PLAN_PATH)
    plan["engine"]["runtime_dependency_manifest"]["core"]["bytes"] += 1
    _patch_gate_documents(monkeypatch, gate, {gate.PLAN_PATH: plan})

    with pytest.raises(ValueError, match="runtime dependency manifest changed"):
        gate.validate_plan()


def test_development_plan_rejects_execution_input_path_drift(monkeypatch) -> None:
    gate = _development_gate_module()
    plan = gate._load(gate.PLAN_PATH)
    plan["runner"]["execution_input_paths"].pop()
    _patch_gate_documents(monkeypatch, gate, {gate.PLAN_PATH: plan})

    with pytest.raises(ValueError, match="runner execution input paths are not exact"):
        gate.validate_plan()


def test_development_gate_requires_a_strict_direct_tetsu_win_without_opening_seeds() -> None:
    gate = _development_gate_module()
    result = gate.gate_report("Kag_03", _report_for_exact_grid("Kag_03", beat_tetsu=True))

    assert result["integrity"] == "PASS"
    assert result["summary"]["raw_games"] == 160
    assert result["summary"]["candidate_metrics_games"] == 160
    assert result["summary"]["candidate_metrics_total"] == {
        "calls": 115040,
        "preemptions": 160,
        "horizon4_preemptions": 160,
    }
    assert result["checks"]["direct_tetsu_match_score_strictly_above_half"] is True
    assert result["checks"]["direct_tetsu_mean_margin_strictly_positive"] is True
    assert result["verdict"] == "DEVELOPMENT_PASS_NON_PROMOTION_NO_3000_GUARANTEE"


def test_development_gate_rejects_direct_tetsu_noninferiority() -> None:
    gate = _development_gate_module()
    result = gate.gate_report("Kag_03", _report_for_exact_grid("Kag_03"))

    assert result["integrity"] == "PASS"
    assert result["checks"]["direct_tetsu_match_score_strictly_above_half"] is False
    assert result["checks"]["direct_tetsu_mean_margin_strictly_positive"] is False
    assert result["verdict"] == "DEVELOPMENT_NO_GO"


def test_development_gate_blocks_a_catastrophic_opponent_lane() -> None:
    gate = _development_gate_module()
    report = _report_for_exact_grid("Kag_03")
    opponent = report["games"][0]["opponent"]
    for row in report["games"]:
        if row["opponent"] == opponent:
            row["candidate_money"] = 0.0
            row["opponent_money"] = 20000.0

    result = gate.gate_report("Kag_03", report)

    assert result["integrity"] == "PASS"
    assert result["checks"]["no_catastrophic_opponent_lane"] is False
    assert result["verdict"] == "DEVELOPMENT_NO_GO"


def test_development_gate_rejects_a_hidden_abnormal_status() -> None:
    gate = _development_gate_module()
    report = _report_for_exact_grid("Kag_04")
    report["games"][0]["hidden_abnormal_status"] = {"step": 1, "status": "ERROR"}

    result = gate.gate_report("Kag_04", report)

    assert result["integrity"] == "INVALID"
    assert result["verdict"] == "INVALID"


def test_development_gate_rejects_missing_runtime_snapshot() -> None:
    gate = _development_gate_module()
    report = _report_for_exact_grid("Kag_03", beat_tetsu=True)
    del report["runtime_environment_at_end"]

    result = gate.gate_report("Kag_03", report)

    assert result["integrity"] == "INVALID"
    assert any("runtime environment start/end snapshots are missing" in error for error in result["errors"])


def test_development_gate_rejects_self_consistent_runtime_tampering() -> None:
    gate = _development_gate_module()
    report = _report_for_exact_grid("Kag_04", beat_tetsu=True)
    for phase in ("start", "end"):
        field = f"runtime_environment_at_{phase}"
        report[field]["runtime_dependency_files"]["core"]["sha256"] = "F" * 64
        report[f"{field}_sha256"] = gate._canonical_json_sha256(report[field])

    result = gate.gate_report("Kag_04", report)

    assert result["integrity"] == "INVALID"
    assert any("does not match the frozen plan and host" in error for error in result["errors"])


def test_development_gate_rejects_self_consistent_execution_input_tampering() -> None:
    gate = _development_gate_module()
    report = _report_for_exact_grid("Kag_03", beat_tetsu=True)
    for phase in ("start", "end"):
        field = f"execution_inputs_at_{phase}"
        pinned_inputs = report[field]["pinned_inputs"]
        pinned_inputs.pop(next(iter(pinned_inputs)))
        report[f"{field}_sha256"] = gate._canonical_json_sha256(report[field])

    result = gate.gate_report("Kag_03", report)

    assert result["integrity"] == "INVALID"
    assert any("do not match current frozen files" in error for error in result["errors"])


def test_development_gate_rejects_bool_laundered_execution_flags() -> None:
    gate = _development_gate_module()
    report = _report_for_exact_grid("Kag_04", beat_tetsu=True)
    report["execution_gate_valid"] = 1
    report["runtime_environment_unchanged_during_run"] = 1

    result = gate.gate_report("Kag_04", report)

    assert result["integrity"] == "INVALID"
    assert any("execution_gate_valid is not exact true" in error for error in result["errors"])
    assert any(
        "runtime_environment_unchanged_during_run is not exact true" in error
        for error in result["errors"]
    )


def test_development_gate_rejects_execution_snapshot_hash_mismatch() -> None:
    gate = _development_gate_module()
    report = _report_for_exact_grid("Kag_03", beat_tetsu=True)
    report["execution_inputs_at_start_sha256"] = "0" * 64

    result = gate.gate_report("Kag_03", report)

    assert result["integrity"] == "INVALID"
    assert any("execution input start hash mismatch" in error for error in result["errors"])


def test_development_gate_rejects_boolean_seat_type_laundering() -> None:
    gate = _development_gate_module()
    report = _report_for_exact_grid("Kag_03", beat_tetsu=True)
    report["games"][0]["seat"] = True

    result = gate.gate_report("Kag_03", report)

    assert result["integrity"] == "INVALID"
    assert any("seed and seat must be exact integers" in error for error in result["errors"])


def test_development_gate_rejects_boolean_resolved_environment_seed() -> None:
    gate = _development_gate_module()
    report = _report_for_exact_grid("Kag_04", beat_tetsu=True)
    report["games"][0]["resolved_environment_seed"] = True

    result = gate.gate_report("Kag_04", report)

    assert result["integrity"] == "INVALID"
    assert any("resolved environment seed mismatch" in error for error in result["errors"])


def test_development_gate_rejects_a_self_consistent_candidate_swap() -> None:
    gate = _development_gate_module()
    report = _report_for_exact_grid("Kag_03", beat_tetsu=True)
    swapped_hash = _load()["slots"][1]["implementation"]["candidate_source_sha256"]
    report["candidate_sha256"] = swapped_hash
    report["candidate_sha256_at_start"] = swapped_hash
    report["candidate_sha256_at_end"] = swapped_hash

    result = gate.gate_report("Kag_03", report)

    assert result["integrity"] == "INVALID"
    assert any("frozen slot hash" in error for error in result["errors"])


def test_development_gate_rejects_a_self_consistent_opponent_swap() -> None:
    gate = _development_gate_module()
    report = _report_for_exact_grid("Kag_04", beat_tetsu=True)
    plan = gate._load(gate.PLAN_PATH)
    tetsu_path = gate._opponent_path_for_alias(plan, "tetsu_v16")
    report["opponent_sha256_at_start"][tetsu_path] = "F" * 64
    report["opponent_sha256_at_end"][tetsu_path] = "F" * 64

    result = gate.gate_report("Kag_04", report)

    assert result["integrity"] == "INVALID"
    assert any("frozen hash" in error for error in result["errors"])


def test_development_gate_rejects_a_self_consistent_alias_based_report() -> None:
    gate = _development_gate_module()
    report = _report_for_exact_grid("Kag_03", beat_tetsu=True)
    plan = gate._load(gate.PLAN_PATH)
    path_to_alias = {
        item["path"]: item["alias"] for item in plan["runner"]["opponents"]
    }
    report["opponents"] = [path_to_alias[path] for path in report["opponents"]]
    report["opponent_sha256_at_start"] = {
        path_to_alias[path]: digest
        for path, digest in report["opponent_sha256_at_start"].items()
    }
    report["opponent_sha256_at_end"] = {
        path_to_alias[path]: digest
        for path, digest in report["opponent_sha256_at_end"].items()
    }
    for row in report["games"]:
        row["opponent"] = path_to_alias[row["opponent"]]

    result = gate.gate_report("Kag_03", report)

    assert result["integrity"] == "INVALID"
    assert any("opponent paths" in error for error in result["errors"])
    assert any("exact development grid" in error for error in result["errors"])


def test_development_gate_rejects_environment_mapping_type_laundering() -> None:
    gate = _development_gate_module()
    report = _report_for_exact_grid("Kag_03", beat_tetsu=True)
    report["games"][0]["environment_configuration"]["episodeSteps"] = True
    report["games"][0]["environment_configuration_sha256"] = gate._canonical_json_sha256(
        report["games"][0]["environment_configuration"]
    )

    result = gate.gate_report("Kag_03", report)

    assert result["integrity"] == "INVALID"
    assert any("environment configuration" in error for error in result["errors"])


def test_development_gate_rejects_missing_candidate_metrics() -> None:
    gate = _development_gate_module()
    report = _report_for_exact_grid("Kag_03", beat_tetsu=True)
    del report["games"][0]["candidate_metrics"]

    result = gate.gate_report("Kag_03", report)

    assert result["integrity"] == "INVALID"
    assert any("candidate metrics are missing" in error for error in result["errors"])


def test_development_gate_rejects_nonexact_candidate_metric_keys() -> None:
    gate = _development_gate_module()
    report = _report_for_exact_grid("Kag_03", beat_tetsu=True)
    report["games"][0]["candidate_metrics"]["unexpected"] = 0

    result = gate.gate_report("Kag_03", report)

    assert result["integrity"] == "INVALID"
    assert any("metric keys are not exact" in error for error in result["errors"])


def test_development_gate_rejects_wrong_candidate_call_count() -> None:
    gate = _development_gate_module()
    report = _report_for_exact_grid("Kag_04", beat_tetsu=True)
    report["games"][0]["candidate_metrics"]["calls"] = 718

    result = gate.gate_report("Kag_04", report)

    assert result["integrity"] == "INVALID"
    assert any("calls are not exactly 719" in error for error in result["errors"])


def test_development_gate_rejects_boolean_candidate_metrics() -> None:
    gate = _development_gate_module()
    report = _report_for_exact_grid("Kag_03", beat_tetsu=True)
    report["games"][0]["candidate_metrics"]["preemptions"] = True

    result = gate.gate_report("Kag_03", report)

    assert result["integrity"] == "INVALID"
    assert any("nonnegative integers" in error for error in result["errors"])


def test_development_gate_rejects_negative_candidate_metrics() -> None:
    gate = _development_gate_module()
    report = _report_for_exact_grid("Kag_04", beat_tetsu=True)
    report["games"][0]["candidate_metrics"]["horizon4_preemptions"] = -1

    result = gate.gate_report("Kag_04", report)

    assert result["integrity"] == "INVALID"
    assert any("nonnegative integers" in error for error in result["errors"])


def test_development_gate_rejects_candidate_metric_total_mismatch() -> None:
    gate = _development_gate_module()
    report = _report_for_exact_grid("Kag_04", beat_tetsu=True)
    report["summary"]["candidate_metrics_total"]["preemptions"] += 1

    result = gate.gate_report("Kag_04", report)

    assert result["integrity"] == "INVALID"
    assert any("does not match game rows" in error for error in result["errors"])


def test_development_gate_rejects_zero_causal_effect() -> None:
    gate = _development_gate_module()
    report = _report_for_exact_grid("Kag_03", beat_tetsu=True)
    for row in report["games"]:
        row["candidate_metrics"]["preemptions"] = 0
        row["candidate_metrics"]["horizon4_preemptions"] = 0
    report["summary"]["candidate_metrics_total"]["preemptions"] = 0
    report["summary"]["candidate_metrics_total"]["horizon4_preemptions"] = 0

    result = gate.gate_report("Kag_03", report)

    assert result["integrity"] == "INVALID"
    assert any("zero preemptions" in error for error in result["errors"])
    assert any("zero horizon4 preemptions" in error for error in result["errors"])


def test_kag03_and_kag04_are_isolated_hypotheses() -> None:
    kag03, kag04 = _load()["slots"]
    assert kag03["slot"] == "Kag_03"
    assert kag04["slot"] == "Kag_04"
    assert kag03["status"] == "CLOSED_IMPLEMENTATION_FREEZE"
    assert kag04["status"] == "CLOSED_IMPLEMENTATION_FREEZE"
    assert kag03["allowed_delta"][0] == (
        "Replace the sole preemption horizon tuple (3,2,1) with (4,3,2,1)."
    )
    assert kag04["allowed_delta"][0] == (
        "Use horizons (4,3,2,1) only when own player index is 0; "
        "otherwise use exact control horizons (3,2,1)."
    )
    assert kag04["implementation"]["candidate_source_sha256"] != kag03["implementation"][
        "candidate_source_sha256"
    ]
    assert kag04["implementation"]["delta"] == (
        "seat 0 uses premium preemption horizons (4,3,2,1); seat 1 keeps exact control "
        "horizons (3,2,1); action-neutral metrics hooks only"
    )


def test_seed_scan_excludes_only_its_own_reservation_artifacts(monkeypatch) -> None:
    seed_reservation = _seed_reservation_module()
    expected = {
        "Kag_03_development": [],
        "Kag_03_confirmation": [],
        "Kag_03_robustness": [],
        "Kag_04_development": [],
        "Kag_04_confirmation": [],
        "Kag_04_robustness": [],
    }

    class Scanner:
        SCAN_EXCLUDES: ClassVar[set[str]] = set()

        @staticmethod
        def scan_observed_seeds(_root: Path) -> dict:
            return {"observed_seed_values": [49999, 55031, 62000]}

    monkeypatch.setattr(seed_reservation, "_load_hardened_scanner", lambda: Scanner)
    result = seed_reservation.validate()
    assert result["collisions"] == expected
    assert result["derived_exclusions"] == sorted(seed_reservation.DERIVED_EXCLUSIONS)
    assert seed_reservation.DERIVED_EXCLUSIONS == {
        "research/campaign_3000/12_next_candidates/candidate_catalog.json",
        "research/campaign_3000/12_next_candidates/seed_collision_scan.json",
        "research/campaign_3000/12_next_candidates/evaluation_plan.json",
        "research/campaign_3000/12_next_candidates/freeze_manifest.json",
        "research/campaign_3000/12_next_candidates/execution_binding.json",
    }
