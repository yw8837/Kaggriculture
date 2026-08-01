from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

import kaggriculture_lab.evaluation.last_chance_gate as gate_module
from kaggriculture_lab.evaluation.last_chance_gate import (
    COUNTER_NAMES,
    FORMAL_OPPONENT,
    META_GATE_FIELDS,
    NUMERIC_GATE_FIELDS,
    aggregate_counters,
    analyze_development,
    frozen_development_plan,
    preregistered_checks,
    run_development_lane,
    validate_candidate_counter_evidence,
)

PROJECT_ROOT = Path.cwd()


def _json_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def _candidate_namespace() -> dict[str, object]:
    source = Path(
        "experiments/source_snapshots/fa02_last_chance_tiebreak/BT1.py"
    ).read_text(encoding="utf-8")
    namespace: dict[str, object] = {}
    exec(compile(source, "<bt1-safety-contract>", "exec"), namespace)  # noqa: S102
    return namespace


def _metrics() -> dict[str, int]:
    return {
        "eligible_opportunity": 1,
        "rank_tiebreak_activated": 1,
        "action_changed_vs_old_comparator_on_same_state": 1,
        "last_chance_action_emitted_on_exact_target": 1,
        "tiebreak_to_exact_target_action_emitted": 1,
        "formal_fallback_due_assignment_set_mismatch": 0,
        "next_day_weed_or_escape_outcome": 0,
    }


def _report(plan: dict, *, candidate: bool) -> dict:
    source_hash = plan["contract"][
        "candidate_source_sha256" if candidate else "control_source_sha256"
    ]
    effective_scenarios = {"default": {"episodeSteps": 720}}
    games = []
    for scenario, opponent, seed, seat in plan["cell_keys"]:
        effective = {"episodeSteps": 720, "seed": seed}
        games.append(
            {
                "scenario": scenario,
                "opponent": opponent,
                "seed": seed,
                "seat": seat,
                "candidate_money": 1000.0 if candidate else 500.0,
                "opponent_money": 900.0,
                "candidate_status": "DONE",
                "opponent_status": "DONE",
                "error": None,
                "effective_configuration": effective,
                "effective_configuration_sha256": _json_sha256(effective),
                "environment_configuration": effective,
                "environment_configuration_sha256": _json_sha256(effective),
                "resolved_environment_seed": seed,
                "candidate_metrics": _metrics() if candidate else None,
            }
        )
    totals = {name: len(games) * value for name, value in _metrics().items()}
    return {
        "candidate_sha256": source_hash,
        "candidate_sha256_at_start": source_hash,
        "candidate_sha256_at_end": source_hash,
        "sources_unchanged_during_run": True,
        "effective_scenarios": effective_scenarios,
        "effective_scenarios_sha256": _json_sha256(effective_scenarios),
        "opponent_sha256_at_start": dict(
            plan["contract"]["opponent_source_sha256"]
        ),
        "opponent_sha256_at_end": dict(plan["contract"]["opponent_source_sha256"]),
        "summary": {
            "raw_games": len(games),
            "candidate_metrics_games": len(games) if candidate else 0,
            "candidate_metrics_total": totals if candidate else {},
        },
        "games": games,
    }


def _write_reports(tmp_path: Path, candidate: dict, control: dict) -> tuple[Path, Path]:
    candidate_path = tmp_path / "candidate.json"
    control_path = tmp_path / "control.json"
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
    control_path.write_text(json.dumps(control), encoding="utf-8")
    return candidate_path, control_path


def _analyze(tmp_path: Path, candidate: dict, control: dict) -> dict:
    candidate_path, control_path = _write_reports(tmp_path, candidate, control)
    return analyze_development(
        PROJECT_ROOT, candidate_path, control_path, tmp_path / "gate.json"
    )


def _passing_result() -> dict:
    per_opponent = {
        name: {"money_delta_mean": 0.0}
        for name in (
            FORMAL_OPPONENT,
            "hamburger",
            "scenario_aware",
            "cow_tilt",
            "public_baseline",
        )
    }
    return {
        "candidate": {
            "failures": 0,
            "invalid": 0,
            "match_score": 0.70,
            "per_opponent": {
                FORMAL_OPPONENT: {"match_score": 0.55, "margin_mean": 0.0}
            },
        },
        "control": {"failures": 0, "invalid": 0},
        "paired": {
            "match_score_delta_mean": 0.02,
            "match_score_delta_seed_cluster_bootstrap_95": [-0.02, 0.10],
            "money_delta_mean": 250.0,
            "money_delta_p10": -1000.0,
            "per_opponent": per_opponent,
        },
    }


