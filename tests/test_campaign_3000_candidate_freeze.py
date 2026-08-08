from __future__ import annotations

import importlib.util
import json
import math
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from kaggriculture_lab.evaluation import runner as evaluation_runner

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HERE = PROJECT_ROOT / "research/campaign_3000/06_candidates"
SPEC = importlib.util.spec_from_file_location("candidate_orchestrator", HERE / "orchestrator.py")
assert SPEC and SPEC.loader
orchestrator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(orchestrator)


def _load(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def _write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _valid_report_bundle(tmp_path: Path) -> dict[str, Path]:
    plan = _load("candidate_plan.json")
    contract = orchestrator.run_contract(plan, "Kag_01", "development")
    environment_snapshot = orchestrator._expected_environment_snapshot(plan)
    execution_inputs = orchestrator._execution_input_snapshot(plan)
    runner_started_path = tmp_path / "raw.started.json"
    outer_started_path = tmp_path / "outer.started.json"
    raw_report_path = tmp_path / "raw.json"
    outer_completed_path = tmp_path / "outer.completed.json"
    runner_started = {
        "candidate": contract["candidate_path"],
        "candidate_sha256_at_start": contract["candidate_sha256"],
        "opponents": contract["opponents"],
        "opponent_sha256_at_start": contract["opponent_sha256"],
        "seeds": contract["seeds"],
        "scenario_overrides": contract["scenarios"],
        "workers": plan["execution"]["workers"],
        "seat_policy": "both seats",
    }
    _write(runner_started_path, runner_started)
    outer_started = {
        "slot": "Kag_01",
        "phase": "development",
        "plan_sha256": orchestrator._sha256(HERE / "candidate_plan.json"),
        "gate_sha256": orchestrator._sha256(HERE / "gate_config.json"),
        "selection_sha256": orchestrator._sha256(HERE / "selection_evidence.json"),
        "runner_sha256": plan["runner"]["sha256"],
        "planned_engine": plan["engine"],
        "engine": environment_snapshot,
        "actual_environment_at_start": environment_snapshot,
        "execution_inputs_at_start": execution_inputs,
        "sources_at_start": contract["sources"],
        "grid_sha256": contract["grid_sha256"],
    }
    _write(outer_started_path, outer_started)
    games = []
    for cell in orchestrator.expected_grid(plan, "Kag_01", "development"):
        configuration = {
            "episodeSteps": 720,
            **contract["scenarios"][cell["scenario"]],
            "seed": cell["seed"],
        }
        environment_configuration = {
            **_load("gate_config.json")["hard_integrity"][
                "environment_configuration_contract"
            ],
            **contract["scenarios"][cell["scenario"]],
            "episodeSteps": plan["engine"]["episode_steps"],
            "seed": None,
        }
        games.append(
            {
                "opponent": cell["opponent"],
                "seed": cell["seed"],
                "seat": cell["seat"],
                "candidate_money": 20000.0,
                "opponent_money": 5000.0,
                "candidate_status": "DONE",
                "opponent_status": "DONE",
                "elapsed_seconds": 2.0,
                "error": None,
                "scenario": cell["scenario"],
                "effective_configuration": configuration,
                "effective_configuration_sha256": orchestrator._json_sha256(configuration),
                "environment_configuration": environment_configuration,
                "environment_configuration_sha256": orchestrator._json_sha256(
                    environment_configuration
                ),
                "resolved_environment_seed": cell["seed"],
                "candidate_metrics": None,
                "hidden_abnormal_status": None,
                "runtime_make_callable": _load("gate_config.json")["hard_integrity"][
                    "runtime_make_callable_contract"
                ],
            }
        )
    report = {
        "start_receipt_sha256": orchestrator._sha256(runner_started_path),
        "candidate": contract["candidate_path"],
        "candidate_sha256": contract["candidate_sha256"],
        "candidate_sha256_at_start": contract["candidate_sha256"],
        "candidate_sha256_at_end": contract["candidate_sha256"],
        "opponents": contract["opponents"],
        "opponent_sha256_at_start": contract["opponent_sha256"],
        "opponent_sha256_at_end": contract["opponent_sha256"],
        "sources_unchanged_during_run": True,
        "seeds": contract["seeds"],
        "scenario_overrides": contract["scenarios"],
        "summary": {"failed_raw_games": 0, "hidden_abnormal_status_failures": 0},
        "games": games,
    }
    _write(raw_report_path, report)
    outer_completed = {
        "outer_start_receipt_sha256": orchestrator._sha256(outer_started_path),
        "runner_start_receipt_sha256": orchestrator._sha256(runner_started_path),
        "raw_report_sha256": orchestrator._sha256(raw_report_path),
        "plan_sha256_at_end": orchestrator._sha256(HERE / "candidate_plan.json"),
        "gate_sha256_at_end": orchestrator._sha256(HERE / "gate_config.json"),
        "selection_sha256_at_end": orchestrator._sha256(HERE / "selection_evidence.json"),
        "runner_sha256_at_end": plan["runner"]["sha256"],
        "planned_engine_at_end": plan["engine"],
        "engine_at_end": environment_snapshot,
        "actual_environment_at_end": environment_snapshot,
        "execution_inputs_at_end": execution_inputs,
        "sources_at_end": contract["sources"],
        "executed_cells": contract["expected_cells"],
        "sources_unchanged_during_phase": True,
        "environment_unchanged_during_phase": True,
        "configs_unchanged_during_phase": True,
    }
    _write(outer_completed_path, outer_completed)
    return {
        "raw": raw_report_path,
        "runner": runner_started_path,
        "outer_start": outer_started_path,
        "outer_complete": outer_completed_path,
    }


def _refresh_raw_receipt(bundle: dict[str, Path], report: dict) -> None:
    _write(bundle["raw"], report)
    completed = json.loads(bundle["outer_complete"].read_text(encoding="utf-8"))
    completed["raw_report_sha256"] = orchestrator._sha256(bundle["raw"])
    _write(bundle["outer_complete"], completed)


def _authorize_bundle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    bundle: dict[str, Path],
    *,
    runner_path: Path | None = None,
) -> Path:
    """Inject a validated authority boundary while keeping report files in pytest temp space."""
    selected_runner = runner_path or bundle["runner"]
    authority = {
        "authority_commit": "C" * 40,
        "execution_commit": "E" * 40,
        "auditor_task_id": orchestrator.AUDITOR_TASK_ID,
    }
    runner_argv = ["python", "authorized_runner.py", "--run-receipt", "authorized_run.json"]
    portable_paths = {
        "test/raw.json": bundle["raw"].resolve(),
        "test/raw.started.json": selected_runner.resolve(),
        "test/outer.started.json": bundle["outer_start"].resolve(),
        "test/outer.completed.json": bundle["outer_complete"].resolve(),
    }
    authorized_run = {
        "slot": "Kag_01",
        "phase": "development",
        "authority": authority,
        "runner_argv": runner_argv,
        "actual_environment_at_receipt_creation": orchestrator._expected_environment_snapshot(
            _load("candidate_plan.json")
        ),
        "execution_inputs_at_receipt_creation": orchestrator._execution_input_snapshot(
            _load("candidate_plan.json")
        ),
        "outputs": {
            "raw_report": "test/raw.json",
            "runner_started": "test/raw.started.json",
            "outer_started": "test/outer.started.json",
            "outer_completed": "test/outer.completed.json",
        },
    }
    run_receipt = tmp_path / "authorized_run.json"
    _write(run_receipt, {"fixture": "validated-authority-boundary"})
    monkeypatch.setattr(
        orchestrator,
        "validate_authorized_run_receipt",
        lambda path: authorized_run if path.resolve() == run_receipt.resolve() else None,
    )
    original_repo_path = orchestrator._repo_path
    monkeypatch.setattr(
        orchestrator,
        "_repo_path",
        lambda root, portable: portable_paths.get(portable, original_repo_path(root, portable)),
    )

    runner = json.loads(bundle["runner"].read_text(encoding="utf-8"))
    runner["git_head_at_start"] = authority["authority_commit"]
    _write(bundle["runner"], runner)
    report = json.loads(bundle["raw"].read_text(encoding="utf-8"))
    report["start_receipt_sha256"] = orchestrator._sha256(bundle["runner"])
    report["git_head_at_start"] = authority["authority_commit"]
    _write(bundle["raw"], report)
    run_sha = orchestrator._sha256(run_receipt)
    outer_start = json.loads(bundle["outer_start"].read_text(encoding="utf-8"))
    outer_start.update(
        {
            "authorized_run_receipt_sha256": run_sha,
            "authority": authority,
            "runner_argv": runner_argv,
        }
    )
    _write(bundle["outer_start"], outer_start)
    outer_complete = json.loads(bundle["outer_complete"].read_text(encoding="utf-8"))
    outer_complete.update(
        {
            "outer_start_receipt_sha256": orchestrator._sha256(bundle["outer_start"]),
            "runner_start_receipt_sha256": orchestrator._sha256(bundle["runner"]),
            "raw_report_sha256": orchestrator._sha256(bundle["raw"]),
            "authorized_run_receipt_sha256": run_sha,
        }
    )
    _write(bundle["outer_complete"], outer_complete)
    return run_receipt


