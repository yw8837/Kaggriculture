from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from kaggriculture_lab.evaluation.runner import _effective_configuration

FROZEN_INPUT_COMMIT = "b61d111abdded451e1a5ec2a7dc00bdc4764e43f"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _effective_scenarios_sha256(names: list[str]) -> str:
    scenario_path = Path("configs/fa_ab_scenarios.json")
    scenarios = json.loads(scenario_path.read_text(encoding="utf-8"))["scenarios"]
    effective = {
        name: _effective_configuration(scenarios[name], seed=None)
        for name in names
    }
    canonical = json.dumps(effective, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest().upper()


def _git_blob(path: Path) -> bytes:
    return subprocess.check_output(
        ["git", "show", f"{FROZEN_INPUT_COMMIT}:{path.as_posix()}"],
        cwd=Path(__file__).resolve().parents[1],
    )


def test_next_boundary_inputs_are_exact_tracked_and_all_pools_remain_closed() -> None:
    manifest = json.loads(
        Path("experiments/source_snapshots/fa_next_boundary_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    config = json.loads(Path(manifest["config"]["path"]).read_text(encoding="utf-8"))
    assert manifest["status"] == "DRAFT_CLOSED_PENDING_CORRECTIVE_AUDIT_PASS"
    assert config["status"] == manifest["status"]

    for section in (
        manifest["config"],
        manifest["scenario_config"],
        *manifest["agents"].values(),
        *manifest["tooling"].values(),
    ):
        path = Path(section["path"])
        payload = _git_blob(path)
        assert len(payload) == section["bytes"]
        assert hashlib.sha256(payload).hexdigest().upper() == section["sha256"]

    assert set(manifest["seed_state"].values()) == {"CLOSED"}
    assert config["A_formal_scenario_confirmation"]["pool"]["status"] == "CLOSED"
    assert config["B_greedy"]["development_pool"]["status"] == "CLOSED"
    assert config["B_greedy"]["confirmation_pool"]["status"] == "CLOSED"
    assert config["B_greedy"]["robustness_pool"]["status"] == "CLOSED"


def test_a_diagnostic_is_paired_seed_clustered_and_preregistered_without_tuning() -> None:
    config = json.loads(Path("configs/fa_next_boundary_draft.json").read_text(encoding="utf-8"))
    diagnostic = config["A_formal_scenario_confirmation"]
    assert diagnostic["variant_selection_allowed"] is False
    assert diagnostic["tuning_allowed"] is False
    assert diagnostic["seat_policy"].startswith("both seats")
    assert diagnostic["scenario_config"]["required_names"] == [
        "default",
        "premium_glut",
        "wheat_scarcity",
        "low_town_demand",
    ]
    assert diagnostic["scenario_config"]["expected_effective_scenarios_sha256"] == (
        _effective_scenarios_sha256(diagnostic["scenario_config"]["required_names"])
    )
    assert len(diagnostic["opponents"]) == 4
    assert config["analysis"]["paired_delta_cluster_unit"] == "seed"
    assert diagnostic["paired_gates"]["all_required"] is True
    assert diagnostic["paired_gates"]["failed_games"] == 0
    assert diagnostic["paired_gates"]["invalid_outputs"] == 0
    assert diagnostic["paired_gates"]["expected_contract"] == "must_use_preregistered"


def test_b_greedy_gate_requires_runtime_and_causal_rescue_counters() -> None:
    config = json.loads(Path("configs/fa_next_boundary_draft.json").read_text(encoding="utf-8"))
    greedy = config["B_greedy"]
    assert greedy["algorithm_constraint"].startswith("bounded greedy")
    assert greedy["development_gates"]["runtime_gate_ref"] == "runtime_gate_ms"
    assert greedy["development_gates"]["minimum_rescue_opportunities"] == 1
    assert greedy["development_gates"]["minimum_completed_rescues"] == 1
    assert greedy["development_gates"]["maximum_weed_or_escape_events_delta_vs_B0"] == 0
    assert greedy["development_gates"]["all_required"] is True
    assert greedy["development_gates"]["expected_contract"] == "must_use_preregistered"
    for partition in ("development", "confirmation", "robustness"):
        assert greedy["scenario_policy"]["expected_effective_scenarios_sha256"][partition] == (
            _effective_scenarios_sha256(greedy["scenario_policy"][partition])
        )
    frozen_runner = Path(greedy["counter_capture"]["runner"])
    assert greedy["counter_capture"]["runner_sha256"] == hashlib.sha256(
        _git_blob(frozen_runner)
    ).hexdigest().upper()
    assert _sha256(frozen_runner) != greedy["counter_capture"]["runner_sha256"]
    assert greedy["paired_analysis"]["bootstrap_cluster_unit"] == "seed"
    assert greedy["runtime_precheck"]["gate_result"] == "PASS"
    assert greedy["runtime_precheck"]["p95_ms"] <= config["runtime_gate_ms"]["p95_max"]
    assert greedy["runtime_precheck"]["p99_ms"] <= config["runtime_gate_ms"]["p99_max"]
    assert greedy["runtime_precheck"]["max_ms"] <= config["runtime_gate_ms"]["absolute_max"]
    assert greedy["runtime_precheck"]["invalid_outputs"] == 0