def _runtime_pass() -> dict[str, bool]:
    return {
        "runtime_source": True,
        "runtime_calls": True,
        "runtime_invalid": True,
        "runtime_p95": True,
        "runtime_p99": True,
        "runtime_max": True,
        "priority_boundary": True,
        "runtime_report_gate": True,
    }


def test_frozen_plan_derives_exact_candidate_control_and_160_cells() -> None:
    plan = frozen_development_plan(PROJECT_ROOT)
    assert plan["candidate"] == (
        "experiments/source_snapshots/fa02_last_chance_tiebreak/BT1.py"
    )
    assert plan["control"] == FORMAL_OPPONENT
    assert len(plan["opponents"]) == 5
    assert plan["seeds"] == list(range(34000, 34016))
    assert plan["scenarios"] == ["default"]
    assert plan["seats"] == [0, 1]
    assert plan["cell_count"] == len(plan["cell_keys"]) == 160
    assert len({tuple(key) for key in plan["cell_keys"]}) == 160


def _run_safety_contract(
    candidate_actions: list[list[str]], candidate_trace: tuple[tuple[object, ...], ...]
) -> tuple:
    namespace = _candidate_namespace()
    formal_actions = [["WATER"], ["MOVE", "N"]]
    formal_trace = (
        (0, 0, 0, 1, 0, 0, None, 0, True),
        (1, 1, 0, 1, 2, 2, None, 0, False),
    )

    def fake_trace(*args: object) -> tuple:
        ranked = args[-1]
        return (
            (candidate_actions, candidate_trace)
            if ranked
            else (formal_actions, formal_trace)
        )

    safe = namespace["_safe_allocation_actions"]
    safe.__globals__["_allocation_trace"] = fake_trace
    namespace["reset_rescue_metrics"]()
    tasks = [{"action": ["WATER"]}, {"action": ["MOVE"]}, {"action": ["FEED"]}]
    result = safe(None, None, None, None, None, tasks)
    return result, namespace["rescue_metrics"]()


def test_safety_contract_accepts_only_nonworsening_terminal_preserving_swap() -> None:
    candidate_actions = [["MOVE", "E"], ["WATER"]]
    candidate_trace = (
        (0, 1, 0, 0, 1, 1, None, 0, True),
        (1, 0, 0, 1, 0, 0, None, 0, False),
    )
    result, metrics = _run_safety_contract(candidate_actions, candidate_trace)
    assert result[0] == candidate_actions
    assert result[1] == candidate_trace
    assert result[7] is True
    assert metrics["formal_fallback_due_assignment_set_mismatch"] == 0


@pytest.mark.parametrize(
    ("candidate_actions", "candidate_trace"),
    [
        # Different task-id set.
        (
            [["MOVE", "E"], ["FEED"]],
            (
                (0, 1, 0, 0, 1, 1, None, 0, True),
                (1, 2, 0, 1, 0, 0, None, 0, False),
            ),
        ),
        # Same tasks, but task 0 is more expensive.
        (
            [["MOVE", "E"], ["WATER"]],
            (
                (0, 1, 0, 0, 1, 1, None, 0, True),
                (1, 0, 0, 1, 1, 0, None, 0, False),
            ),
        ),
        # Same assignment cost, but task 0 path cost is worse.
        (
            [["MOVE", "E"], ["WATER"]],
            (
                (0, 1, 0, 0, 1, 1, None, 0, True),
                (1, 0, 0, 1, 0, 1, None, 0, False),
            ),
        ),
        # Same tasks/costs, but candidate adds a pickup.
        (
            [["MOVE", "E"], ["WATER"]],
            (
                (0, 1, 0, 0, 1, 1, "WHEAT", 4, True),
                (1, 0, 0, 1, 0, 0, None, 0, False),
            ),
        ),
        # Same tasks/costs, but a formal non-PASS task becomes PASS.
        (
            [["PASS"], ["WATER"]],
            (
                (0, 1, 0, 0, 1, 1, None, 0, True),
                (1, 0, 0, 1, 0, 0, None, 0, False),
            ),
        ),
        # Same tasks/costs, but terminal WATER is no longer terminal.
        (
            [["MOVE", "E"], ["MOVE", "N"]],
            (
                (0, 1, 0, 0, 1, 1, None, 0, True),
                (1, 0, 0, 1, 0, 0, None, 0, False),
            ),
        ),
    ],
)
def test_safety_contract_falls_back_on_each_invariant_violation(
    candidate_actions: list[list[str]],
    candidate_trace: tuple[tuple[object, ...], ...],
) -> None:
    result, metrics = _run_safety_contract(candidate_actions, candidate_trace)
    formal_actions = [["WATER"], ["MOVE", "N"]]
    formal_trace = (
        (0, 0, 0, 1, 0, 0, None, 0, True),
        (1, 1, 0, 1, 2, 2, None, 0, False),
    )
    assert result[0] == formal_actions
    assert result[1] == formal_trace
    assert result[7] is False
    assert metrics["formal_fallback_due_assignment_set_mismatch"] == 1


