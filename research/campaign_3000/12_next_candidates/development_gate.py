"""Validate the CLOSED Kag_03/Kag_04 development evaluation contract.

This module validates plans and already-produced runner reports.  It never starts
the runner, opens a seed pool, or authorizes an external action.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import re
import statistics
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CATALOG_PATH = HERE / "candidate_catalog.json"
PLAN_PATH = HERE / "evaluation_plan.json"
SCENARIOS_PATH = HERE / "development_scenarios.json"
SLOTS = ("Kag_03", "Kag_04")
SHA256_RE = re.compile(r"[0-9A-Fa-f]{64}")
CANDIDATE_METRIC_KEYS = ("calls", "preemptions", "horizon4_preemptions")
EXPECTED_CANDIDATE_CALLS_PER_GAME = 719
EXPECTED_RUNTIME_DEPENDENCY_MANIFEST = {
    "package_init": {
        "relative_path": "kaggle_environments/__init__.py",
        "bytes": 4713,
        "sha256": "05304FFE18CB783E24CB825B441047A9CBC45B201BE11E7B83507A035BC33A19",
    },
    "core": {
        "relative_path": "kaggle_environments/core.py",
        "bytes": 30284,
        "sha256": "0922C4599A1B6E0D8C3DADF06AE5297F98138D859D686F00DAEE6F36E6D45D0E",
    },
    "utils": {
        "relative_path": "kaggle_environments/utils.py",
        "bytes": 8634,
        "sha256": "537B627B11784D424147EF57EBB0369B039BF83C9F891E81F10486B1F552334B",
    },
    "agent": {
        "relative_path": "kaggle_environments/agent.py",
        "bytes": 8090,
        "sha256": "9B7682CE9921C8F34080A8BE0F7B41598CC12AC7EB14D24E4B707883F25213B6",
    },
    "kaggriculture_py": {
        "relative_path": "kaggle_environments/envs/kaggriculture/kaggriculture.py",
        "bytes": 39801,
        "sha256": "FB9215C5E21A25243E2D13E75B3D70A79CF7D78FFF150A90F1BB5EACF9BA2BCF",
    },
    "kaggriculture_json": {
        "relative_path": "kaggle_environments/envs/kaggriculture/kaggriculture.json",
        "bytes": 5877,
        "sha256": "7F196F4AAF9B4E482FBD61BA4BF19F5CEC4DA0F81938ECE756954035A65C0BB5",
    },
}
EXPECTED_RUNTIME_MAKE_CALLABLE_CONTRACT = {
    "package_make_is_core_make": True,
    "function_type": True,
    "globals_is_core_module": True,
    "module": "kaggle_environments.core",
    "qualname": "make",
    "source_path_matches_core": True,
    "compiled_make_count": 1,
    "ast_make_count": 1,
    "ast_function_sha256": "7A9BCC66212C822AF494904756ECC915F6EC5DEEAF316EDB417648787E09E340",
    "function_source_sha256": "3090CF7871CCF6C046138987B22B47956DE1B3C2B7CFF9FC3D5ED617AFEDFEB7",
    "code_equals_compiled_source": True,
    "startup_environment": {
        "PYTHONPATH": None,
        "PYTHONHOME": None,
        "PYTHONSTARTUP": None,
        "PYTHONINSPECT": None,
        "PYTHONUSERBASE": None,
    },
    "defaults_sha256": "310DDDF0453ADA7D5A566EF2CDC450C58912C9FC466C552322FA9A0D27D0371C",
}
EXPECTED_EXECUTION_INPUT_PATHS = [
    "research/campaign_3000/12_next_candidates/candidate_catalog.json",
    "research/campaign_3000/12_next_candidates/evaluation_plan.json",
    "research/campaign_3000/12_next_candidates/development_gate.py",
    "research/campaign_3000/12_next_candidates/development_scenarios.json",
    "research/campaign_3000/12_next_candidates/freeze_manifest.json",
    "research/campaign_3000/12_next_candidates/execution_binding.json",
]
RUNTIME_IMPORTED_DEPENDENCY_LABELS = (
    "package_init",
    "core",
    "utils",
    "agent",
    "kaggriculture_py",
)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    return value


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _slot(catalog: Mapping[str, Any], slot: str) -> Mapping[str, Any]:
    matches = [item for item in catalog["slots"] if item.get("slot") == slot]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one catalog slot: {slot}")
    return matches[0]


def _development_pool(catalog: Mapping[str, Any], slot: str) -> Mapping[str, Any]:
    pool = _slot(catalog, slot)["seed_pools"]["development"]
    if not isinstance(pool, Mapping):
        raise TypeError(f"development pool must be an object: {slot}")
    return pool


def _opponent_paths(plan: Mapping[str, Any]) -> list[str]:
    opponents = plan["runner"]["opponents"]
    if not isinstance(opponents, list):
        raise TypeError("runner.opponents must be a list")
    paths = [item["path"] for item in opponents]
    if not all(isinstance(path, str) and path for path in paths):
        raise TypeError("runner opponent paths must be non-empty strings")
    return paths


def _opponent_path_for_alias(plan: Mapping[str, Any], alias: str) -> str:
    matches = [
        item["path"]
        for item in plan["runner"]["opponents"]
        if item.get("alias") == alias
    ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one opponent path for alias: {alias}")
    return matches[0]


def _canonical_json_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def _canonical_json_equals(actual: object, expected: object) -> bool:
    try:
        return _canonical_json_sha256(actual) == _canonical_json_sha256(expected)
    except (TypeError, ValueError):
        return False


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _current_file_snapshot(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    try:
        payload = resolved.read_bytes()
    except OSError as exc:
        return {
            "path": resolved.as_posix(),
            "exists": False,
            "bytes": None,
            "sha256": None,
            "read_error": f"{type(exc).__name__}: {exc}",
        }
    return {
        "path": resolved.as_posix(),
        "exists": True,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest().upper(),
        "read_error": None,
    }


def _expected_runtime_environment_snapshot(
    engine: Mapping[str, Any],
) -> dict[str, Any]:
    distribution = importlib.metadata.distribution("kaggle-environments")
    distribution_root = Path(distribution.locate_file("")).resolve()
    if distribution.version != engine.get("version"):
        raise ValueError("installed kaggle-environments version does not match the plan")
    manifest = engine.get("runtime_dependency_manifest")
    if not isinstance(manifest, Mapping):
        raise TypeError("runtime dependency manifest is missing")
    dependency_files: dict[str, dict[str, Any]] = {}
    for label, pin in manifest.items():
        if not isinstance(pin, Mapping):
            raise TypeError(f"runtime dependency pin is malformed: {label}")
        record = _current_file_snapshot(distribution_root / str(pin.get("relative_path")))
        if (
            record["exists"] is not True
            or record["read_error"] is not None
            or record["bytes"] != pin.get("bytes")
            or record["sha256"] != pin.get("sha256")
        ):
            raise ValueError(f"installed runtime dependency does not match plan: {label}")
        dependency_files[label] = record
    imported_module_paths = {
        label: {"path": dependency_files[label]["path"], "error": None}
        for label in RUNTIME_IMPORTED_DEPENDENCY_LABELS
    }
    return {
        "schema_version": 1,
        "distribution_name": "kaggle-environments",
        "distribution_version": distribution.version,
        "distribution_root": distribution_root.as_posix(),
        "distribution_error": None,
        "python_executable": Path(sys.executable).resolve().as_posix(),
        "imported_module_paths": imported_module_paths,
        "runtime_dependency_files": dependency_files,
        "make_callable_contract": engine.get("runtime_make_callable_contract"),
        "make_callable_contract_matches_expected": True,
        "make_callable_error": None,
    }


def _expected_execution_inputs_snapshot(plan: Mapping[str, Any]) -> dict[str, Any]:
    runner = plan["runner"]
    paths = [ROOT / path for path in runner["execution_input_paths"]]
    return {
        "schema_version": 1,
        "runner": _current_file_snapshot(ROOT / runner["source"]["path"]),
        "pinned_inputs": {
            path.resolve().as_posix(): _current_file_snapshot(path)
            for path in sorted(paths, key=lambda item: item.resolve().as_posix())
        },
    }


def _valid_file_pin(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    path_value = value.get("path")
    expected_hash = value.get("sha256")
    expected_bytes = value.get("bytes")
    if (
        not isinstance(path_value, str)
        or not SHA256_RE.fullmatch(str(expected_hash))
        or not _is_int(expected_bytes)
    ):
        return False
    path = ROOT / path_value
    return (
        path.is_file()
        and path.stat().st_size == expected_bytes
        and _file_sha256(path) == str(expected_hash).upper()
    )


def expected_development_cells(
    slot: str,
    catalog: Mapping[str, Any] | None = None,
    plan: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return the one default-scenario, five-opponent, both-seat development grid."""
    if slot not in SLOTS:
        raise ValueError(f"unknown slot: {slot}")
    catalog = catalog or _load(CATALOG_PATH)
    plan = plan or _load(PLAN_PATH)
    pool = _development_pool(catalog, slot)
    return [
        {"scenario": "default", "opponent": opponent, "seed": seed, "seat": seat}
        for opponent in _opponent_paths(plan)
        for seed in range(pool["start"], pool["end_inclusive"] + 1)
        for seat in plan["runner"]["seats"]
    ]


