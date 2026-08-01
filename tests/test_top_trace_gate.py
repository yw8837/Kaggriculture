from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path

import pytest

from kaggriculture_lab.evaluation import top_trace_gate as gate

IMPLEMENTATION_HEAD = "0" * 40
EXECUTION_HEAD = "1" * 40
S2_IMPLEMENTATION_HEAD = "2" * 40
CLOSED_EXECUTION_HEAD = "3" * 40
OPENED_AT = "2026-08-02T00:00:00Z"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _json_sha(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2) + "\n").encode()


def _value_sha(value: object) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest().upper()


def _without_paths(value: dict[str, object], paths: tuple[str, ...]) -> dict[str, object]:
    result = copy.deepcopy(value)
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


def _entry(root: Path, relative: str, payload: str) -> dict[str, object]:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return {"path": relative, "sha256": _sha(path), "bytes": path.stat().st_size}


def _registry(*, opened: bool = True) -> dict[str, object]:
    def pool(start: int, end: int, status: str, opened: bool) -> dict[str, object]:
        return {
            "start": start,
            "end_inclusive": end,
            "count": end - start + 1,
            "status": status,
            "opened": opened,
            "consumed": False,
            "evaluated_games": 0,
        }

    development = pool(
        40000, 40015, "OPEN" if opened else "CLOSED", opened
    )
    if opened:
        development["opened_at_utc"] = OPENED_AT
    return {
        "next_boundary_reservations": {
            "Fa04_top_trace_guard_development": development,
            "confirmation": pool(41000, 41063, "CLOSED", False),
            "robustness": pool(42000, 42031, "CLOSED", False),
        }
    }


def _pools(*, opened: bool = True) -> dict[str, object]:
    return {
        "development": {
            "registry_key": "Fa04_top_trace_guard_development",
            "start": 40000,
            "end_inclusive": 40015,
            "count": 16,
            "status": "OPEN" if opened else "CLOSED",
        },
        "confirmation": {
            "registry_key": "confirmation",
            "start": 41000,
            "end_inclusive": 41063,
            "count": 64,
            "status": "CLOSED",
        },
        "robustness": {
            "registry_key": "robustness",
            "start": 42000,
            "end_inclusive": 42031,
            "count": 32,
            "status": "CLOSED",
        },
    }


def _gates() -> dict[str, object]:
    return {
        "candidate_failures": 0,
        "control_failures": 0,
        "minimum_candidate_top_trace_match_score": 0.0,
        "minimum_each_top_trace_match_score": 0.0,
        "minimum_formal_match_score": 0.0,
        "minimum_each_opponent_mean_margin": -1_000_000.0,
        "minimum_paired_match_delta_vs_control": -1.0,
        "minimum_paired_money_delta_vs_control": -1_000_000.0,
        "minimum_actions_changed": 1,
        "runtime_p95_ms_max": 8.0,
        "runtime_p99_ms_max": 15.0,
        "runtime_absolute_ms_max": 50.0,
        "invalid_outputs": 0,
    }


def _transition_invariant(
    closed_boundary: dict[str, object], closed_registry: dict[str, object]
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "basis": {
            "label": "S2_IMPLEMENTATION_E2_EXECUTION",
            "implementation_commit": S2_IMPLEMENTATION_HEAD,
            "closed_execution_commit": CLOSED_EXECUTION_HEAD,
        },
        "canonicalization": {
            "algorithm": gate.CANONICAL_ALGORITHM,
            "boundary_excluded_paths": list(gate.BOUNDARY_CANONICAL_EXCLUDED_PATHS),
            "registry_excluded_paths": list(gate.REGISTRY_CANONICAL_EXCLUDED_PATHS),
        },
        "allowed_open_delta": gate.EXPECTED_ALLOWED_OPEN_DELTA,
        "required_open_metadata": gate.EXPECTED_OPEN_METADATA,
        "canonical_boundary_non_lifecycle_sha256": _json_sha(
            _without_paths(closed_boundary, gate.BOUNDARY_CANONICAL_EXCLUDED_PATHS)
        ),
        "canonical_registry_non_lifecycle_sha256": _json_sha(
            _without_paths(closed_registry, gate.REGISTRY_CANONICAL_EXCLUDED_PATHS)
        ),
    }