@pytest.mark.parametrize("lane", ["candidate", "control"])
def test_lane_wrapper_calls_runner_with_only_frozen_default_grid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lane: str
) -> None:
    captured = {}

    def fake_run_batch(*args: object) -> dict:
        captured["args"] = args
        return {"summary": {"raw_games": 160}}

    monkeypatch.setattr(gate_module, "run_batch", fake_run_batch)
    output = tmp_path / f"{lane}.json"
    report = run_development_lane(PROJECT_ROOT, lane, output, workers=3)
    plan = frozen_development_plan(PROJECT_ROOT)
    args = captured["args"]
    assert args[0] == plan[lane]
    assert args[1] == plan["opponents"]
    assert args[2] == list(range(34000, 34016))
    assert args[3] == output
    assert args[4] == 3
    assert args[6] == {"default": {}}
    assert report["summary"]["raw_games"] == 160


def test_exact_reports_pass_and_publish_full_and_nonself_views(tmp_path: Path) -> None:
    plan = frozen_development_plan(PROJECT_ROOT)
    result = _analyze(tmp_path, _report(plan, candidate=True), _report(plan, candidate=False))
    assert result["gate_eligible"] is True
    assert result["raw_cells"] == 160
    assert result["aggregate_views"]["all_opponents_including_formal_self_lane"][
        "raw_cells"
    ] == 160
    assert result["aggregate_views"]["improvement_excluding_formal_self_lane"][
        "raw_cells"
    ] == 128
    assert result["causal_counter_coverage"]["counter_rows"] == 160
    assert result["causal_counter_totals"] == {
        "eligible_opportunity": 160,
        "rank_tiebreak_activated": 160,
        "action_changed_vs_old_comparator_on_same_state": 160,
        "last_chance_action_emitted_on_exact_target": 160,
        "tiebreak_to_exact_target_action_emitted": 160,
        "formal_fallback_due_assignment_set_mismatch": 0,
        "next_day_weed_or_escape_outcome": 0,
    }
    assert result["preregistered_gate_pass"] is True


@pytest.mark.parametrize("cell_count", [1, 159])
def test_gate_rejects_one_or_159_cells(tmp_path: Path, cell_count: int) -> None:
    plan = frozen_development_plan(PROJECT_ROOT)
    candidate = _report(plan, candidate=True)
    control = _report(plan, candidate=False)
    candidate["games"] = candidate["games"][:cell_count]
    control["games"] = control["games"][:cell_count]
    with pytest.raises(ValueError, match="160/160"):
        _analyze(tmp_path, candidate, control)


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        ("wrong_source", "source hash mismatch"),
        ("extra_scenario", "expected contract"),
        ("wrong_seed", "expected contract"),
        ("wrong_opponent", "expected contract"),
        ("wrong_opponent_hash", "opponent source hash mismatch"),
    ],
)
def test_gate_rejects_wrong_source_grid_or_hash(
    tmp_path: Path, mutation: str, match: str
) -> None:
    plan = frozen_development_plan(PROJECT_ROOT)
    candidate = _report(plan, candidate=True)
    control = _report(plan, candidate=False)
    if mutation == "wrong_source":
        candidate["candidate_sha256_at_end"] = "0" * 64
    elif mutation == "extra_scenario":
        candidate["games"][0]["scenario"] = "premium_glut"
        control["games"][0]["scenario"] = "premium_glut"
    elif mutation == "wrong_seed":
        candidate["games"][0]["seed"] = 33999
        control["games"][0]["seed"] = 33999
    elif mutation == "wrong_opponent":
        candidate["games"][0]["opponent"] = "unknown.py"
        control["games"][0]["opponent"] = "unknown.py"
    else:
        opponent = plan["opponents"][0]
        candidate["opponent_sha256_at_end"][opponent] = "0" * 64
    with pytest.raises(ValueError, match=match):
        _analyze(tmp_path, candidate, control)


