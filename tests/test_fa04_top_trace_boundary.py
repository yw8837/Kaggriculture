from __future__ import annotations

import hashlib
import json
from pathlib import Path

from kaggriculture_lab.evaluation.runner import _effective_configuration


ROOT = Path(__file__).parents[1]
BOUNDARY = ROOT / "configs/fa04_top_trace_guard_boundary.json"
REGISTRY = ROOT / "configs/fa_ab_seed_registry.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _json_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def _expand(pool: dict) -> set[int]:
    seeds = set(range(pool["start"], pool["end_inclusive"] + 1))
    assert len(seeds) == pool["count"]
    return seeds


def test_fa04_top_trace_boundary_binds_exact_sources_and_attribution() -> None:
    config = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    assert config["status"] == "DEVELOPMENT_OPEN_AUTHORIZED"
    assert config["attribution"] == {
        "source": "official public Kaggle episode replay",
        "episode_id": 89256171,
        "team": "radiant-allomancer",
        "player": 0,
        "replay_sha256": "ADADDE60EEFB93B56DBE9922B51D5D1970803F89DDF0EEEE67B9890024090405",
        "recorded_actions": 719,
        "policy": (
            "Keep episode/team/player/replay hash in the generated source; "
            "do not claim authorship of the teacher trajectory."
        ),
    }
    bound = [config["candidate"], config["control"], *config["opponents"]]
    for entry in bound:
        path = ROOT / entry["path"]
        assert path.stat().st_size == entry["bytes"]
        assert _sha256(path) == entry["sha256"]
    candidate = (ROOT / config["candidate"]["path"]).read_text(encoding="utf-8")
    assert "SOURCE_EPISODE_ID = 89256171" in candidate
    assert "SOURCE_TEAM = 'radiant-allomancer'" in candidate
    assert "SOURCE_MODE = 'sell_guard'" in candidate


def test_fa04_top_trace_scenario_and_seed_pools_are_exact_closed_and_disjoint() -> None:
    config = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    expected_scenarios = {
        name: _effective_configuration(override)
        for name, override in config["scenario_overrides"].items()
    }
    assert _json_sha256(expected_scenarios) == config[
        "expected_effective_scenarios_sha256"
    ]

    reservations = registry["next_boundary_reservations"]
    all_pools: list[set[int]] = []
    for name, pool in reservations.items():
        if name == "policy" or not isinstance(pool, dict) or "start" not in pool:
            continue
        all_pools.append(_expand(pool))
    assert sum(map(len, all_pools)) == len(set().union(*all_pools))

    for purpose, bounds in {
        "development": (40000, 40015, 16),
        "confirmation": (41000, 41063, 64),
        "robustness": (42000, 42031, 32),
    }.items():
        lane = config["pools"][purpose]
        pool = reservations[lane["registry_key"]]
        assert (pool["start"], pool["end_inclusive"], pool["count"]) == bounds
        if purpose == "development":
            assert pool["status"] == lane["status"] == "OPEN"
            assert pool["opened"] is True and pool["consumed"] is False
            assert pool["opened_at_utc"] == config["development_opened_at_utc"]
        else:
            assert pool["status"] == lane["status"] == "CLOSED"
            assert pool["opened"] is pool["consumed"] is False
        assert pool["evaluated_games"] == 0


def test_fa04_top_trace_gates_keep_score_target_as_an_unverified_goal() -> None:
    config = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    assert "not guaranteed" in config["target"]
    gates = config["development_gates"]
    assert gates["candidate_failures"] == gates["control_failures"] == 0
    assert gates["minimum_candidate_top_trace_match_score"] == 0.75
    assert gates["minimum_formal_match_score"] == 0.9
    assert gates["minimum_actions_changed"] == 1
    assert gates["runtime_p95_ms_max"] == 8.0
    assert gates["runtime_p99_ms_max"] == 15.0
    assert gates["runtime_absolute_ms_max"] == 50.0
    assert gates["invalid_outputs"] == 0