def test_closed_plan_has_exact_isolated_sources_and_disjoint_fresh_ranges() -> None:
    result = orchestrator.validate_plan()
    plan = _load("candidate_plan.json")
    scan = orchestrator.scan_observed_seeds()
    observed = set(scan["observed_seed_values"])
    reserved: set[int] = set()

    assert result["status"] == "VALID_CLOSED_PLAN"
    assert result["fresh_games_executed"] == 0
    assert [item["archive_name"] for item in plan["candidates"]] == [
        "Kag_01 - Tetsu v16 Exact.tar.gz",
        "Kag_02 - Kaito v22 Price Impact.tar.gz",
    ]
    for candidate in plan["candidates"]:
        assert candidate["status"] == "CLOSED"
        assert candidate["candidate_path"].startswith(
            "research/campaign_3000/06_candidates/snapshots/"
        )
        assert candidate["candidate_alias"] not in candidate["opponents"]
        for phase, pool in candidate["seed_pools"].items():
            values = set(range(pool["start"], pool["end_inclusive"] + 1))
            assert pool == {
                "start": pool["start"],
                "end_inclusive": pool["end_inclusive"],
                "count": len(values),
                "status": "CLOSED",
                "opened": False,
                "consumed": False,
                "evaluated_games": 0,
            }
            assert not values & observed
            assert not values & reserved
            reserved.update(values)
            grid = orchestrator.expected_grid(plan, candidate["slot"], phase)
            assert len(grid) == candidate["expected_cells"][phase]
            assert {row["seat"] for row in grid} == {0, 1}
            assert {row["seed_status"] for row in grid} == {"CLOSED"}