def _games(plan: dict[str, object], lane: str) -> list[dict[str, object]]:
    rows = []
    for opponent in plan["opponent_paths"]:
        for seed in plan["seeds"]:
            for seat in (0, 1):
                effective = {"episodeSteps": 720, "seed": seed}
                rows.append(
                    {
                        "scenario": "default",
                        "opponent": opponent,
                        "seed": seed,
                        "seat": seat,
                        "candidate_money": 200.0 if lane == "candidate" else 190.0,
                        "opponent_money": 100.0,
                        "candidate_status": "DONE",
                        "opponent_status": "DONE",
                        "error": None,
                        "effective_configuration": effective,
                        "effective_configuration_sha256": _json_sha(effective),
                        "environment_configuration": dict(effective),
                        "environment_configuration_sha256": _json_sha(effective),
                        "resolved_environment_seed": seed,
                        "candidate_metrics": (
                            {"actions_changed": 1} if lane == "candidate" else None
                        ),
                    }
                )
    return rows


def _runner_receipt(
    root: Path,
    plan: dict[str, object],
    lane: str,
    source: dict[str, object],
    workers: int = 4,
) -> tuple[str, str]:
    relative = gate._runner_receipt_relative(plan["artifacts"][f"{lane}_report"])
    receipt = {
        "schema_version": 1,
        "git_head_at_start": EXECUTION_HEAD,
        "candidate": source["path"],
        "candidate_path": str((root / source["path"]).resolve()),
        "candidate_sha256_at_start": source["sha256"],
        "opponents": plan["opponent_paths"],
        "opponent_paths": {
            item: str((root / item).resolve()) for item in plan["opponent_paths"]
        },
        "opponent_sha256_at_start": plan["opponent_hashes"],
        "seeds": plan["seeds"],
        "seat_policy": "both seats",
        "workers": workers,
        "scenario_overrides": {"default": {}},
        "effective_scenarios": {"default": {"episodeSteps": 720}},
        "effective_scenarios_sha256": plan["effective_scenarios_sha256"],
    }
    path = root / relative
    _write_json(path, receipt)
    return relative, _sha(path)


def _base_report(
    root: Path,
    plan: dict[str, object],
    lane: str,
    source: dict[str, object],
    workers: int = 4,
) -> dict[str, object]:
    runner_path, runner_hash = _runner_receipt(root, plan, lane, source, workers)
    return {
        "schema_version": 1,
        "implementation_commit": IMPLEMENTATION_HEAD,
        "git_head_at_start": EXECUTION_HEAD,
        "workers": workers,
        "start_receipt": str((root / runner_path).resolve()),
        "start_receipt_sha256": runner_hash,
        "candidate": source["path"],
        "candidate_sha256_at_start": source["sha256"],
        "candidate_sha256_at_end": source["sha256"],
        "sources_unchanged_during_run": True,
        "opponents": plan["opponent_paths"],
        "opponent_sha256_at_start": plan["opponent_hashes"],
        "opponent_sha256_at_end": plan["opponent_hashes"],
        "seeds": plan["seeds"],
        "scenario_overrides": {"default": {}},
        "effective_scenarios": {"default": {"episodeSteps": 720}},
        "effective_scenarios_sha256": plan["effective_scenarios_sha256"],
        "summary": {"raw_games": 192, "valid_raw_games": 192, "failed_raw_games": 0},
        "games": _games(plan, lane),
    }