@pytest.mark.parametrize("mutation", ["missing", "extra", "negative", "boolean"])
def test_every_candidate_row_requires_exact_nonnegative_integer_counters(
    tmp_path: Path, mutation: str
) -> None:
    plan = frozen_development_plan(PROJECT_ROOT)
    candidate = _report(plan, candidate=True)
    control = _report(plan, candidate=False)
    metrics = candidate["games"][0]["candidate_metrics"]
    if mutation == "missing":
        metrics.pop(COUNTER_NAMES[0])
    elif mutation == "extra":
        metrics["forged"] = 1
    elif mutation == "negative":
        metrics[COUNTER_NAMES[0]] = -1
    else:
        metrics[COUNTER_NAMES[0]] = True
    with pytest.raises((TypeError, ValueError), match="counter|invalid"):
        _analyze(tmp_path, candidate, control)


def test_gate_rejects_forged_counter_summary(tmp_path: Path) -> None:
    plan = frozen_development_plan(PROJECT_ROOT)
    candidate = _report(plan, candidate=True)
    candidate["summary"]["candidate_metrics_total"][COUNTER_NAMES[0]] += 1
    with pytest.raises(ValueError, match="recomputed raw totals"):
        _analyze(tmp_path, candidate, _report(plan, candidate=False))


def test_counter_aggregation_and_160_of_160_coverage_are_exact() -> None:
    plan = frozen_development_plan(PROJECT_ROOT)
    report = _report(plan, candidate=True)
    assert aggregate_counters(report["games"]) == report["summary"][
        "candidate_metrics_total"
    ]
    assert validate_candidate_counter_evidence(report, 160) == report["summary"][
        "candidate_metrics_total"
    ]


def test_runtime_report_binds_reproducible_generator_and_machine_provenance() -> None:
    report = json.loads(
        Path(
            "experiments/evaluations/fa02_last_chance_tiebreak/BT1_runtime.json"
        ).read_text(encoding="utf-8")
    )
    assert report["schema_version"] == 2
    assert report["created_at_utc"].endswith("+00:00")
    assert len(report["git_head"]) == 40
    assert report["command"] == (
        "uv run python -m kaggriculture_lab.evaluation.last_chance_gate "
        "--generate-runtime --project-root . "
        "--output experiments/evaluations/fa02_last_chance_tiebreak/BT1_runtime.json"
    )
    assert report["python"]
    assert report["platform"]
    generator = report["generator"]
    assert generator["path"] == (
        "src/kaggriculture_lab/evaluation/last_chance_gate.py"
    )
    assert generator["sha256"] == hashlib.sha256(
        Path(generator["path"]).read_bytes()
    ).hexdigest().upper()


def test_gate_module_consumes_every_preregistered_threshold() -> None:
    config = json.loads(
        Path("configs/fa02_last_chance_boundary.json").read_text(encoding="utf-8")
    )
    assert set(config["development_gates"]) == NUMERIC_GATE_FIELDS | META_GATE_FIELDS


def test_numeric_direct_nonself_per_opponent_runtime_and_counters_are_strict() -> None:
    config = json.loads(
        Path("configs/fa02_last_chance_boundary.json").read_text(encoding="utf-8")
    )
    gates = config["development_gates"]
    result = _passing_result()
    counters = _metrics()
    checks, _ = preregistered_checks(
        result,
        gates,
        counters,
        improvement_result=copy.deepcopy(result),
        runtime_checks=_runtime_pass(),
    )
    assert all(checks.values())

    direct = copy.deepcopy(result)
    direct["candidate"]["per_opponent"][FORMAL_OPPONENT]["margin_mean"] = -0.01
    assert preregistered_checks(
        direct, gates, counters, runtime_checks=_runtime_pass()
    )[0]["direct_formal_margin"] is False

    nonself = copy.deepcopy(result)
    nonself["paired"]["money_delta_mean"] = 249.99
    checks, _ = preregistered_checks(
        result,
        gates,
        counters,
        improvement_result=nonself,
        runtime_checks=_runtime_pass(),
    )
    assert checks["paired_money_mean_nonself"] is False

    opponent = copy.deepcopy(result)
    opponent["paired"]["per_opponent"]["hamburger"]["money_delta_mean"] = -0.01
    assert preregistered_checks(
        opponent, gates, counters, runtime_checks=_runtime_pass()
    )[0]["every_opponent_money"] is False

    runtime = _runtime_pass()
    runtime["runtime_p99"] = False
    assert preregistered_checks(
        result, gates, counters, runtime_checks=runtime
    )[0]["runtime_gate"] is False

    adverse = dict(counters, next_day_weed_or_escape_outcome=1)
    assert preregistered_checks(
        result, gates, adverse, runtime_checks=_runtime_pass()
    )[0]["next_day_adverse"] is False