def test_open_is_hard_blocked_and_nonfinite_metrics_are_rejected() -> None:
    with pytest.raises(PermissionError, match="CLOSED"):
        orchestrator.require_open_authority()
    with pytest.raises(ValueError, match="nonfinite candidate_money"):
        orchestrator.summarize_rows(
            [
                {
                    "candidate_money": math.nan,
                    "opponent_money": 1.0,
                    "elapsed_seconds": 1.0,
                    "seed": 1,
                    "opponent": "fa04_g1",
                    "scenario": "default",
                }
            ],
            _load("gate_config.json")["bootstrap"],
        )
    with pytest.raises(ValueError, match="Out of range float values"):
        orchestrator._json_sha256({"nonfinite": math.nan})


def test_runner_records_actual_hidden_abnormal_step_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeEnvironment:
        def __init__(self) -> None:
            self.configuration = {"episodeSteps": 720, "seed": None}
            self.info = {"seed": 50000}
            self.steps = [
                [
                    SimpleNamespace(reward=None, status="ACTIVE"),
                    SimpleNamespace(reward=None, status="ACTIVE"),
                ],
                [
                    SimpleNamespace(reward=None, status="ERROR"),
                    SimpleNamespace(reward=None, status="ACTIVE"),
                ],
                [
                    SimpleNamespace(reward=0.0, status="DONE"),
                    SimpleNamespace(reward=1.0, status="DONE"),
                ],
            ]

        def run(self, _agents: list[object]) -> None:
            return None

    def fake_make(*_args: object, **_kwargs: object) -> FakeEnvironment:
        return FakeEnvironment()
    monkeypatch.setattr(
        evaluation_runner,
        "_validated_kaggle_make",
        lambda: (fake_make, evaluation_runner.EXPECTED_MAKE_CALLABLE),
    )
    result = evaluation_runner._run_game(
        evaluation_runner.GameSpec(
            "candidate.py",
            "opponent.py",
            "opponent",
            50000,
            0,
            str(tmp_path),
        )
    )

    assert result.hidden_abnormal_status == {
        "step": 1,
        "player": 0,
        "status": "ERROR",
    }
    assert evaluation_runner.summarize([result])["hidden_abnormal_status_failures"] == 1


