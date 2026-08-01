"""Strict provenance and result gate for the frozen Fa04 top-trace experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import statistics
import subprocess
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

EXPECTED_BOUNDARY_STATUS = "DEVELOPMENT_OPEN_AUTHORIZED"
EXPECTED_OPEN_POOL_STATUS = "OPEN"
EXPECTED_CLOSED_POOL_STATUS = "CLOSED"
EXPECTED_CELL_COUNT = 192
TOOLING_KEYS = (
    "generator",
    "runner",
    "paired_analyzer",
    "runtime_generator",
    "runtime_benchmark",
    "gate_evaluator",
)
BOUNDARY_RELATIVE = "configs/fa04_top_trace_guard_boundary.json"
CANONICAL_ALGORITHM = "SHA256_CANONICAL_JSON_SORTED_KEYS_COMPACT_ASCII"
BOUNDARY_CANONICAL_EXCLUDED_PATHS = (
    "open_transition_invariant",
    "implementation_commit",
    "seed_registry_sha256",
    "status",
    "pools.development.status",
    "development_opened_at_utc",
    "opening_authority",
)
REGISTRY_CANONICAL_EXCLUDED_PATHS = (
    "next_boundary_reservations.Fa04_top_trace_guard_development.status",
    "next_boundary_reservations.Fa04_top_trace_guard_development.opened",
    "next_boundary_reservations.Fa04_top_trace_guard_development.opened_at_utc",
)
OPENING_AUTHORITY = (
    "User authorization opens local development evaluation only; "
    "it does not authorize SaveRun or competition submission."
)
EXPECTED_ALLOWED_OPEN_DELTA = {
    "boundary": {
        "status": [
            "CLOSED_PENDING_CORRECTED_FREEZE_AUDIT",
            "DEVELOPMENT_OPEN_AUTHORIZED",
        ],
        "pools.development.status": ["CLOSED", "OPEN"],
    },
    "registry": {
        "next_boundary_reservations.Fa04_top_trace_guard_development.status": [
            "CLOSED",
            "OPEN",
        ],
        "next_boundary_reservations.Fa04_top_trace_guard_development.opened": [
            False,
            True,
        ],
    },
}
EXPECTED_OPEN_METADATA = {
    "boundary.development_opened_at_utc": "RFC3339_UTC",
    "boundary.opening_authority": OPENING_AUTHORITY,
    "registry.next_boundary_reservations.Fa04_top_trace_guard_development.opened_at_utc": (
        "MUST_EQUAL_BOUNDARY_DEVELOPMENT_OPENED_AT_UTC"
    ),
}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return value


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be an object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _json_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{label} must be a SHA-256 digest")
    normalized = value.upper()
    if any(character not in "0123456789ABCDEF" for character in normalized):
        raise ValueError(f"{label} must be a SHA-256 digest")
    return normalized


def _git(project_root: Path, *args: str, text: bool = True) -> str | bytes:
    completed = subprocess.run(
        ["git", "-c", f"safe.directory={project_root.resolve()}", *args],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=text,
    )
    return completed.stdout.strip() if text else completed.stdout


def _git_file_sha256(project_root: Path, head: str, relative: str) -> str:
    try:
        payload = _git(project_root, "show", f"{head}:{relative}", text=False)
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"{relative} is absent at implementation HEAD") from exc
    if not isinstance(payload, bytes):
        raise TypeError("git show did not return bytes")
    return hashlib.sha256(payload).hexdigest().upper()


def _git_json_blob(
    project_root: Path, head: str, relative: str, label: str
) -> tuple[dict[str, Any], str]:
    try:
        payload = _git(project_root, "show", f"{head}:{relative}", text=False)
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"{label} is absent at implementation commit") from exc
    if not isinstance(payload, bytes):
        raise TypeError("git show did not return bytes")
    try:
        value = json.loads(payload)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} at implementation commit is not valid JSON") from exc
    if not isinstance(value, dict):
        raise TypeError(f"{label} at implementation commit must be an object")
    return value, hashlib.sha256(payload).hexdigest().upper()


def _without_paths(value: Mapping[str, Any], paths: tuple[str, ...]) -> dict[str, Any]:
    result = json.loads(json.dumps(value, sort_keys=True))
    for path in paths:
        parts = path.split(".")
        current = result
        for part in parts[:-1]:
            if not isinstance(current, dict) or part not in current:
                break
            current = current[part]
        else:
            if isinstance(current, dict):
                current.pop(parts[-1], None)
    return result


def _canonical_projection_sha256(
    value: Mapping[str, Any], excluded_paths: tuple[str, ...]
) -> str:
    return _json_sha256(_without_paths(value, excluded_paths))


def _relative_path(project_root: Path, path: Path, label: str) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"{label} must be inside the project root") from exc


def _checked_file_entry(
    project_root: Path, entry: Mapping[str, Any], label: str
) -> dict[str, Any]:
    relative = entry.get("path")
    if not isinstance(relative, str) or not relative:
        raise ValueError(f"{label}.path must be a non-empty string")
    expected = _digest(entry.get("sha256"), f"{label}.sha256")
    path = project_root / relative
    if not path.is_file():
        raise ValueError(f"{label} file is missing: {relative}")
    actual = _sha256(path)
    if actual != expected:
        raise ValueError(f"{label} hash mismatch")
    if "bytes" in entry and entry.get("bytes") != path.stat().st_size:
        raise ValueError(f"{label} byte-size mismatch")
    return {"path": relative, "sha256": actual, "bytes": path.stat().st_size}


def _commit(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) != 40:
        raise ValueError(f"{label} must be a full commit id")
    normalized = value.lower()
    if any(character not in "0123456789abcdef" for character in normalized):
        raise ValueError(f"{label} must be a full commit id")
    return normalized


def _verify_git_freeze(
    project_root: Path,
    implementation_commit: str,
    implementation_paths: set[str],
    execution_paths: set[str],
    allowed_untracked: set[str],
) -> dict[str, str]:
    execution_head = _git(project_root, "rev-parse", "HEAD")
    if not isinstance(execution_head, str) or len(execution_head) != 40:
        raise ValueError("implementation HEAD is not a full commit id")
    status = _git(project_root, "status", "--porcelain=v1", "--untracked-files=all")
    if status:
        unexpected = []
        for line in str(status).splitlines():
            relative = line[3:].replace("\\", "/") if len(line) >= 4 else ""
            if not line.startswith("?? ") or relative not in allowed_untracked:
                unexpected.append(line)
        if unexpected:
            raise ValueError(
                "implementation tree must be clean except frozen evidence: "
                + " | ".join(unexpected)
            )
    try:
        _git(
            project_root,
            "merge-base",
            "--is-ancestor",
            implementation_commit,
            execution_head,
        )
    except subprocess.CalledProcessError as exc:
        raise ValueError("implementation commit is not an ancestor of execution HEAD") from exc
    for relative in sorted(implementation_paths):
        if _git_file_sha256(project_root, implementation_commit, relative) != _sha256(
            project_root / relative
        ):
            raise ValueError(f"source/tooling differs from implementation commit: {relative}")
    for relative in sorted(execution_paths):
        if _git_file_sha256(project_root, execution_head, relative) != _sha256(
            project_root / relative
        ):
            raise ValueError(f"execution config differs from execution HEAD: {relative}")
    return {
        "implementation_commit": implementation_commit,
        "execution_head": execution_head,
    }


def _pool_range(pool: Mapping[str, Any], label: str) -> list[int]:
    start = pool.get("start")
    end = pool.get("end_inclusive")
    count = pool.get("count")
    if (
        isinstance(start, bool)
        or not isinstance(start, int)
        or isinstance(end, bool)
        or not isinstance(end, int)
        or isinstance(count, bool)
        or not isinstance(count, int)
        or end < start
    ):
        raise ValueError(f"{label} range is invalid")
    seeds = list(range(start, end + 1))
    if len(seeds) != count:
        raise ValueError(f"{label} count does not match its range")
    return seeds


def _validate_lifecycle(
    boundary: Mapping[str, Any], registry: Mapping[str, Any]
) -> list[int]:
    if boundary.get("status") != EXPECTED_BOUNDARY_STATUS:
        raise ValueError("boundary is not in DEVELOPMENT_OPEN_AUTHORIZED state")
    pools = _mapping(boundary.get("pools"), "boundary.pools")
    registry_pools = _mapping(
        registry.get("next_boundary_reservations"),
        "seed registry.next_boundary_reservations",
    )
    development_seeds: list[int] | None = None
    for name in ("development", "confirmation", "robustness"):
        pool = _mapping(pools.get(name), f"boundary.pools.{name}")
        key = pool.get("registry_key")
        if not isinstance(key, str):
            raise TypeError(f"boundary.pools.{name}.registry_key must be a string")
        registered = _mapping(
            registry_pools.get(key),
            f"seed registry.next_boundary_reservations.{key}",
        )
        seeds = _pool_range(pool, f"boundary.pools.{name}")
        registered_seeds = _pool_range(
            registered,
            f"seed registry.next_boundary_reservations.{key}",
        )
        if seeds != registered_seeds:
            raise ValueError(f"{name} boundary/registry range mismatch")
        if name == "development":
            if pool.get("status") != EXPECTED_OPEN_POOL_STATUS:
                raise ValueError("development boundary pool is not OPEN")
            if (
                registered.get("status") != EXPECTED_OPEN_POOL_STATUS
                or registered.get("opened") is not True
                or registered.get("consumed") is not False
                or registered.get("evaluated_games") != 0
            ):
                raise ValueError("development registry lifecycle is not OPEN/unconsumed")
            development_seeds = seeds
        elif (
            pool.get("status") != EXPECTED_CLOSED_POOL_STATUS
            or registered.get("status") != EXPECTED_CLOSED_POOL_STATUS
            or registered.get("opened") is not False
            or registered.get("consumed") is not False
            or registered.get("evaluated_games") != 0
        ):
            raise ValueError(f"{name} pool must remain CLOSED and unused")
    if development_seeds is None or len(development_seeds) != 16:
        raise ValueError("development must contain exactly 16 seeds")
    return development_seeds


def _validate_open_transition_invariant(
    project_root: Path,
    boundary: Mapping[str, Any],
    registry: Mapping[str, Any],
    implementation_commit: str,
    registry_relative: str,
) -> None:
    base_boundary, _ = _git_json_blob(
        project_root,
        implementation_commit,
        BOUNDARY_RELATIVE,
        "S3 boundary",
    )
    base_registry, base_registry_blob_sha256 = _git_json_blob(
        project_root,
        implementation_commit,
        registry_relative,
        "S3 seed registry",
    )
    invariant = dict(
        _mapping(boundary.get("open_transition_invariant"), "open_transition_invariant")
    )
    base_invariant = dict(
        _mapping(
            base_boundary.get("open_transition_invariant"),
            "S3 boundary.open_transition_invariant",
        )
    )
    if invariant != base_invariant:
        raise ValueError("open transition invariant differs from S3 implementation")

    expected_canonicalization = {
        "algorithm": CANONICAL_ALGORITHM,
        "boundary_excluded_paths": list(BOUNDARY_CANONICAL_EXCLUDED_PATHS),
        "registry_excluded_paths": list(REGISTRY_CANONICAL_EXCLUDED_PATHS),
    }
    if invariant.get("schema_version") != 1:
        raise ValueError("open transition invariant schema is not version 1")
    if invariant.get("canonicalization") != expected_canonicalization:
        raise ValueError("open transition canonicalization contract is not exact")
    if invariant.get("allowed_open_delta") != EXPECTED_ALLOWED_OPEN_DELTA:
        raise ValueError("open transition allowed delta contract is not exact")
    if invariant.get("required_open_metadata") != EXPECTED_OPEN_METADATA:
        raise ValueError("open transition metadata contract is not exact")

    basis = _mapping(invariant.get("basis"), "open_transition_invariant.basis")
    if basis.get("label") != "S2_IMPLEMENTATION_E2_EXECUTION":
        raise ValueError("open transition basis label is not exact")
    basis_implementation = _commit(
        basis.get("implementation_commit"),
        "open_transition_invariant.basis.implementation_commit",
    )
    _commit(
        basis.get("closed_execution_commit"),
        "open_transition_invariant.basis.closed_execution_commit",
    )
    if _commit(
        base_boundary.get("implementation_commit"),
        "S3 boundary.implementation_commit",
    ) != basis_implementation:
        raise ValueError("S3 boundary is not bound to the S2 implementation basis")
    if base_boundary.get("status") != "CLOSED_PENDING_CORRECTED_FREEZE_AUDIT":
        raise ValueError("S3 boundary base is not CLOSED")
    base_pools = _mapping(base_boundary.get("pools"), "S3 boundary.pools")
    base_development = _mapping(
        base_pools.get("development"), "S3 boundary.pools.development"
    )
    if base_development.get("status") != EXPECTED_CLOSED_POOL_STATUS:
        raise ValueError("S3 boundary development base is not CLOSED")
    base_registry_pools = _mapping(
        base_registry.get("next_boundary_reservations"),
        "S3 seed registry.next_boundary_reservations",
    )
    base_registered = _mapping(
        base_registry_pools.get("Fa04_top_trace_guard_development"),
        "S3 seed registry Fa04 development",
    )
    if (
        base_registered.get("status") != EXPECTED_CLOSED_POOL_STATUS
        or base_registered.get("opened") is not False
        or "opened_at_utc" in base_registered
    ):
        raise ValueError("S3 seed registry development base is not CLOSED/unopened")
    if _digest(
        base_boundary.get("seed_registry_sha256"),
        "S3 boundary.seed_registry_sha256",
    ) != base_registry_blob_sha256:
        raise ValueError("S3 boundary seed registry self-hash is invalid")

    expected_boundary_hash = _digest(
        invariant.get("canonical_boundary_non_lifecycle_sha256"),
        "canonical_boundary_non_lifecycle_sha256",
    )
    expected_registry_hash = _digest(
        invariant.get("canonical_registry_non_lifecycle_sha256"),
        "canonical_registry_non_lifecycle_sha256",
    )
    for label, value in (("S3", base_boundary), ("current", boundary)):
        if (
            _canonical_projection_sha256(value, BOUNDARY_CANONICAL_EXCLUDED_PATHS)
            != expected_boundary_hash
        ):
            raise ValueError(f"{label} boundary canonical invariant hash mismatch")
    for label, value in (("S3", base_registry), ("current", registry)):
        if (
            _canonical_projection_sha256(value, REGISTRY_CANONICAL_EXCLUDED_PATHS)
            != expected_registry_hash
        ):
            raise ValueError(f"{label} registry canonical invariant hash mismatch")

    opened_at = boundary.get("development_opened_at_utc")
    if not isinstance(opened_at, str) or "T" not in opened_at:
        raise ValueError("development_opened_at_utc must be RFC3339 UTC")
    try:
        parsed_opened_at = datetime.fromisoformat(opened_at)
    except ValueError as exc:
        raise ValueError("development_opened_at_utc must be RFC3339 UTC") from exc
    if (
        parsed_opened_at.tzinfo is None
        or parsed_opened_at.utcoffset() is None
        or parsed_opened_at.utcoffset().total_seconds() != 0
    ):
        raise ValueError("development_opened_at_utc must be RFC3339 UTC")
    if boundary.get("opening_authority") != OPENING_AUTHORITY:
        raise ValueError("opening_authority is not the preregistered exact authority")
    registry_pools = _mapping(
        registry.get("next_boundary_reservations"),
        "seed registry.next_boundary_reservations",
    )
    registered = _mapping(
        registry_pools.get("Fa04_top_trace_guard_development"),
        "seed registry Fa04 development",
    )
    if registered.get("opened_at_utc") != opened_at:
        raise ValueError("registry opened_at_utc does not match boundary opening time")


def _effective_configuration(override: Mapping[str, Any], seed: int | None) -> dict[str, Any]:
    configuration = {"episodeSteps": 720, **json.loads(json.dumps(override, sort_keys=True))}
    if seed is not None:
        configuration["seed"] = seed
    return configuration


def _frozen_plan(project_root: Path, boundary_path: Path) -> dict[str, Any]:
    boundary = _mapping(_load(boundary_path), "boundary")
    if _relative_path(project_root, boundary_path, "boundary") != BOUNDARY_RELATIVE:
        raise ValueError("unexpected Fa04 boundary path")
    implementation_commit = _commit(
        boundary.get("implementation_commit"), "implementation_commit"
    )
    registry_relative = boundary.get("seed_registry")
    if not isinstance(registry_relative, str):
        raise TypeError("seed_registry must be a string path")
    registry_path = project_root / registry_relative
    expected_registry_hash = _digest(
        boundary.get("seed_registry_sha256"), "seed_registry_sha256"
    )
    if _sha256(registry_path) != expected_registry_hash:
        raise ValueError("seed registry hash mismatch")
    registry = _mapping(_load(registry_path), "seed registry")
    _validate_open_transition_invariant(
        project_root,
        boundary,
        registry,
        implementation_commit,
        registry_relative,
    )
    seeds = _validate_lifecycle(boundary, registry)

    scenario_entry = _mapping(boundary.get("scenario_config"), "scenario_config")
    scenario_file = _checked_file_entry(project_root, scenario_entry, "scenario_config")
    scenario_document = _mapping(
        _load(project_root / scenario_file["path"]), "scenario config"
    )
    scenarios = _mapping(scenario_document.get("scenarios"), "scenario config.scenarios")
    if set(scenarios) != {"default"}:
        raise ValueError("development scenario config must contain only default")
    default_override = dict(_mapping(scenarios.get("default"), "scenario default"))
    effective_scenarios = {"default": _effective_configuration(default_override, None)}
    scenario_sha = _json_sha256(effective_scenarios)
    if scenario_sha != _digest(
        boundary.get("expected_effective_scenarios_sha256"),
        "expected_effective_scenarios_sha256",
    ):
        raise ValueError("effective scenario hash mismatch")

    candidate = _checked_file_entry(
        project_root, _mapping(boundary.get("candidate"), "candidate"), "candidate"
    )
    control = _checked_file_entry(
        project_root, _mapping(boundary.get("control"), "control"), "control"
    )
    raw_opponents = boundary.get("opponents")
    if not isinstance(raw_opponents, list) or len(raw_opponents) != 6:
        raise ValueError("Fa04 development requires exactly six opponents")
    opponents: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_opponents):
        entry = _checked_file_entry(
            project_root, _mapping(raw, f"opponents[{index}]"), f"opponents[{index}]"
        )
        identity = _mapping(raw, f"opponents[{index}]").get("identity")
        if not isinstance(identity, str):
            raise TypeError(f"opponents[{index}].identity must be a string")
        opponents.append({**entry, "identity": identity})
    opponent_paths = [entry["path"] for entry in opponents]
    if len(set(opponent_paths)) != 6:
        raise ValueError("opponent paths must be unique")
    if sum(entry["identity"] == "formal_final_day_labor" for entry in opponents) != 1:
        raise ValueError("opponents must contain exactly one formal lane")

    tooling_config = _mapping(boundary.get("tooling"), "tooling")
    tooling: dict[str, dict[str, Any]] = {}
    for name in TOOLING_KEYS:
        tooling[name] = _checked_file_entry(
            project_root,
            {
                "path": tooling_config.get(name),
                "sha256": tooling_config.get(f"{name}_sha256"),
            },
            f"tooling.{name}",
        )
    gates_hash = _json_sha256(_mapping(boundary.get("development_gates"), "development_gates"))
    freeze = _mapping(boundary.get("execution_freeze"), "execution_freeze")
    if gates_hash != _digest(
        freeze.get("development_gates_sha256"),
        "execution_freeze.development_gates_sha256",
    ):
        raise ValueError("development gate threshold hash mismatch")
    third_party = {
        name: _checked_file_entry(
            project_root,
            _mapping(freeze.get(name), f"execution_freeze.{name}"),
            f"execution_freeze.{name}",
        )
        for name in ("third_party_license", "third_party_attribution")
    }
    runtime_replay = _checked_file_entry(
        project_root,
        _mapping(freeze.get("runtime_replay"), "execution_freeze.runtime_replay"),
        "execution_freeze.runtime_replay",
    )
    attribution = _mapping(boundary.get("attribution"), "attribution")
    if runtime_replay["sha256"] != _digest(
        attribution.get("replay_sha256"), "attribution.replay_sha256"
    ):
        raise ValueError("runtime replay does not match the attributed source replay")

    artifacts = _mapping(freeze.get("artifacts"), "execution_freeze.artifacts")
    required_artifacts = {
        "candidate_report",
        "control_report",
        "candidate_start_receipt",
        "control_start_receipt",
        "runtime_report",
        "analysis_report",
    }
    if set(artifacts) != required_artifacts or not all(
        isinstance(value, str) and value for value in artifacts.values()
    ):
        raise ValueError("execution artifact paths are incomplete")
    if artifacts["candidate_start_receipt"] == artifacts["control_start_receipt"]:
        raise ValueError("candidate and control must have separate start receipts")
    for lane in ("candidate", "control"):
        report_relative = artifacts[f"{lane}_report"]
        runner_receipt = Path(report_relative).with_name(
            f"{Path(report_relative).stem}.started.json"
        ).as_posix()
        if artifacts[f"{lane}_start_receipt"] == runner_receipt:
            raise ValueError(
                f"{lane} outer receipt must be separate from the runner receipt"
            )

    design = _mapping(boundary.get("development_design"), "development_design")
    expected_workers = design.get("workers_per_lane")
    if (
        isinstance(expected_workers, bool)
        or not isinstance(expected_workers, int)
        or not 1 <= expected_workers <= 12
    ):
        raise ValueError("development workers_per_lane must be an integer from 1 through 12")
    if (
        design.get("scenarios") != ["default"]
        or design.get("seeds") != "40000-40015"
        or design.get("seats") != [0, 1]
        or design.get("opponents") != 6
        or design.get("exact_cells_per_lane") != EXPECTED_CELL_COUNT
    ):
        raise ValueError("development design does not match the frozen 192-cell grid")

    implementation_paths = {
        candidate["path"],
        control["path"],
        *opponent_paths,
        *[entry["path"] for entry in tooling.values()],
        *[entry["path"] for entry in third_party.values()],
    }
    execution_paths = {
        _relative_path(project_root, boundary_path, "boundary"),
        registry_relative,
        scenario_file["path"],
    }
    allowed_untracked = {str(value) for value in artifacts.values()}
    allowed_untracked.update(
        _runner_receipt_relative(str(artifacts[f"{lane}_report"]))
        for lane in ("candidate", "control")
    )
    allowed_untracked.add(_runtime_receipt_relative(str(artifacts["runtime_report"])))
    git_freeze = _verify_git_freeze(
        project_root,
        implementation_commit,
        implementation_paths,
        execution_paths,
        allowed_untracked,
    )
    cell_keys = {
        ("default", opponent, seed, seat)
        for opponent in opponent_paths
        for seed in seeds
        for seat in (0, 1)
    }
    if len(cell_keys) != EXPECTED_CELL_COUNT:
        raise ValueError("Fa04 development must derive exactly 192 unique cells")
    return {
        "boundary": dict(boundary),
        "boundary_file": {
            "path": _relative_path(project_root, boundary_path, "boundary"),
            "sha256": _sha256(boundary_path),
            "bytes": boundary_path.stat().st_size,
        },
        "registry_file": {
            "path": registry_relative,
            "sha256": expected_registry_hash,
            "bytes": registry_path.stat().st_size,
        },
        "scenario_file": scenario_file,
        "tooling": tooling,
        "third_party": third_party,
        "runtime_replay": runtime_replay,
        "development_gates_sha256": gates_hash,
        "implementation_commit": git_freeze["implementation_commit"],
        "execution_head": git_freeze["execution_head"],
        "candidate": candidate,
        "control": control,
        "opponents": opponents,
        "opponent_paths": opponent_paths,
        "opponent_hashes": {entry["path"]: entry["sha256"] for entry in opponents},
        "seeds": seeds,
        "default_override": default_override,
        "effective_scenarios": effective_scenarios,
        "effective_scenarios_sha256": scenario_sha,
        "cell_keys": cell_keys,
        "artifacts": dict(artifacts),
        "workers_per_lane": expected_workers,
    }


def _require_artifact_path(
    project_root: Path, actual: Path, expected_relative: str, label: str
) -> None:
    if _relative_path(project_root, actual, label) != expected_relative:
        raise ValueError(f"{label} path does not match the frozen contract")


def _relative_report_path(project_root: Path, value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty path")
    path = Path(value)
    if not path.is_absolute():
        path = project_root / path
    return _relative_path(project_root, path, label)


def _runner_receipt_relative(report_relative: str) -> str:
    report_path = Path(report_relative)
    return report_path.with_name(f"{report_path.stem}.started.json").as_posix()


def _runtime_receipt_relative(report_relative: str) -> str:
    report_path = Path(report_relative)
    return report_path.with_name(f"{report_path.stem}.started.json").as_posix()


def _outer_receipt_payload(
    lane: str,
    workers: int,
    source: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> dict[str, Any]:
    artifacts = _mapping(plan["artifacts"], "artifacts")
    return {
        "schema_version": 2,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "lane": lane,
        "implementation_commit": plan["implementation_commit"],
        "git_head": plan["execution_head"],
        "tracked_tree_clean": True,
        "workers": workers,
        "output": artifacts[f"{lane}_report"],
        "runner_start_receipt": _runner_receipt_relative(
            str(artifacts[f"{lane}_report"])
        ),
        "boundary": plan["boundary_file"],
        "registry": plan["registry_file"],
        "scenario_config": plan["scenario_file"],
        "development_gates_sha256": plan["development_gates_sha256"],
        "tooling": plan["tooling"],
        "third_party": plan["third_party"],
        "runtime_replay": plan["runtime_replay"],
        "source": dict(source),
        "opponents": plan["opponent_paths"],
        "opponent_source_sha256": plan["opponent_hashes"],
        "seeds": plan["seeds"],
        "scenarios": ["default"],
        "scenario_overrides": {"default": plan["default_override"]},
        "effective_scenarios": plan["effective_scenarios"],
        "effective_scenarios_sha256": plan["effective_scenarios_sha256"],
        "cell_count": EXPECTED_CELL_COUNT,
    }


def _validate_runner_receipt(
    project_root: Path,
    report: Mapping[str, Any],
    lane: str,
    workers: int,
    source: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> dict[str, Any]:
    artifacts = _mapping(plan["artifacts"], "artifacts")
    expected_relative = _runner_receipt_relative(str(artifacts[f"{lane}_report"]))
    actual_relative = _relative_report_path(
        project_root, report.get("start_receipt"), f"{lane} runner receipt"
    )
    if actual_relative != expected_relative:
        raise ValueError(f"{lane} runner receipt path mismatch")
    receipt_path = project_root / actual_relative
    if not receipt_path.is_file():
        raise ValueError(f"{lane} runner receipt is missing")
    receipt_hash = _sha256(receipt_path)
    if receipt_hash != _digest(
        report.get("start_receipt_sha256"), f"{lane} runner receipt hash"
    ):
        raise ValueError(f"{lane} runner receipt hash mismatch")
    receipt = _mapping(_load(receipt_path), f"{lane} runner receipt")
    opponent_absolute = {
        relative: str((project_root / relative).resolve())
        for relative in plan["opponent_paths"]
    }
    expected = {
        "git_head_at_start": plan["execution_head"],
        "candidate": source["path"],
        "candidate_path": str((project_root / source["path"]).resolve()),
        "candidate_sha256_at_start": source["sha256"],
        "opponents": plan["opponent_paths"],
        "opponent_paths": opponent_absolute,
        "opponent_sha256_at_start": plan["opponent_hashes"],
        "seeds": plan["seeds"],
        "seat_policy": "both seats",
        "workers": workers,
        "scenario_overrides": {"default": plan["default_override"]},
        "effective_scenarios": plan["effective_scenarios"],
        "effective_scenarios_sha256": plan["effective_scenarios_sha256"],
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise ValueError(f"{lane} runner receipt {key} mismatch")
    return {"path": actual_relative, "sha256": receipt_hash}


def _validate_receipt(
    project_root: Path,
    report: Mapping[str, Any],
    lane: str,
    source: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> dict[str, Any]:
    artifacts = _mapping(plan["artifacts"], "artifacts")
    execution_provenance = _mapping(
        report.get("execution_provenance"), f"{lane}.execution_provenance"
    )
    outer_link = _mapping(
        execution_provenance.get("start_receipt"),
        f"{lane}.execution_provenance.start_receipt",
    )
    relative = outer_link.get("path")
    if relative != artifacts.get(f"{lane}_start_receipt"):
        raise ValueError(f"{lane} outer receipt path mismatch")
    if not isinstance(relative, str):
        raise TypeError(f"{lane} outer receipt path must be a string")
    receipt_path = project_root / relative
    if not receipt_path.is_file():
        raise ValueError(f"{lane} outer receipt is missing")
    receipt_hash = _sha256(receipt_path)
    if receipt_hash != _digest(
        outer_link.get("sha256"), f"{lane} outer receipt sha256"
    ):
        raise ValueError(f"{lane} outer receipt hash mismatch")
    receipt = _mapping(_load(receipt_path), f"{lane} receipt")
    workers = receipt.get("workers")
    if isinstance(workers, bool) or not isinstance(workers, int) or not 1 <= workers <= 12:
        raise ValueError(f"{lane} receipt workers are missing or invalid")
    if workers != plan["workers_per_lane"]:
        raise ValueError(f"{lane} receipt workers differ from the frozen design")
    expected = _outer_receipt_payload(lane, workers, source, plan)
    expected.pop("created_at_utc")
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise ValueError(f"{lane} outer receipt {key} mismatch")
    if not isinstance(receipt.get("created_at_utc"), str):
        raise TypeError(f"{lane} outer receipt created_at_utc is missing")
    if (
        report.get("implementation_commit") != plan["implementation_commit"]
        or report.get("git_head_at_start") != plan["execution_head"]
        or report.get("workers") != workers
        or execution_provenance.get("lane") != lane
        or execution_provenance.get("implementation_commit")
        != plan["implementation_commit"]
        or execution_provenance.get("git_head") != plan["execution_head"]
    ):
        raise ValueError(f"{lane} report git_head/workers mismatch")
    runner_receipt = _validate_runner_receipt(
        project_root, report, lane, workers, source, plan
    )
    return {
        "path": relative,
        "sha256": receipt_hash,
        "workers": workers,
        "runner_receipt": runner_receipt,
    }


def _validate_report(
    report: Mapping[str, Any],
    *,
    expected_agent: Mapping[str, Any],
    plan: Mapping[str, Any],
    label: str,
) -> dict[tuple[str, str, int, int], dict[str, Any]]:
    opponent_paths = plan["opponent_paths"]
    expected_hashes = plan["opponent_hashes"]
    expected_keys = plan["cell_keys"]
    if report.get("candidate") != expected_agent["path"]:
        raise ValueError(f"{label} source path mismatch")
    source_hash = expected_agent["sha256"]
    if (
        report.get("candidate_sha256_at_start") != source_hash
        or report.get("candidate_sha256_at_end") != source_hash
        or report.get("sources_unchanged_during_run") is not True
        or report.get("opponents") != opponent_paths
        or report.get("seeds") != plan["seeds"]
        or report.get("scenario_overrides") != {"default": plan["default_override"]}
        or report.get("effective_scenarios") != plan["effective_scenarios"]
        or report.get("effective_scenarios_sha256")
        != plan["effective_scenarios_sha256"]
        or report.get("opponent_sha256_at_start") != expected_hashes
        or report.get("opponent_sha256_at_end") != expected_hashes
    ):
        raise ValueError(f"{label} frozen report contract mismatch")
    summary = _mapping(report.get("summary"), f"{label}.summary")
    if (
        summary.get("raw_games") != EXPECTED_CELL_COUNT
        or summary.get("valid_raw_games") != EXPECTED_CELL_COUNT
        or summary.get("failed_raw_games") != 0
    ):
        raise ValueError(f"{label} summary is not exactly 192 valid cells")
    games = report.get("games")
    if not isinstance(games, list) or len(games) != EXPECTED_CELL_COUNT:
        raise ValueError(f"{label} games must contain exactly 192 rows")

    rows: dict[tuple[str, str, int, int], dict[str, Any]] = {}
    for index, raw_row in enumerate(games):
        row = _mapping(raw_row, f"{label}.games[{index}]")
        scenario = row.get("scenario")
        opponent = row.get("opponent")
        seed = row.get("seed")
        seat = row.get("seat")
        if (
            scenario != "default"
            or opponent not in opponent_paths
            or isinstance(seed, bool)
            or not isinstance(seed, int)
            or isinstance(seat, bool)
            or seat not in (0, 1)
        ):
            raise ValueError(f"{label}.games[{index}] cell identity is invalid")
        key = (scenario, opponent, seed, seat)
        if key in rows:
            raise ValueError(f"{label} contains a duplicate cell")
        if (
            row.get("error") is not None
            or row.get("candidate_status") != "DONE"
            or row.get("opponent_status") != "DONE"
            or row.get("candidate_money") is None
            or row.get("opponent_money") is None
        ):
            raise ValueError(f"{label}.games[{index}] is not a valid DONE result")
        effective = _mapping(
            row.get("effective_configuration"),
            f"{label}.games[{index}].effective_configuration",
        )
        expected_effective = _effective_configuration(plan["default_override"], seed)
        if dict(effective) != expected_effective or _json_sha256(effective) != _digest(
            row.get("effective_configuration_sha256"),
            f"{label}.games[{index}].effective_configuration_sha256",
        ):
            raise ValueError(f"{label}.games[{index}] effective configuration mismatch")
        environment = _mapping(
            row.get("environment_configuration"),
            f"{label}.games[{index}].environment_configuration",
        )
        if _json_sha256(environment) != _digest(
            row.get("environment_configuration_sha256"),
            f"{label}.games[{index}].environment_configuration_sha256",
        ):
            raise ValueError(f"{label}.games[{index}] environment hash mismatch")
        for name, value in expected_effective.items():
            if name != "seed" and environment.get(name) != value:
                raise ValueError(
                    f"{label}.games[{index}] environment scenario value mismatch"
                )
        resolved_seed = row.get("resolved_environment_seed")
        environment_seed = environment.get("seed")
        if environment_seed is not None and (
            environment_seed != seed or environment_seed != resolved_seed
        ):
            raise ValueError(
                f"{label}.games[{index}] environment seed contradicts requested/resolved seed"
            )
        if resolved_seed != seed:
            raise ValueError(f"{label}.games[{index}] resolved seed mismatch")
        rows[key] = dict(row)
    if set(rows) != expected_keys:
        raise ValueError(f"{label} does not contain the exact frozen 192-cell grid")
    return rows


def _validate_environment_pairs(
    candidate_rows: Mapping[tuple[str, str, int, int], dict[str, Any]],
    control_rows: Mapping[tuple[str, str, int, int], dict[str, Any]],
) -> None:
    if set(candidate_rows) != set(control_rows):
        raise ValueError("candidate/control cell keys differ")
    for key in candidate_rows:
        candidate = candidate_rows[key]
        control = control_rows[key]
        if (
            candidate["effective_configuration"] != control["effective_configuration"]
            or candidate["effective_configuration_sha256"]
            != control["effective_configuration_sha256"]
            or candidate["environment_configuration"]
            != control["environment_configuration"]
            or candidate["environment_configuration_sha256"]
            != control["environment_configuration_sha256"]
            or candidate["resolved_environment_seed"]
            != control["resolved_environment_seed"]
        ):
            raise ValueError(f"candidate/control environment mismatch for cell {key}")


def _outcome(row: Mapping[str, Any]) -> float:
    candidate = float(row["candidate_money"])
    opponent = float(row["opponent_money"])
    return 1.0 if candidate > opponent else 0.0 if candidate < opponent else 0.5


def _finite_nonnegative(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be a finite nonnegative number")
    normalized = float(value)
    if not math.isfinite(normalized) or normalized < 0:
        raise ValueError(f"{label} must be a finite nonnegative number")
    return normalized


def _run_batch_exact(
    candidate_ref: str,
    opponents: list[str],
    seeds: list[int],
    output: Path,
    workers: int,
    project_root: Path,
    scenarios: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    from kaggriculture_lab.evaluation.runner import run_batch

    return run_batch(
        candidate_ref,
        opponents,
        seeds,
        output,
        workers,
        project_root,
        scenarios,
    )


def run_development_lane(
    project_root: Path,
    boundary_path: Path,
    lane: str,
    workers: int,
) -> dict[str, Any]:
    if lane not in {"candidate", "control"}:
        raise ValueError("lane must be candidate or control")
    if isinstance(workers, bool) or not isinstance(workers, int) or not 1 <= workers <= 12:
        raise ValueError("workers must be an integer from 1 through 12")
    project_root = project_root.resolve()
    boundary_path = boundary_path.resolve()
    plan = _frozen_plan(project_root, boundary_path)
    if workers != plan["workers_per_lane"]:
        raise ValueError("workers differ from the frozen development design")
    source = plan[lane]
    artifacts = _mapping(plan["artifacts"], "artifacts")
    report_relative = str(artifacts[f"{lane}_report"])
    outer_relative = str(artifacts[f"{lane}_start_receipt"])
    runner_relative = _runner_receipt_relative(report_relative)
    output_path = project_root / report_relative
    outer_path = project_root / outer_relative
    runner_path = project_root / runner_relative
    for path, label in (
        (output_path, "report"),
        (outer_path, "outer receipt"),
        (runner_path, "runner receipt"),
    ):
        if path.exists():
            raise ValueError(f"{lane} {label} already exists; refusing seed reuse")

    outer = _outer_receipt_payload(lane, workers, source, plan)
    outer_path.parent.mkdir(parents=True, exist_ok=True)
    outer_path.write_text(json.dumps(outer, indent=2) + "\n", encoding="utf-8")
    outer_hash = _sha256(outer_path)
    report = _run_batch_exact(
        str(source["path"]),
        list(plan["opponent_paths"]),
        list(plan["seeds"]),
        output_path,
        workers,
        project_root,
        {"default": dict(plan["default_override"])},
    )
    if not isinstance(report, dict):
        raise TypeError("runner did not return a report object")
    report["implementation_commit"] = plan["implementation_commit"]
    report["execution_provenance"] = {
        "lane": lane,
        "implementation_commit": plan["implementation_commit"],
        "git_head": plan["execution_head"],
        "start_receipt": {"path": outer_relative, "sha256": outer_hash},
    }
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    _validate_receipt(project_root, report, lane, source, plan)
    _validate_report(report, expected_agent=source, plan=plan, label=f"{lane} report")
    return report


def _runtime_receipt_payload(plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "implementation_commit": plan["implementation_commit"],
        "git_head": plan["execution_head"],
        "tracked_tree_clean": True,
        "output": plan["artifacts"]["runtime_report"],
        "boundary": plan["boundary_file"],
        "registry": plan["registry_file"],
        "scenario_config": plan["scenario_file"],
        "tooling": plan["tooling"],
        "source": plan["candidate"],
        "runtime_replay": plan["runtime_replay"],
        "player": 0,
        "command": (
            "python -m kaggriculture_lab.evaluation.top_trace_gate "
            "--generate-runtime --boundary "
            f"{plan['boundary_file']['path']}"
        ),
    }


def _validate_runtime_receipt(
    project_root: Path,
    runtime: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> dict[str, str]:
    link = _mapping(runtime.get("generation_receipt"), "runtime.generation_receipt")
    expected_relative = _runtime_receipt_relative(
        str(plan["artifacts"]["runtime_report"])
    )
    if link.get("path") != expected_relative:
        raise ValueError("runtime generation receipt path mismatch")
    receipt_path = project_root / expected_relative
    if not receipt_path.is_file():
        raise ValueError("runtime generation receipt is missing")
    receipt_hash = _sha256(receipt_path)
    if receipt_hash != _digest(
        link.get("sha256"), "runtime.generation_receipt.sha256"
    ):
        raise ValueError("runtime generation receipt hash mismatch")
    receipt = _mapping(_load(receipt_path), "runtime generation receipt")
    expected = _runtime_receipt_payload(plan)
    expected.pop("created_at_utc")
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise ValueError(f"runtime generation receipt {key} mismatch")
    if not isinstance(receipt.get("created_at_utc"), str):
        raise TypeError("runtime generation receipt created_at_utc is missing")
    return {"path": expected_relative, "sha256": receipt_hash}


def generate_runtime_report(project_root: Path, boundary_path: Path) -> dict[str, Any]:
    from kaggriculture_lab.evaluation.runtime import benchmark

    project_root = project_root.resolve()
    boundary_path = boundary_path.resolve()
    plan = _frozen_plan(project_root, boundary_path)
    output_relative = str(plan["artifacts"]["runtime_report"])
    output = project_root / output_relative
    receipt_relative = _runtime_receipt_relative(output_relative)
    receipt_path = project_root / receipt_relative
    if output.exists() or receipt_path.exists():
        raise ValueError("runtime report/receipt already exists; refusing evidence overwrite")
    source = project_root / plan["candidate"]["path"]
    replay = project_root / plan["runtime_replay"]["path"]
    receipt = _runtime_receipt_payload(plan)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    receipt_hash = _sha256(receipt_path)
    report = benchmark(source, replay, 0)
    report.update(
        {
            "schema_version": 2,
            "created_at_utc": datetime.now(UTC).isoformat(),
            "python": sys.version,
            "platform": platform.platform(),
            "command": (
                "python -m kaggriculture_lab.evaluation.top_trace_gate "
                "--generate-runtime --boundary "
                f"{plan['boundary_file']['path']}"
            ),
            "generator": dict(plan["tooling"]["runtime_generator"]),
            "git_head": plan["execution_head"],
            "tracked_tree_clean": True,
            "generation_receipt": {
                "path": receipt_relative,
                "sha256": receipt_hash,
            },
            "tracked_provenance": {
                "project_root": project_root.as_posix(),
                "implementation_commit": plan["implementation_commit"],
                "git_head": plan["execution_head"],
                "tracked_tree_clean": True,
                "source_relative": plan["candidate"]["path"],
                "source_at_head_sha256": plan["candidate"]["sha256"],
                "runtime_replay": dict(plan["runtime_replay"]),
            },
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def analyze(
    candidate_report_path: Path,
    control_report_path: Path,
    runtime_report_path: Path,
    boundary_path: Path,
) -> dict[str, Any]:
    project_root = boundary_path.resolve().parent.parent
    plan = _frozen_plan(project_root, boundary_path.resolve())
    _require_artifact_path(
        project_root,
        candidate_report_path,
        plan["artifacts"]["candidate_report"],
        "candidate report",
    )
    _require_artifact_path(
        project_root,
        control_report_path,
        plan["artifacts"]["control_report"],
        "control report",
    )
    _require_artifact_path(
        project_root,
        runtime_report_path,
        plan["artifacts"]["runtime_report"],
        "runtime report",
    )
    candidate_report = _mapping(_load(candidate_report_path), "candidate report")
    control_report = _mapping(_load(control_report_path), "control report")
    runtime = _mapping(_load(runtime_report_path), "runtime report")
    candidate_receipt = _validate_receipt(
        project_root, candidate_report, "candidate", plan["candidate"], plan
    )
    control_receipt = _validate_receipt(
        project_root, control_report, "control", plan["control"], plan
    )
    if candidate_receipt["path"] == control_receipt["path"]:
        raise ValueError("candidate/control reports share a start receipt")
    candidate_rows = _validate_report(
        candidate_report,
        expected_agent=plan["candidate"],
        plan=plan,
        label="candidate report",
    )
    control_rows = _validate_report(
        control_report,
        expected_agent=plan["control"],
        plan=plan,
        label="control report",
    )
    _validate_environment_pairs(candidate_rows, control_rows)

    formal_path = next(
        entry["path"]
        for entry in plan["opponents"]
        if entry["identity"] == "formal_final_day_labor"
    )
    per_opponent: dict[str, dict[str, float | int]] = {}
    for opponent in plan["opponent_paths"]:
        rows = [row for key, row in candidate_rows.items() if key[1] == opponent]
        per_opponent[opponent] = {
            "games": len(rows),
            "match_score": statistics.mean(_outcome(row) for row in rows),
            "margin_mean": statistics.mean(
                float(row["candidate_money"] - row["opponent_money"]) for row in rows
            ),
        }
    top_rows = [row for key, row in candidate_rows.items() if key[1] != formal_path]
    paired_match = [
        _outcome(candidate_rows[key]) - _outcome(control_rows[key])
        for key in candidate_rows
    ]
    paired_money = [
        float(candidate_rows[key]["candidate_money"] - control_rows[key]["candidate_money"])
        for key in candidate_rows
    ]
    actions_changed = sum(
        int((row.get("candidate_metrics") or {}).get("actions_changed", 0))
        for row in candidate_rows.values()
    )
    gates = _mapping(plan["boundary"].get("development_gates"), "development_gates")
    runtime_receipt = _validate_runtime_receipt(project_root, runtime, plan)
    calls = _finite_nonnegative(runtime.get("calls"), "runtime.calls")
    invalid_outputs = _finite_nonnegative(
        runtime.get("invalid_outputs"), "runtime.invalid_outputs"
    )
    p95_ms = _finite_nonnegative(runtime.get("p95_ms"), "runtime.p95_ms")
    p99_ms = _finite_nonnegative(runtime.get("p99_ms"), "runtime.p99_ms")
    max_ms = _finite_nonnegative(runtime.get("max_ms"), "runtime.max_ms")
    if not 0 <= p95_ms <= p99_ms <= max_ms:
        raise ValueError("runtime timings must satisfy 0 <= p95 <= p99 <= max")
    runtime_head = runtime.get("git_head")
    if (
        runtime_head != plan["execution_head"]
        or runtime.get("tracked_tree_clean") is not True
    ):
        raise ValueError("runtime report is not bound to the clean execution HEAD")
    runtime_generator = _mapping(runtime.get("generator"), "runtime.generator")
    expected_runtime_generator = plan["tooling"]["runtime_generator"]
    if (
        _relative_report_path(
            project_root, runtime_generator.get("path"), "runtime generator"
        )
        != expected_runtime_generator["path"]
        or _digest(runtime_generator.get("sha256"), "runtime.generator.sha256")
        != expected_runtime_generator["sha256"]
    ):
        raise ValueError("runtime generator is not the frozen tooling")
    tracked = _mapping(runtime.get("tracked_provenance"), "runtime.tracked_provenance")
    tracked_project_root = tracked.get("project_root")
    if not isinstance(tracked_project_root, str):
        raise TypeError("runtime tracked project root is missing")
    if (
        Path(tracked_project_root).resolve() != project_root.resolve()
        or tracked.get("implementation_commit") != plan["implementation_commit"]
        or tracked.get("git_head") != plan["execution_head"]
        or tracked.get("tracked_tree_clean") is not True
        or tracked.get("source_relative") != plan["candidate"]["path"]
        or tracked.get("runtime_replay") != plan["runtime_replay"]
        or _digest(
            tracked.get("source_at_head_sha256"),
            "runtime.tracked_provenance.source_at_head_sha256",
        )
        != plan["candidate"]["sha256"]
        or _relative_report_path(project_root, runtime.get("source"), "runtime source")
        != plan["candidate"]["path"]
        or _relative_report_path(project_root, runtime.get("replay"), "runtime replay")
        != plan["runtime_replay"]["path"]
        or runtime.get("player") != 0
    ):
        raise ValueError("runtime tracked source provenance mismatch")
    checks = {
        "candidate_failures": candidate_report["summary"]["failed_raw_games"]
        == gates["candidate_failures"],
        "control_failures": control_report["summary"]["failed_raw_games"]
        == gates["control_failures"],
        "top_trace_match": statistics.mean(_outcome(row) for row in top_rows)
        >= gates["minimum_candidate_top_trace_match_score"],
        "each_top_trace_match": all(
            values["match_score"] >= gates["minimum_each_top_trace_match_score"]
            for opponent, values in per_opponent.items()
            if opponent != formal_path
        ),
        "formal_match": per_opponent[formal_path]["match_score"]
        >= gates["minimum_formal_match_score"],
        "each_margin": all(
            values["margin_mean"] >= gates["minimum_each_opponent_mean_margin"]
            for values in per_opponent.values()
        ),
        "paired_match_noninferior": statistics.mean(paired_match)
        >= gates["minimum_paired_match_delta_vs_control"],
        "paired_money_noninferior": statistics.mean(paired_money)
        >= gates["minimum_paired_money_delta_vs_control"],
        "guard_activated": actions_changed >= gates["minimum_actions_changed"],
        "runtime_calls": calls == 720,
        "runtime_invalid": invalid_outputs == gates["invalid_outputs"],
        "runtime_p95": p95_ms <= gates["runtime_p95_ms_max"],
        "runtime_p99": p99_ms <= gates["runtime_p99_ms_max"],
        "runtime_max": max_ms <= gates["runtime_absolute_ms_max"],
        "runtime_source": runtime.get("source_sha256") == plan["candidate"]["sha256"],
        "runtime_replay": runtime.get("replay_sha256")
        == plan["boundary"]["attribution"]["replay_sha256"],
    }
    return {
        "schema_version": 2,
        "implementation_commit": plan["implementation_commit"],
        "execution_head": plan["execution_head"],
        "boundary": plan["boundary_file"],
        "registry": plan["registry_file"],
        "scenario_config": plan["scenario_file"],
        "tooling": plan["tooling"],
        "candidate_start_receipt": candidate_receipt,
        "control_start_receipt": control_receipt,
        "runtime_generation_receipt": runtime_receipt,
        "candidate_report_sha256": _sha256(candidate_report_path),
        "control_report_sha256": _sha256(control_report_path),
        "runtime_report_sha256": _sha256(runtime_report_path),
        "cells": len(candidate_rows),
        "top_trace_match_score": statistics.mean(_outcome(row) for row in top_rows),
        "formal_match_score": per_opponent[formal_path]["match_score"],
        "per_opponent": per_opponent,
        "paired_match_delta": statistics.mean(paired_match),
        "paired_money_delta": statistics.mean(paired_money),
        "actions_changed": actions_changed,
        "runtime": dict(runtime),
        "checks": checks,
        "development_pass": all(checks.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run or analyze frozen Fa04 top-trace development"
    )
    parser.add_argument("--candidate-report", type=Path)
    parser.add_argument("--control-report", type=Path)
    parser.add_argument("--runtime-report", type=Path)
    parser.add_argument("--boundary", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--run-lane", choices=("candidate", "control"))
    parser.add_argument("--generate-runtime", action="store_true")
    parser.add_argument("--workers", type=int)
    args = parser.parse_args()
    project_root = args.boundary.resolve().parent.parent
    if args.generate_runtime:
        if any(
            value is not None
            for value in (
                args.candidate_report,
                args.control_report,
                args.runtime_report,
                args.output,
                args.run_lane,
                args.workers,
            )
        ):
            parser.error("--generate-runtime cannot be combined with other modes")
        report = generate_runtime_report(project_root, args.boundary)
        print(json.dumps({"calls": report["calls"], "output": report["source"]}))
        return
    if args.run_lane is not None:
        if any(
            value is not None
            for value in (
                args.candidate_report,
                args.control_report,
                args.runtime_report,
                args.output,
            )
        ):
            parser.error("--run-lane cannot be combined with analysis arguments")
        if args.workers is None:
            parser.error("--workers is required with --run-lane")
        report = run_development_lane(
            project_root, args.boundary, args.run_lane, args.workers
        )
        print(
            json.dumps(
                {
                    "lane": args.run_lane,
                    "games": len(report.get("games", [])),
                    "report": report.get("candidate"),
                }
            )
        )
        return
    if args.workers is not None:
        parser.error("--workers is only valid with --run-lane")
    if any(
        value is None
        for value in (
            args.candidate_report,
            args.control_report,
            args.runtime_report,
            args.output,
        )
    ):
        parser.error("analysis requires candidate/control/runtime reports and --output")
    boundary = _load(args.boundary)
    artifacts = _mapping(
        _mapping(boundary.get("execution_freeze"), "execution_freeze").get("artifacts"),
        "execution_freeze.artifacts",
    )
    _require_artifact_path(
        project_root, args.output, str(artifacts.get("analysis_report")), "analysis report"
    )
    result = analyze(
        args.candidate_report,
        args.control_report,
        args.runtime_report,
        args.boundary,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"development_pass": result["development_pass"], **result["checks"]}))
    if not result["development_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
