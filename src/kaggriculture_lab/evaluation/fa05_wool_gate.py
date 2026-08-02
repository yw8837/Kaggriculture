"""Frozen, fail-closed development gate for the Fa05 W1 Wool Glut Buffer.

The checked-in boundary keeps every seed pool CLOSED.  This module can validate
that closed design without materialising or running a seed.  The run, runtime,
and analysis entry points become usable only after an independently authorised
lifecycle-only open transition is committed.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import struct
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kaggriculture_lab.evaluation import paired
from kaggriculture_lab.evaluation import top_trace_gate as core

BOUNDARY_RELATIVE = "configs/fa05_wool_glut_boundary.json"
REGISTRY_RELATIVE = "configs/fa_ab_seed_registry.json"
SCENARIO_RELATIVE = "configs/fa05_wool_glut_scenarios.json"
MANIFEST_RELATIVE = "configs/fa05_wool_glut_manifest.json"
DEVELOPMENT_KEY = "Fa05_wool_glut_buffer_development"
CONFIRMATION_KEY = "Fa05_wool_glut_buffer_confirmation"
ROBUSTNESS_KEY = "Fa05_wool_glut_buffer_robustness"
PENDING_IMPLEMENTATION_COMMIT = "PENDING_CLOSED_FREEZE_COMMIT"
OPENING_AUTHORITY = (
    "A separate independent-auditor approval may open only exact Fa05 Wool "
    "development seeds 46000-46015; it does not authorize SaveRun, submission, "
    "confirmation, robustness, or publication."
)
RELEASE_POLICY = (
    "Development PASS permits only a separate private SaveRun audit request. "
    "Confirmation, robustness, competition submission, and publication stay closed."
)

CANDIDATE_ENTRY = {
    "identity": "W1_wool_glut_buffer",
    "path": "experiments/source_snapshots/fa05_wool_glut/W1_wool_glut_buffer.py",
    "sha256": "78B9697E4646BA27516AE0DEE067B2F95E749B35B369583534FD6475AC2DA2C6",
    "bytes": 221585,
}
CONTROL_ENTRY = {
    "identity": "Fa04_G1_sell_guard_control",
    "path": "experiments/source_snapshots/fa04_top_trace/G1_sell_guard.py",
    "sha256": "81159A18DF3CD1A5CAABE5EDBBA0A597561775F77A49465FA39DF6802A706922",
    "bytes": 197808,
}
EXPECTED_OPPONENT_CONTRACT = {
    "C135_chocolat": (
        "experiments/source_snapshots/fa04_top_trace/C135.py",
        "13C88E1D9232F66A219AF0B66A36A46D622C2466856D191E57A8FDC42BC7C1EE",
    ),
    "R140_radiant": (
        "experiments/source_snapshots/fa04_top_trace/R140.py",
        "E4BDEDB791FC129AA73941D96BEA2C20709D9431A8C9628AB526EA186B0F4870",
    ),
    "R145_radiant": (
        "experiments/source_snapshots/fa04_top_trace/R145.py",
        "99CE3CABA350D03DC59B9649B9E6D0D28F3D896C5BE0783D355A3D8701476650",
    ),
    "R150_radiant": (
        "experiments/source_snapshots/fa04_top_trace/R150.py",
        "80AB5C9E50540FE49D68DED3D170FF79C34603FAF19257BD01554A19E30DA599",
    ),
    "R155_radiant": (
        "experiments/source_snapshots/fa04_top_trace/R155.py",
        "857A8F98425D06262E503D46C15FC9480358ADA7621BC5D6D30575B2B71A167C",
    ),
    "formal_final_day_labor": (
        "artifacts/candidates/final_day_labor/main.py",
        "112AF9EC28030B53CE852927CEE986834F18F0245F3A88FB2E06F423291C9F8B",
    ),
}
WEAK_IDENTITIES = {"R140_radiant", "R155_radiant"}
PROTECTED_IDENTITIES = {
    "C135_chocolat",
    "R150_radiant",
    "formal_final_day_labor",
}
R145_IDENTITY = "R145_radiant"

POOL_CONTRACT = {
    "development": {
        "registry_key": DEVELOPMENT_KEY,
        "start": 46000,
        "end_inclusive": 46015,
        "count": 16,
        "purpose": (
            "Fresh paired default-scenario development of the single-delta W1 Wool "
            "Glut Buffer against C135, R140, R145, R150, R155, and formal; no "
            "direct-G1 opponent lane."
        ),
    },
    "confirmation": {
        "registry_key": CONFIRMATION_KEY,
        "start": 47000,
        "end_inclusive": 47063,
        "count": 64,
        "purpose": (
            "One-time sealed-strength confirmation only after W1 development passes "
            "and a separate independent audit authorizes opening."
        ),
    },
    "robustness": {
        "registry_key": ROBUSTNESS_KEY,
        "start": 48000,
        "end_inclusive": 48031,
        "count": 32,
        "purpose": (
            "One-time scenario robustness only after W1 sealed-strength confirmation "
            "passes and a separate independent audit authorizes opening."
        ),
    },
}

EXPECTED_GATES = {
    "candidate_failures": 0,
    "control_failures": 0,
    "weak": {
        "identities": ["R140_radiant", "R155_radiant"],
        "exact_cells": 64,
        "paired_match_delta_strict_gt": 0.03,
        "seed_cluster_bootstrap_95_lower_gte": -0.02,
        "bootstrap_draws": 10000,
        "bootstrap_random_seed": 0,
        "paired_money_delta_gte": 250.0,
        "each_candidate_money_mean_strict_gt": 0.0,
        "each_candidate_money_r7_p10_strict_gt": -500.0,
        "each_lane_create_observed_units_strict_gt": 0,
        "each_lane_release_observed_units_strict_gt": 0,
        "each_lane_causal_completed_release_units_strict_gt": 0,
    },
    "protected": {
        "identities": [
            "C135_chocolat",
            "R150_radiant",
            "formal_final_day_labor",
        ],
        "exact_cells": 96,
        "create_observed_units_eq": 0,
        "release_observed_units_eq": 0,
        "causal_completed_release_units_eq": 0,
        "overlay_action_changes_eq": 0,
        "protected_lane_action_diff_eq": 0,
        "action_vectors_final_rewards_and_both_money_bit_exact": True,
    },
    "r145": {
        "identity": "R145_radiant",
        "exact_cells": 32,
        "paired_match_delta_gte": -0.02,
        "paired_money_delta_gte": -100.0,
    },
    "all_opponents": {
        "exact_cells": 192,
        "each_candidate_absolute_margin_mean_gte": 0.0,
    },
    "safety": {
        "reserve_conservation_each_game": True,
        "causal_completion_identity_each_game": True,
        "fallback_count_eq": 0,
        "false_trigger_count_eq": 0,
        "blocked_release_units_eq": 0,
        "outside_allowed_action_diff_eq": 0,
        "candidate_caused_overflow_or_discard_units_eq": 0,
        "impossible_sell_units_eq": 0,
        "terminal_pending_eq": 0,
        "terminal_wool_remaining_eq": 0,
    },
    "runtime": {
        "calls": 720,
        "invalid_outputs": 0,
        "p95_ms_max": 8.0,
        "p99_ms_max": 15.0,
        "absolute_ms_max": 50.0,
    },
}

BASE_METRIC_KEYS = {
    "actions_changed",
    "hands_adjusted",
    "sell_clamped",
    "sell_dropped",
    "terminal_rewritten",
}
WOOL_METRIC_KEYS = {
    "eligible_trigger_turns",
    "create_requested_units",
    "create_observed_units",
    "sell_suppressed_orders",
    "release_requested_units",
    "release_observed_units",
    "release_orders",
    "pending_start",
    "pending_end",
    "causal_completed_reserve_release_units",
    "blocked_release_units",
    "fallback_count",
    "false_trigger_count",
    "outside_allowed_action_diff",
    "protected_lane_action_diff",
    "candidate_caused_overflow_or_discard_units",
    "impossible_sell_units",
    "terminal_pending",
    "terminal_wool_remaining",
}
EXPECTED_METRIC_KEYS = BASE_METRIC_KEYS | WOOL_METRIC_KEYS


def _utc_datetime(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be an ISO-8601 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO-8601 UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError(f"{label} must be UTC")
    return parsed


def _exact_nonnegative_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer and not bool")
    return value


def _validate_opponent_contract(
    opponents: list[Mapping[str, Any]], control: Mapping[str, Any]
) -> None:
    actual = {
        str(entry["identity"]): (str(entry["path"]), str(entry["sha256"]))
        for entry in opponents
    }
    if actual != EXPECTED_OPPONENT_CONTRACT:
        raise ValueError("W1 opponent identity/path/hash contract is not exact")
    if len({entry["path"] for entry in opponents}) != 6:
        raise ValueError("W1 requires six unique external opponent paths")
    if any(
        (entry["path"], entry["sha256"])
        == (control["path"], control["sha256"])
        for entry in opponents
    ):
        raise ValueError("direct G1 is forbidden from the W1 opponent grid")


def _validate_single_delta_prefix(project_root: Path) -> None:
    candidate = (project_root / CANDIDATE_ENTRY["path"]).read_bytes()
    control = (project_root / CONTROL_ENTRY["path"]).read_bytes()
    if not candidate.startswith(control):
        raise ValueError("W1 is not an exact byte-prefix derivative of frozen G1")
    suffix = candidate[len(control) :]
    markers = (
        b"Fa05 one-delta derivative: Wool Glut Buffer",
        b"Only legal SELL WOOL quantities may differ from the frozen G1 action",
        b"def rescue_metrics():",
        b"def _apply_wool_glut_buffer(",
    )
    if not suffix or any(marker not in suffix for marker in markers):
        raise ValueError("W1 frozen single-delta suffix markers are incomplete")


def _validate_pool_contract(
    boundary: Mapping[str, Any], registry: Mapping[str, Any], *, opened: bool
) -> list[int]:
    pools = core._mapping(boundary.get("pools"), "boundary.pools")
    reservations = core._mapping(
        registry.get("next_boundary_reservations"), "registry reservations"
    )
    development: list[int] | None = None
    for lane, expected in POOL_CONTRACT.items():
        pool = core._mapping(pools.get(lane), f"pools.{lane}")
        registered = core._mapping(
            reservations.get(expected["registry_key"]),
            f"registry.{expected['registry_key']}",
        )
        for field in ("start", "end_inclusive", "count"):
            if pool.get(field) != expected[field] or registered.get(field) != expected[field]:
                raise ValueError(f"{lane} {field} differs from its exact reservation")
        if pool.get("registry_key") != expected["registry_key"]:
            raise ValueError(f"{lane} registry key mismatch")
        if registered.get("purpose") != expected["purpose"]:
            raise ValueError(f"{lane} purpose mismatch")
        seeds = core._pool_range(pool, f"pools.{lane}")
        if seeds != core._pool_range(registered, f"registry.{lane}"):
            raise ValueError(f"{lane} boundary/registry range mismatch")
        lane_is_open = opened and lane == "development"
        expected_status = "OPEN" if lane_is_open else "CLOSED"
        if (
            pool.get("status") != expected_status
            or registered.get("status") != expected_status
            or registered.get("opened") is not lane_is_open
            or registered.get("consumed") is not False
            or registered.get("evaluated_games") != 0
        ):
            raise ValueError(f"{lane} lifecycle is not exact and unused")
        if not lane_is_open and "opened_at_utc" in registered:
            raise ValueError(f"{lane} must remain unopened")
        if lane == "development":
            development = seeds
    if development != list(range(46000, 46016)):
        raise ValueError("development seeds are not exact 46000-46015")
    return development


def _validate_gate_contract(boundary: Mapping[str, Any]) -> None:
    if boundary.get("development_gates") != EXPECTED_GATES:
        raise ValueError("W1 development gates differ from the frozen exact contract")
    design = core._mapping(boundary.get("development_design"), "development_design")
    if design != {
        "scenarios": ["default"],
        "seeds": "46000-46015",
        "seats": [0, 1],
        "opponent_identities": [
            "C135_chocolat",
            "R140_radiant",
            "R145_radiant",
            "R150_radiant",
            "R155_radiant",
            "formal_final_day_labor",
        ],
        "opponents": 6,
        "exact_cells_per_lane": 192,
        "workers_per_lane": 6,
        "separate_start_receipts_required": True,
        "direct_g1_opponent_forbidden": True,
        "control": "exact frozen Fa04 G1",
    }:
        raise ValueError("W1 development design is not the exact 192-cell grid")
    if boundary.get("release_policy") != RELEASE_POLICY:
        raise ValueError("W1 release policy is not exact")


def _validate_manifest_contract(
    manifest: Mapping[str, Any], boundary: Mapping[str, Any]
) -> None:
    expected = {
        "schema_version": 1,
        "identity": "Fa05_W1_wool_glut_buffer_frozen_sources",
        "status": "FROZEN_SOURCE_MANIFEST",
        "candidate": boundary["candidate"],
        "control": boundary["control"],
        "opponents": boundary["opponents"],
        "scenario_config": boundary["scenario_config"],
        "seed_registry": {
            "path": boundary["seed_registry"],
            "sha256": boundary["seed_registry_sha256"],
        },
        "tooling": boundary["tooling"],
        "single_delta_contract": {
            "candidate_starts_with_control_bytes": True,
            "only_permitted_action_delta": "legal SELL WOOL quantity",
            "direct_g1_opponent_forbidden": True,
        },
    }
    if dict(manifest) != expected:
        raise ValueError("W1 source manifest does not match the boundary contract")


def validate_closed_design(project_root: Path, boundary_path: Path) -> dict[str, Any]:
    """Validate the checked-in CLOSED contract without opening or executing seeds."""
    project_root = project_root.resolve()
    boundary_path = boundary_path.resolve()
    if core._relative_path(project_root, boundary_path, "boundary") != BOUNDARY_RELATIVE:
        raise ValueError("unexpected W1 boundary path")
    boundary = core._mapping(core._load(boundary_path), "boundary")
    if boundary.get("status") != "CLOSED_PENDING_INDEPENDENT_AUDIT":
        raise ValueError("W1 closed-design validator requires the CLOSED boundary")
    if boundary.get("implementation_commit") != PENDING_IMPLEMENTATION_COMMIT:
        core._commit(boundary.get("implementation_commit"), "implementation_commit")

    registry_path = project_root / REGISTRY_RELATIVE
    registry_hash = core._sha256(registry_path)
    if boundary.get("seed_registry") != REGISTRY_RELATIVE or core._digest(
        boundary.get("seed_registry_sha256"), "seed_registry_sha256"
    ) != registry_hash:
        raise ValueError("W1 closed boundary seed registry binding mismatch")
    registry = core._mapping(core._load(registry_path), "registry")
    _validate_pool_contract(boundary, registry, opened=False)
    _validate_gate_contract(boundary)

    scenario = core._checked_file_entry(
        project_root,
        core._mapping(boundary.get("scenario_config"), "scenario_config"),
        "scenario_config",
    )
    scenario_doc = core._mapping(
        core._load(project_root / scenario["path"]), "scenario document"
    )
    if scenario["path"] != SCENARIO_RELATIVE or scenario_doc != {"scenarios": {"default": {}}}:
        raise ValueError("W1 scenario config must contain only an empty default override")
    effective = {"default": core._effective_configuration({}, None)}
    effective_sha = core._json_sha256(effective)
    if effective_sha != core._digest(
        boundary.get("expected_effective_scenarios_sha256"),
        "expected_effective_scenarios_sha256",
    ):
        raise ValueError("W1 effective default configuration hash mismatch")

    candidate = core._checked_file_entry(
        project_root, core._mapping(boundary.get("candidate"), "candidate"), "candidate"
    )
    control = core._checked_file_entry(
        project_root, core._mapping(boundary.get("control"), "control"), "control"
    )
    if boundary.get("candidate") != CANDIDATE_ENTRY or boundary.get("control") != CONTROL_ENTRY:
        raise ValueError("W1 candidate/control identity is not exact")
    raw_opponents = boundary.get("opponents")
    if not isinstance(raw_opponents, list) or len(raw_opponents) != 6:
        raise ValueError("W1 requires exactly six external opponents")
    opponents = []
    for index, raw in enumerate(raw_opponents):
        mapping = core._mapping(raw, f"opponents[{index}]")
        entry = core._checked_file_entry(project_root, mapping, f"opponents[{index}]")
        identity = mapping.get("identity")
        if not isinstance(identity, str):
            raise TypeError(f"opponents[{index}].identity must be a string")
        opponents.append({**entry, "identity": identity})
    _validate_opponent_contract(opponents, control)
    _validate_single_delta_prefix(project_root)

    manifest_entry = core._checked_file_entry(
        project_root, core._mapping(boundary.get("manifest"), "manifest"), "manifest"
    )
    if manifest_entry["path"] != MANIFEST_RELATIVE:
        raise ValueError("unexpected W1 manifest path")
    manifest = core._mapping(
        core._load(project_root / manifest_entry["path"]), "manifest document"
    )
    _validate_manifest_contract(manifest, boundary)
    tooling = core._mapping(boundary.get("tooling"), "tooling")
    for name in core.TOOLING_KEYS:
        core._checked_file_entry(
            project_root,
            {"path": tooling.get(name), "sha256": tooling.get(f"{name}_sha256")},
            f"tooling.{name}",
        )
    freeze = core._mapping(boundary.get("execution_freeze"), "execution_freeze")
    if core._json_sha256(EXPECTED_GATES) != core._digest(
        freeze.get("development_gates_sha256"), "development_gates_sha256"
    ):
        raise ValueError("W1 development-gate hash mismatch")
    return {
        "status": boundary["status"],
        "candidate": candidate,
        "control": control,
        "opponents": opponents,
        "manifest": manifest_entry,
        "registry_sha256": registry_hash,
        "effective_scenarios_sha256": effective_sha,
        "seeds_executed": 0,
    }


def _validate_lifecycle(
    boundary: Mapping[str, Any], registry: Mapping[str, Any]
) -> list[int]:
    if boundary.get("status") != "DEVELOPMENT_OPEN_AUTHORIZED":
        raise ValueError("W1 seed pools remain CLOSED; development execution is forbidden")
    seeds = _validate_pool_contract(boundary, registry, opened=True)
    opened_at = _utc_datetime(
        boundary.get("development_opened_at_utc"), "development_opened_at_utc"
    )
    if boundary.get("opening_authority") != OPENING_AUTHORITY:
        raise ValueError("W1 opening authority is not the exact independent-audit authority")
    reservations = core._mapping(
        registry.get("next_boundary_reservations"), "registry reservations"
    )
    registered = core._mapping(reservations.get(DEVELOPMENT_KEY), DEVELOPMENT_KEY)
    if registered.get("opened_at_utc") != boundary.get("development_opened_at_utc"):
        raise ValueError("W1 registry/boundary opening timestamps differ")
    _utc_datetime(registered.get("opened_at_utc"), "registry development opened_at_utc")
    if opened_at != _utc_datetime(registered["opened_at_utc"], "registry opened_at_utc"):
        raise ValueError("W1 opening timestamps are not identical")
    return seeds


def _validate_open_delta(
    project_root: Path,
    boundary: Mapping[str, Any],
    registry: Mapping[str, Any],
    implementation_commit: str,
) -> None:
    base_boundary, _ = core._git_json_blob(
        project_root, implementation_commit, BOUNDARY_RELATIVE, "W1 closed boundary"
    )
    base_registry, base_registry_sha = core._git_json_blob(
        project_root, implementation_commit, REGISTRY_RELATIVE, "W1 closed registry"
    )
    if base_boundary.get("status") != "CLOSED_PENDING_INDEPENDENT_AUDIT":
        raise ValueError("W1 implementation boundary was not CLOSED")
    if base_boundary.get("seed_registry_sha256") != base_registry_sha:
        raise ValueError("W1 implementation registry self-hash mismatch")
    boundary_excluded = (
        "implementation_commit",
        "status",
        "pools.development.status",
        "development_opened_at_utc",
        "opening_authority",
    )
    registry_excluded = (
        f"next_boundary_reservations.{DEVELOPMENT_KEY}.status",
        f"next_boundary_reservations.{DEVELOPMENT_KEY}.opened",
        f"next_boundary_reservations.{DEVELOPMENT_KEY}.opened_at_utc",
    )
    if core._without_paths(base_boundary, boundary_excluded) != core._without_paths(
        boundary, boundary_excluded
    ):
        raise ValueError("W1 boundary changed beyond lifecycle-only fields")
    if core._without_paths(base_registry, registry_excluded) != core._without_paths(
        registry, registry_excluded
    ):
        raise ValueError("W1 registry changed beyond lifecycle-only fields")


def _frozen_plan(project_root: Path, boundary_path: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    boundary_path = boundary_path.resolve()
    if core._relative_path(project_root, boundary_path, "boundary") != BOUNDARY_RELATIVE:
        raise ValueError("unexpected W1 boundary path")
    boundary = core._mapping(core._load(boundary_path), "boundary")
    if boundary.get("status") != "DEVELOPMENT_OPEN_AUTHORIZED":
        raise ValueError("W1 seed pools remain CLOSED; development execution is forbidden")
    if boundary.get("implementation_commit") == PENDING_IMPLEMENTATION_COMMIT:
        raise ValueError("W1 implementation commit is not frozen")
    implementation_commit = core._commit(
        boundary.get("implementation_commit"), "implementation_commit"
    )
    registry_path = project_root / REGISTRY_RELATIVE
    registry_sha = core._digest(
        boundary.get("seed_registry_sha256"), "seed_registry_sha256"
    )
    if boundary.get("seed_registry") != REGISTRY_RELATIVE or core._sha256(registry_path) != registry_sha:
        raise ValueError("W1 registry path/hash mismatch")
    registry = core._mapping(core._load(registry_path), "registry")
    _validate_open_delta(project_root, boundary, registry, implementation_commit)
    seeds = _validate_lifecycle(boundary, registry)
    _validate_gate_contract(boundary)

    scenario = core._checked_file_entry(
        project_root, core._mapping(boundary.get("scenario_config"), "scenario"), "scenario"
    )
    scenario_doc = core._mapping(core._load(project_root / scenario["path"]), "scenario doc")
    if scenario["path"] != SCENARIO_RELATIVE or scenario_doc != {"scenarios": {"default": {}}}:
        raise ValueError("W1 scenario config is not exact")
    default_override: dict[str, Any] = {}
    effective = {"default": core._effective_configuration(default_override, None)}
    effective_sha = core._json_sha256(effective)
    if effective_sha != core._digest(
        boundary.get("expected_effective_scenarios_sha256"), "effective scenarios"
    ):
        raise ValueError("W1 effective scenario hash mismatch")

    candidate = core._checked_file_entry(
        project_root, core._mapping(boundary.get("candidate"), "candidate"), "candidate"
    )
    control = core._checked_file_entry(
        project_root, core._mapping(boundary.get("control"), "control"), "control"
    )
    if boundary.get("candidate") != CANDIDATE_ENTRY or boundary.get("control") != CONTROL_ENTRY:
        raise ValueError("W1 candidate/control identity is not exact")
    raw_opponents = boundary.get("opponents")
    if not isinstance(raw_opponents, list) or len(raw_opponents) != 6:
        raise ValueError("W1 requires exactly six external opponents")
    opponents: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_opponents):
        mapping = core._mapping(raw, f"opponents[{index}]")
        checked = core._checked_file_entry(project_root, mapping, f"opponents[{index}]")
        identity = mapping.get("identity")
        if not isinstance(identity, str):
            raise TypeError("W1 opponent identity is missing")
        opponents.append({**checked, "identity": identity})
    _validate_opponent_contract(opponents, control)
    _validate_single_delta_prefix(project_root)

    manifest_entry = core._checked_file_entry(
        project_root, core._mapping(boundary.get("manifest"), "manifest"), "manifest"
    )
    manifest = core._mapping(
        core._load(project_root / manifest_entry["path"]), "manifest document"
    )
    _validate_manifest_contract(manifest, boundary)
    tooling_config = core._mapping(boundary.get("tooling"), "tooling")
    tooling: dict[str, dict[str, Any]] = {}
    for name in core.TOOLING_KEYS:
        tooling[name] = core._checked_file_entry(
            project_root,
            {"path": tooling_config.get(name), "sha256": tooling_config.get(f"{name}_sha256")},
            f"tooling.{name}",
        )
    freeze = core._mapping(boundary.get("execution_freeze"), "execution_freeze")
    gates_sha = core._json_sha256(EXPECTED_GATES)
    if gates_sha != core._digest(
        freeze.get("development_gates_sha256"), "development_gates_sha256"
    ):
        raise ValueError("W1 development gate hash mismatch")
    frozen_files = {
        name: core._checked_file_entry(
            project_root,
            core._mapping(freeze.get(name), f"execution_freeze.{name}"),
            f"execution_freeze.{name}",
        )
        for name in ("third_party_license", "third_party_attribution", "runtime_replay")
    }
    frozen_files["manifest"] = manifest_entry
    runtime_entry = core._mapping(freeze.get("runtime_replay"), "runtime_replay")
    if (
        runtime_entry.get("player") != 0
        or runtime_entry.get("observations") != 720
        or runtime_entry.get("recorded_actions") != 719
    ):
        raise ValueError("W1 runtime replay player/count contract mismatch")
    artifacts = core._mapping(freeze.get("artifacts"), "artifacts")
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
        raise ValueError("W1 artifact contract is incomplete")
    if artifacts["candidate_start_receipt"] == artifacts["control_start_receipt"]:
        raise ValueError("W1 candidate/control must have separate outer receipts")

    opponent_paths = [entry["path"] for entry in opponents]
    implementation_paths = {
        candidate["path"],
        control["path"],
        *opponent_paths,
        *[entry["path"] for entry in tooling.values()],
        *[entry["path"] for entry in frozen_files.values()],
    }
    execution_paths = {BOUNDARY_RELATIVE, REGISTRY_RELATIVE, SCENARIO_RELATIVE}
    allowed = {str(value) for value in artifacts.values()}
    allowed.update(
        core._runner_receipt_relative(str(artifacts[f"{lane}_report"]))
        for lane in ("candidate", "control")
    )
    allowed.add(core._runtime_receipt_relative(str(artifacts["runtime_report"])))
    git_freeze = core._verify_git_freeze(
        project_root, implementation_commit, implementation_paths, execution_paths, allowed
    )
    cells = {
        ("default", opponent, seed, seat)
        for opponent in opponent_paths
        for seed in seeds
        for seat in (0, 1)
    }
    if len(cells) != 192:
        raise ValueError("W1 development must derive exactly 192 cells per lane")
    return {
        "boundary": dict(boundary),
        "boundary_file": {
            "path": BOUNDARY_RELATIVE,
            "sha256": core._sha256(boundary_path),
            "bytes": boundary_path.stat().st_size,
        },
        "registry_file": {
            "path": REGISTRY_RELATIVE,
            "sha256": registry_sha,
            "bytes": registry_path.stat().st_size,
        },
        "scenario_file": scenario,
        "tooling": tooling,
        "third_party": frozen_files,
        "runtime_replay": {**frozen_files["runtime_replay"], "player": 0},
        "runtime_player": 0,
        "development_gates_sha256": gates_sha,
        "implementation_commit": git_freeze["implementation_commit"],
        "execution_head": git_freeze["execution_head"],
        "candidate": candidate,
        "control": control,
        "opponents": opponents,
        "opponent_paths": opponent_paths,
        "opponent_hashes": {entry["path"]: entry["sha256"] for entry in opponents},
        "seeds": seeds,
        "default_override": default_override,
        "effective_scenarios": effective,
        "effective_scenarios_sha256": effective_sha,
        "cell_keys": cells,
        "artifacts": dict(artifacts),
        "workers_per_lane": 6,
    }


def run_development_lane(project_root: Path, boundary_path: Path, lane: str) -> dict[str, Any]:
    original = core._frozen_plan
    core._frozen_plan = _frozen_plan
    try:
        return core.run_development_lane(project_root, boundary_path, lane, 6)
    finally:
        core._frozen_plan = original


def _runtime_receipt(plan: Mapping[str, Any]) -> dict[str, Any]:
    command = [
        "python",
        "-m",
        "kaggriculture_lab.evaluation.fa05_wool_gate",
        "--boundary",
        BOUNDARY_RELATIVE,
        "--generate-runtime",
    ]
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
        "observations": 720,
        "recorded_actions": 719,
        "command": command,
        "generator": plan["tooling"]["runtime_generator"],
        "tracked_provenance": {
            "implementation_commit": plan["implementation_commit"],
            "execution_head": plan["execution_head"],
            "source": plan["candidate"],
            "replay": plan["runtime_replay"],
            "player": 0,
        },
    }


def generate_runtime(project_root: Path, boundary_path: Path) -> dict[str, Any]:
    from kaggriculture_lab.evaluation.fa05_runtime import benchmark_player_replay

    plan = _frozen_plan(project_root.resolve(), boundary_path.resolve())
    output = project_root / plan["artifacts"]["runtime_report"]
    receipt_relative = core._runtime_receipt_relative(
        str(plan["artifacts"]["runtime_report"])
    )
    receipt_path = project_root / receipt_relative
    if output.exists() or receipt_path.exists():
        raise ValueError("W1 runtime evidence already exists; refusing overwrite")
    receipt = _runtime_receipt(plan)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    report = benchmark_player_replay(
        project_root / plan["candidate"]["path"],
        project_root / plan["runtime_replay"]["path"],
        0,
    )
    report.update(
        {
            "schema_version": 2,
            "created_at_utc": datetime.now(UTC).isoformat(),
            "python": sys.version,
            "platform": platform.platform(),
            "git_head": plan["execution_head"],
            "tracked_tree_clean": True,
            "source_sha256": plan["candidate"]["sha256"],
            "source": plan["candidate"]["path"],
            "replay_sha256": plan["runtime_replay"]["sha256"],
            "replay": plan["runtime_replay"]["path"],
            "player": 0,
            "observations": 720,
            "recorded_actions": 719,
            "command": receipt["command"],
            "generator": receipt["generator"],
            "tracked_provenance": receipt["tracked_provenance"],
            "generation_receipt": {
                "path": receipt_relative,
                "sha256": core._sha256(receipt_path),
            },
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _validate_lane_receipt_schema(
    project_root: Path,
    lane: str,
    source: Mapping[str, Any],
    validated: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> None:
    outer = core._mapping(
        core._load(project_root / str(validated["path"])), f"{lane} outer receipt"
    )
    expected_outer_keys = set(core._outer_receipt_payload(lane, 6, source, plan))
    if set(outer) != expected_outer_keys or outer.get("schema_version") != 2:
        raise ValueError(f"{lane} outer receipt schema/keyset mismatch")
    outer_time = _utc_datetime(
        outer.get("created_at_utc"), f"{lane} outer receipt created_at_utc"
    )
    runner_link = core._mapping(validated.get("runner_receipt"), "runner receipt link")
    runner = core._mapping(
        core._load(project_root / str(runner_link["path"])), f"{lane} runner receipt"
    )
    expected_runner_keys = {
        "schema_version",
        "started_at_utc",
        "git_head_at_start",
        "candidate",
        "candidate_path",
        "candidate_sha256_at_start",
        "opponents",
        "opponent_paths",
        "opponent_sha256_at_start",
        "seeds",
        "seat_policy",
        "workers",
        "scenario_overrides",
        "effective_scenarios",
        "effective_scenarios_sha256",
    }
    if set(runner) != expected_runner_keys or runner.get("schema_version") != 1:
        raise ValueError(f"{lane} runner receipt schema/keyset mismatch")
    runner_time = _utc_datetime(
        runner.get("started_at_utc"), f"{lane} runner receipt started_at_utc"
    )
    if runner_time < outer_time:
        raise ValueError(f"{lane} runner receipt predates its outer receipt")


def _validate_candidate_metrics(
    report: Mapping[str, Any],
    rows: Mapping[tuple[str, str, int, int], Mapping[str, Any]],
) -> dict[tuple[str, str, int, int], dict[str, int]]:
    validated: dict[tuple[str, str, int, int], dict[str, int]] = {}
    totals = {name: 0 for name in EXPECTED_METRIC_KEYS}
    for key, row in rows.items():
        metrics = core._mapping(row.get("candidate_metrics"), f"candidate metrics {key}")
        values = _validate_metric_mapping(metrics, str(key))
        for name, value in values.items():
            totals[name] += value
        validated[key] = values
    summary = core._mapping(report.get("summary"), "candidate summary")
    if summary.get("candidate_metrics_games") != 192:
        raise ValueError("candidate summary must report metrics for all 192 raw games")
    summary_totals = core._mapping(
        summary.get("candidate_metrics_total"), "candidate summary metric totals"
    )
    if dict(summary_totals) != totals:
        raise ValueError("candidate summary metric totals differ from raw-row recomputation")
    return validated


def _validate_metric_mapping(
    metrics: Mapping[str, Any], label: str
) -> dict[str, int]:
    if set(metrics) != EXPECTED_METRIC_KEYS:
        raise ValueError(f"candidate metrics keyset mismatch for cell {label}")
    values = {
        name: _exact_nonnegative_int(metrics.get(name), f"{label}.{name}")
        for name in EXPECTED_METRIC_KEYS
    }
    if values["create_observed_units"] - values["release_observed_units"] != values["pending_end"]:
        raise ValueError(f"reserve conservation mismatch for cell {label}")
    if values["release_observed_units"] != values["causal_completed_reserve_release_units"]:
        raise ValueError(f"causal release completion mismatch for cell {label}")
    if values["create_observed_units"] > values["create_requested_units"]:
        raise ValueError(f"observed create exceeds requested create for cell {label}")
    if values["release_observed_units"] > values["release_requested_units"]:
        raise ValueError(f"observed release exceeds requested release for cell {label}")
    return values


def _validate_cell_partition(
    keys_by_identity: Mapping[str, list[tuple[str, str, int, int]]]
) -> None:
    expected = WEAK_IDENTITIES | PROTECTED_IDENTITIES | {R145_IDENTITY}
    if set(keys_by_identity) != expected:
        raise ValueError("W1 cell partition identities are not exact")
    if any(len(keys_by_identity[identity]) != 32 for identity in expected):
        raise ValueError("W1 each opponent lane must contain exactly 32 cells")


def _outcome(row: Mapping[str, Any]) -> float:
    return core._outcome(row)


def _float_bits_equal(left: object, right: object) -> bool:
    left_value = core._finite_number(left, "left bit-exact numeric")
    right_value = core._finite_number(right, "right bit-exact numeric")
    return struct.pack("!d", left_value) == struct.pack("!d", right_value)


def _r7_p10(values: list[float], label: str) -> float:
    result = paired._percentile(values, 0.10)
    if result is None:
        raise ValueError(f"{label} has no values")
    return core._finite_number(result, label)


def _paired_group(
    keys: list[tuple[str, str, int, int]],
    candidate_rows: Mapping[tuple[str, str, int, int], Mapping[str, Any]],
    control_rows: Mapping[tuple[str, str, int, int], Mapping[str, Any]],
) -> dict[str, Any]:
    if not keys:
        raise ValueError("paired group is empty")
    match = [_outcome(candidate_rows[key]) - _outcome(control_rows[key]) for key in keys]
    money = [
        core._finite_number(candidate_rows[key]["candidate_money"], "candidate money")
        - core._finite_number(control_rows[key]["candidate_money"], "control money")
        for key in keys
    ]
    by_seed: dict[int, list[float]] = {}
    for key, value in zip(keys, match, strict=True):
        by_seed.setdefault(key[2], []).append(value)
    clusters = [statistics.fmean(values) for _, values in sorted(by_seed.items())]
    ci = paired._cluster_bootstrap_ci(clusters, 10_000, 0)
    if ci is None:
        raise ValueError("paired group seed-cluster bootstrap is empty")
    return {
        "cells": len(keys),
        "paired_match_delta": core._finite_number(statistics.fmean(match), "match delta"),
        "paired_money_delta": core._finite_number(statistics.fmean(money), "money delta"),
        "seed_cluster_count": len(clusters),
        "match_delta_seed_cluster_bootstrap_95": [
            core._finite_number(ci[0], "bootstrap lower"),
            core._finite_number(ci[1], "bootstrap upper"),
        ],
        "bootstrap_draws": 10_000,
        "bootstrap_random_seed": 0,
        "bootstrap_cluster_unit": "seed",
    }


def _validate_runtime_report(
    runtime: Mapping[str, Any], receipt: Mapping[str, Any], plan: Mapping[str, Any]
) -> None:
    expected_keys = {
        "schema_version", "created_at_utc", "python", "platform", "git_head",
        "tracked_tree_clean", "source", "source_sha256", "replay", "replay_sha256",
        "player", "observations", "recorded_actions", "recorded_action_offset",
        "recorded_action_matches", "recorded_action_differences", "step_provenance",
        "calls", "invalid_outputs", "p50_ms", "p95_ms", "p99_ms", "max_ms",
        "command", "generator", "tracked_provenance", "generation_receipt",
    }
    if set(runtime) != expected_keys or runtime.get("schema_version") != 2:
        raise ValueError("W1 runtime report schema/keyset mismatch")
    for label in ("p50_ms", "p95_ms", "p99_ms", "max_ms"):
        core._finite_nonnegative(runtime.get(label), f"runtime.{label}")
    for label, expected in (
        ("calls", 720), ("invalid_outputs", 0), ("player", 0),
        ("observations", 720), ("recorded_actions", 719),
        ("recorded_action_offset", 1),
    ):
        actual = runtime.get(label)
        if isinstance(actual, bool) or not isinstance(actual, int) or actual != expected:
            raise ValueError(f"runtime.{label} must be the exact integer {expected}")
    for label in ("recorded_action_matches", "recorded_action_differences"):
        _exact_nonnegative_int(runtime.get(label), f"runtime.{label}")
    if runtime["recorded_action_matches"] + runtime["recorded_action_differences"] != 719:
        raise ValueError("W1 runtime recorded-action accounting mismatch")
    _utc_datetime(runtime.get("created_at_utc"), "runtime.created_at_utc")
    if (
        runtime.get("git_head") != plan["execution_head"]
        or runtime.get("tracked_tree_clean") is not True
        or runtime.get("source_sha256") != plan["candidate"]["sha256"]
        or runtime.get("source") != plan["candidate"]["path"]
        or runtime.get("replay_sha256") != plan["runtime_replay"]["sha256"]
        or runtime.get("replay") != plan["runtime_replay"]["path"]
        or runtime.get("command") != receipt["command"]
        or runtime.get("generator") != receipt["generator"]
        or runtime.get("tracked_provenance") != receipt["tracked_provenance"]
    ):
        raise ValueError("W1 runtime provenance mismatch")
    if not runtime["p50_ms"] <= runtime["p95_ms"] <= runtime["p99_ms"] <= runtime["max_ms"]:
        raise ValueError("W1 runtime percentiles are not ordered")


def analyze(project_root: Path, boundary_path: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    plan = _frozen_plan(project_root, boundary_path.resolve())
    artifacts = plan["artifacts"]
    candidate_report = core._mapping(
        core._load(project_root / artifacts["candidate_report"]), "candidate report"
    )
    control_report = core._mapping(
        core._load(project_root / artifacts["control_report"]), "control report"
    )
    candidate_receipt = core._validate_receipt(
        project_root, candidate_report, "candidate", plan["candidate"], plan
    )
    control_receipt = core._validate_receipt(
        project_root, control_report, "control", plan["control"], plan
    )
    if candidate_receipt["path"] == control_receipt["path"]:
        raise ValueError("W1 candidate/control share an outer receipt")
    _validate_lane_receipt_schema(
        project_root, "candidate", plan["candidate"], candidate_receipt, plan
    )
    _validate_lane_receipt_schema(
        project_root, "control", plan["control"], control_receipt, plan
    )
    candidate_rows = core._validate_report(
        candidate_report, expected_agent=plan["candidate"], plan=plan,
        label="candidate report",
    )
    control_rows = core._validate_report(
        control_report, expected_agent=plan["control"], plan=plan,
        label="control report",
    )
    core._validate_environment_pairs(candidate_rows, control_rows)
    raw_metrics = _validate_candidate_metrics(candidate_report, candidate_rows)

    expected_contract = {
        "candidate_source_sha256": plan["candidate"]["sha256"],
        "control_source_sha256": plan["control"]["sha256"],
        "root_config": plan["boundary_file"],
        "scenario_config": plan["scenario_file"],
        "effective_scenarios_sha256": plan["effective_scenarios_sha256"],
        "opponent_source_sha256": plan["opponent_hashes"],
        "cell_keys": [list(key) for key in sorted(plan["cell_keys"])],
        "cell_count": 192,
    }
    paired_result = paired.compare_reports(
        candidate_report, control_report, bootstrap_draws=10_000,
        bootstrap_random_seed=0, expected_contract=expected_contract,
    )
    paired.require_gate_eligible(paired_result)

    identity_by_path = {entry["path"]: entry["identity"] for entry in plan["opponents"]}
    path_by_identity = {identity: path for path, identity in identity_by_path.items()}
    keys_by_identity = {
        identity: sorted(key for key in candidate_rows if key[1] == path)
        for identity, path in path_by_identity.items()
    }
    _validate_cell_partition(keys_by_identity)
    weak_keys = sorted(
        key for identity in WEAK_IDENTITIES for key in keys_by_identity[identity]
    )
    protected_keys = sorted(
        key for identity in PROTECTED_IDENTITIES for key in keys_by_identity[identity]
    )
    r145_keys = keys_by_identity[R145_IDENTITY]
    weak_result = _paired_group(weak_keys, candidate_rows, control_rows)
    r145_result = _paired_group(r145_keys, candidate_rows, control_rows)

    per_opponent: dict[str, dict[str, Any]] = {}
    for identity, keys in keys_by_identity.items():
        money = [
            core._finite_number(candidate_rows[key]["candidate_money"], f"{identity} money")
            for key in keys
        ]
        margins = [
            core._finite_number(candidate_rows[key]["candidate_money"], "candidate money")
            - core._finite_number(candidate_rows[key]["opponent_money"], "opponent money")
            for key in keys
        ]
        totals = {
            name: sum(raw_metrics[key][name] for key in keys)
            for name in EXPECTED_METRIC_KEYS
        }
        per_opponent[identity] = {
            "cells": len(keys),
            "candidate_money_mean": core._finite_number(
                statistics.fmean(money), f"{identity} candidate money mean"
            ),
            "candidate_money_r7_p10": _r7_p10(money, f"{identity} candidate money p10"),
            "candidate_absolute_margin_mean": core._finite_number(
                statistics.fmean(margins), f"{identity} absolute margin mean"
            ),
            "metrics_recomputed_from_raw_rows": totals,
        }

    protected_totals = {
        name: sum(raw_metrics[key][name] for key in protected_keys)
        for name in EXPECTED_METRIC_KEYS
    }
    protected_both_money_exact = all(
        _float_bits_equal(
            candidate_rows[key]["candidate_money"], control_rows[key]["candidate_money"]
        )
        and _float_bits_equal(
            candidate_rows[key]["opponent_money"], control_rows[key]["opponent_money"]
        )
        for key in protected_keys
    )
    protected_overlay_changes = (
        protected_totals["sell_suppressed_orders"] + protected_totals["release_orders"]
    )

    safety_names = (
        "fallback_count",
        "false_trigger_count",
        "blocked_release_units",
        "outside_allowed_action_diff",
        "candidate_caused_overflow_or_discard_units",
        "impossible_sell_units",
        "terminal_pending",
        "terminal_wool_remaining",
    )
    safety_totals = {
        name: sum(metrics[name] for metrics in raw_metrics.values()) for name in safety_names
    }

    runtime = core._mapping(
        core._load(project_root / artifacts["runtime_report"]), "runtime report"
    )
    runtime_link = core._mapping(runtime.get("generation_receipt"), "runtime receipt link")
    receipt_relative = core._runtime_receipt_relative(str(artifacts["runtime_report"]))
    receipt_path = project_root / receipt_relative
    if set(runtime_link) != {"path", "sha256"} or runtime_link.get("path") != receipt_relative:
        raise ValueError("W1 runtime receipt link mismatch")
    if runtime_link.get("sha256") != core._sha256(receipt_path):
        raise ValueError("W1 runtime receipt hash mismatch")
    runtime_receipt = core._mapping(core._load(receipt_path), "runtime receipt")
    expected_runtime_receipt = _runtime_receipt(plan)
    if set(runtime_receipt) != set(expected_runtime_receipt):
        raise ValueError("W1 runtime receipt keyset mismatch")
    receipt_time = _utc_datetime(
        runtime_receipt.get("created_at_utc"), "runtime receipt created_at_utc"
    )
    expected_runtime_receipt.pop("created_at_utc")
    if any(runtime_receipt.get(key) != value for key, value in expected_runtime_receipt.items()):
        raise ValueError("W1 runtime receipt contract mismatch")
    _validate_runtime_report(runtime, runtime_receipt, plan)
    if _utc_datetime(runtime["created_at_utc"], "runtime created_at_utc") < receipt_time:
        raise ValueError("W1 runtime report predates its receipt")

    weak_gate = EXPECTED_GATES["weak"]
    protected_gate = EXPECTED_GATES["protected"]
    r145_gate = EXPECTED_GATES["r145"]
    runtime_gate = EXPECTED_GATES["runtime"]
    checks = {
        "candidate_failures": candidate_report["summary"]["failed_raw_games"] == 0,
        "control_failures": control_report["summary"]["failed_raw_games"] == 0,
        "exact_cells": len(candidate_rows) == len(control_rows) == 192,
        "weak_exact_cells": weak_result["cells"] == weak_gate["exact_cells"],
        "weak_paired_match": weak_result["paired_match_delta"] > weak_gate["paired_match_delta_strict_gt"],
        "weak_bootstrap_lower": weak_result["match_delta_seed_cluster_bootstrap_95"][0] >= weak_gate["seed_cluster_bootstrap_95_lower_gte"],
        "weak_paired_money": weak_result["paired_money_delta"] >= weak_gate["paired_money_delta_gte"],
        "weak_each_money_mean": all(per_opponent[name]["candidate_money_mean"] > weak_gate["each_candidate_money_mean_strict_gt"] for name in WEAK_IDENTITIES),
        "weak_each_money_p10": all(per_opponent[name]["candidate_money_r7_p10"] > weak_gate["each_candidate_money_r7_p10_strict_gt"] for name in WEAK_IDENTITIES),
        "weak_each_create_observed": all(per_opponent[name]["metrics_recomputed_from_raw_rows"]["create_observed_units"] > 0 for name in WEAK_IDENTITIES),
        "weak_each_release_observed": all(per_opponent[name]["metrics_recomputed_from_raw_rows"]["release_observed_units"] > 0 for name in WEAK_IDENTITIES),
        "weak_each_causal_completed": all(per_opponent[name]["metrics_recomputed_from_raw_rows"]["causal_completed_reserve_release_units"] > 0 for name in WEAK_IDENTITIES),
        "protected_exact_cells": len(protected_keys) == protected_gate["exact_cells"],
        "protected_create_zero": protected_totals["create_observed_units"] == 0,
        "protected_release_zero": protected_totals["release_observed_units"] == 0,
        "protected_causal_zero": protected_totals["causal_completed_reserve_release_units"] == 0,
        "protected_overlay_zero": protected_overlay_changes == 0,
        "protected_action_diff_zero": protected_totals["protected_lane_action_diff"] == 0,
        "protected_action_reward_both_money_bit_exact": protected_both_money_exact,
        "r145_exact_cells": r145_result["cells"] == r145_gate["exact_cells"],
        "r145_paired_match": r145_result["paired_match_delta"] >= r145_gate["paired_match_delta_gte"],
        "r145_paired_money": r145_result["paired_money_delta"] >= r145_gate["paired_money_delta_gte"],
        "each_absolute_margin": all(row["candidate_absolute_margin_mean"] >= 0.0 for row in per_opponent.values()),
        "safety_counters_zero": all(value == 0 for value in safety_totals.values()),
        "runtime_calls": runtime["calls"] == runtime_gate["calls"],
        "runtime_invalid": runtime["invalid_outputs"] == runtime_gate["invalid_outputs"],
        "runtime_p95": runtime["p95_ms"] <= runtime_gate["p95_ms_max"],
        "runtime_p99": runtime["p99_ms"] <= runtime_gate["p99_ms_max"],
        "runtime_max": runtime["max_ms"] <= runtime_gate["absolute_ms_max"],
    }
    return {
        "schema_version": 1,
        "identity": "Fa05_W1_wool_glut_buffer_development_gate",
        "implementation_commit": plan["implementation_commit"],
        "execution_head": plan["execution_head"],
        "cells_per_lane": len(candidate_rows),
        "weak": weak_result,
        "protected": {
            "cells": len(protected_keys),
            "metrics_recomputed_from_raw_rows": protected_totals,
            "overlay_action_changes": protected_overlay_changes,
            "final_rewards_and_both_money_bit_exact": protected_both_money_exact,
            "action_vector_semantics": (
                "The frozen candidate is the exact G1 byte prefix plus one overlay; zero "
                "sell_suppressed_orders, release_orders, and outside_allowed_action_diff "
                "prove that overlay returned the G1 vector on protected cells."
            ),
        },
        "r145": r145_result,
        "per_opponent": per_opponent,
        "safety_totals_recomputed_from_raw_rows": safety_totals,
        "paired_contract": paired_result["contract"],
        "runtime": dict(runtime),
        "checks": checks,
        "development_pass": all(checks.values()),
        "release_policy": RELEASE_POLICY,
    }


def result_path(boundary_path: Path) -> str:
    boundary = core._load(boundary_path)
    freeze = core._mapping(boundary.get("execution_freeze"), "execution_freeze")
    return str(core._mapping(freeze.get("artifacts"), "artifacts")["analysis_report"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boundary", type=Path, required=True)
    parser.add_argument("--validate-closed", action="store_true")
    parser.add_argument("--run-lane", choices=("candidate", "control"))
    parser.add_argument("--generate-runtime", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    args = parser.parse_args()
    root = args.boundary.resolve().parent.parent
    selected = sum(
        (args.validate_closed, args.run_lane is not None, args.generate_runtime, args.analyze)
    )
    if selected != 1:
        parser.error("select exactly one mode")
    if args.validate_closed:
        result = validate_closed_design(root, args.boundary)
        print(json.dumps(result, sort_keys=True))
    elif args.run_lane:
        report = run_development_lane(root, args.boundary, args.run_lane)
        print(json.dumps({"lane": args.run_lane, "games": len(report["games"])}))
    elif args.generate_runtime:
        report = generate_runtime(root, args.boundary)
        print(json.dumps({"calls": report["calls"], "player": report["player"]}))
    else:
        result = analyze(root, args.boundary)
        output = root / result_path(args.boundary)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"development_pass": result["development_pass"], **result["checks"]}))
        if not result["development_pass"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