def test_exploratory_saverun_is_explicitly_not_strict_promotion() -> None:
    summary = {
        "match_score": 0.34,
        "match_score_seed_cluster_bootstrap_95": [0.20, 0.48],
        "mean_margin": -100.0,
        "margin_p10": -1000.0,
        "game_runtime_p99_seconds": 20.0,
        "game_runtime_max_seconds": 21.0,
        "by_opponent_match_score": {"fa04_g1": 1.0, "tetsu_v16": 0.0},
        "by_opponent_mean_margin": {"fa04_g1": 25000.0, "tetsu_v16": -4000.0},
        "by_scenario_match_score": {"default": 0.34},
        "by_scenario_mean_margin": {"default": -100.0},
    }
    strict = orchestrator.evaluate_thresholds(summary, "development")
    exploratory = orchestrator.evaluate_exploratory_readiness(summary, True, True)

    assert strict["verdict"] == "NO_GO"
    assert exploratory == {
        "verdict": "EXPLORATORY_PRIVATE_SAVERUN_READY_NON_PROMOTION",
        "checks": {
            "hard_integrity": True,
            "runtime_p99": True,
            "runtime_max": True,
            "fa04_g1_match_score": True,
            "fa04_g1_mean_margin": True,
            "package_and_final_audit": True,
        },
        "strict_promotion_claim": False,
    }


def test_report_validator_accepts_only_the_exact_128_cell_grid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = _valid_report_bundle(tmp_path)
    run_receipt = _authorize_bundle(monkeypatch, tmp_path, bundle)
    rows = orchestrator.validate_report_files(
        "Kag_01",
        "development",
        bundle["raw"],
        bundle["runner"],
        bundle["outer_start"],
        bundle["outer_complete"],
        run_receipt,
    )
    assert len(rows) == 128


@pytest.mark.parametrize("mutation", ["one_of_127", "duplicate", "wrong_seed", "wrong_source", "error_before_done"])
def test_report_validator_rejects_adversarial_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    bundle = _valid_report_bundle(tmp_path)
    report = json.loads(bundle["raw"].read_text(encoding="utf-8"))
    if mutation == "one_of_127":
        report["games"].pop()
    elif mutation == "duplicate":
        report["games"][-1] = deepcopy(report["games"][0])
    elif mutation == "wrong_seed":
        row = report["games"][0]
        row["seed"] = 49999
        row["resolved_environment_seed"] = 49999
        row["effective_configuration"]["seed"] = 49999
        row["effective_configuration_sha256"] = orchestrator._json_sha256(
            row["effective_configuration"]
        )
    elif mutation == "wrong_source":
        report["candidate_sha256_at_end"] = "B" * 64
    else:
        report["games"][0]["error"] = "framework_status_ERROR_before_terminal_DONE"
    _refresh_raw_receipt(bundle, report)
    run_receipt = _authorize_bundle(monkeypatch, tmp_path, bundle)

    with pytest.raises(ValueError):
        orchestrator.validate_report_files(
            "Kag_01",
            "development",
            bundle["raw"],
            bundle["runner"],
            bundle["outer_start"],
            bundle["outer_complete"],
            run_receipt,
        )