@pytest.fixture
def frozen_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    root = tmp_path
    candidate = _entry(root, "agents/candidate.py", "def agent(obs, config=None): return {}\n")
    control = _entry(root, "agents/control.py", "def agent(obs, config=None): return {}\n")
    opponents = []
    for index in range(6):
        entry = _entry(
            root,
            f"agents/opponent_{index}.py",
            f"def agent(obs, config=None): return {{}}  # {index}\n",
        )
        entry["identity"] = "formal_final_day_labor" if index == 5 else f"top_{index}"
        opponents.append(entry)
    scenario_path = root / "configs/scenarios.json"
    _write_json(scenario_path, {"scenarios": {"default": {}}})
    registry_path = root / "configs/registry.json"
    closed_registry = _registry(opened=False)
    registry = _registry(opened=True)
    _write_json(registry_path, registry)
    tooling_entries = {
        name: _entry(root, f"tooling/{name}.py", f"# frozen {name}\n")
        for name in gate.TOOLING_KEYS
    }
    third_party_license = _entry(root, "third_party/LICENSE", "license\n")
    third_party_attribution = _entry(
        root, "third_party/ATTRIBUTION.md", "attribution\n"
    )
    runtime_replay = _entry(root, "references/replay.json", '{"steps": []}\n')
    gates = _gates()
    artifacts = {
        "candidate_report": "reports/candidate.json",
        "control_report": "reports/control.json",
        "candidate_start_receipt": "reports/candidate.contract.started.json",
        "control_start_receipt": "reports/control.contract.started.json",
        "runtime_report": "reports/runtime.json",
        "analysis_report": "reports/analysis.json",
    }
    boundary = {
        "schema_version": 2,
        "identity": "Fa04_top_trace_guard_G1",
        "status": "CLOSED_PENDING_CORRECTED_FREEZE_AUDIT",
        "implementation_commit": S2_IMPLEMENTATION_HEAD,
        "attribution": {"replay_sha256": runtime_replay["sha256"]},
        "seed_registry": "configs/registry.json",
        "seed_registry_sha256": _value_sha(closed_registry),
        "pools": _pools(opened=False),
        "scenario_config": {
            "path": "configs/scenarios.json",
            "sha256": _sha(scenario_path),
            "bytes": scenario_path.stat().st_size,
        },
        "expected_effective_scenarios_sha256": _json_sha(
            {"default": {"episodeSteps": 720}}
        ),
        "candidate": candidate,
        "control": control,
        "opponents": opponents,
        "tooling": {
            key: value
            for name, entry in tooling_entries.items()
            for key, value in ((name, entry["path"]), (f"{name}_sha256", entry["sha256"]))
        },
        "development_design": {
            "scenarios": ["default"],
            "seeds": "40000-40015",
            "seats": [0, 1],
            "opponents": 6,
            "exact_cells_per_lane": 192,
            "workers_per_lane": 4,
            "receipts": "separate candidate and control start receipts are mandatory",
        },
        "development_gates": gates,
        "execution_freeze": {
            "development_gates_sha256": _json_sha(gates),
            "third_party_license": third_party_license,
            "third_party_attribution": third_party_attribution,
            "runtime_replay": runtime_replay,
            "artifacts": artifacts,
        },
        "release_policy": (
            "Development PASS permits only a separate SaveRun readiness request; "
            "no SaveRun without separate authorization/audit verdict."
        ),
    }
    boundary["open_transition_invariant"] = _transition_invariant(
        boundary, closed_registry
    )
    closed_boundary = copy.deepcopy(boundary)
    boundary["status"] = "DEVELOPMENT_OPEN_AUTHORIZED"
    boundary["implementation_commit"] = IMPLEMENTATION_HEAD
    boundary["seed_registry_sha256"] = _sha(registry_path)
    boundary["pools"]["development"]["status"] = "OPEN"
    boundary["development_opened_at_utc"] = OPENED_AT
    boundary["opening_authority"] = gate.OPENING_AUTHORITY
    boundary_path = root / "configs/fa04_top_trace_guard_boundary.json"
    _write_json(boundary_path, boundary)
    def fake_git_json_blob(
        _project_root: Path, _head: str, relative: str, _label: str
    ) -> tuple[dict[str, object], str]:
        value = (
            closed_boundary
            if relative == gate.BOUNDARY_RELATIVE
            else closed_registry
        )
        return copy.deepcopy(value), _value_sha(value)

    monkeypatch.setattr(gate, "_git_json_blob", fake_git_json_blob)
    monkeypatch.setattr(
        gate,
        "_verify_git_freeze",
        lambda *_args: {
            "implementation_commit": IMPLEMENTATION_HEAD,
            "execution_head": EXECUTION_HEAD,
        },
    )
    plan = gate._frozen_plan(root, boundary_path)
    for lane, source in (("candidate", candidate), ("control", control)):
        outer = gate._outer_receipt_payload(lane, 4, source, plan)
        outer_path = root / artifacts[f"{lane}_start_receipt"]
        _write_json(outer_path, outer)
        report = _base_report(root, plan, lane, source)
        report["execution_provenance"] = {
            "lane": lane,
            "implementation_commit": IMPLEMENTATION_HEAD,
            "git_head": EXECUTION_HEAD,
            "start_receipt": {
                "path": artifacts[f"{lane}_start_receipt"],
                "sha256": _sha(outer_path),
            },
        }
        _write_json(root / artifacts[f"{lane}_report"], report)
    runtime_generator = tooling_entries["runtime_generator"]
    runtime_receipt_relative = gate._runtime_receipt_relative(
        artifacts["runtime_report"]
    )
    runtime_receipt_path = root / runtime_receipt_relative
    _write_json(runtime_receipt_path, gate._runtime_receipt_payload(plan))
    runtime = {
        "git_head": EXECUTION_HEAD,
        "tracked_tree_clean": True,
        "generation_receipt": {
            "path": runtime_receipt_relative,
            "sha256": _sha(runtime_receipt_path),
        },
        "generator": {
            "path": str((root / runtime_generator["path"]).resolve()),
            "sha256": runtime_generator["sha256"],
        },
        "tracked_provenance": {
            "project_root": str(root.resolve()),
            "implementation_commit": IMPLEMENTATION_HEAD,
            "git_head": EXECUTION_HEAD,
            "tracked_tree_clean": True,
            "source_relative": candidate["path"],
            "source_at_head_sha256": candidate["sha256"],
            "runtime_replay": runtime_replay,
        },
        "source": str((root / candidate["path"]).resolve()),
        "source_sha256": candidate["sha256"],
        "replay": str((root / runtime_replay["path"]).resolve()),
        "replay_sha256": runtime_replay["sha256"],
        "player": 0,
        "calls": 720,
        "invalid_outputs": 0,
        "p95_ms": 1.0,
        "p99_ms": 2.0,
        "max_ms": 3.0,
    }
    _write_json(root / artifacts["runtime_report"], runtime)
    return {
        "root": root,
        "boundary": boundary_path,
        "registry": registry_path,
        "candidate_report": root / artifacts["candidate_report"],
        "control_report": root / artifacts["control_report"],
        "runtime": root / artifacts["runtime_report"],
        "artifacts": artifacts,
        "tooling": tooling_entries,
        "plan": plan,
        "candidate": candidate,
    }