def _expected_runner_cli(slot: str, catalog: Mapping[str, Any], plan: Mapping[str, Any]) -> str:
    pool = _development_pool(catalog, slot)
    candidate = plan["slots"][slot]["candidate_path"]
    opponents = ",".join(_opponent_paths(plan))
    seeds = ",".join(str(seed) for seed in range(pool["start"], pool["end_inclusive"] + 1))
    raw_report = plan["slots"][slot]["raw_report"]
    scenario_config = plan["runner"]["scenario_config"]
    input_pin_cli = " ".join(
        f"--input-pin {path}"
        for path in plan["runner"]["execution_input_paths"]
        if path != scenario_config
    )
    return (
        ".\\.venv\\Scripts\\python.exe -m kaggriculture_lab.evaluation.runner "
        f"--agent {candidate} --opponents {opponents} --seeds {seeds} "
        f"--scenario-config {scenario_config} {input_pin_cli} "
        f"--output {raw_report} --workers 8"
    )


def _expected_gate_cli(slot: str, plan: Mapping[str, Any]) -> str:
    slot_plan = plan["slots"][slot]
    return (
        ".\\.venv\\Scripts\\python.exe "
        "research/campaign_3000/12_next_candidates/development_gate.py "
        f"gate --slot {slot} --report {slot_plan['raw_report']} "
        f"--output {slot_plan['gate_report']}"
    )


