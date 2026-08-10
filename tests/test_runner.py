from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from kaggle_environments import make

from kaggriculture_lab.evaluation import runner
from kaggriculture_lab.evaluation.runner import GameResult, summarize


def _row(
    seat: int,
    mine: float,
    theirs: float,
    *,
    seed: int = 7,
    opponent: str = "opponent",
    scenario: str = "default",
) -> GameResult:
    return GameResult(
        opponent,
        seed,
        seat,
        mine,
        theirs,
        "DONE",
        "DONE",
        1.0,
        None,
        scenario,
    )


def test_summary_clusters_but_scores_both_seats() -> None:
    summary = summarize([_row(0, 10, 5), _row(1, 10, 5)])
    assert summary["raw_games"] == 2
    assert summary["seed_opponent_pairs"] == 1
    assert summary["bootstrap_seed_clusters"] == 1
    assert summary["bootstrap_cluster_unit"] == "seed"
    assert summary["wins"] == 2
    assert summary["seat_pair_differences"] == []


def test_summary_flags_seat_difference() -> None:
    summary = summarize([_row(0, 10, 5), _row(1, 9, 5)])
    assert len(summary["seat_pair_differences"]) == 1


def test_summary_keeps_all_opponents_and_scenarios_with_one_seed_in_one_cluster() -> None:
    results = []
    for scenario in ("default", "stress"):
        for opponent in ("alpha", "beta"):
            results.extend(
                [
                    _row(0, 10, 5, seed=11, opponent=opponent, scenario=scenario),
                    _row(1, 10, 5, seed=11, opponent=opponent, scenario=scenario),
                ]
            )
    summary = summarize(results)
    assert summary["scenario_opponent_seed_pairs"] == 4
    assert summary["bootstrap_seed_clusters"] == 1
    assert summary["match_score_seed_cluster_bootstrap_95"] == [1.0, 1.0]


def test_run_batch_writes_start_receipt_and_source_provenance(
    tmp_path: Path, monkeypatch,
) -> None:
    candidate = tmp_path / "candidate.py"
    opponent = tmp_path / "opponent.py"
    candidate.write_text("def agent(obs): return {}\n", encoding="utf-8")
    opponent.write_text("def agent(obs): return {}\n", encoding="utf-8")
    pinned_input = tmp_path / "evaluation_plan.json"
    pinned_input.write_text('{"status":"frozen"}\n', encoding="utf-8")

    def fake_run(spec: runner.GameSpec) -> GameResult:
        return GameResult(
            spec.opponent_name, spec.seed, spec.seat, 10.0, 5.0,
            "DONE", "DONE", 0.01, None,
        )

    monkeypatch.setattr(runner, "_run_game", fake_run)
    output = tmp_path / "evaluation.json"
    report = runner.run_batch(
        "candidate.py", ["opponent.py"], [7], output, 1, tmp_path,
        input_paths=[pinned_input],
    )

    receipt = tmp_path / "evaluation.started.json"
    receipt_payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert receipt_payload["started_at_utc"] == report["started_at_utc"]
    assert receipt_payload["workers"] == 1
    assert receipt_payload["effective_scenarios"] == {"default": {"episodeSteps": 720}}
    assert receipt_payload["effective_scenarios_sha256"] == runner._json_sha256(
        {"default": {"episodeSteps": 720}}
    )
    assert receipt_payload["runtime_environment_at_start"] == report[
        "runtime_environment_at_start"
    ]
    assert receipt_payload["execution_inputs_at_start"] == report[
        "execution_inputs_at_start"
    ]
    assert report["runtime_environment_unchanged_during_run"] is True
    assert report["execution_inputs_unchanged_during_run"] is True
    assert report["execution_context_unchanged_during_run"] is True
    assert report["execution_gate_valid"] is True
    pinned_key = pinned_input.resolve().as_posix()
    pinned_record = report["execution_inputs_at_start"]["pinned_inputs"][pinned_key]
    assert type(pinned_record["bytes"]) is int
    assert pinned_record["sha256"] == hashlib.sha256(
        pinned_input.read_bytes()
    ).hexdigest().upper()
    assert report["sources_unchanged_during_run"] is True
    assert report["candidate_sha256_at_start"] == report["candidate_sha256_at_end"]
    assert report["start_receipt_sha256"] == hashlib.sha256(receipt.read_bytes()).hexdigest().upper()


