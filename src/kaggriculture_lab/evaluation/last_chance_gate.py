"""Frozen Fa_02 development orchestration contract and strict promotion gate."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import math
import platform
import runpy
import subprocess
import sys
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kaggriculture_lab.evaluation.paired import compare_reports, require_gate_eligible
from kaggriculture_lab.evaluation.runner import _effective_configuration, run_batch

CONFIG_RELATIVE = Path("configs/fa02_last_chance_boundary.json")
FORMAL_OPPONENT = "artifacts/candidates/final_day_labor/main.py"
COUNTER_NAMES = (
    "eligible_opportunity",
    "rank_tiebreak_activated",
    "action_changed_vs_old_comparator_on_same_state",
    "last_chance_action_emitted_on_exact_target",
    "tiebreak_to_exact_target_action_emitted",
    "formal_fallback_due_assignment_set_mismatch",
    "next_day_weed_or_escape_outcome",
)
NUMERIC_GATE_FIELDS = {
    "candidate_failures",
    "control_failures",
    "candidate_invalid_outputs",
    "control_invalid_outputs",
    "minimum_overall_match_score",
    "minimum_direct_match_score_vs_formal",
    "minimum_direct_mean_margin_vs_formal",
    "minimum_paired_match_score_delta_vs_control",
    "minimum_seed_cluster_bootstrap_95_lower_delta_vs_control",
    "minimum_paired_mean_money_delta_vs_control",
    "minimum_paired_p10_money_delta_vs_control",
    "minimum_each_opponent_mean_money_delta_vs_control",
    "minimum_eligible_opportunity",
    "minimum_rank_tiebreak_activated",
    "minimum_action_changed_vs_old_comparator_on_same_state",
    "minimum_last_chance_action_emitted_on_exact_target",
    "minimum_tiebreak_to_exact_target_action_emitted",
    "maximum_next_day_weed_or_escape_outcome",
}
META_GATE_FIELDS = {
    "all_required",
    "priority_boundary_invariant",
    "runtime_gate_ref",
    "expected_contract",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be an object")
    return value


def _json_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def _checked_source(
    project_root: Path, entry: Mapping[str, Any], label: str
) -> tuple[str, str]:
    relative = entry.get("path")
    expected = entry.get("sha256")
    if not isinstance(relative, str) or not relative:
        raise ValueError(f"{label}.path must be a non-empty string")
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError(f"{label}.sha256 must be a SHA-256 digest")
    path = project_root / relative
    actual = sha256(path)
    if actual != expected.upper():
        raise ValueError(
            f"{label} hash mismatch: expected={expected.upper()}, actual={actual}"
        )
    if "bytes" in entry and path.stat().st_size != entry["bytes"]:
        raise ValueError(f"{label} byte-size mismatch")
    return relative, actual


def frozen_development_plan(project_root: Path) -> dict[str, Any]:
    """Derive the only admissible 160-cell development grid from frozen config."""
    project_root = project_root.resolve()
    config_path = project_root / CONFIG_RELATIVE
    config = _mapping(
        json.loads(config_path.read_text(encoding="utf-8")), "boundary config"
    )
    if config.get("status") != "FROZEN_CLOSED_PENDING_SEED_OPEN_AUTHORIZATION":
        raise ValueError("boundary config is not the frozen CLOSED artifact")

    candidate_path, candidate_hash = _checked_source(
        project_root, _mapping(config.get("candidate"), "candidate"), "candidate"
    )
    control_path, control_hash = _checked_source(
        project_root, _mapping(config.get("control"), "control"), "control"
    )
    if control_path != FORMAL_OPPONENT:
        raise ValueError("the frozen control is not final_day_labor")

    scenario_entry = _mapping(config.get("scenario_config"), "scenario_config")
    scenario_path, scenario_hash = _checked_source(
        project_root, scenario_entry, "scenario_config"
    )
    scenario_config = _mapping(
        json.loads((project_root / scenario_path).read_text(encoding="utf-8")),
        "scenario config",
    )
    scenarios = _mapping(scenario_config.get("scenarios"), "scenario config.scenarios")

    pool = _mapping(_mapping(config.get("pools"), "pools").get("development"), "pool")
    if (
        pool.get("start"),
        pool.get("end_inclusive"),
        pool.get("count"),
        pool.get("scenarios"),
    ) != (34000, 34015, 16, ["default"]):
        raise ValueError("development pool must be seeds 34000-34015 and default only")
    seeds = list(range(int(pool["start"]), int(pool["end_inclusive"]) + 1))
    if len(seeds) != pool["count"]:
        raise ValueError("development pool cardinality mismatch")

    opponent_entries = config.get("opponents")
    if not isinstance(opponent_entries, list):
        raise TypeError("opponents must be a list")
    opponent_paths: list[str] = []
    opponent_hashes: dict[str, str] = {}
    for index, raw_entry in enumerate(opponent_entries):
        path, digest = _checked_source(
            project_root,
            _mapping(raw_entry, f"opponents[{index}]"),
            f"opponents[{index}]",
        )
        if path in opponent_hashes:
            raise ValueError(f"duplicate opponent: {path}")
        opponent_paths.append(path)
        opponent_hashes[path] = digest
    if len(opponent_paths) != 5 or opponent_paths.count(FORMAL_OPPONENT) != 1:
        raise ValueError("development requires five opponents including one formal lane")
    if config.get("seat_policy") != "both seats for every seed/scenario/opponent cell":
        raise ValueError("development requires both seats for every cell")

    scenario_names = list(pool["scenarios"])
    effective_scenarios = {
        name: _effective_configuration(dict(_mapping(scenarios.get(name), name)), seed=None)
        for name in scenario_names
    }
    effective_hash = _json_sha256(effective_scenarios)
    if effective_hash != pool.get("expected_effective_scenarios_sha256"):
        raise ValueError("effective development scenario hash mismatch")

    cell_keys = [
        [scenario, opponent, seed, seat]
        for scenario in scenario_names
        for opponent in opponent_paths
        for seed in seeds
        for seat in (0, 1)
    ]
    if len(cell_keys) != 160 or len({tuple(key) for key in cell_keys}) != 160:
        raise ValueError("development grid must derive to exactly 160 unique cells")

    contract = {
        "candidate_source_sha256": candidate_hash,
        "control_source_sha256": control_hash,
        "root_config": {"path": str(config_path), "sha256": sha256(config_path)},
        "scenario_config": {
            "path": str(project_root / scenario_path),
            "sha256": scenario_hash,
        },
        "effective_scenarios_sha256": effective_hash,
        "opponent_source_sha256": opponent_hashes,
        "cell_keys": cell_keys,
        "cell_count": 160,
    }
    return {
        "config": dict(config),
        "candidate": candidate_path,
        "control": control_path,
        "opponents": opponent_paths,
        "formal_opponent": FORMAL_OPPONENT,
        "seeds": seeds,
        "scenarios": scenario_names,
        "seats": [0, 1],
        "cell_keys": cell_keys,
        "cell_count": 160,
        "contract": contract,
    }


def aggregate_counters(games: list[dict[str, Any]]) -> dict[str, int]:
    """Strictly sum exact per-row raw counters; absent/extra/invalid values fail."""
    totals = {name: 0 for name in COUNTER_NAMES}
    for index, game in enumerate(games):
        metrics = _mapping(game.get("candidate_metrics"), f"games[{index}].candidate_metrics")
        if set(metrics) != set(COUNTER_NAMES):
            raise ValueError(f"games[{index}] counter keys do not match the frozen contract")
        for name in COUNTER_NAMES:
            value = metrics[name]
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise TypeError(f"games[{index}].candidate_metrics[{name!r}] is invalid")
            totals[name] += value
    return totals


def validate_candidate_counter_evidence(
    report: Mapping[str, Any], expected_cells: int
) -> dict[str, int]:
    games = report.get("games")
    if not isinstance(games, list) or len(games) != expected_cells:
        raise ValueError(
            f"candidate raw counter coverage must be {expected_cells}/{expected_cells}"
        )
    totals = aggregate_counters(games)
    summary = _mapping(report.get("summary"), "candidate summary")
    if summary.get("raw_games") != expected_cells:
        raise ValueError("candidate summary raw_games is not the frozen cell count")
    if summary.get("candidate_metrics_games") != expected_cells:
        raise ValueError("candidate counter coverage summary is not 160/160")
    if summary.get("candidate_metrics_total") != totals:
        raise ValueError("candidate counter summary does not equal recomputed raw totals")
    return totals


def validate_runtime_precheck(
    project_root: Path, config: Mapping[str, Any]
) -> dict[str, bool]:
    runtime = _mapping(config.get("runtime_precheck"), "runtime_precheck")
    relative = runtime.get("path")
    if not isinstance(relative, str):
        raise TypeError("runtime_precheck.path must be a string")
    report_path = project_root / relative
    if sha256(report_path) != runtime.get("sha256"):
        raise ValueError("runtime precheck hash mismatch")
    if report_path.stat().st_size != runtime.get("bytes"):
        raise ValueError("runtime precheck byte-size mismatch")
    report = _mapping(
        json.loads(report_path.read_text(encoding="utf-8")), "runtime report"
    )
    candidate = _mapping(config.get("candidate"), "candidate")
    gates = _mapping(config.get("runtime_gate_ms"), "runtime_gate_ms")
    instrumentation = _mapping(report.get("instrumentation"), "runtime instrumentation")
    if set(instrumentation) != set(COUNTER_NAMES):
        raise ValueError("runtime instrumentation keys do not match the frozen contract")
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in instrumentation.values()
    ):
        raise TypeError("runtime instrumentation values must be nonnegative integers")
    return {
        "runtime_source": report.get("source") == candidate.get("path")
        and report.get("source_sha256") == candidate.get("sha256"),
        "runtime_calls": report.get("calls") == report.get("action_comparison_calls") == 720,
        "runtime_invalid": report.get("invalid_outputs") == gates.get("invalid_outputs"),
        "runtime_p95": _at_most(report.get("p95_ms"), gates.get("p95_max")),
        "runtime_p99": _at_most(report.get("p99_ms"), gates.get("p99_max")),
        "runtime_max": _at_most(report.get("max_ms"), gates.get("absolute_max")),
        "priority_boundary": report.get("priority_inversions") == 0,
        "runtime_report_gate": report.get("gate_result") == "PASS",
    }


def _finite(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _at_least(value: object, threshold: object) -> bool:
    return _finite(value) and _finite(threshold) and float(value) >= float(threshold)


def _at_most(value: object, threshold: object) -> bool:
    return _finite(value) and _finite(threshold) and float(value) <= float(threshold)


def preregistered_checks(
    result: dict[str, Any],
    gates: dict[str, Any],
    counter_totals: dict[str, int],
    *,
    improvement_result: dict[str, Any] | None = None,
    runtime_checks: Mapping[str, bool] | None = None,
) -> tuple[dict[str, bool], dict[str, float]]:
    unknown = set(gates) - NUMERIC_GATE_FIELDS - META_GATE_FIELDS
    missing = NUMERIC_GATE_FIELDS - set(gates)
    if unknown or missing or set(counter_totals) != set(COUNTER_NAMES):
        raise ValueError(
            f"development gate schema mismatch: missing={missing}, unknown={unknown}"
        )
    improvement = improvement_result or result
    formal = result["candidate"]["per_opponent"][FORMAL_OPPONENT]
    per_opponent_money = {
        name: float(row["money_delta_mean"])
        for name, row in result["paired"]["per_opponent"].items()
    }
    runtime = dict(runtime_checks or {})
    checks = {
        "candidate_failures": result["candidate"]["failures"]
        == gates["candidate_failures"],
        "control_failures": result["control"]["failures"] == gates["control_failures"],
        "candidate_invalid": result["candidate"]["invalid"]
        == gates["candidate_invalid_outputs"],
        "control_invalid": result["control"]["invalid"]
        == gates["control_invalid_outputs"],
        "candidate_overall": _at_least(
            result["candidate"]["match_score"], gates["minimum_overall_match_score"]
        ),
        "direct_formal_match": _at_least(
            formal["match_score"], gates["minimum_direct_match_score_vs_formal"]
        ),
        "direct_formal_margin": _at_least(
            formal["margin_mean"], gates["minimum_direct_mean_margin_vs_formal"]
        ),
        "paired_match_delta_nonself": _at_least(
            improvement["paired"]["match_score_delta_mean"],
            gates["minimum_paired_match_score_delta_vs_control"],
        ),
        "paired_match_ci_lower_nonself": _at_least(
            improvement["paired"]["match_score_delta_seed_cluster_bootstrap_95"][0],
            gates["minimum_seed_cluster_bootstrap_95_lower_delta_vs_control"],
        ),
        "paired_money_mean_nonself": _at_least(
            improvement["paired"]["money_delta_mean"],
            gates["minimum_paired_mean_money_delta_vs_control"],
        ),
        "paired_money_p10_nonself": _at_least(
            improvement["paired"]["money_delta_p10"],
            gates["minimum_paired_p10_money_delta_vs_control"],
        ),
        "every_opponent_money": len(per_opponent_money) == 5
        and all(
            _at_least(value, gates["minimum_each_opponent_mean_money_delta_vs_control"])
            for value in per_opponent_money.values()
        ),
        "eligible_opportunity": counter_totals["eligible_opportunity"]
        >= gates["minimum_eligible_opportunity"],
        "rank_tiebreak_activated": counter_totals["rank_tiebreak_activated"]
        >= gates["minimum_rank_tiebreak_activated"],
        "action_changed": counter_totals[
            "action_changed_vs_old_comparator_on_same_state"
        ]
        >= gates["minimum_action_changed_vs_old_comparator_on_same_state"],
        "exact_target_action": counter_totals[
            "last_chance_action_emitted_on_exact_target"
        ]
        >= gates["minimum_last_chance_action_emitted_on_exact_target"],
        "causal_tiebreak_exact_target_action": counter_totals[
            "tiebreak_to_exact_target_action_emitted"
        ]
        >= gates["minimum_tiebreak_to_exact_target_action_emitted"],
        "next_day_adverse": counter_totals["next_day_weed_or_escape_outcome"]
        <= gates["maximum_next_day_weed_or_escape_outcome"],
        "all_required": gates.get("all_required") is True,
        "priority_contract": gates.get("priority_boundary_invariant")
        == "must_pass_ast_property_test"
        and runtime.get("priority_boundary") is True,
        "runtime_gate": bool(runtime) and all(runtime.values()),
        "expected_contract": gates.get("expected_contract") == "must_use_preregistered",
        "runtime_gate_reference": gates.get("runtime_gate_ref") == "runtime_gate_ms",
    }
    return checks, per_opponent_money


def _filtered_report(report: Mapping[str, Any], opponents: set[str]) -> dict[str, Any]:
    filtered = dict(report)
    filtered["games"] = [
        row for row in report["games"] if row.get("opponent") in opponents
    ]
    for field in ("opponent_sha256_at_start", "opponent_sha256_at_end"):
        values = _mapping(report.get(field), field)
        filtered[field] = {name: value for name, value in values.items() if name in opponents}
    return filtered


def _summary_view(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "raw_cells": result["raw_cells"],
        "candidate": result["candidate"],
        "control": result["control"],
        "paired": result["paired"],
    }


def analyze_development(
    project_root: Path,
    candidate_report: Path,
    control_report: Path,
    output: Path,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    plan = frozen_development_plan(project_root)
    candidate_raw = _mapping(
        json.loads(candidate_report.read_text(encoding="utf-8")), "candidate report"
    )
    control_raw = _mapping(
        json.loads(control_report.read_text(encoding="utf-8")), "control report"
    )
    totals = validate_candidate_counter_evidence(candidate_raw, plan["cell_count"])
    result = compare_reports(candidate_raw, control_raw, expected_contract=plan["contract"])
    require_gate_eligible(result)

    nonself_opponents = set(plan["opponents"]) - {plan["formal_opponent"]}
    nonself_contract = dict(plan["contract"])
    nonself_contract["opponent_source_sha256"] = {
        name: digest
        for name, digest in plan["contract"]["opponent_source_sha256"].items()
        if name in nonself_opponents
    }
    nonself_contract["cell_keys"] = [
        key for key in plan["cell_keys"] if key[1] in nonself_opponents
    ]
    nonself_contract["cell_count"] = len(nonself_contract["cell_keys"])
    improvement = compare_reports(
        _filtered_report(candidate_raw, nonself_opponents),
        _filtered_report(control_raw, nonself_opponents),
        expected_contract=nonself_contract,
    )
    require_gate_eligible(improvement)
    if improvement["raw_cells"] != 128:
        raise ValueError("nonself improvement view must contain exactly 128 cells")

    runtime_checks = validate_runtime_precheck(project_root, plan["config"])
    checks, per_opponent_money = preregistered_checks(
        result,
        plan["config"]["development_gates"],
        totals,
        improvement_result=improvement,
        runtime_checks=runtime_checks,
    )
    result["aggregate_views"] = {
        "all_opponents_including_formal_self_lane": _summary_view(result),
        "improvement_excluding_formal_self_lane": _summary_view(improvement),
    }
    result["causal_counter_coverage"] = {
        "raw_cells": plan["cell_count"],
        "counter_rows": plan["cell_count"],
        "required_keys": list(COUNTER_NAMES),
    }
    result["causal_counter_totals"] = totals
    result["runtime_precheck_checks"] = runtime_checks
    result["per_opponent_money_delta_mean"] = per_opponent_money
    result["preregistered_gate_checks"] = checks
    result["preregistered_gate_pass"] = all(checks.values())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def run_development_lane(
    project_root: Path,
    lane: str,
    output: Path,
    workers: int,
) -> dict[str, Any]:
    """Run exactly one frozen candidate/control lane through runner.run_batch."""
    if lane not in {"candidate", "control"}:
        raise ValueError("lane must be candidate or control")
    if not 1 <= workers <= 12:
        raise ValueError("workers must be between 1 and 12")
    project_root = project_root.resolve()
    plan = frozen_development_plan(project_root)
    scenario_path = project_root / plan["config"]["scenario_config"]["path"]
    scenario_payload = _mapping(
        json.loads(scenario_path.read_text(encoding="utf-8")), "scenario config"
    )
    all_scenarios = _mapping(scenario_payload.get("scenarios"), "scenarios")
    scenarios = {
        name: dict(_mapping(all_scenarios.get(name), f"scenario {name}"))
        for name in plan["scenarios"]
    }
    return run_batch(
        plan[lane],
        list(plan["opponents"]),
        list(plan["seeds"]),
        output,
        workers,
        project_root,
        scenarios,
    )


def _percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * probability)]


def _load_agent(path: Path) -> tuple[Any, dict[str, Any]]:
    namespace = runpy.run_path(str(path))
    agent = namespace.get("agent")
    if not callable(agent):
        raise TypeError(f"agent callable not found in {path}")
    return agent, namespace


def _assert_priority_order(source: Path) -> None:
    tree = ast.parse(source.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_allocation_trace"
    )
    ranked_keys = []
    for node in ast.walk(function):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == "key" and isinstance(
            node.value, ast.Tuple
        ):
            ranked_keys.append([ast.unparse(item) for item in node.value.elts])
    if ["priority", "rank", "cost"] not in [key[:3] for key in ranked_keys]:
        raise ValueError("candidate priority/rank/cost AST invariant failed")


def _git_head(project_root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def generate_runtime_precheck(project_root: Path, output: Path) -> dict[str, Any]:
    """Reproduce the tracked 720-observation BT1 runtime/provenance report."""
    project_root = project_root.resolve()
    config = _mapping(
        json.loads((project_root / CONFIG_RELATIVE).read_text(encoding="utf-8")),
        "boundary config",
    )
    candidate = _mapping(config.get("candidate"), "candidate")
    control = _mapping(config.get("control"), "control")
    source = project_root / str(candidate["path"])
    reference = project_root / str(control["path"])
    replay_relative = Path("artifacts/submission_replays/episode-89143277-replay.json")
    replay_path = project_root / replay_relative
    generator_relative = Path("src/kaggriculture_lab/evaluation/last_chance_gate.py")
    generator_path = project_root / generator_relative
    if sha256(source) != candidate.get("sha256"):
        raise ValueError("runtime source does not match frozen candidate hash")
    if sha256(reference) != control.get("sha256"):
        raise ValueError("runtime reference does not match frozen control hash")
    _assert_priority_order(source)

    replay = _mapping(json.loads(replay_path.read_text(encoding="utf-8")), "replay")
    steps = replay.get("steps")
    if not isinstance(steps, list) or len(steps) != 720:
        raise ValueError("runtime replay must contain exactly 720 steps")
    candidate_agent, candidate_namespace = _load_agent(source)
    reference_agent, _ = _load_agent(reference)
    reset = candidate_namespace.get("reset_rescue_metrics")
    metrics = candidate_namespace.get("rescue_metrics")
    if not callable(reset) or not callable(metrics):
        raise TypeError("candidate counter export/reset API is missing")
    reset()

    timings_ms: list[float] = []
    invalid_outputs = 0
    difference_steps: list[int] = []
    for index, state in enumerate(steps):
        observation = state[0]["observation"]
        reference_action = reference_agent(copy.deepcopy(observation))
        started = time.perf_counter_ns()
        candidate_action = candidate_agent(copy.deepcopy(observation))
        timings_ms.append((time.perf_counter_ns() - started) / 1_000_000)
        if not isinstance(candidate_action, dict) or not {
            "farmer",
            "hands",
            "market",
        } <= candidate_action.keys():
            invalid_outputs += 1
        if candidate_action != reference_action:
            difference_steps.append(index)
    instrumentation = metrics()
    if not isinstance(instrumentation, dict) or set(instrumentation) != set(COUNTER_NAMES):
        raise ValueError("runtime instrumentation does not match the seven-counter API")

    gates = _mapping(config.get("runtime_gate_ms"), "runtime gates")
    report = {
        "schema_version": 2,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "git_head": _git_head(project_root),
        "command": (
            "uv run python -m kaggriculture_lab.evaluation.last_chance_gate "
            "--generate-runtime --project-root . "
            "--output experiments/evaluations/fa02_last_chance_tiebreak/BT1_runtime.json"
        ),
        "python": sys.version,
        "platform": platform.platform(),
        "generator": {
            "path": generator_relative.as_posix(),
            "sha256": sha256(generator_path),
        },
        "source": str(candidate["path"]),
        "source_sha256": sha256(source),
        "replay": replay_relative.as_posix(),
        "replay_sha256": sha256(replay_path),
        "player": 0,
        "calls": len(timings_ms),
        "invalid_outputs": invalid_outputs,
        "p50_ms": round(_percentile(timings_ms, 0.50), 4),
        "p95_ms": round(_percentile(timings_ms, 0.95), 4),
        "p99_ms": round(_percentile(timings_ms, 0.99), 4),
        "max_ms": round(max(timings_ms), 4),
        "reference_source": str(control["path"]),
        "reference_source_sha256": sha256(reference),
        "action_comparison_calls": len(timings_ms),
        "action_differences_vs_reference": len(difference_steps),
        "action_difference_steps": difference_steps,
        "priority_inversions": 0,
        "instrumentation": instrumentation,
        "comparison_method": (
            "Deep-copied player-0 observations from the tracked replay were passed "
            "sequentially to frozen final_day_labor and BT1; no environment or seed "
            "was run. BT1 counters were reset immediately before the 720-call pass."
        ),
        "runtime_gate_ms": dict(gates),
    }
    report["gate_result"] = (
        "PASS"
        if invalid_outputs == gates["invalid_outputs"]
        and report["p95_ms"] <= gates["p95_max"]
        and report["p99_ms"] <= gates["p99_max"]
        and report["max_ms"] <= gates["absolute_max"]
        and not difference_steps
        else "FAIL"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze frozen BT1 development reports")
    parser.add_argument("--candidate-report", type=Path)
    parser.add_argument("--control-report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--generate-runtime", action="store_true")
    parser.add_argument("--run-lane", choices=("candidate", "control"))
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.generate_runtime:
        report = generate_runtime_precheck(args.project_root, args.output)
        print(json.dumps(report, indent=2))
        return
    if args.run_lane:
        report = run_development_lane(
            args.project_root, args.run_lane, args.output, args.workers
        )
        print(json.dumps(report["summary"], indent=2))
        return
    if args.candidate_report is None or args.control_report is None:
        parser.error("analysis requires --candidate-report and --control-report")
    result = analyze_development(
        args.project_root.resolve(), args.candidate_report, args.control_report, args.output
    )
    print(
        json.dumps(
            {
                "gate_eligible": result["gate_eligible"],
                "raw_cells": result["raw_cells"],
                "checks": result["preregistered_gate_checks"],
                "pass": result["preregistered_gate_pass"],
                "output": str(args.output),
                "sha256": sha256(args.output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
