"""Static guard for Kag_03/Kag_04 planning reservations."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import ClassVar

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


def _report_for_exact_grid(slot: str, *, beat_tetsu: bool = False) -> dict:
    gate = _development_gate_module()
    plan = gate._load(gate.PLAN_PATH)
    cells = gate.expected_development_cells(slot)
    slot_plan = plan["slots"][slot]
    opponent_hashes = {
        item["alias"]: item["sha256"] for item in plan["runner"]["opponents"]
    }
    tetsu_alias = "tetsu_v16"
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
    return {
        "candidate": slot_plan["candidate_path"],
        "candidate_path": str((ROOT / slot_plan["candidate_path"]).resolve()),
        "opponents": [item["alias"] for item in plan["runner"]["opponents"]],
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
        },
        "games": [
            {
                **cell,
                "candidate_money": 101.0 if beat_tetsu and cell["opponent"] == tetsu_alias else 100.0,
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


def test_development_gate_requires_a_strict_direct_tetsu_win_without_opening_seeds() -> None:
    gate = _development_gate_module()
    result = gate.gate_report("Kag_03", _report_for_exact_grid("Kag_03", beat_tetsu=True))

    assert result["integrity"] == "PASS"
    assert result["summary"]["raw_games"] == 160
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
    alias = "tetsu_v16"
    report["opponent_sha256_at_start"][alias] = "F" * 64
    report["opponent_sha256_at_end"][alias] = "F" * 64

    result = gate.gate_report("Kag_04", report)

    assert result["integrity"] == "INVALID"
    assert any("frozen hash" in error for error in result["errors"])


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


def test_kag03_and_kag04_are_isolated_hypotheses() -> None:
    kag03, kag04 = _load()["slots"]
    assert kag03["slot"] == "Kag_03"
    assert kag04["slot"] == "Kag_04"
    assert "Farmer or hands action changes." in kag03["forbidden_delta"]
    assert kag04["status"] == "CLOSED_IMPLEMENTATION_FREEZE"
    assert kag04["implementation"]["candidate_source_sha256"] != kag03["implementation"][
        "candidate_source_sha256"
    ]
    assert kag04["implementation"]["delta"] == (
        "exact Tetsu COW2/SHEEP2 -> COW1/SHEEP3"
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
    }