def test_report_validator_rejects_missing_separate_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = _valid_report_bundle(tmp_path)
    missing = tmp_path / "missing.started.json"
    run_receipt = _authorize_bundle(
        monkeypatch, tmp_path, bundle, runner_path=missing
    )
    with pytest.raises(ValueError, match="missing separate receipt"):
        orchestrator.validate_report_files(
            "Kag_01",
            "development",
            bundle["raw"],
            missing,
            bundle["outer_start"],
            bundle["outer_complete"],
            run_receipt,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_environment",
        "environment_hash_mismatch",
        "environment_default_mutated",
        "environment_seed_missing",
        "environment_seed_wrong",
        "environment_seed_exact_int",
        "environment_random_seed",
        "seed_bool",
        "seed_string",
        "seat_bool",
        "seat_out_of_range",
        "elapsed_negative",
        "elapsed_bool",
        "hidden_abnormal_missing",
        "hidden_abnormal_forged",
        "hidden_abnormal_summary_missing",
        "hidden_abnormal_summary_bool",
        "failed_raw_games_bool",
        "environment_nan",
        "environment_typed_equality",
        "effective_typed_equality",
        "effective_nan",
        "resolved_seed_bool",
        "runtime_make_missing",
        "runtime_make_forged",
    ],
)
def test_report_validator_rejects_lossy_or_unbound_row_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    bundle = _valid_report_bundle(tmp_path)
    report = json.loads(bundle["raw"].read_text(encoding="utf-8"))
    row = report["games"][0]
    if mutation == "missing_environment":
        del row["environment_configuration"]
    elif mutation == "environment_hash_mismatch":
        row["environment_configuration_sha256"] = "B" * 64
    elif mutation == "environment_default_mutated":
        row["environment_configuration"]["shedCapacity"] = 101
        row["environment_configuration_sha256"] = orchestrator._json_sha256(
            row["environment_configuration"]
        )
    elif mutation == "environment_seed_missing":
        del row["environment_configuration"]["seed"]
        row["environment_configuration_sha256"] = orchestrator._json_sha256(
            row["environment_configuration"]
        )
    elif mutation == "environment_seed_wrong":
        row["environment_configuration"]["seed"] = row["seed"] + 1
        row["environment_configuration_sha256"] = orchestrator._json_sha256(
            row["environment_configuration"]
        )
    elif mutation == "environment_seed_exact_int":
        row["environment_configuration"]["seed"] = row["seed"]
        row["environment_configuration_sha256"] = orchestrator._json_sha256(
            row["environment_configuration"]
        )
    elif mutation == "environment_random_seed":
        row["environment_configuration"]["randomSeed"] = row["seed"]
        row["environment_configuration_sha256"] = orchestrator._json_sha256(
            row["environment_configuration"]
        )
    elif mutation == "environment_nan":
        row["environment_configuration"]["weedSpawnChance"] = math.nan
        row["environment_configuration_sha256"] = "C" * 64
    elif mutation == "environment_typed_equality":
        row["environment_configuration"]["shedCapacity"] = 100.0
        row["environment_configuration_sha256"] = orchestrator._json_sha256(
            row["environment_configuration"]
        )
    elif mutation == "effective_typed_equality":
        row["effective_configuration"]["episodeSteps"] = 720.0
        row["effective_configuration_sha256"] = orchestrator._json_sha256(
            row["effective_configuration"]
        )
    elif mutation == "effective_nan":
        row["effective_configuration"]["episodeSteps"] = math.nan
        row["effective_configuration_sha256"] = "D" * 64
    elif mutation == "seed_bool":
        row["seed"] = True
    elif mutation == "seed_string":
        row["seed"] = str(row["seed"])
    elif mutation == "seat_bool":
        row["seat"] = False
    elif mutation == "seat_out_of_range":
        row["seat"] = 2
    elif mutation == "elapsed_negative":
        row["elapsed_seconds"] = -0.001
    elif mutation == "elapsed_bool":
        row["elapsed_seconds"] = False
    elif mutation == "hidden_abnormal_missing":
        del row["hidden_abnormal_status"]
    elif mutation == "hidden_abnormal_forged":
        row["hidden_abnormal_status"] = False
    elif mutation == "hidden_abnormal_summary_missing":
        del report["summary"]["hidden_abnormal_status_failures"]
    elif mutation == "hidden_abnormal_summary_bool":
        report["summary"]["hidden_abnormal_status_failures"] = False
    elif mutation == "failed_raw_games_bool":
        report["summary"]["failed_raw_games"] = False
    elif mutation == "runtime_make_missing":
        del row["runtime_make_callable"]
    elif mutation == "runtime_make_forged":
        row["runtime_make_callable"]["ast_function_sha256"] = "E" * 64
    else:
        row["resolved_environment_seed"] = True
    _refresh_raw_receipt(bundle, report)
    run_receipt = _authorize_bundle(monkeypatch, tmp_path, bundle)

    with pytest.raises((TypeError, ValueError)):
        orchestrator.validate_report_files(
            "Kag_01",
            "development",
            bundle["raw"],
            bundle["runner"],
            bundle["outer_start"],
            bundle["outer_complete"],
            run_receipt,
        )


@pytest.mark.parametrize(
    "mutation",
    ["environment_end", "execution_inputs_end", "derived_environment_flag"],
)
def test_report_validator_rejects_static_or_forged_runtime_freeze_receipts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    bundle = _valid_report_bundle(tmp_path)
    completed = json.loads(bundle["outer_complete"].read_text(encoding="utf-8"))
    if mutation == "environment_end":
        completed["actual_environment_at_end"]["version"] = "0.0.0-forged"
    elif mutation == "execution_inputs_end":
        completed["execution_inputs_at_end"]["runner"] = "F" * 64
        completed["runner_sha256_at_end"] = "F" * 64
    else:
        completed["environment_unchanged_during_phase"] = False
    _write(bundle["outer_complete"], completed)
    run_receipt = _authorize_bundle(monkeypatch, tmp_path, bundle)

    with pytest.raises(ValueError):
        orchestrator.validate_report_files(
            "Kag_01",
            "development",
            bundle["raw"],
            bundle["runner"],
            bundle["outer_start"],
            bundle["outer_complete"],
            run_receipt,
        )