def test_runtime_environment_snapshot_is_process_stable_and_exact() -> None:
    first = runner._runtime_environment_snapshot()
    second = runner._runtime_environment_snapshot()

    assert first == second
    assert first["distribution_name"] == "kaggle-environments"
    assert first["distribution_version"] == "1.32.6"
    assert set(first["runtime_dependency_files"]) == {
        "package_init",
        "core",
        "utils",
        "agent",
        "kaggriculture_py",
        "kaggriculture_json",
    }
    root = Path(first["distribution_root"])
    for record in first["runtime_dependency_files"].values():
        assert record["exists"] is True
        assert type(record["bytes"]) is int and record["bytes"] > 0
        assert type(record["sha256"]) is str and len(record["sha256"]) == 64
        assert Path(record["path"]).is_relative_to(root)
    for record in first["imported_module_paths"].values():
        assert record["error"] is None
        assert Path(record["path"]).is_relative_to(root)
    assert first["make_callable_error"] is None
    assert first["make_callable_contract"]["module"] == "kaggle_environments.core"
    assert type(first["make_callable_contract_matches_expected"]) is bool


def test_run_batch_preserves_false_report_on_runtime_environment_drift(
    tmp_path: Path, monkeypatch,
) -> None:
    candidate = tmp_path / "candidate.py"
    opponent = tmp_path / "opponent.py"
    candidate.write_text("def agent(obs): return {}\n", encoding="utf-8")
    opponent.write_text("def agent(obs): return {}\n", encoding="utf-8")
    snapshots = iter(
        [
            {"schema_version": 1, "distribution_version": "1.32.6", "sha": "A"},
            {"schema_version": 1, "distribution_version": "1.32.7", "sha": "B"},
        ]
    )
    monkeypatch.setattr(runner, "_runtime_environment_snapshot", lambda: next(snapshots))
    monkeypatch.setattr(
        runner,
        "_run_game",
        lambda spec: GameResult(
            spec.opponent_name, spec.seed, spec.seat, 10.0, 5.0,
            "DONE", "DONE", 0.01, None,
        ),
    )
    output = tmp_path / "runtime-drift.json"

    report = runner.run_batch(
        "candidate.py", ["opponent.py"], [7], output, 1, tmp_path,
    )

    assert report["runtime_environment_unchanged_during_run"] is False
    assert report["execution_context_unchanged_during_run"] is False
    assert report["execution_gate_valid"] is False
    assert json.loads(output.read_text(encoding="utf-8")) == report


def test_run_batch_detects_pinned_input_drift_and_keeps_completed_report(
    tmp_path: Path, monkeypatch,
) -> None:
    candidate = tmp_path / "candidate.py"
    opponent = tmp_path / "opponent.py"
    pinned_input = tmp_path / "candidate_catalog.json"
    candidate.write_text("def agent(obs): return {}\n", encoding="utf-8")
    opponent.write_text("def agent(obs): return {}\n", encoding="utf-8")
    pinned_input.write_text('{"revision":1}\n', encoding="utf-8")

    def mutate_input(spec: runner.GameSpec) -> GameResult:
        pinned_input.write_text('{"revision":2}\n', encoding="utf-8")
        return GameResult(
            spec.opponent_name, spec.seed, spec.seat, 10.0, 5.0,
            "DONE", "DONE", 0.01, None,
        )

    monkeypatch.setattr(runner, "_run_game", mutate_input)
    output = tmp_path / "input-drift.json"
    report = runner.run_batch(
        "candidate.py", ["opponent.py"], [7], output, 1, tmp_path,
        input_paths=[pinned_input],
    )

    key = pinned_input.resolve().as_posix()
    assert report["execution_inputs_at_start"]["pinned_inputs"][key]["sha256"] != (
        report["execution_inputs_at_end"]["pinned_inputs"][key]["sha256"]
    )
    assert report["execution_inputs_unchanged_during_run"] is False
    assert report["execution_gate_valid"] is False
    assert json.loads(output.read_text(encoding="utf-8")) == report


def test_run_batch_detects_runner_snapshot_drift(tmp_path: Path, monkeypatch) -> None:
    candidate = tmp_path / "candidate.py"
    opponent = tmp_path / "opponent.py"
    candidate.write_text("def agent(obs): return {}\n", encoding="utf-8")
    opponent.write_text("def agent(obs): return {}\n", encoding="utf-8")
    snapshots = iter(
        [
            {"schema_version": 1, "runner": {"sha256": "A"}, "pinned_inputs": {}},
            {"schema_version": 1, "runner": {"sha256": "B"}, "pinned_inputs": {}},
        ]
    )
    monkeypatch.setattr(
        runner, "_execution_input_snapshot", lambda _paths: next(snapshots)
    )
    monkeypatch.setattr(
        runner,
        "_run_game",
        lambda spec: GameResult(
            spec.opponent_name, spec.seed, spec.seat, 10.0, 5.0,
            "DONE", "DONE", 0.01, None,
        ),
    )

    report = runner.run_batch(
        "candidate.py", ["opponent.py"], [7], tmp_path / "runner-drift.json",
        1, tmp_path,
    )

    assert report["execution_inputs_unchanged_during_run"] is False
    assert report["execution_context_unchanged_during_run"] is False
    assert report["execution_gate_valid"] is False


