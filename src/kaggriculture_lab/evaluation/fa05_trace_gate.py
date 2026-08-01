"""Strict frozen development gate for the Fa05 R145 trace-diversity candidate."""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kaggriculture_lab.evaluation import paired
from kaggriculture_lab.evaluation import top_trace_gate as core

BOUNDARY_RELATIVE = "configs/fa05_r145_trace_boundary.json"
OPENING_AUTHORITY = (
    "Independent auditor task 019fb8b8-7758-7860-9304-39eb4f06c65c "
    "authorizes only exact Fa05 development seeds 43000-43015."
)
DEVELOPMENT_KEY = "Fa05_R145_trace_guard_development"
TOP_TRACE_IDENTITIES = {
    "C135_chocolat",
    "R140_radiant",
    "R150_radiant",
    "R155_radiant",
}
FORMAL_IDENTITY = "formal_final_day_labor"
DIRECT_G1_IDENTITY = "Fa04_G1_sell_guard"
EXPECTED_OPPONENT_CONTRACT = {
    "C135_chocolat": (
        "experiments/source_snapshots/fa04_top_trace/C135.py",
        "13C88E1D9232F66A219AF0B66A36A46D622C2466856D191E57A8FDC42BC7C1EE",
    ),
    "R140_radiant": (
        "experiments/source_snapshots/fa04_top_trace/R140.py",
        "E4BDEDB791FC129AA73941D96BEA2C20709D9431A8C9628AB526EA186B0F4870",
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
    "Fa04_G1_sell_guard": (
        "experiments/source_snapshots/fa04_top_trace/G1_sell_guard.py",
        "81159A18DF3CD1A5CAABE5EDBBA0A597561775F77A49465FA39DF6802A706922",
    ),
}


def _utc_datetime(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be an ISO-8601 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO-8601 UTC timestamp") from exc
    if parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError(f"{label} must be UTC")
    return parsed


def _validate_opponent_contract(
    opponents: list[Mapping[str, Any]], control: Mapping[str, Any]
) -> None:
    actual_contract = {
        str(entry["identity"]): (entry["path"], entry["sha256"])
        for entry in opponents
    }
    if actual_contract != EXPECTED_OPPONENT_CONTRACT:
        raise ValueError("Fa05 opponent identity/path/hash contract is not exact")
    if (
        actual_contract[DIRECT_G1_IDENTITY]
        != (control["path"], control["sha256"])
        or any(
            actual_contract[identity] == (control["path"], control["sha256"])
            for identity in TOP_TRACE_IDENTITIES | {FORMAL_IDENTITY}
        )
    ):
        raise ValueError("Fa05 external/direct control lanes are not separated")


def _drop_paths(value: Mapping[str, Any], paths: tuple[str, ...]) -> dict[str, Any]:
    return core._without_paths(value, paths)


def _validate_lifecycle(
    boundary: Mapping[str, Any], registry: Mapping[str, Any]
) -> list[int]:
    if boundary.get("status") != "DEVELOPMENT_OPEN_AUTHORIZED":
        raise ValueError("Fa05 boundary is not open")
    pools = core._mapping(boundary.get("pools"), "boundary.pools")
    registered = core._mapping(
        registry.get("next_boundary_reservations"), "registry reservations"
    )
    development: list[int] | None = None
    for lane in ("development", "confirmation", "robustness"):
        pool = core._mapping(pools.get(lane), f"pools.{lane}")
        key = pool.get("registry_key")
        if not isinstance(key, str):
            raise TypeError(f"pools.{lane}.registry_key must be a string")
        actual = core._mapping(registered.get(key), f"registry.{key}")
        seeds = core._pool_range(pool, f"pools.{lane}")
        if seeds != core._pool_range(actual, f"registry.{key}"):
            raise ValueError(f"{lane} range mismatch")
        if lane == "development":
            if (
                pool.get("status") != "OPEN"
                or actual.get("status") != "OPEN"
                or actual.get("opened") is not True
                or actual.get("consumed") is not False
                or actual.get("evaluated_games") != 0
            ):
                raise ValueError("Fa05 development is not OPEN and unused")
            development = seeds
        elif (
            pool.get("status") != "CLOSED"
            or actual.get("status") != "CLOSED"
            or actual.get("opened") is not False
            or actual.get("consumed") is not False
            or actual.get("evaluated_games") != 0
        ):
            raise ValueError(f"Fa05 {lane} must stay CLOSED")
    if development != list(range(43000, 43016)):
        raise ValueError("Fa05 development seeds are not exact 43000-43015")
    opened_at = boundary.get("development_opened_at_utc")
    if not isinstance(opened_at, str) or "T" not in opened_at:
        raise ValueError("development_opened_at_utc is missing")
    _utc_datetime(opened_at, "development_opened_at_utc")
    if boundary.get("opening_authority") != OPENING_AUTHORITY:
        raise ValueError("opening authority is not exact")
    actual = core._mapping(
        registered.get(DEVELOPMENT_KEY), f"registry.{DEVELOPMENT_KEY}"
    )
    if actual.get("opened_at_utc") != opened_at:
        raise ValueError("registry/boundary opening time mismatch")
    return development


def _validate_open_delta(
    project_root: Path,
    boundary: Mapping[str, Any],
    registry: Mapping[str, Any],
    implementation_commit: str,
) -> None:
    base_boundary, _ = core._git_json_blob(
        project_root, implementation_commit, BOUNDARY_RELATIVE, "Fa05 implementation boundary"
    )
    registry_relative = str(boundary["seed_registry"])
    base_registry, base_registry_sha = core._git_json_blob(
        project_root, implementation_commit, registry_relative, "Fa05 implementation registry"
    )
    if base_boundary.get("status") != "CLOSED_PENDING_INDEPENDENT_AUDIT":
        raise ValueError("implementation boundary was not CLOSED")
    base_pool = core._mapping(
        core._mapping(base_boundary.get("pools"), "base pools").get("development"),
        "base development",
    )
    base_registered = core._mapping(
        core._mapping(
            base_registry.get("next_boundary_reservations"), "base registry"
        ).get(DEVELOPMENT_KEY),
        "base registered development",
    )
    if (
        base_pool.get("status") != "CLOSED"
        or base_registered.get("status") != "CLOSED"
        or base_registered.get("opened") is not False
        or "opened_at_utc" in base_registered
    ):
        raise ValueError("implementation seed pool was not CLOSED/unopened")
    if base_boundary.get("seed_registry_sha256") != base_registry_sha:
        raise ValueError("implementation registry self-hash mismatch")
    boundary_excluded = (
        "implementation_commit",
        "seed_registry_sha256",
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
    if _drop_paths(base_boundary, boundary_excluded) != _drop_paths(
        boundary, boundary_excluded
    ):
        raise ValueError("Fa05 boundary changed beyond lifecycle fields")
    if _drop_paths(base_registry, registry_excluded) != _drop_paths(
        registry, registry_excluded
    ):
        raise ValueError("Fa05 registry changed beyond lifecycle fields")


def _frozen_plan(project_root: Path, boundary_path: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    boundary_path = boundary_path.resolve()
    if core._relative_path(project_root, boundary_path, "boundary") != BOUNDARY_RELATIVE:
        raise ValueError("unexpected Fa05 boundary path")
    boundary = core._mapping(core._load(boundary_path), "boundary")
    implementation_commit = core._commit(
        boundary.get("implementation_commit"), "implementation_commit"
    )
    registry_relative = boundary.get("seed_registry")
    if not isinstance(registry_relative, str):
        raise TypeError("seed_registry must be a path")
    registry_path = project_root / registry_relative
    expected_registry_hash = core._digest(
        boundary.get("seed_registry_sha256"), "seed_registry_sha256"
    )
    if core._sha256(registry_path) != expected_registry_hash:
        raise ValueError("seed registry hash mismatch")
    registry = core._mapping(core._load(registry_path), "registry")
    _validate_open_delta(project_root, boundary, registry, implementation_commit)
    seeds = _validate_lifecycle(boundary, registry)

    scenario = core._checked_file_entry(
        project_root, core._mapping(boundary.get("scenario_config"), "scenario"), "scenario"
    )
    scenario_doc = core._mapping(core._load(project_root / scenario["path"]), "scenario doc")
    scenarios = core._mapping(scenario_doc.get("scenarios"), "scenarios")
    if set(scenarios) != {"default"}:
        raise ValueError("Fa05 development must use only default scenario")
    default_override = dict(core._mapping(scenarios["default"], "default"))
    effective = {"default": core._effective_configuration(default_override, None)}
    effective_sha = core._json_sha256(effective)
    if effective_sha != core._digest(
        boundary.get("expected_effective_scenarios_sha256"), "effective scenarios"
    ):
        raise ValueError("effective scenario hash mismatch")

    candidate = core._checked_file_entry(
        project_root, core._mapping(boundary.get("candidate"), "candidate"), "candidate"
    )
    control = core._checked_file_entry(
        project_root, core._mapping(boundary.get("control"), "control"), "control"
    )
    raw_opponents = boundary.get("opponents")
    if not isinstance(raw_opponents, list) or len(raw_opponents) != 6:
        raise ValueError("Fa05 requires six exact opponents")
    opponents: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_opponents):
        mapping = core._mapping(raw, f"opponents[{index}]")
        entry = core._checked_file_entry(project_root, mapping, f"opponents[{index}]")
        identity = mapping.get("identity")
        if not isinstance(identity, str):
            raise TypeError("opponent identity is missing")
        opponents.append({**entry, "identity": identity})
    _validate_opponent_contract(opponents, control)

    tooling_config = core._mapping(boundary.get("tooling"), "tooling")
    tooling: dict[str, dict[str, Any]] = {}
    for name in core.TOOLING_KEYS:
        tooling[name] = core._checked_file_entry(
            project_root,
            {"path": tooling_config.get(name), "sha256": tooling_config.get(f"{name}_sha256")},
            f"tooling.{name}",
        )
    gates = core._mapping(boundary.get("development_gates"), "development gates")
    gates_sha = core._json_sha256(gates)
    freeze = core._mapping(boundary.get("execution_freeze"), "execution freeze")
    if gates_sha != core._digest(
        freeze.get("development_gates_sha256"), "development gates sha"
    ):
        raise ValueError("development gate hash mismatch")
    third_party = {
        name: core._checked_file_entry(
            project_root,
            core._mapping(freeze.get(name), f"execution_freeze.{name}"),
            f"execution_freeze.{name}",
        )
        for name in ("third_party_license", "third_party_attribution")
    }
    runtime_entry = core._mapping(freeze.get("runtime_replay"), "runtime replay")
    runtime_replay = {
        **core._checked_file_entry(project_root, runtime_entry, "runtime replay"),
        "player": runtime_entry.get("player"),
        "observations": runtime_entry.get("observations"),
        "recorded_actions": runtime_entry.get("recorded_actions"),
        "tracking": runtime_entry.get("tracking"),
        "origin": runtime_entry.get("origin"),
        "acquisition_provenance": runtime_entry.get("acquisition_provenance"),
    }
    if (
        runtime_entry.get("player") != 1
        or runtime_entry.get("observations") != 720
        or runtime_entry.get("recorded_actions") != 719
        or runtime_entry.get("tracking") != "IMMUTABLE_LOCAL_EXTERNAL"
        or runtime_entry.get("origin")
        != "public Kaggle competition replay episode 89268002"
        or runtime_entry.get("acquisition_provenance")
        != "LOCAL_HASH_PINNED; REMOTE_RETRIEVAL_RECEIPT_REQUIRED_BEFORE_SAVERUN_OR_PUBLICATION"
    ):
        raise ValueError("Fa05 runtime replay player/count contract mismatch")
    artifacts = core._mapping(freeze.get("artifacts"), "artifacts")
    required = {
        "candidate_report",
        "control_report",
        "candidate_start_receipt",
        "control_start_receipt",
        "runtime_report",
        "analysis_report",
    }
    if set(artifacts) != required:
        raise ValueError("Fa05 artifacts are incomplete")
    design = core._mapping(boundary.get("development_design"), "development design")
    if design != {
        "scenarios": ["default"],
        "seeds": "43000-43015",
        "seats": [0, 1],
        "opponents": 6,
        "exact_cells_per_lane": 192,
        "workers_per_lane": 6,
        "separate_start_receipts_required": True,
    }:
        raise ValueError("Fa05 development design is not exact")
    opponent_paths = [entry["path"] for entry in opponents]
    implementation_paths = {
        candidate["path"], control["path"], *opponent_paths,
        *[entry["path"] for entry in tooling.values()],
        *[entry["path"] for entry in third_party.values()],
    }
    execution_paths = {BOUNDARY_RELATIVE, registry_relative, scenario["path"]}
    allowed = {str(value) for value in artifacts.values()}
    allowed.update(core._runner_receipt_relative(str(artifacts[f"{lane}_report"])) for lane in ("candidate", "control"))
    allowed.add(core._runtime_receipt_relative(str(artifacts["runtime_report"])))
    git_freeze = core._verify_git_freeze(
        project_root, implementation_commit, implementation_paths, execution_paths, allowed
    )
    cells = {
        ("default", opponent, seed, seat)
        for opponent in opponent_paths for seed in seeds for seat in (0, 1)
    }
    if len(cells) != 192:
        raise ValueError("Fa05 must derive exactly 192 cells")
    return {
        "boundary": dict(boundary),
        "boundary_file": {"path": BOUNDARY_RELATIVE, "sha256": core._sha256(boundary_path), "bytes": boundary_path.stat().st_size},
        "registry_file": {"path": registry_relative, "sha256": expected_registry_hash, "bytes": registry_path.stat().st_size},
        "scenario_file": scenario,
        "tooling": tooling,
        "third_party": third_party,
        "runtime_replay": runtime_replay,
        "runtime_player": 1,
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
        "kaggriculture_lab.evaluation.fa05_trace_gate",
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
        "player": 1,
        "observations": 720,
        "recorded_actions": 719,
        "step_reconstruction": {
            "target_player": 1,
            "shared_step_source_player": 0,
            "only_fill_when_missing": True,
            "required_observed_steps": "0-719_exact_unique",
            "preserve_player_and_private": True,
        },
        "command": command,
        "generator": plan["tooling"]["runtime_generator"],
        "tracked_provenance": {
            "implementation_commit": plan["implementation_commit"],
            "execution_head": plan["execution_head"],
            "source": plan["candidate"],
            "replay": plan["runtime_replay"],
            "player": 1,
        },
    }


def generate_runtime(project_root: Path, boundary_path: Path) -> dict[str, Any]:
    from kaggriculture_lab.evaluation.fa05_runtime import benchmark_player_replay

    plan = _frozen_plan(project_root.resolve(), boundary_path.resolve())
    output = project_root / plan["artifacts"]["runtime_report"]
    receipt_path = project_root / core._runtime_receipt_relative(str(plan["artifacts"]["runtime_report"]))
    if output.exists() or receipt_path.exists():
        raise ValueError("Fa05 runtime evidence already exists")
    receipt = _runtime_receipt(plan)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    report = benchmark_player_replay(
        project_root / plan["candidate"]["path"],
        project_root / plan["runtime_replay"]["path"],
        1,
    )
    report.update({
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
        "player": 1,
        "observations": 720,
        "recorded_actions": 719,
        "command": receipt["command"],
        "generator": receipt["generator"],
        "tracked_provenance": receipt["tracked_provenance"],
        "generation_receipt": {
            "path": core._runtime_receipt_relative(str(plan["artifacts"]["runtime_report"])),
            "sha256": core._sha256(receipt_path),
        },
    })
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _outcome(row: Mapping[str, Any]) -> float:
    return core._outcome(row)


def _finite_difference(left: object, right: object, label: str) -> float:
    left_number = core._finite_number(left, f"{label} left operand")
    right_number = core._finite_number(right, f"{label} right operand")
    return core._finite_number(left_number - right_number, label)


def _finite_mean(values: list[float], label: str) -> float:
    return core._finite_number(statistics.mean(values), label)


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
    expected_outer_keys = set(
        core._outer_receipt_payload(
            lane, int(validated["workers"]), source, plan
        )
    )
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


def _validate_runtime_report(
    runtime: Mapping[str, Any], receipt: Mapping[str, Any], plan: Mapping[str, Any]
) -> None:
    expected_keys = {
        "schema_version",
        "created_at_utc",
        "python",
        "platform",
        "git_head",
        "tracked_tree_clean",
        "source",
        "source_sha256",
        "replay",
        "replay_sha256",
        "player",
        "observations",
        "recorded_actions",
        "recorded_action_offset",
        "recorded_action_matches",
        "recorded_action_differences",
        "step_provenance",
        "calls",
        "invalid_outputs",
        "p50_ms",
        "p95_ms",
        "p99_ms",
        "max_ms",
        "command",
        "generator",
        "tracked_provenance",
        "generation_receipt",
    }
    if set(runtime) != expected_keys or runtime.get("schema_version") != 2:
        raise ValueError("Fa05 runtime report schema/keyset mismatch")
    for label in ("p50_ms", "p95_ms", "p99_ms", "max_ms"):
        core._finite_nonnegative(runtime.get(label), f"runtime.{label}")
    for label, expected in (
        ("calls", 720),
        ("invalid_outputs", 0),
        ("player", 1),
        ("observations", 720),
        ("recorded_actions", 719),
        ("recorded_action_offset", 1),
    ):
        actual = runtime.get(label)
        if isinstance(actual, bool) or not isinstance(actual, int) or actual != expected:
            raise ValueError(f"runtime.{label} must be the exact integer {expected}")
    for label in ("recorded_action_matches", "recorded_action_differences"):
        actual = runtime.get(label)
        if isinstance(actual, bool) or not isinstance(actual, int) or actual < 0:
            raise ValueError(f"runtime.{label} must be a nonnegative integer")
    if (
        runtime["recorded_action_matches"]
        + runtime["recorded_action_differences"]
        != 719
    ):
        raise ValueError("Fa05 runtime recorded action accounting mismatch")
    step_provenance = core._mapping(
        runtime.get("step_provenance"), "runtime.step_provenance"
    )
    if step_provenance != {
        "method": "copy_player_observation_and_fill_only_missing_step_from_player0",
        "observed_steps": list(range(720)),
        "observed_step_start": 0,
        "observed_step_end": 719,
        "unique_observed_steps": 720,
        "injected_missing_steps": 720,
        "preserved_existing_steps": 0,
        "player_and_private_preserved": True,
    }:
        raise ValueError("Fa05 runtime step reconstruction provenance mismatch")
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
        raise ValueError("Fa05 runtime provenance mismatch")
    if not (
        runtime["p50_ms"]
        <= runtime["p95_ms"]
        <= runtime["p99_ms"]
        <= runtime["max_ms"]
    ):
        raise ValueError("Fa05 runtime percentiles are not ordered")


def analyze(project_root: Path, boundary_path: Path) -> dict[str, Any]:
    plan = _frozen_plan(project_root.resolve(), boundary_path.resolve())
    artifacts = plan["artifacts"]
    candidate_report = core._mapping(core._load(project_root / artifacts["candidate_report"]), "candidate report")
    control_report = core._mapping(core._load(project_root / artifacts["control_report"]), "control report")
    candidate_receipt = core._validate_receipt(project_root, candidate_report, "candidate", plan["candidate"], plan)
    control_receipt = core._validate_receipt(project_root, control_report, "control", plan["control"], plan)
    if candidate_receipt["path"] == control_receipt["path"]:
        raise ValueError("Fa05 candidate/control share an outer receipt")
    _validate_lane_receipt_schema(
        project_root, "candidate", plan["candidate"], candidate_receipt, plan
    )
    _validate_lane_receipt_schema(
        project_root, "control", plan["control"], control_receipt, plan
    )
    candidate_rows = core._validate_report(candidate_report, expected_agent=plan["candidate"], plan=plan, label="candidate report")
    control_rows = core._validate_report(control_report, expected_agent=plan["control"], plan=plan, label="control report")
    core._validate_environment_pairs(candidate_rows, control_rows)
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
        candidate_report,
        control_report,
        expected_contract=expected_contract,
    )
    paired.require_gate_eligible(paired_result)
    identity_by_path = {entry["path"]: entry["identity"] for entry in plan["opponents"]}
    per_opponent: dict[str, dict[str, float | int]] = {}
    for path, identity in identity_by_path.items():
        keys = [key for key in candidate_rows if key[1] == path]
        candidate_outcomes = [_outcome(candidate_rows[key]) for key in keys]
        control_outcomes = [_outcome(control_rows[key]) for key in keys]
        candidate_margins = [
            _finite_difference(
                candidate_rows[key]["candidate_money"],
                candidate_rows[key]["opponent_money"],
                f"{identity} candidate margin",
            )
            for key in keys
        ]
        control_margins = [
            _finite_difference(
                control_rows[key]["candidate_money"],
                control_rows[key]["opponent_money"],
                f"{identity} control margin",
            )
            for key in keys
        ]
        deltas = [
            _finite_difference(
                candidate_outcomes[i],
                control_outcomes[i],
                f"{identity} paired match delta",
            )
            for i in range(len(keys))
        ]
        money_deltas = [
            _finite_difference(
                candidate_rows[key]["candidate_money"],
                control_rows[key]["candidate_money"],
                f"{identity} paired money delta",
            )
            for key in keys
        ]
        per_opponent[identity] = {
            "games": len(keys),
            "candidate_match_score": _finite_mean(
                candidate_outcomes, f"{identity} candidate match score"
            ),
            "control_match_score": _finite_mean(
                control_outcomes, f"{identity} control match score"
            ),
            "candidate_margin_mean": _finite_mean(
                candidate_margins, f"{identity} candidate margin mean"
            ),
            "control_margin_mean": _finite_mean(
                control_margins, f"{identity} control margin mean"
            ),
            "paired_match_delta": _finite_mean(
                deltas, f"{identity} paired match delta mean"
            ),
            "paired_money_delta": _finite_mean(
                money_deltas, f"{identity} paired money delta mean"
            ),
            "rescue_cells": sum(control_outcomes[i] == 0 and candidate_outcomes[i] == 1 for i in range(len(keys))),
            "new_loss_cells": sum(control_outcomes[i] == 1 and candidate_outcomes[i] == 0 for i in range(len(keys))),
        }
    top = [per_opponent[name] for name in sorted(TOP_TRACE_IDENTITIES)]
    external = [per_opponent[name] for name in sorted(TOP_TRACE_IDENTITIES | {FORMAL_IDENTITY})]
    runtime = core._mapping(core._load(project_root / artifacts["runtime_report"]), "runtime")
    runtime_link = core._mapping(runtime.get("generation_receipt"), "runtime receipt link")
    if set(runtime_link) != {"path", "sha256"}:
        raise ValueError("Fa05 runtime receipt link schema mismatch")
    runtime_receipt_relative = core._runtime_receipt_relative(
        str(artifacts["runtime_report"])
    )
    runtime_receipt_path = project_root / runtime_receipt_relative
    if runtime_link.get("path") != runtime_receipt_relative:
        raise ValueError("Fa05 runtime receipt path mismatch")
    if runtime_link.get("sha256") != core._sha256(runtime_receipt_path):
        raise ValueError("Fa05 runtime receipt hash mismatch")
    receipt = core._mapping(core._load(runtime_receipt_path), "runtime receipt")
    expected_receipt = _runtime_receipt(plan)
    if set(receipt) != set(expected_receipt) or receipt.get("schema_version") != 1:
        raise ValueError("Fa05 runtime receipt schema/keyset mismatch")
    receipt_time = _utc_datetime(
        receipt.get("created_at_utc"), "runtime receipt created_at_utc"
    )
    expected_receipt.pop("created_at_utc")
    if any(receipt.get(key) != value for key, value in expected_receipt.items()):
        raise ValueError("Fa05 runtime receipt contract mismatch")
    _validate_runtime_report(runtime, receipt, plan)
    if _utc_datetime(runtime["created_at_utc"], "runtime created_at_utc") < receipt_time:
        raise ValueError("Fa05 runtime report predates its receipt")
    gates = core._mapping(plan["boundary"].get("development_gates"), "gates")
    top_score = _finite_mean(
        [float(row["candidate_match_score"]) for row in top],
        "top trace aggregate match score",
    )
    external_match = _finite_mean(
        [float(row["paired_match_delta"]) for row in external],
        "external paired match delta",
    )
    external_money = _finite_mean(
        [float(row["paired_money_delta"]) for row in external],
        "external paired money delta",
    )
    complementarity = any(
        float(row["paired_match_delta"]) >= gates["minimum_complementarity_lane_match_delta"]
        and float(row["paired_money_delta"]) > gates["minimum_complementarity_lane_money_delta"]
        for row in top
    )
    checks = {
        "candidate_failures": candidate_report["summary"]["failed_raw_games"] == 0,
        "control_failures": control_report["summary"]["failed_raw_games"] == 0,
        "exact_cells": len(candidate_rows) == len(control_rows) == 192,
        "top_trace_match": top_score >= gates["minimum_candidate_top_trace_match_score"],
        "each_top_trace_match": all(float(row["candidate_match_score"]) > gates["minimum_each_top_trace_match_score"] for row in top),
        "formal_match": float(per_opponent[FORMAL_IDENTITY]["candidate_match_score"]) > gates["minimum_formal_match_score"],
        "direct_g1_match": float(per_opponent[DIRECT_G1_IDENTITY]["candidate_match_score"]) > gates["minimum_direct_g1_match_score"],
        "direct_g1_margin": float(per_opponent[DIRECT_G1_IDENTITY]["candidate_margin_mean"]) >= gates["minimum_direct_g1_margin"],
        "each_margin": all(float(row["candidate_margin_mean"]) >= gates["minimum_each_opponent_mean_margin"] for row in per_opponent.values()),
        "paired_external_match": external_match >= gates["minimum_paired_external_match_delta"],
        "paired_external_money": external_money >= gates["minimum_paired_external_money_delta"],
        "complementarity": complementarity,
        "runtime_calls": runtime["calls"] == 720,
        "runtime_invalid": runtime["invalid_outputs"] == gates["invalid_outputs"],
        "runtime_p95": runtime["p95_ms"] <= gates["runtime_p95_ms_max"],
        "runtime_p99": runtime["p99_ms"] <= gates["runtime_p99_ms_max"],
        "runtime_max": runtime["max_ms"] <= gates["runtime_absolute_ms_max"],
    }
    return {
        "schema_version": 1,
        "implementation_commit": plan["implementation_commit"],
        "execution_head": plan["execution_head"],
        "cells_per_lane": len(candidate_rows),
        "top_trace_match_score": top_score,
        "paired_external_match_delta": external_match,
        "paired_external_money_delta": external_money,
        "per_opponent": per_opponent,
        "balance": {
            "seeds": len(plan["seeds"]),
            "seats": [0, 1],
            "cells_per_opponent": 32,
            "candidate_cells": len(candidate_rows),
            "control_cells": len(control_rows),
        },
        "paired_contract": paired_result["contract"],
        "runtime": dict(runtime),
        "checks": checks,
        "development_pass": all(checks.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run/analyze frozen Fa05 trace development")
    parser.add_argument("--boundary", type=Path, required=True)
    parser.add_argument("--run-lane", choices=("candidate", "control"))
    parser.add_argument("--generate-runtime", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    args = parser.parse_args()
    root = args.boundary.resolve().parent.parent
    selected = sum((args.run_lane is not None, args.generate_runtime, args.analyze))
    if selected != 1:
        parser.error("select exactly one mode")
    if args.run_lane:
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


def result_path(boundary_path: Path) -> str:
    boundary = core._load(boundary_path)
    return str(core._mapping(boundary["execution_freeze"], "freeze")["artifacts"]["analysis_report"])


if __name__ == "__main__":
    main()