def _strict_summary() -> dict:
    return {
        "match_score": 0.75,
        "match_score_seed_cluster_bootstrap_95": [0.60, 0.90],
        "mean_margin": 1000.0,
        "margin_p10": 100.0,
        "game_runtime_p99_seconds": 1.0,
        "game_runtime_max_seconds": 2.0,
        "by_opponent_match_score": {"a": 0.75, "b": 0.50},
        "by_opponent_mean_margin": {"a": 4000.0, "b": 100.0},
        "by_scenario_match_score": {"default": 0.75},
        "by_scenario_mean_margin": {"default": 1000.0},
    }


def test_strict_gate_cannot_average_away_an_opponent_margin_regression() -> None:
    summary = _strict_summary()
    summary["by_opponent_mean_margin"]["b"] = -1.0

    result = orchestrator.evaluate_thresholds(summary, "development")

    assert result["verdict"] == "NO_GO"
    assert result["checks"]["mean_margin"] is True
    assert result["checks"]["each_opponent_mean_margin"] is False


def test_robustness_gate_cannot_average_away_a_scenario_margin_regression() -> None:
    summary = _strict_summary()
    summary["by_scenario_match_score"] = {"default": 0.90, "premium_glut": 0.50}
    summary["by_scenario_mean_margin"] = {
        "default": 3000.0,
        "premium_glut": -1.0,
    }

    result = orchestrator.evaluate_thresholds(summary, "robustness")

    assert result["verdict"] == "NO_GO"
    assert result["checks"]["each_scenario"] is True
    assert result["checks"]["each_scenario_mean_margin"] is False


def test_canonical_json_hashes_match_runner_and_reject_type_equivalence() -> None:
    value = {"한글": [1, 1.0, True, None], "nested": {"x": "농장"}}
    assert orchestrator._json_sha256(value) == evaluation_runner._json_sha256(value)
    assert orchestrator._json_sha256({"x": 1}) != orchestrator._json_sha256({"x": 1.0})
    assert orchestrator._json_sha256({"x": 1}) != orchestrator._json_sha256({"x": True})
    with pytest.raises(ValueError, match="typed mismatch"):
        orchestrator._require_typed_json_equal({"x": True}, {"x": 1}, "typed")
    assert evaluation_runner.EXPECTED_MAKE_CALLABLE == _load("gate_config.json")[
        "hard_integrity"
    ]["runtime_make_callable_contract"]


def test_worker_accepts_only_the_frozen_real_make_callable() -> None:
    make_callable, snapshot = evaluation_runner._validated_kaggle_make()
    assert callable(make_callable)
    assert snapshot == evaluation_runner.EXPECTED_MAKE_CALLABLE


def test_environment_snapshot_baseline_equals_expected() -> None:
    plan = _load("candidate_plan.json")
    assert orchestrator._environment_snapshot() == orchestrator._expected_environment_snapshot(
        plan
    )