def validate_plan() -> dict[str, Any]:
    """Validate the CLOSED development-only plan without running any game."""
    catalog = _load(CATALOG_PATH)
    plan = _load(PLAN_PATH)
    scenarios = _load(SCENARIOS_PATH)
    errors: list[str] = []

    if catalog.get("status") != "CLOSED_PLANNING_NO_SEED_AUTHORITY":
        errors.append("catalog is not CLOSED")
    if plan.get("status") != "CLOSED_DEVELOPMENT_ONLY":
        errors.append("evaluation plan is not CLOSED development-only")
    if plan.get("catalog") != CATALOG_PATH.relative_to(ROOT).as_posix():
        errors.append("evaluation plan catalog path mismatch")
    expected_engine = {
        "package": "kaggle-environments",
        "version": "1.32.6",
        "environment": "kaggriculture",
        "episode_steps": 720,
        "kaggriculture_py_sha256": (
            "FB9215C5E21A25243E2D13E75B3D70A79CF7D78FFF150A90F1BB5EACF9BA2BCF"
        ),
    }
    engine = plan.get("engine")
    if not isinstance(engine, Mapping):
        errors.append("engine contract is missing")
    else:
        if any(engine.get(key) != value for key, value in expected_engine.items()):
            errors.append("engine identity contract changed")
        environment_configuration = engine.get("environment_configuration")
        if not isinstance(environment_configuration, Mapping):
            errors.append("engine environment configuration is missing")
        elif (
            _canonical_json_sha256(environment_configuration)
            != engine.get("environment_configuration_sha256")
        ):
            errors.append("engine environment configuration hash mismatch")
        if not _canonical_json_equals(
            engine.get("runtime_dependency_manifest"),
            EXPECTED_RUNTIME_DEPENDENCY_MANIFEST,
        ):
            errors.append("engine runtime dependency manifest changed")
        if not _canonical_json_equals(
            engine.get("runtime_make_callable_contract"),
            EXPECTED_RUNTIME_MAKE_CALLABLE_CONTRACT,
        ):
            errors.append("engine runtime make callable contract changed")
        try:
            _expected_runtime_environment_snapshot(engine)
        except (
            KeyError,
            OSError,
            TypeError,
            ValueError,
            importlib.metadata.PackageNotFoundError,
        ) as exc:
            errors.append(f"installed runtime environment does not match the plan: {exc}")
    if scenarios != {
        "schema_version": 1,
        "status": "CLOSED_DEFAULT_ONLY",
        "authority": "SCENARIO_DEFINITION_ONLY_NO_SEED_AUTHORITY",
        "scenarios": {"default": {}},
    }:
        errors.append("development scenarios must remain exact default-only")

    runner = plan.get("runner")
    if not isinstance(runner, Mapping):
        errors.append("runner plan is missing")
    else:
        if not _valid_file_pin(runner.get("source")):
            errors.append("runner source pin does not match current bytes")
        aliases = [item.get("alias") for item in runner.get("opponents", [])]
        if aliases != ["tetsu_v16", "ray_c45_exact", "boatlee_v14", "kaito_v22", "fa04_g1"]:
            errors.append("development opponent aliases are not exact")
        if runner.get("seats") != [0, 1]:
            errors.append("development seats must be exactly both seats")
        if runner.get("scenario_names") != ["default"]:
            errors.append("development scenario must be default only")
        if runner.get("execution_input_paths") != EXPECTED_EXECUTION_INPUT_PATHS:
            errors.append("runner execution input paths are not exact")
        elif any(not (ROOT / path).is_file() for path in EXPECTED_EXECUTION_INPUT_PATHS):
            errors.append("runner execution input path is missing")
        if runner.get("workers") != 8:
            errors.append("development worker count must remain pinned")
        for opponent in runner.get("opponents", []):
            if not _valid_file_pin(opponent):
                errors.append("development opponent source pin does not match current bytes")
                break

    slot_plans = plan.get("slots")
    if not isinstance(slot_plans, Mapping) or set(slot_plans) != set(SLOTS):
        errors.append("development execution slots must be exactly Kag_03 and Kag_04")
        slot_plans = {}

    tetsu_paths = [
        item.get("path")
        for item in runner.get("opponents", [])
        if isinstance(item, Mapping) and item.get("alias") == "tetsu_v16"
    ] if isinstance(runner, Mapping) else []
    expected_control_path = tetsu_paths[0] if len(tetsu_paths) == 1 else None

    pools: list[set[int]] = []
    for slot in SLOTS:
        candidate = _slot(catalog, slot)
        slot_plan = slot_plans.get(slot)
        if not isinstance(slot_plan, Mapping):
            errors.append(f"execution plan is missing: {slot}")
            continue
        if candidate.get("development_opponents") != [
            "tetsu_v16",
            "ray_c45_exact",
            "boatlee_v14",
            "kaito_v22",
            "fa04_g1",
        ]:
            errors.append(f"catalog opponents mismatch: {slot}")
        if candidate.get("status") != "CLOSED_IMPLEMENTATION_FREEZE":
            errors.append(f"candidate is not an implementation-freeze input: {slot}")
        implementation = candidate.get("implementation")
        candidate_pin = {
            "path": slot_plan.get("candidate_path"),
            "sha256": slot_plan.get("candidate_source_sha256"),
            "bytes": slot_plan.get("candidate_source_bytes"),
        }
        builder_pin = {
            "path": slot_plan.get("builder_path"),
            "sha256": slot_plan.get("builder_sha256"),
            "bytes": slot_plan.get("builder_bytes"),
        }
        if not _valid_file_pin(candidate_pin):
            errors.append(f"candidate source pin does not match current bytes: {slot}")
        if not _valid_file_pin(builder_pin):
            errors.append(f"builder source pin does not match current bytes: {slot}")
        if not isinstance(implementation, Mapping):
            errors.append(f"catalog and execution candidate pins disagree: {slot}")
        else:
            if (
                implementation.get("candidate_path") != slot_plan.get("candidate_path")
                or implementation.get("candidate_source_sha256")
                != slot_plan.get("candidate_source_sha256")
                or implementation.get("candidate_source_bytes")
                != slot_plan.get("candidate_source_bytes")
                or slot_plan.get("candidate_status") != "CLOSED_IMPLEMENTATION_FREEZE"
            ):
                errors.append(f"catalog and execution candidate pins disagree: {slot}")
            if (
                implementation.get("builder_path") != slot_plan.get("builder_path")
                or implementation.get("builder_sha256") != slot_plan.get("builder_sha256")
                or implementation.get("builder_bytes") != slot_plan.get("builder_bytes")
            ):
                errors.append(f"catalog and execution builder pins disagree: {slot}")
            if implementation.get("control_path") != expected_control_path:
                errors.append(f"catalog control path is not the frozen Tetsu control: {slot}")
        for phase, pool in candidate["seed_pools"].items():
            if not isinstance(pool, Mapping):
                errors.append(f"pool is not an object: {slot}/{phase}")
                continue
            start, end, count = pool.get("start"), pool.get("end_inclusive"), pool.get("count")
            if not (_is_int(start) and _is_int(end) and _is_int(count)) or count != end - start + 1:
                errors.append(f"invalid inclusive pool bounds: {slot}/{phase}")
                continue
            if (
                pool.get("status") != "CLOSED"
                or pool.get("opened") is not False
                or pool.get("consumed") is not False
                or pool.get("evaluated_games") != 0
            ):
                errors.append(f"pool is not pristine CLOSED: {slot}/{phase}")
            values = set(range(start, end + 1))
            if any(values.intersection(previous) for previous in pools):
                errors.append(f"pool overlaps a prior reservation: {slot}/{phase}")
            pools.append(values)
        development = _development_pool(catalog, slot)
        if len(expected_development_cells(slot, catalog, plan)) != development.get("expected_cells"):
            errors.append(f"development cell count mismatch: {slot}")
        raw_report = slot_plan.get("raw_report")
        if not isinstance(raw_report, str) or not raw_report.endswith("development_raw_report.json"):
            errors.append(f"raw report path mismatch: {slot}")
        elif slot_plan.get("runner_started_receipt") != raw_report.replace(
            ".json", ".started.json"
        ):
            errors.append(f"runner started receipt path mismatch: {slot}")
        if slot_plan.get("runner_cli") != _expected_runner_cli(slot, catalog, plan):
            errors.append(f"runner CLI mismatch: {slot}")
        if slot_plan.get("gate_cli") != _expected_gate_cli(slot, plan):
            errors.append(f"gate CLI mismatch: {slot}")

    gate = plan.get("development_gate")
    if not isinstance(gate, Mapping):
        errors.append("development gate is missing")
    else:
        expected_integrity = {
            "exact_complete_grid": True,
            "both_seats_required": True,
            "finite_money_and_runtime": True,
            "failures": 0,
            "hidden_abnormal_status_failures": 0,
            "candidate_and_opponent_source_start_equals_end": True,
            "actual_runtime_environment_start_equals_end_and_matches_plan": True,
            "execution_inputs_start_equals_end_and_match_frozen_files": True,
            "execution_gate_valid": True,
            "resolved_environment_seed_matches_requested": True,
            "default_scenario_only": True,
            "candidate_metrics_required": True,
            "candidate_metrics_exact_keys": list(CANDIDATE_METRIC_KEYS),
            "calls_per_game": EXPECTED_CANDIDATE_CALLS_PER_GAME,
            "minimum_total_preemptions_exclusive": 0,
            "minimum_total_horizon4_preemptions_exclusive": 0,
        }
        if not _canonical_json_equals(gate.get("integrity"), expected_integrity):
            errors.append("development integrity gate changed")
        performance = gate.get("performance")
        direct_tetsu = (
            performance.get("direct_tetsu_v16_control")
            if isinstance(performance, Mapping)
            else None
        )
        catastrophic = (
            performance.get("per_opponent_catastrophic_regression")
            if isinstance(performance, Mapping)
            else None
        )
        if (
            not isinstance(performance, Mapping)
            or not isinstance(direct_tetsu, Mapping)
            or not isinstance(catastrophic, Mapping)
        ):
            errors.append("development performance gate is malformed")
        elif (
            performance.get("minimum_overall_match_score") != 0.5
            or performance.get("minimum_overall_mean_margin") != 0.0
            or direct_tetsu.get("minimum_match_score_exclusive") != 0.5
            or direct_tetsu.get("minimum_mean_margin_exclusive") != 0.0
            or catastrophic.get("minimum_match_score") != 0.25
            or catastrophic.get("minimum_mean_margin") != -10000.0
        ):
            errors.append("development gate thresholds changed")

    future = plan.get("future_phases")
    if not isinstance(future, Mapping) or set(future) != {"confirmation", "robustness"}:
        errors.append("future phases must be explicit CLOSED placeholders")
    if errors:
        raise ValueError("; ".join(errors))
    return {
        "status": "VALID_CLOSED_DEVELOPMENT_PLAN",
        "slots": list(SLOTS),
        "development_cells": {
            slot: len(expected_development_cells(slot, catalog, plan)) for slot in SLOTS
        },
        "future_phases": "CLOSED_NO_EVALUATION_FRAMEWORK",
    }