def _analyze(case: dict[str, object]) -> dict[str, object]:
    return gate.analyze(
        case["candidate_report"], case["control_report"], case["runtime"], case["boundary"]
    )


def _mutate_json(path: Path, mutation: object) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    mutation(value)
    _write_json(path, value)


def test_gate_has_no_assert_and_compiles_under_optimized_python() -> None:
    source_path = Path(gate.__file__)
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert not any(isinstance(node, ast.Assert) for node in ast.walk(tree))
    compile(source, str(source_path), "exec", optimize=2)


def test_git_freeze_allows_only_exact_frozen_untracked_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    implementation = _entry(tmp_path, "src/agent.py", "agent\n")
    execution = _entry(tmp_path, "configs/boundary.json", "boundary\n")
    status = "?? reports/candidate.json"

    def fake_git(_root: Path, *args: str, text: bool = True) -> str:
        del text
        if args == ("rev-parse", "HEAD"):
            return EXECUTION_HEAD
        if args[0] == "status":
            return status
        return ""

    monkeypatch.setattr(gate, "_git", fake_git)
    monkeypatch.setattr(
        gate,
        "_git_file_sha256",
        lambda root, _head, relative: _sha(root / relative),
    )
    result = gate._verify_git_freeze(
        tmp_path,
        IMPLEMENTATION_HEAD,
        {implementation["path"]},
        {execution["path"]},
        {"reports/candidate.json"},
    )
    assert result["execution_head"] == EXECUTION_HEAD
    with pytest.raises(ValueError, match="must be clean"):
        gate._verify_git_freeze(
            tmp_path,
            IMPLEMENTATION_HEAD,
            {implementation["path"]},
            {execution["path"]},
            {"reports/other.json"},
        )