def test_main_passes_repeatable_and_scenario_execution_input_pins(
    tmp_path: Path, monkeypatch,
) -> None:
    first_pin = tmp_path / "candidate_catalog.json"
    second_pin = tmp_path / "development_gate.py"
    scenario_pin = tmp_path / "development_scenarios.json"
    for path in (first_pin, second_pin, scenario_pin):
        path.write_text("{}\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_run_batch(*args: object) -> dict[str, object]:
        captured["args"] = args
        return {"summary": {}}

    monkeypatch.setattr(runner, "run_batch", fake_run_batch)
    monkeypatch.setattr(runner, "_load_scenarios", lambda _path: {"default": {}})
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "runner",
            "--agent", "candidate.py",
            "--opponents", "opponent.py",
            "--seeds", "7",
            "--scenario-config", str(scenario_pin),
            "--input-pin", str(first_pin),
            "--input-pin", str(second_pin),
            "--output", str(tmp_path / "report.json"),
            "--workers", "1",
        ],
    )

    runner.main()

    args = captured["args"]
    assert isinstance(args, tuple)
    assert args[7] == [first_pin, second_pin, scenario_pin]


@pytest.mark.parametrize(
    ("field", "value"),
    [("seeds", [True]), ("workers", True), ("opponents", [Path("opponent.py")])],
)
def test_run_batch_rejects_lossy_input_types(
    tmp_path: Path, field: str, value: object,
) -> None:
    kwargs = {
        "candidate_ref": "candidate.py",
        "opponents": ["opponent.py"],
        "seeds": [7],
        "output": tmp_path / "invalid.json",
        "workers": 1,
        "project_root": tmp_path,
    }
    kwargs[field] = value
    with pytest.raises(TypeError):
        runner.run_batch(**kwargs)


def test_run_batch_expands_and_hashes_registered_scenarios(
    tmp_path: Path, monkeypatch,
) -> None:
    candidate = tmp_path / "candidate.py"
    opponent = tmp_path / "opponent.py"
    candidate.write_text("def agent(obs): return {}\n", encoding="utf-8")
    opponent.write_text("def agent(obs): return {}\n", encoding="utf-8")

    seen = []

    def fake_run(spec: runner.GameSpec) -> GameResult:
        seen.append((spec.scenario, spec.configuration, spec.seed, spec.seat))
        return GameResult(
            spec.opponent_name, spec.seed, spec.seat, 10.0, 5.0,
            "DONE", "DONE", 0.01, None, spec.scenario,
        )

    monkeypatch.setattr(runner, "_run_game", fake_run)
    scenarios = {
        "default": {},
        "premium_glut": {
            "marketParams": {
                "STRAWBERRY": {"above_target": 2.4},
                "MILK": {"above_target": 2.4},
            }
        },
    }
    report = runner.run_batch(
        "candidate.py", ["opponent.py"], [17], tmp_path / "scenarios.json",
        1, tmp_path, scenarios,
    )

    assert len(seen) == 4
    assert {row[0] for row in seen} == {"default", "premium_glut"}
    expected_effective = {
        "default": {"episodeSteps": 720},
        "premium_glut": {
            "episodeSteps": 720,
            "marketParams": {
                "STRAWBERRY": {"above_target": 2.4},
                "MILK": {"above_target": 2.4},
            },
        },
    }
    assert report["scenario_overrides"] == scenarios
    assert report["effective_scenarios"] == expected_effective
    assert report["effective_scenarios_sha256"] == runner._json_sha256(expected_effective)
    assert report["summary"]["scenario_opponent_seed_pairs"] == 2