def _cell_key(row: Mapping[str, Any]) -> tuple[str, str, int, int]:
    scenario = row.get("scenario")
    opponent = row.get("opponent")
    seed = row.get("seed")
    seat = row.get("seat")
    if not isinstance(scenario, str) or not isinstance(opponent, str):
        raise TypeError("row scenario and opponent must be strings")
    if not _is_int(seed) or not _is_int(seat) or seat not in (0, 1):
        raise TypeError("row seed and seat must be exact integers")
    return scenario, opponent, seed, seat


def _sha256(value: object) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _runtime_make_contract_is_valid(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    if any(
        value.get(key) is not True
        for key in (
            "package_make_is_core_make",
            "function_type",
            "globals_is_core_module",
            "source_path_matches_core",
            "code_equals_compiled_source",
        )
    ):
        return False
    if (
        value.get("module") != "kaggle_environments.core"
        or value.get("qualname") != "make"
        or value.get("compiled_make_count") != 1
        or value.get("ast_make_count") != 1
    ):
        return False
    if any(
        not _sha256(value.get(key))
        for key in (
            "ast_function_sha256",
            "function_source_sha256",
            "defaults_sha256",
        )
    ):
        return False
    return value.get("startup_environment") == {
        "PYTHONPATH": None,
        "PYTHONHOME": None,
        "PYTHONSTARTUP": None,
        "PYTHONINSPECT": None,
        "PYTHONUSERBASE": None,
    }


def _resolved_path(value: object) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    return (path if path.is_absolute() else ROOT / path).resolve()


def _source_integrity(
    report: Mapping[str, Any], slot: str, plan: Mapping[str, Any]
) -> list[str]:
    errors: list[str] = []
    if report.get("sources_unchanged_during_run") is not True:
        errors.append("sources_unchanged_during_run is not true")
    slot_plan = plan["slots"][slot]
    expected_candidate_path = slot_plan["candidate_path"]
    expected_candidate_hash = slot_plan["candidate_source_sha256"]
    if report.get("candidate") != expected_candidate_path:
        errors.append("report candidate path does not match the frozen slot")
    if _resolved_path(report.get("candidate_path")) != (ROOT / expected_candidate_path).resolve():
        errors.append("resolved report candidate path does not match the frozen slot")
    candidate_hashes = [
        report.get("candidate_sha256"),
        report.get("candidate_sha256_at_start"),
        report.get("candidate_sha256_at_end"),
    ]
    if (
        not all(_sha256(value) for value in candidate_hashes)
        or {str(value).upper() for value in candidate_hashes} != {expected_candidate_hash}
    ):
        errors.append("candidate source hash is missing, changed, or not the frozen slot hash")
    opponents = plan["runner"]["opponents"]
    expected_paths = [item["path"] for item in opponents]
    expected_hashes = {item["path"]: item["sha256"] for item in opponents}
    if report.get("opponents") != expected_paths:
        errors.append("report opponent paths do not match the frozen panel")
    start = report.get("opponent_sha256_at_start")
    end = report.get("opponent_sha256_at_end")
    if not isinstance(start, Mapping) or not isinstance(end, Mapping):
        return [*errors, "opponent hash receipts are missing"]
    if set(start) != set(expected_paths) or set(end) != set(expected_paths):
        errors.append("opponent hash receipt keys do not match the fixed panel")
    elif any(
        not _sha256(start[path])
        or str(start[path]).upper() != expected_hashes[path]
        or str(end[path]).upper() != expected_hashes[path]
        for path in expected_paths
    ):
        errors.append("opponent source hash is malformed, changed, or not the frozen hash")
    return errors


def _execution_context_integrity(
    report: Mapping[str, Any], plan: Mapping[str, Any]
) -> list[str]:
    errors: list[str] = []
    schema_version = report.get("execution_context_schema_version")
    if not _is_int(schema_version) or schema_version != 1:
        errors.append("execution context schema version is not exact")
    for name in (
        "runtime_environment_unchanged_during_run",
        "execution_inputs_unchanged_during_run",
        "execution_context_unchanged_during_run",
        "execution_gate_valid",
    ):
        if report.get(name) is not True:
            errors.append(f"{name} is not exact true")

    runtime_start = report.get("runtime_environment_at_start")
    runtime_end = report.get("runtime_environment_at_end")
    if not isinstance(runtime_start, Mapping) or not isinstance(runtime_end, Mapping):
        errors.append("runtime environment start/end snapshots are missing")
    else:
        try:
            if report.get("runtime_environment_at_start_sha256") != _canonical_json_sha256(
                runtime_start
            ):
                errors.append("runtime environment start hash mismatch")
            if report.get("runtime_environment_at_end_sha256") != _canonical_json_sha256(
                runtime_end
            ):
                errors.append("runtime environment end hash mismatch")
            if not _canonical_json_equals(runtime_start, runtime_end):
                errors.append("runtime environment changed during run")
            expected_runtime = _expected_runtime_environment_snapshot(plan["engine"])
            if not _canonical_json_equals(runtime_start, expected_runtime):
                errors.append("runtime environment does not match the frozen plan and host")
        except (
            KeyError,
            OSError,
            TypeError,
            ValueError,
            importlib.metadata.PackageNotFoundError,
        ) as exc:
            errors.append(f"runtime environment snapshot validation failed: {exc}")

    inputs_start = report.get("execution_inputs_at_start")
    inputs_end = report.get("execution_inputs_at_end")
    if not isinstance(inputs_start, Mapping) or not isinstance(inputs_end, Mapping):
        errors.append("execution input start/end snapshots are missing")
    else:
        try:
            if report.get("execution_inputs_at_start_sha256") != _canonical_json_sha256(
                inputs_start
            ):
                errors.append("execution input start hash mismatch")
            if report.get("execution_inputs_at_end_sha256") != _canonical_json_sha256(
                inputs_end
            ):
                errors.append("execution input end hash mismatch")
            if not _canonical_json_equals(inputs_start, inputs_end):
                errors.append("execution inputs changed during run")
            expected_inputs = _expected_execution_inputs_snapshot(plan)
            if not _canonical_json_equals(inputs_start, expected_inputs):
                errors.append("execution inputs do not match current frozen files")
        except (KeyError, OSError, TypeError, ValueError) as exc:
            errors.append(f"execution input snapshot validation failed: {exc}")
    return errors


def gate_report(slot: str, report: Mapping[str, Any]) -> dict[str, Any]:
    """Return an INVALID, NO_GO, or non-promotion development PASS verdict."""
    validate_plan()
    catalog = _load(CATALOG_PATH)
    plan = _load(PLAN_PATH)
    expected = {
        (row["scenario"], row["opponent"], row["seed"], row["seat"])
        for row in expected_development_cells(slot, catalog, plan)
    }
    expected_opponents = set(_opponent_paths(plan))
    errors = _source_integrity(report, slot, plan)
    errors.extend(_execution_context_integrity(report, plan))
    expected_effective_scenarios = {"default": {"episodeSteps": 720}}
    if report.get("scenario_overrides") != {"default": {}}:
        errors.append("report scenario overrides are not exact default-only")
    if report.get("effective_scenarios") != expected_effective_scenarios:
        errors.append("report does not use the exact default effective scenario")
    if report.get("effective_scenarios_sha256") != _canonical_json_sha256(
        expected_effective_scenarios
    ):
        errors.append("effective scenario hash mismatch")
    expected_seeds = list(
        range(
            _development_pool(catalog, slot)["start"],
            _development_pool(catalog, slot)["end_inclusive"] + 1,
        )
    )
    if report.get("seeds") != expected_seeds:
        errors.append("report seeds do not equal the frozen development pool")
    if report.get("seat_policy") != "both seats scored; confidence interval is clustered by seed":
        errors.append("report seat policy is not the required both-seat policy")

    rows = report.get("games")
    if not isinstance(rows, list):
        errors.append("report games must be a list")
        rows = []
    indexed: dict[tuple[str, str, int, int], Mapping[str, Any]] = {}
    for raw in rows:
        if not isinstance(raw, Mapping):
            errors.append("report contains a non-object game row")
            continue
        try:
            key = _cell_key(raw)
        except TypeError as exc:
            errors.append(str(exc))
            continue
        if key in indexed:
            errors.append(f"duplicate game cell: {key}")
            continue
        indexed[key] = raw
    if set(indexed) != expected:
        errors.append("report cells do not equal the exact development grid")

    outcomes: list[float] = []
    margins: list[float] = []
    candidate_metrics_games = 0
    candidate_metrics_total = {name: 0 for name in CANDIDATE_METRIC_KEYS}
    per_opponent: dict[str, list[tuple[float, float]]] = {
        opponent: [] for opponent in expected_opponents
    }
    for key, row in indexed.items():
        candidate_metrics = row.get("candidate_metrics")
        if not isinstance(candidate_metrics, Mapping):
            errors.append(f"candidate metrics are missing or not an object: {key}")
        elif set(candidate_metrics) != set(CANDIDATE_METRIC_KEYS):
            errors.append(f"candidate metric keys are not exact: {key}")
        elif any(
            not _is_int(candidate_metrics[name]) or candidate_metrics[name] < 0
            for name in CANDIDATE_METRIC_KEYS
        ):
            errors.append(f"candidate metric values are not exact nonnegative integers: {key}")
        elif candidate_metrics["calls"] != EXPECTED_CANDIDATE_CALLS_PER_GAME:
            errors.append(f"candidate metric calls are not exactly 719: {key}")
        else:
            candidate_metrics_games += 1
            for name in CANDIDATE_METRIC_KEYS:
                candidate_metrics_total[name] += candidate_metrics[name]
        if key[1] not in per_opponent:
            errors.append(f"unexpected opponent path: {key}")
            continue
        if (
            row.get("error") is not None
            or row.get("candidate_status") != "DONE"
            or row.get("opponent_status") != "DONE"
        ):
            errors.append(f"failed game row: {key}")
            continue
        values = (row.get("candidate_money"), row.get("opponent_money"), row.get("elapsed_seconds"))
        if not all(_is_finite_number(value) for value in values):
            errors.append(f"non-finite game value: {key}")
            continue
        if float(values[2]) < 0:
            errors.append(f"negative elapsed time: {key}")
            continue
        if "hidden_abnormal_status" not in row or row.get("hidden_abnormal_status") is not None:
            errors.append(f"hidden abnormal status: {key}")
            continue
        resolved_environment_seed = row.get("resolved_environment_seed")
        if (
            not _is_int(resolved_environment_seed)
            or resolved_environment_seed != key[2]
        ):
            errors.append(f"resolved environment seed mismatch: {key}")
            continue
        expected_effective_configuration = {"episodeSteps": 720, "seed": key[2]}
        if not _canonical_json_equals(
            row.get("effective_configuration"), expected_effective_configuration
        ):
            errors.append(f"effective configuration mismatch: {key}")
            continue
        if row.get("effective_configuration_sha256") != _canonical_json_sha256(
            expected_effective_configuration
        ):
            errors.append(f"effective configuration hash mismatch: {key}")
            continue
        expected_environment = plan["engine"]["environment_configuration"]
        if not _canonical_json_equals(row.get("environment_configuration"), expected_environment):
            errors.append(f"environment configuration mismatch: {key}")
            continue
        if row.get("environment_configuration_sha256") != plan["engine"].get(
            "environment_configuration_sha256"
        ):
            errors.append(f"environment configuration hash mismatch: {key}")
            continue
        if not _runtime_make_contract_is_valid(row.get("runtime_make_callable")):
            errors.append(f"runtime make callable contract mismatch: {key}")
            continue
        candidate_money, opponent_money = float(values[0]), float(values[1])
        outcome = 1.0 if candidate_money > opponent_money else 0.0
        if candidate_money == opponent_money:
            outcome = 0.5
        margin = candidate_money - opponent_money
        outcomes.append(outcome)
        margins.append(margin)
        per_opponent[key[1]].append((outcome, margin))

    summary = report.get("summary")
    if not isinstance(summary, Mapping):
        errors.append("report summary is missing")
    else:
        expected_count = len(expected)
        exact_counts = {
            "raw_games": expected_count,
            "valid_raw_games": expected_count,
            "failed_raw_games": 0,
            "hidden_abnormal_status_failures": 0,
        }
        for name, expected_value in exact_counts.items():
            value = summary.get(name)
            if not _is_int(value) or value != expected_value:
                errors.append(f"report summary {name} is not exact")
        if (
            not _is_int(summary.get("candidate_metrics_games"))
            or summary.get("candidate_metrics_games") != expected_count
            or summary.get("candidate_metrics_games") != candidate_metrics_games
        ):
            errors.append("report summary candidate_metrics_games is not exact")
        reported_metrics_total = summary.get("candidate_metrics_total")
        if (
            not isinstance(reported_metrics_total, Mapping)
            or set(reported_metrics_total) != set(CANDIDATE_METRIC_KEYS)
            or any(
                not _is_int(reported_metrics_total[name])
                or reported_metrics_total[name] < 0
                for name in CANDIDATE_METRIC_KEYS
            )
        ):
            errors.append("report summary candidate_metrics_total is malformed")
        elif dict(reported_metrics_total) != candidate_metrics_total:
            errors.append("report summary candidate_metrics_total does not match game rows")

    if candidate_metrics_total["preemptions"] <= 0:
        errors.append("candidate metrics show zero preemptions")
    if candidate_metrics_total["horizon4_preemptions"] <= 0:
        errors.append("candidate metrics show zero horizon4 preemptions")

    if errors:
        return {
            "slot": slot,
            "phase": "development",
            "integrity": "INVALID",
            "errors": sorted(set(errors)),
            "verdict": "INVALID",
        }

    gate = plan["development_gate"]["performance"]
    direct_tetsu = gate["direct_tetsu_v16_control"]
    catastrophic = gate["per_opponent_catastrophic_regression"]
    tetsu_path = _opponent_path_for_alias(plan, "tetsu_v16")
    summary = {
        "raw_games": len(indexed),
        "candidate_metrics_games": candidate_metrics_games,
        "candidate_metrics_total": candidate_metrics_total,
        "match_score": statistics.fmean(outcomes),
        "mean_margin": statistics.fmean(margins),
        "per_opponent": {
            opponent: {
                "raw_games": len(values),
                "match_score": statistics.fmean(value[0] for value in values),
                "mean_margin": statistics.fmean(value[1] for value in values),
            }
            for opponent, values in sorted(per_opponent.items())
        },
    }
    checks = {
        "overall_match_score": summary["match_score"] >= gate["minimum_overall_match_score"],
        "overall_mean_margin": summary["mean_margin"] >= gate["minimum_overall_mean_margin"],
        "direct_tetsu_match_score_strictly_above_half": (
            summary["per_opponent"][tetsu_path]["match_score"]
            > direct_tetsu["minimum_match_score_exclusive"]
        ),
        "direct_tetsu_mean_margin_strictly_positive": (
            summary["per_opponent"][tetsu_path]["mean_margin"]
            > direct_tetsu["minimum_mean_margin_exclusive"]
        ),
        "no_catastrophic_opponent_lane": all(
            value["match_score"] >= catastrophic["minimum_match_score"]
            and value["mean_margin"] >= catastrophic["minimum_mean_margin"]
            for value in summary["per_opponent"].values()
        ),
    }
    return {
        "slot": slot,
        "phase": "development",
        "integrity": "PASS",
        "summary": summary,
        "checks": checks,
        "verdict": (
            plan["development_gate"]["pass_verdict"]
            if all(checks.values())
            else plan["development_gate"]["nonpass_verdict"]
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate CLOSED next-candidate evaluation plans")
    parser.add_argument("command", choices=("validate-plan", "grid", "gate"))
    parser.add_argument("--slot", choices=SLOTS)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "validate-plan":
        result = validate_plan()
    elif args.command == "grid":
        if args.slot is None:
            parser.error("grid requires --slot")
        result = {"slot": args.slot, "cells": expected_development_cells(args.slot)}
    else:
        if args.slot is None or args.report is None:
            parser.error("gate requires --slot and --report")
        result = gate_report(args.slot, _load(args.report))
    payload = json.dumps(result, indent=2, allow_nan=False)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