def test_fresh_process_outer_and_worker_callable_baselines_match() -> None:
    script = f"""
import importlib.util
from pathlib import Path
from kaggriculture_lab.evaluation import runner
p=Path({str(HERE / 'orchestrator.py')!r})
s=importlib.util.spec_from_file_location('fresh_callable_probe',p)
m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
plan=m._load(m.PLAN_PATH)
outer=m._environment_snapshot()['make_callable']
expected=m._expected_environment_snapshot(plan)['make_callable']
_,worker=runner._validated_kaggle_make()
assert outer == expected == worker
print('FRESH_CALLABLE_BASELINE_PASS')
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.stdout.strip() == "FRESH_CALLABLE_BASELINE_PASS"


@pytest.mark.parametrize("payload", ['{"x":NaN}', '{"x":1,"x":2}'])
def test_strict_json_loader_rejects_nonfinite_and_duplicate_keys(
    tmp_path: Path, payload: str
) -> None:
    path = tmp_path / "adversarial.json"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError):
        orchestrator._load(path)


@pytest.mark.parametrize("resolved_seed", [True, "50000", 50000.0, 50001])
def test_runner_rejects_lossy_resolved_environment_seed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    resolved_seed: object,
) -> None:
    class FakeEnvironment:
        def __init__(self) -> None:
            self.configuration = {"episodeSteps": 720, "seed": None}
            self.info = {"seed": resolved_seed}
            self.steps = [[
                SimpleNamespace(reward=1.0, status="DONE"),
                SimpleNamespace(reward=0.0, status="DONE"),
            ]]

        def run(self, _agents: list[object]) -> None:
            return None

    def fake_make(*_args: object, **_kwargs: object) -> FakeEnvironment:
        return FakeEnvironment()
    monkeypatch.setattr(
        evaluation_runner,
        "_validated_kaggle_make",
        lambda: (fake_make, evaluation_runner.EXPECTED_MAKE_CALLABLE),
    )
    result = evaluation_runner._run_game(
        evaluation_runner.GameSpec(
            "candidate.py", "opponent.py", "opponent", 50000, 0, str(tmp_path)
        )
    )
    assert result.candidate_status == "EXCEPTION"
    assert result.error == "ValueError: environment resolved seed is not the exact requested int"


def test_runner_rejects_random_seed_in_direct_scenario_mapping(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.py"
    opponent = tmp_path / "opponent.py"
    candidate.write_text("def agent(obs): return {}\n", encoding="utf-8")
    opponent.write_text("def agent(obs): return {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="runner-controlled"):
        evaluation_runner.run_batch(
            str(candidate),
            [str(opponent)],
            [50000],
            tmp_path / "should-not-exist.json",
            1,
            tmp_path,
            {"bad": {"randomSeed": 7}},
        )


def test_environment_snapshot_rejects_import_shadow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    shadow = tmp_path / "kaggle_environments" / "__init__.py"
    shadow.parent.mkdir()
    shadow.write_text("", encoding="utf-8")
    real_import = orchestrator.importlib.import_module

    def fake_import(name: str) -> object:
        if name == "kaggle_environments":
            return SimpleNamespace(__file__=str(shadow))
        return real_import(name)

    monkeypatch.setattr(orchestrator.importlib, "import_module", fake_import)
    snapshot = orchestrator._environment_snapshot()
    assert snapshot["import_paths_match_distribution"] is False
    assert snapshot != orchestrator._expected_environment_snapshot(_load("candidate_plan.json"))


def test_environment_snapshot_rejects_runtime_dependency_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_sha256 = orchestrator._sha256

    def mutated_sha(path: Path) -> str:
        if path.as_posix().endswith("kaggle_environments/utils.py"):
            return "F" * 64
        return real_sha256(path)

    monkeypatch.setattr(orchestrator, "_sha256", mutated_sha)
    snapshot = orchestrator._environment_snapshot()
    expected = orchestrator._expected_environment_snapshot(_load("candidate_plan.json"))
    assert snapshot["runtime_dependencies"]["kaggle_environments/utils.py"] != expected[
        "runtime_dependencies"
    ]["kaggle_environments/utils.py"]


def test_environment_snapshot_detects_make_callable_monkeypatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import kaggle_environments

    monkeypatch.setattr(kaggle_environments, "make", lambda *_args, **_kwargs: None)
    snapshot = orchestrator._environment_snapshot()
    expected = orchestrator._expected_environment_snapshot(_load("candidate_plan.json"))
    assert snapshot["runtime_dependencies"] == expected["runtime_dependencies"]
    assert snapshot["make_callable"] != expected["make_callable"]


def test_worker_rejects_package_make_monkeypatch(monkeypatch: pytest.MonkeyPatch) -> None:
    import kaggle_environments

    monkeypatch.setattr(kaggle_environments, "make", lambda *_args, **_kwargs: None)
    with pytest.raises(RuntimeError, match="callable identity mismatch"):
        evaluation_runner._validated_kaggle_make()


def test_worker_rejects_forged_core_filename_and_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import kaggle_environments
    import kaggle_environments.core as core_module

    core_path = str(Path(core_module.__file__).resolve())

    def forged_make(*_args: object, **_kwargs: object) -> None:
        return None

    forged_make.__module__ = "kaggle_environments.core"
    forged_make.__qualname__ = "make"
    forged_make.__code__ = forged_make.__code__.replace(co_filename=core_path)
    monkeypatch.setattr(core_module, "make", forged_make)
    monkeypatch.setattr(kaggle_environments, "make", forged_make)
    with pytest.raises(RuntimeError, match="callable identity mismatch"):
        evaluation_runner._validated_kaggle_make()


def test_runtime_startup_environment_is_absent_or_empty_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _load("candidate_plan.json")
    monkeypatch.setenv("PYTHONSTARTUP", "")
    assert orchestrator._environment_snapshot() == orchestrator._expected_environment_snapshot(
        plan
    )
    monkeypatch.setenv("PYTHONSTARTUP", "C:/attacker/startup.py")
    snapshot = orchestrator._environment_snapshot()
    assert snapshot["startup_environment"]["PYTHONSTARTUP"] == "C:/attacker/startup.py"
    assert snapshot != orchestrator._expected_environment_snapshot(plan)
    with pytest.raises(RuntimeError, match="callable identity mismatch"):
        evaluation_runner._validated_kaggle_make()


def test_environment_snapshot_blocks_pythonpath_shadow_in_subprocess(
    tmp_path: Path,
) -> None:
    shadow = tmp_path / "kaggle_environments"
    shadow.mkdir()
    (shadow / "__init__.py").write_text("", encoding="utf-8")
    script = f"""
