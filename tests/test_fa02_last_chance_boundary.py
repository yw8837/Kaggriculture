from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

from kaggriculture_lab.evaluation.runner import _effective_configuration

ROOT = Path(".")
CONFIG = ROOT / "configs/fa02_last_chance_boundary.json"
MANIFEST = ROOT / "experiments/source_snapshots/fa02_last_chance_manifest.json"
REGISTRY = ROOT / "configs/fa_ab_seed_registry.json"

NEW_POOLS = {
    "Fa02_last_chance_development": (34000, 34015, 16),
    "Fa02_last_chance_confirmation": (35000, 35063, 64),
    "Fa02_last_chance_robustness": (36000, 36031, 32),
}

COUNTER_SEMANTICS = {
    "eligible_opportunity": (
        "Each formal allocator decision point where the current minimum-priority "
        "feasible unit-task pair group contains both rank-0 and rank-1 pairs."
    ),
    "rank_tiebreak_activated": (
        "Within the same formal priority, rank 0 actually replaces the rank-1 "
        "choice made by the old comparator."
    ),
    "action_changed_vs_old_comparator_on_same_state": (
        "The final emitted full action vector differs from the formal comparator on "
        "the identical observation; selection displacement alone remains "
        "rank_tiebreak_activated."
    ),
    "last_chance_action_emitted_on_exact_target": (
        "A terminal WATER or FEED action is actually emitted on the exact rank-0 "
        "target; travel or mere assignment does not count."
    ),
    "tiebreak_to_exact_target_action_emitted": (
        "A terminal WATER or FEED action is emitted on the exact rank-0 target by "
        "an accepted causal tie-break trajectory."
    ),
    "formal_fallback_due_assignment_set_mismatch": (
        "The ranked trajectory failed at least one frozen assignment-safety "
        "invariant, so the exact formal actions and trace were emitted instead."
    ),
    "next_day_weed_or_escape_outcome": (
        "A target with an emitted last-chance action is observed next day as WEED "
        "or with its animal missing."
    ),
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _expand(pool: dict) -> set[int]:
    values = set(range(pool["start"], pool["end_inclusive"] + 1))
    assert len(values) == pool["count"]
    return values


def _effective_scenarios_sha256(names: list[str]) -> str:
    scenarios = _load(Path("configs/fa_ab_scenarios.json"))["scenarios"]
    effective = {
        name: _effective_configuration(scenarios[name], seed=None) for name in names
    }
    canonical = json.dumps(effective, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest().upper()


def test_registry_preserves_history_and_new_closed_pools_are_disjoint() -> None:
    registry = _load(REGISTRY)
    reservations = registry["next_boundary_reservations"]

    old_lifecycle = {
        "B_greedy_development": ("CONSUMED_NO_GO", True, True),
        "B_greedy_confirmation": ("RETIRED_UNUSED", False, False),
        "B_greedy_robustness": ("RETIRED_UNUSED", False, False),
    }
    for name, expected in old_lifecycle.items():
        pool = reservations[name]
        assert (pool["status"], pool["opened"], pool["consumed"]) == expected
        assert pool["promotion_eligible"] is False

    all_ranges: list[tuple[str, set[int]]] = []
    for candidate, partitions in registry["candidates"].items():
        for partition, pool in partitions.items():
            if isinstance(pool, dict) and "start" in pool:
                all_ranges.append((f"{candidate}.{partition}", _expand(pool)))
    for name, pool in reservations.items():
        if isinstance(pool, dict) and "start" in pool:
            all_ranges.append((name, _expand(pool)))

    for index, (left_name, left) in enumerate(all_ranges):
        for right_name, right in all_ranges[index + 1 :]:
            assert left.isdisjoint(right), f"seed collision: {left_name}/{right_name}"

    for name, bounds in NEW_POOLS.items():
        pool = reservations[name]
        assert (pool["start"], pool["end_inclusive"], pool["count"]) == bounds
        assert pool["status"] == "CLOSED"
        assert pool["opened"] is pool["consumed"] is False
        assert pool["evaluated_games"] == 0


def test_effective_scenario_hashes_are_exact_for_every_partition() -> None:
    config = _load(CONFIG)
    assert config["scenario_config"]["sha256"] == _sha256(
        Path(config["scenario_config"]["path"])
    )
    for pool in config["pools"].values():
        assert pool["expected_effective_scenarios_sha256"] == (
            _effective_scenarios_sha256(pool["scenarios"])
        )


def test_manifest_hash_and_byte_loop_freezes_every_required_input() -> None:
    manifest = _load(MANIFEST)
    config = _load(CONFIG)
    expected_paths = {
        "configs/fa02_last_chance_boundary.json",
        "configs/fa_ab_seed_registry.json",
        "configs/fa_ab_scenarios.json",
        "artifacts/submission_replays/episode-89143277-replay.json",
        "experiments/source_snapshots/fa02_last_chance_tiebreak/BT1.py",
        "artifacts/candidates/final_day_labor/main.py",
        "artifacts/opponents/public_kaggle/hamburger_current.py",
        "artifacts/opponents/public_kaggle/scenario_aware.py",
        "artifacts/candidates/cow_tilt/main.py",
        "artifacts/candidates/public_expansion_baseline/main.py",
        "src/kaggriculture_lab/candidates/last_chance_tiebreak.py",
        "src/kaggriculture_lab/evaluation/runner.py",
        "src/kaggriculture_lab/evaluation/paired.py",
        "src/kaggriculture_lab/evaluation/last_chance_gate.py",
        "experiments/evaluations/fa02_last_chance_tiebreak/BT1_runtime.json",
        "tests/test_last_chance_gate.py",
        "tests/test_last_chance_tiebreak.py",
        "tests/test_fa02_last_chance_boundary.py",
        "tests/test_seed_registry.py",
    }
    frozen = [
        manifest["config"],
        manifest["seed_registry"],
        manifest["scenario_config"],
        manifest["runtime_replay"],
        *manifest["agents"].values(),
        *manifest["tooling"].values(),
        *manifest["test_sources"].values(),
    ]
    assert manifest["schema_version"] == 3
    assert manifest["role"] == "INPUT_FREEZE"
    assert "test_evidence" not in manifest
    assert len(frozen) == 19
    assert {entry["path"] for entry in frozen} == expected_paths
    for entry in frozen:
        path = Path(entry["path"])
        assert path.stat().st_size == entry["bytes"]
        assert _sha256(path) == entry["sha256"]

    assert manifest["status"] == config["status"]
    assert manifest["seed_state"] == {
        name: "CLOSED" for name in NEW_POOLS
    }
    assert config["candidate"]["sha256"] == manifest["agents"]["BT1"]["sha256"]
    assert config["seed_registry"] == manifest["seed_registry"]["path"]
    assert config["tooling"]["builder_sha256"] == manifest["tooling"]["builder"][
        "sha256"
    ]
    assert config["tooling"]["runner_sha256"] == manifest["tooling"]["runner"][
        "sha256"
    ]
    assert config["tooling"]["analyzer_sha256"] == manifest["tooling"][
        "paired_analysis"
    ]["sha256"]
    assert config["tooling"]["gate_evaluator_sha256"] == manifest["tooling"][
        "development_orchestrator_gate_runtime_generator"
    ]["sha256"]


def test_execution_freeze_separates_inputs_from_evidence_and_hashes_thresholds() -> None:
    config = _load(CONFIG)
    manifest = _load(MANIFEST)
    freeze = config["execution_freeze"]
    assert freeze["input_manifest"] == MANIFEST.as_posix()
    assert freeze["development_gates_sha256"] == hashlib.sha256(
        json.dumps(
            config["development_gates"], sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest().upper()
    allowed = set(freeze["allowed_evidence_only_tracked_paths"])
    assert set(freeze["artifacts"].values()) <= allowed | {
        freeze["artifacts"]["post_test_evidence_manifest"]
    }
    assert not any(path.startswith(("src/", "configs/")) for path in allowed)
    replay = manifest["runtime_replay"]
    assert replay["tracking"] == "IMMUTABLE_LOCAL_EXTERNAL"
    assert freeze["immutable_local_external_inputs"] == [replay["path"]]


def test_gates_counter_contract_and_priority_order_are_frozen() -> None:
    config = _load(CONFIG)
    gates = config["development_gates"]
    assert gates == {
        "all_required": True,
        "candidate_failures": 0,
        "control_failures": 0,
        "candidate_invalid_outputs": 0,
        "control_invalid_outputs": 0,
        "minimum_overall_match_score": 0.70,
        "minimum_direct_match_score_vs_formal": 0.55,
        "minimum_direct_mean_margin_vs_formal": 0.0,
        "minimum_paired_match_score_delta_vs_control": 0.02,
        "minimum_seed_cluster_bootstrap_95_lower_delta_vs_control": -0.02,
        "minimum_paired_mean_money_delta_vs_control": 250.0,
        "minimum_paired_p10_money_delta_vs_control": -1000.0,
        "minimum_each_opponent_mean_money_delta_vs_control": 0.0,
        "minimum_eligible_opportunity": 1,
        "minimum_rank_tiebreak_activated": 1,
        "minimum_action_changed_vs_old_comparator_on_same_state": 1,
        "minimum_last_chance_action_emitted_on_exact_target": 1,
        "minimum_tiebreak_to_exact_target_action_emitted": 1,
        "maximum_next_day_weed_or_escape_outcome": 0,
        "priority_boundary_invariant": "must_pass_ast_property_test",
        "runtime_gate_ref": "runtime_gate_ms",
        "expected_contract": "must_use_preregistered",
    }
    assert config["counter_semantics"] == COUNTER_SEMANTICS
    assert config["counter_capture"] == {
        "export_api": "rescue_metrics",
        "reset_api": "reset_rescue_metrics",
        "required_counters": list(COUNTER_SEMANTICS),
    }

    source = Path(config["candidate"]["path"]).read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_allocation_trace"
    )
    key_orders: list[list[str]] = []
    for node in ast.walk(function):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == "key":
            assert isinstance(node.value, ast.Tuple)
            key_orders.append([ast.unparse(value) for value in node.value.elts])
    assert [
        "priority",
        "cost",
        "task['pos'][1]",
        "task['pos'][0]",
        "i",
        "j",
    ] in key_orders
    assert [
        "priority",
        "rank",
        "cost",
        "task['pos'][1]",
        "task['pos'][0]",
        "i",
        "j",
    ] in key_orders
    assert config["static_invariants"]["priority_boundary_inversions"] == 0
    safety = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_safe_allocation_actions"
    )
    safety_source = ast.unparse(safety)
    for invariant in (
        "same_tasks",
        "cost_nonworsening",
        "path_nonworsening",
        "pickup_nonincreasing",
        "nonpass_preserved",
        "terminal_preserved",
    ):
        assert invariant in safety_source
    accepted = next(
        node
        for node in ast.walk(safety)
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "accepted"
    )
    assert isinstance(accepted.value, ast.BoolOp)
    assert isinstance(accepted.value.op, ast.And)
    assert [ast.unparse(value) for value in accepted.value.values] == [
        "cost_nonworsening",
        "path_nonworsening",
        "pickup_nonincreasing",
        "nonpass_preserved",
        "terminal_preserved",
    ]

    runtime = config["runtime_precheck"]
    assert runtime["gate_result"] == "PASS"
    assert runtime["calls"] == runtime["action_comparison_calls"] == 720
    assert runtime["invalid_outputs"] == 0
    assert runtime["priority_inversions"] == 0
    assert runtime["instrumentation"] == {
        "eligible_opportunity": 41,
        "rank_tiebreak_activated": 8,
        "action_changed_vs_old_comparator_on_same_state": 0,
        "last_chance_action_emitted_on_exact_target": 82,
        "tiebreak_to_exact_target_action_emitted": 0,
        "formal_fallback_due_assignment_set_mismatch": 0,
        "next_day_weed_or_escape_outcome": 0,
    }
    assert runtime["p95_ms"] <= config["runtime_gate_ms"]["p95_max"]
    assert runtime["p99_ms"] <= config["runtime_gate_ms"]["p99_max"]
    assert runtime["max_ms"] <= config["runtime_gate_ms"]["absolute_max"]