def test_exact_frozen_192_cell_reports_pass_with_distinct_s_and_e(
    frozen_case: dict[str, object],
) -> None:
    result = _analyze(frozen_case)
    assert result["cells"] == 192
    assert result["development_pass"] is True
    assert result["implementation_commit"] == IMPLEMENTATION_HEAD
    assert result["execution_head"] == EXECUTION_HEAD
    assert IMPLEMENTATION_HEAD != EXECUTION_HEAD


def test_wrong_source_is_rejected(frozen_case: dict[str, object]) -> None:
    _mutate_json(
        frozen_case["candidate_report"],
        lambda report: report.__setitem__("candidate_sha256_at_end", "F" * 64),
    )
    with pytest.raises(ValueError, match="frozen report contract"):
        _analyze(frozen_case)


@pytest.mark.parametrize("field", ["candidate_money", "opponent_money"])
@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), float("-inf"), True, "200.0"],
)
def test_money_must_be_finite_numeric_not_bool(
    frozen_case: dict[str, object], field: str, value: object
) -> None:
    def mutation(report: dict[str, object]) -> None:
        report["games"][0][field] = value

    _mutate_json(frozen_case["candidate_report"], mutation)
    with pytest.raises((TypeError, ValueError), match="finite number"):
        _analyze(frozen_case)


def test_191_cells_are_rejected(frozen_case: dict[str, object]) -> None:
    def mutation(report: dict[str, object]) -> None:
        report["games"].pop()
        report["summary"]["raw_games"] = 191
        report["summary"]["valid_raw_games"] = 191

    _mutate_json(frozen_case["candidate_report"], mutation)
    with pytest.raises(ValueError, match="192"):
        _analyze(frozen_case)


@pytest.mark.parametrize("mode", ["missing", "shared", "runner_missing"])
def test_missing_or_shared_receipts_are_rejected(
    frozen_case: dict[str, object], mode: str
) -> None:
    root = frozen_case["root"]
    artifacts = frozen_case["artifacts"]
    if mode == "missing":
        (root / artifacts["candidate_start_receipt"]).unlink()
    elif mode == "shared":
        candidate_outer = artifacts["candidate_start_receipt"]
        _mutate_json(
            frozen_case["control_report"],
            lambda report: report["execution_provenance"]["start_receipt"].update(
                {
                    "path": candidate_outer,
                    "sha256": _sha(root / candidate_outer),
                }
            ),
        )
    else:
        (root / gate._runner_receipt_relative(artifacts["candidate_report"])).unlink()
    with pytest.raises(ValueError, match="receipt"):
        _analyze(frozen_case)


