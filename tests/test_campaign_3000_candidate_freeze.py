from __future__ import annotations

import importlib.util
import json
import math
from copy import deepcopy
from pathlib import Path

import pytest

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
        "engine": plan["engine"],
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
                "environment_configuration_sha256": "A" * 64,
                "resolved_environment_seed": cell["seed"],
                "candidate_metrics": None,
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
        "engine_at_end": plan["engine"],
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