def test_run_game_passes_and_records_effective_environment_configuration(
    tmp_path: Path, monkeypatch,
) -> None:
    captured: list[dict] = []

    class FakeEnvironment:
        def __init__(self) -> None:
            self.configuration = expected
            self.info = {"seed": 23000}
            self.steps = [[
                SimpleNamespace(reward=101.0, status="DONE"),
                SimpleNamespace(reward=99.0, status="DONE"),
            ]]

        def run(self, _agents) -> None:
            return None

    def fake_make(_name, *, configuration, debug):
        assert debug is False
        captured.append(configuration)
        return FakeEnvironment()

    monkeypatch.setattr(
        runner,
        "_validated_kaggle_make",
        lambda: (fake_make, runner.EXPECTED_MAKE_CALLABLE),
    )
    override = {
        "townShopSellInterval": 8,
        "marketParams": {"WHEAT": {"below_target": 3.5}},
    }
    expected = {"episodeSteps": 720, **override, "seed": 23000}
    result = runner._run_game(
        runner.GameSpec(
            "candidate.py", "opponent.py", "opponent", 23000, 0,
            str(tmp_path), "scarcity", override,
        )
    )

    assert captured == [expected]
    assert result.error is None
    assert result.effective_configuration == expected
    assert result.effective_configuration_sha256 == runner._json_sha256(expected)
    assert result.environment_configuration == expected
    assert result.environment_configuration_sha256 == runner._json_sha256(expected)
    assert result.resolved_environment_seed == 23000
    assert result.candidate_metrics is None


def test_run_game_rejects_failure_hidden_by_terminal_done(tmp_path: Path, monkeypatch) -> None:
    class FakeEnvironment:
        def __init__(self) -> None:
            self.configuration = {"episodeSteps": 720, "seed": 23000}
            self.info = {"seed": 23000}
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
                    SimpleNamespace(reward=100.0, status="DONE"),
                ],
            ]

        def run(self, _agents) -> None:
            return None

    def fake_make(*_args, **_kwargs):
        return FakeEnvironment()
    monkeypatch.setattr(
        runner,
        "_validated_kaggle_make",
        lambda: (fake_make, runner.EXPECTED_MAKE_CALLABLE),
    )
    result = runner._run_game(
        runner.GameSpec(
            "candidate.py", "opponent.py", "opponent", 23000, 0,
            str(tmp_path), "default", {},
        )
    )

    assert result.candidate_status == "EXCEPTION"
    assert result.candidate_money is None
    assert result.error == "RuntimeError: framework agent failure at step=1, player=0, status=ERROR"


def test_run_game_records_and_summarizes_instrumented_candidate_counters(
    tmp_path: Path, monkeypatch,
) -> None:
    candidate = tmp_path / "instrumented.py"
    candidate.write_text(
        """_METRICS = {"opportunities": 0, "assignments": 0}
def rescue_metrics(): return dict(_METRICS)
def reset_rescue_metrics():
    for key in _METRICS: _METRICS[key] = 0
def agent(obs):
    _METRICS["opportunities"] += 2
    _METRICS["assignments"] += 1
    return {}
""",
        encoding="utf-8",
    )

    class FakeEnvironment:
        def __init__(self) -> None:
            self.configuration = {"episodeSteps": 720, "seed": 17}
            self.info = {"seed": 17}
            self.steps = [[
                SimpleNamespace(reward=20.0, status="DONE"),
                SimpleNamespace(reward=10.0, status="DONE"),
            ]]

        def run(self, agents) -> None:
            agents[0]({})

    def fake_make(*_args, **_kwargs):
        return FakeEnvironment()
    monkeypatch.setattr(
        runner,
        "_validated_kaggle_make",
        lambda: (fake_make, runner.EXPECTED_MAKE_CALLABLE),
    )
    result = runner._run_game(
        runner.GameSpec(
            str(candidate), "opponent.py", "opponent", 17, 0, str(tmp_path),
        )
    )

    assert result.candidate_metrics == {"opportunities": 2, "assignments": 1}
    summary = summarize([result])
    assert summary["candidate_metrics_games"] == 1
    assert summary["candidate_metrics_total"] == {"opportunities": 2, "assignments": 1}


def test_load_scenarios_rejects_seed_override(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"scenarios":{"bad":{"seed":9}}}', encoding="utf-8")

    try:
        runner._load_scenarios(path)
    except ValueError as exc:
        assert "runner-controlled" in str(exc)
    else:
        raise AssertionError("seed override should be rejected")


def test_registered_scenario_overrides_reach_official_environment() -> None:
    scenarios = runner._load_scenarios(Path("configs/fa_ab_scenarios.json"))

    for name, override in scenarios.items():
        effective = runner._effective_configuration(override, 25000)
        environment = make("kaggriculture", configuration=effective, debug=False)
        assert environment.configuration.episodeSteps == 720
        assert environment.configuration.seed is None
        assert environment.info["seed"] == 25000
        if "marketParams" in override:
            assert dict(environment.configuration.marketParams) == override["marketParams"]
        if name == "low_town_demand":
            assert environment.configuration.townShopSellInterval == 8
            assert environment.configuration.townCenterSellInterval == 24