import importlib.util
from pathlib import Path
p=Path({str(HERE / 'orchestrator.py')!r})
s=importlib.util.spec_from_file_location('shadow_probe',p)
m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
try:
    snapshot=m._environment_snapshot()
except Exception as exc:
    print('BLOCKED:'+type(exc).__name__)
else:
    print('BLOCKED:SHADOW' if not snapshot['import_paths_match_distribution'] else 'UNSAFE_PASS')
"""
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=PROJECT_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.stdout.strip().startswith("BLOCKED:")


def test_execute_derives_environment_unchanged_from_live_end_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = _load("candidate_plan.json")
    contract = orchestrator.run_contract(plan, "Kag_01", "development")
    paths = {
        "authorized_run_receipt": "test/authorized_run.json",
        "raw_report": "test/raw.json",
        "runner_started": "test/raw.started.json",
        "outer_started": "test/outer.started.json",
        "outer_completed": "test/outer.completed.json",
    }
    actual_paths = {key: tmp_path / Path(value).name for key, value in paths.items()}
    run_path = actual_paths["authorized_run_receipt"]
    _write(run_path, {"fixture": True})
    expected_environment = orchestrator._expected_environment_snapshot(plan)
    changed_environment = deepcopy(expected_environment)
    changed_environment["runtime_dependencies_sha256"] = "E" * 64
    execution_inputs = {
        "runner": plan["runner"]["sha256"],
        "scenario_source": plan["scenario_source"]["sha256"],
    }
    run = {
        "slot": "Kag_01",
        "phase": "development",
        "contract": contract,
        "outputs": paths,
        "plan_sha256": "A" * 64,
        "gate_sha256": "B" * 64,
        "selection_sha256": "C" * 64,
        "authority": {"authority_commit": "D" * 40},
        "runner_argv": ["python", "authorized_runner.py"],
        "actual_environment_at_receipt_creation": expected_environment,
        "execution_inputs_at_receipt_creation": execution_inputs,
        "sources_at_receipt_creation": contract["sources"],
    }
    monkeypatch.setattr(orchestrator, "validate_authorized_run_receipt", lambda _path: run)
    monkeypatch.setattr(
        orchestrator,
        "_repo_path",
        lambda _root, portable: actual_paths.get(
            next((key for key, value in paths.items() if value == portable), ""),
            PROJECT_ROOT / portable,
        ),
    )
    snapshots = iter([expected_environment, changed_environment])
    monkeypatch.setattr(orchestrator, "_environment_snapshot", lambda: next(snapshots))
    monkeypatch.setattr(orchestrator, "_execution_input_snapshot", lambda _plan: execution_inputs)
    monkeypatch.setattr(orchestrator, "_source_snapshot", lambda _contract: contract["sources"])

    def fake_run_batch(*_args: object, **_kwargs: object) -> dict:
        report = {
            "games": [],
            "summary": {"failed_raw_games": 0, "hidden_abnormal_status_failures": 0},
            "sources_unchanged_during_run": True,
        }
        _write(actual_paths["raw_report"], report)
        _write(actual_paths["runner_started"], {"started": True})
        return report

    monkeypatch.setattr(evaluation_runner, "run_batch", fake_run_batch)
    with pytest.raises(RuntimeError, match="runtime freeze drift"):
        orchestrator.execute_authorized_run_receipt(run_path)
    completed = json.loads(actual_paths["outer_completed"].read_text(encoding="utf-8"))
    assert completed["actual_environment_at_end"] == changed_environment
    assert completed["environment_unchanged_during_phase"] is False