@pytest.mark.parametrize(
    "field,value",
    [("git_head_at_start", "2" * 40), ("workers", 9), ("implementation_commit", "3" * 40)],
)
def test_wrong_git_head_workers_or_implementation_is_rejected(
    frozen_case: dict[str, object], field: str, value: object
) -> None:
    _mutate_json(
        frozen_case["candidate_report"], lambda report: report.__setitem__(field, value)
    )
    with pytest.raises(ValueError, match="git_head/workers"):
        _analyze(frozen_case)


@pytest.mark.parametrize(
    "mode",
    [
        "effective",
        "environment",
        "environment_seed",
        "environment_seed_missing",
        "environment_random_seed",
        "resolved_seed",
    ],
)
def test_wrong_per_row_configuration_or_seed_is_rejected(
    frozen_case: dict[str, object], mode: str
) -> None:
    def mutation(report: dict[str, object]) -> None:
        row = report["games"][0]
        if mode == "effective":
            row["effective_configuration"]["seed"] += 1
            row["effective_configuration_sha256"] = _json_sha(
                row["effective_configuration"]
            )
        elif mode == "environment":
            row["environment_configuration"]["episodeSteps"] = 719
            row["environment_configuration_sha256"] = _json_sha(
                row["environment_configuration"]
            )
        elif mode == "environment_seed":
            row["environment_configuration"]["seed"] += 1
            row["environment_configuration_sha256"] = _json_sha(
                row["environment_configuration"]
            )
        elif mode == "environment_seed_missing":
            row["environment_configuration"].pop("seed")
            row["environment_configuration_sha256"] = _json_sha(
                row["environment_configuration"]
            )
        elif mode == "environment_random_seed":
            row["environment_configuration"]["randomSeed"] = row["seed"] + 1
            row["environment_configuration_sha256"] = _json_sha(
                row["environment_configuration"]
            )
        else:
            row["resolved_environment_seed"] += 1

    _mutate_json(frozen_case["candidate_report"], mutation)
    with pytest.raises(ValueError, match="configuration|scenario|seed"):
        _analyze(frozen_case)


def test_closed_development_registry_is_rejected(frozen_case: dict[str, object]) -> None:
    def close(registry: dict[str, object]) -> None:
        registry["next_boundary_reservations"][
            "Fa04_top_trace_guard_development"
        ].update(
            {"status": "CLOSED", "opened": False, "consumed": False}
        )

    _mutate_json(frozen_case["registry"], close)
    _mutate_json(
        frozen_case["boundary"],
        lambda boundary: boundary.__setitem__(
            "seed_registry_sha256", _sha(frozen_case["registry"])
        ),
    )
    with pytest.raises(ValueError, match="lifecycle"):
        _analyze(frozen_case)


@pytest.mark.parametrize(
    "mode",
    ["threshold", "opponent", "replay", "artifact", "scenario", "registry", "self_hash"],
)
def test_production_invariant_rejects_non_lifecycle_self_hash_updates(
    frozen_case: dict[str, object], mode: str
) -> None:
    boundary_path = frozen_case["boundary"]
    registry_path = frozen_case["registry"]
    boundary = json.loads(boundary_path.read_text(encoding="utf-8"))
    if mode in {"threshold", "self_hash"}:
        boundary["development_gates"]["minimum_actions_changed"] = 999
        boundary["execution_freeze"]["development_gates_sha256"] = _json_sha(
            boundary["development_gates"]
        )
        if mode == "self_hash":
            boundary["open_transition_invariant"][
                "canonical_boundary_non_lifecycle_sha256"
            ] = _json_sha(
                _without_paths(boundary, gate.BOUNDARY_CANONICAL_EXCLUDED_PATHS)
            )
    elif mode == "opponent":
        boundary["opponents"][0]["sha256"] = "A" * 64
    elif mode == "replay":
        boundary["attribution"]["replay_sha256"] = "A" * 64
        boundary["execution_freeze"]["runtime_replay"]["sha256"] = "A" * 64
    elif mode == "artifact":
        boundary["candidate"]["sha256"] = "A" * 64
    elif mode == "scenario":
        boundary["scenario_config"]["sha256"] = "A" * 64
    else:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        pool = registry["next_boundary_reservations"][
            "Fa04_top_trace_guard_development"
        ]
        pool.update({"start": 40001, "end_inclusive": 40016, "count": 16})
        _write_json(registry_path, registry)
        boundary["seed_registry_sha256"] = _sha(registry_path)
    _write_json(boundary_path, boundary)
    with pytest.raises(ValueError, match="invariant"):
        gate._frozen_plan(frozen_case["root"], boundary_path)


