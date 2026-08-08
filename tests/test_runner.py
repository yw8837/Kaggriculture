from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

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

    def fake_run(spec: runner.GameSpec) -> GameResult:
        return GameResult(
            spec.opponent_name, spec.seed, spec.seat, 10.0, 5.0,
            "DONE", "DONE", 0.01, None,
        )

    monkeypatch.setattr(runner, "_run_game", fake_run)
    output = tmp_path / "evaluation.json"
    report = runner.run_batch(
        "candidate.py", ["opponent.py"], [7], output, 1, tmp_path,
    )

    receipt = tmp_path / "evaluation.started.json"
    receipt_payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert receipt_payload["started_at_utc"] == report["started_at_utc"]
    assert receipt_payload["workers"] == 1
    assert receipt_payload["effective_scenarios"] == {"default": {"episodeSteps": 720}}
    assert receipt_payload["effective_scenarios_sha256"] == runner._json_sha256(
        {"default": {"episodeSteps": 720}}
    )
    assert report["sources_unchanged_during_run"] is True
    assert report["candidate_sha256_at_start"] == report["candidate_sha256_at_end"]
    assert report["start_receipt_sha256"] == hashlib.sha256(receipt.read_bytes()).hexdigest().upper()


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

    import kaggle_environments

    monkeypatch.setattr(kaggle_environments, "make", fake_make)
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

    import kaggle_environments

    monkeypatch.setattr(kaggle_environments, "make", lambda *_args, **_kwargs: FakeEnvironment())
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

    import kaggle_environments

    monkeypatch.setattr(kaggle_environments, "make", lambda *args, **kwargs: FakeEnvironment())
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