def test_modified_gate_tooling_is_rejected(frozen_case: dict[str, object]) -> None:
    path = frozen_case["root"] / frozen_case["tooling"]["gate_evaluator"]["path"]
    path.write_text("# modified gate\n", encoding="utf-8")
    with pytest.raises(ValueError, match="tooling.gate_evaluator hash mismatch"):
        _analyze(frozen_case)


def test_runtime_generator_and_tracked_source_are_required(
    frozen_case: dict[str, object],
) -> None:
    _mutate_json(
        frozen_case["runtime"],
        lambda report: report["tracked_provenance"].__setitem__(
            "source_at_head_sha256", "F" * 64
        ),
    )
    with pytest.raises(ValueError, match="runtime tracked source provenance"):
        _analyze(frozen_case)


@pytest.mark.parametrize(
    "field,value",
    [
        ("p95_ms", float("nan")),
        ("p95_ms", float("inf")),
        ("p95_ms", -0.1),
        ("p95_ms", 4.0),
    ],
)
def test_runtime_timings_must_be_finite_nonnegative_and_ordered(
    frozen_case: dict[str, object], field: str, value: float
) -> None:
    _mutate_json(
        frozen_case["runtime"],
        lambda report: report.__setitem__(field, value),
    )
    with pytest.raises(ValueError, match="finite nonnegative|p95 <= p99 <= max"):
        _analyze(frozen_case)


@pytest.mark.parametrize("field", ["implementation_commit", "runtime_replay"])
def test_runtime_tracked_provenance_is_exact(
    frozen_case: dict[str, object], field: str
) -> None:
    replacement: object = "F" * 40 if field == "implementation_commit" else {}
    _mutate_json(
        frozen_case["runtime"],
        lambda report: report["tracked_provenance"].__setitem__(field, replacement),
    )
    with pytest.raises(ValueError, match="runtime tracked source provenance"):
        _analyze(frozen_case)


@pytest.mark.parametrize("mode", ["missing", "wrong_head", "wrong_hash"])
def test_runtime_generation_receipt_is_required_and_bound_to_execution_contract(
    frozen_case: dict[str, object], mode: str
) -> None:
    runtime = json.loads(frozen_case["runtime"].read_text(encoding="utf-8"))
    receipt_path = frozen_case["root"] / runtime["generation_receipt"]["path"]
    if mode == "missing":
        receipt_path.unlink()
    elif mode == "wrong_head":
        _mutate_json(
            receipt_path,
            lambda receipt: receipt.__setitem__("git_head", "F" * 40),
        )
        _mutate_json(
            frozen_case["runtime"],
            lambda report: report["generation_receipt"].__setitem__(
                "sha256", _sha(receipt_path)
            ),
        )
    else:
        _mutate_json(
            frozen_case["runtime"],
            lambda report: report["generation_receipt"].__setitem__(
                "sha256", "F" * 64
            ),
        )
    with pytest.raises(ValueError, match="runtime generation receipt"):
        _analyze(frozen_case)


def test_modified_runtime_generator_tooling_is_rejected(
    frozen_case: dict[str, object],
) -> None:
    entry = frozen_case["tooling"]["runtime_generator"]
    (frozen_case["root"] / entry["path"]).write_text("# modified\n", encoding="utf-8")
    with pytest.raises(ValueError, match="tooling.runtime_generator hash mismatch"):
        _analyze(frozen_case)


def test_modified_runtime_benchmark_tooling_is_rejected(
    frozen_case: dict[str, object],
) -> None:
    entry = frozen_case["tooling"]["runtime_benchmark"]
    (frozen_case["root"] / entry["path"]).write_text("# modified\n", encoding="utf-8")
    with pytest.raises(ValueError, match="tooling.runtime_benchmark hash mismatch"):
        _analyze(frozen_case)


def test_run_lane_writes_outer_receipt_before_exact_runner_call(
    frozen_case: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    root = frozen_case["root"]
    plan = frozen_case["plan"]
    artifacts = frozen_case["artifacts"]
    lane = "candidate"
    for relative in (
        artifacts["candidate_report"],
        artifacts["candidate_start_receipt"],
        gate._runner_receipt_relative(artifacts["candidate_report"]),
    ):
        (root / relative).unlink()

    def fake_run(
        candidate_ref: str,
        opponents: list[str],
        seeds: list[int],
        output: Path,
        workers: int,
        project_root: Path,
        scenarios: dict[str, dict[str, object]],
    ) -> dict[str, object]:
        assert (root / artifacts["candidate_start_receipt"]).is_file()
        assert candidate_ref == frozen_case["candidate"]["path"]
        assert opponents == plan["opponent_paths"]
        assert seeds == list(range(40000, 40016))
        assert output == root / artifacts["candidate_report"]
        assert workers == 4
        assert project_root == root.resolve()
        assert scenarios == {"default": {}}
        return _base_report(root, plan, lane, frozen_case["candidate"], workers=4)

    monkeypatch.setattr(gate, "_run_batch_exact", fake_run)
    report = gate.run_development_lane(root, frozen_case["boundary"], lane, 4)
    assert len(report["games"]) == 192
    assert report["implementation_commit"] == IMPLEMENTATION_HEAD
    assert report["execution_provenance"]["git_head"] == EXECUTION_HEAD
    assert report["start_receipt"] != report["execution_provenance"]["start_receipt"]["path"]


def test_generate_runtime_binds_execution_head_source_and_replay(
    frozen_case: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    from kaggriculture_lab.evaluation import runtime

    output = frozen_case["runtime"]
    output.unlink()
    runtime_receipt = frozen_case["root"] / gate._runtime_receipt_relative(
        frozen_case["artifacts"]["runtime_report"]
    )
    runtime_receipt.unlink()
    monkeypatch.setattr(
        runtime,
        "benchmark",
        lambda source, replay, player: {
            "schema_version": 1,
            "source": source.as_posix(),
            "source_sha256": _sha(source),
            "replay": replay.as_posix(),
            "replay_sha256": _sha(replay),
            "player": player,
            "calls": 720,
            "invalid_outputs": 0,
            "p50_ms": 0.1,
            "p95_ms": 0.2,
            "p99_ms": 0.3,
            "max_ms": 0.4,
        },
    )
    report = gate.generate_runtime_report(
        frozen_case["root"], frozen_case["boundary"]
    )
    assert report["git_head"] == EXECUTION_HEAD
    assert report["tracked_provenance"]["implementation_commit"] == IMPLEMENTATION_HEAD
    assert report["tracked_provenance"]["source_at_head_sha256"] == frozen_case[
        "candidate"
    ]["sha256"]
    assert report["tracked_provenance"]["runtime_replay"] == frozen_case["plan"][
        "runtime_replay"
    ]
    assert runtime_receipt.is_file()
    assert report["generation_receipt"]["sha256"] == _sha(runtime_receipt)
    assert json.loads(output.read_text(encoding="utf-8")) == report
