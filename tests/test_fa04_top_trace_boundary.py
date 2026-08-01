from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path

from kaggriculture_lab.evaluation.runner import _effective_configuration

ROOT = Path(__file__).parents[1]
BOUNDARY = ROOT / "configs/fa04_top_trace_guard_boundary.json"
REGISTRY = ROOT / "configs/fa_ab_seed_registry.json"
EXPECTED_BOUNDARY_NON_LIFECYCLE_SHA256 = (
    "B01D69548E96869E56ECFB42A916045ABCBC1AD868C3DAC52DFC50B62152221F"
)
EXPECTED_REGISTRY_NON_LIFECYCLE_SHA256 = (
    "9E38D7332622F0D1D4017BC82E42A4CAE54D0EBBB96B89F6464E4DC887CCCDAE"
)
BOUNDARY_EXCLUDED_PATHS = [
    "open_transition_invariant",
    "implementation_commit",
    "seed_registry_sha256",
    "status",
    "pools.development.status",
    "development_opened_at_utc",
    "opening_authority",
]
REGISTRY_EXCLUDED_PATHS = [
    "next_boundary_reservations.Fa04_top_trace_guard_development.status",
    "next_boundary_reservations.Fa04_top_trace_guard_development.opened",
    "next_boundary_reservations.Fa04_top_trace_guard_development.opened_at_utc",
]
OPENING_AUTHORITY = (
    "User authorization opens local development evaluation only; "
    "it does not authorize SaveRun or competition submission."
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _json_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def _expand(pool: dict) -> set[int]:
    seeds = set(range(pool["start"], pool["end_inclusive"] + 1))
    assert len(seeds) == pool["count"]
    return seeds


def _without_paths(value: dict, paths: list[str]) -> dict:
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


def _canonical_projection_sha256(value: dict, excluded_paths: list[str]) -> str:
    return _json_sha256(_without_paths(value, excluded_paths))


def _assert_fa04_lifecycle(boundary: dict, registry: dict) -> None:
    boundary_pool = boundary["pools"]["development"]
    registry_pool = registry["next_boundary_reservations"]["Fa04_top_trace_guard_development"]
    if boundary["status"] == "CLOSED_PENDING_CORRECTED_FREEZE_AUDIT":
        assert boundary_pool["status"] == registry_pool["status"] == "CLOSED"
        assert registry_pool["opened"] is False
        assert "development_opened_at_utc" not in boundary
        assert "opening_authority" not in boundary
        assert "opened_at_utc" not in registry_pool
    else:
        assert boundary["status"] == "DEVELOPMENT_OPEN_AUTHORIZED"
        assert boundary_pool["status"] == registry_pool["status"] == "OPEN"
        assert registry_pool["opened"] is True
        opened_at = boundary["development_opened_at_utc"]
        parsed = datetime.fromisoformat(opened_at)
        assert parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0
        assert boundary["opening_authority"] == OPENING_AUTHORITY
        assert registry_pool["opened_at_utc"] == opened_at
    assert registry_pool["consumed"] is False
    assert registry_pool["evaluated_games"] == 0


def test_fa04_top_trace_boundary_binds_exact_sources_and_attribution() -> None:
    config = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    assert config["status"] in {
        "CLOSED_PENDING_CORRECTED_FREEZE_AUDIT",
        "DEVELOPMENT_OPEN_AUTHORIZED",
    }
    attribution = config["attribution"]
    assert attribution == {
        "source": "official public Kaggle episode replay",
        "upstream_notebook": (
            "https://www.kaggle.com/code/prvsiyan/kaggriculture-frontier-lab-high-score-visuals"
        ),
        "upstream_author": "PRVSIYAN",
        "upstream_license": "Apache-2.0",
        "upstream_public_score_observed": 1298.6,
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
    assert "Upstream license: Apache-2.0" in candidate
    assert "kaggriculture-frontier-lab-high-score-visuals" in candidate


def test_fa04_top_trace_scenario_and_seed_pools_are_exact_closed_and_disjoint() -> None:
    config = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    expected_scenarios = {
        name: _effective_configuration(override)
        for name, override in config["scenario_overrides"].items()
    }
    assert _json_sha256(expected_scenarios) == config["expected_effective_scenarios_sha256"]

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
        if purpose != "development":
            assert pool["status"] == lane["status"] == "CLOSED"
            assert pool["opened"] is False
        assert pool["consumed"] is False
        assert pool["evaluated_games"] == 0
    _assert_fa04_lifecycle(config, registry)


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


def test_fa04_execution_freeze_binds_tooling_license_replay_and_exact_design() -> None:
    config = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    tooling = config["tooling"]
    for name in (
        "generator",
        "runner",
        "paired_analyzer",
        "runtime_generator",
        "gate_evaluator",
    ):
        assert _sha256(ROOT / tooling[name]) == tooling[f"{name}_sha256"]
    for name in ("third_party_license", "third_party_attribution", "runtime_replay"):
        entry = config["execution_freeze"][name]
        path = ROOT / entry["path"]
        assert path.stat().st_size == entry["bytes"]
        assert _sha256(path) == entry["sha256"]
    assert (
        config["execution_freeze"]["runtime_replay"]["sha256"]
        == config["attribution"]["replay_sha256"]
    )
    assert config["development_design"] == {
        "scenarios": ["default"],
        "seeds": "40000-40015",
        "seats": [0, 1],
        "opponents": 6,
        "exact_cells_per_lane": 192,
        "workers_per_lane": 6,
        "receipts": "separate candidate and control start receipts are mandatory",
    }


def test_fa04_open_transition_canonical_invariant_is_preregistered() -> None:
    boundary = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    invariant = boundary["open_transition_invariant"]
    assert invariant == {
        "schema_version": 1,
        "basis": {
            "label": "S2_IMPLEMENTATION_E2_EXECUTION",
            "implementation_commit": "586e69c110ade7e1ca0a7c7bf49eb6aeb1ab6a82",
            "closed_execution_commit": "bfbddb37c4f25ddbbf6f746f20604eff5f894663",
        },
        "canonicalization": {
            "algorithm": "SHA256_CANONICAL_JSON_SORTED_KEYS_COMPACT_ASCII",
            "boundary_excluded_paths": BOUNDARY_EXCLUDED_PATHS,
            "registry_excluded_paths": REGISTRY_EXCLUDED_PATHS,
        },
        "allowed_open_delta": {
            "boundary": {
                "status": [
                    "CLOSED_PENDING_CORRECTED_FREEZE_AUDIT",
                    "DEVELOPMENT_OPEN_AUTHORIZED",
                ],
                "pools.development.status": ["CLOSED", "OPEN"],
            },
            "registry": {
                "next_boundary_reservations.Fa04_top_trace_guard_development.status": [
                    "CLOSED",
                    "OPEN",
                ],
                "next_boundary_reservations.Fa04_top_trace_guard_development.opened": [
                    False,
                    True,
                ],
            },
        },
        "required_open_metadata": {
            "boundary.development_opened_at_utc": "RFC3339_UTC",
            "boundary.opening_authority": OPENING_AUTHORITY,
            "registry.next_boundary_reservations.Fa04_top_trace_guard_development.opened_at_utc": (
                "MUST_EQUAL_BOUNDARY_DEVELOPMENT_OPENED_AT_UTC"
            ),
        },
        "canonical_boundary_non_lifecycle_sha256": (EXPECTED_BOUNDARY_NON_LIFECYCLE_SHA256),
        "canonical_registry_non_lifecycle_sha256": (EXPECTED_REGISTRY_NON_LIFECYCLE_SHA256),
    }
    assert (
        _canonical_projection_sha256(boundary, BOUNDARY_EXCLUDED_PATHS)
        == EXPECTED_BOUNDARY_NON_LIFECYCLE_SHA256
    )
    assert (
        _canonical_projection_sha256(registry, REGISTRY_EXCLUDED_PATHS)
        == EXPECTED_REGISTRY_NON_LIFECYCLE_SHA256
    )
    assert invariant["canonical_boundary_non_lifecycle_sha256"] == (
        EXPECTED_BOUNDARY_NON_LIFECYCLE_SHA256
    )
    assert invariant["canonical_registry_non_lifecycle_sha256"] == (
        EXPECTED_REGISTRY_NON_LIFECYCLE_SHA256
    )
    assert boundary["release_policy"] == (
        "Development PASS permits only a separate SaveRun readiness request; "
        "no SaveRun without separate authorization/audit verdict."
    )
    _assert_fa04_lifecycle(boundary, registry)


def test_fa04_open_transition_changes_only_preregistered_lifecycle_fields() -> None:
    boundary = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    opened_boundary = copy.deepcopy(boundary)
    opened_registry = copy.deepcopy(registry)
    opened_at = "2026-08-02T00:00:00Z"
    opened_boundary["status"] = "DEVELOPMENT_OPEN_AUTHORIZED"
    opened_boundary["pools"]["development"]["status"] = "OPEN"
    opened_boundary["development_opened_at_utc"] = opened_at
    opened_boundary["opening_authority"] = OPENING_AUTHORITY
    opened_pool = opened_registry["next_boundary_reservations"]["Fa04_top_trace_guard_development"]
    opened_pool["status"] = "OPEN"
    opened_pool["opened"] = True
    opened_pool["opened_at_utc"] = opened_at
    _assert_fa04_lifecycle(opened_boundary, opened_registry)
    assert (
        _canonical_projection_sha256(opened_boundary, BOUNDARY_EXCLUDED_PATHS)
        == EXPECTED_BOUNDARY_NON_LIFECYCLE_SHA256
    )
    assert (
        _canonical_projection_sha256(opened_registry, REGISTRY_EXCLUDED_PATHS)
        == EXPECTED_REGISTRY_NON_LIFECYCLE_SHA256
    )

    tampered_values = []
    for mutate in (
        lambda value: value["scenario_config"].__setitem__("sha256", "0" * 64),
        lambda value: value["opponents"][0].__setitem__("sha256", "0" * 64),
        lambda value: value["development_gates"].__setitem__(
            "minimum_candidate_top_trace_match_score", 0.0
        ),
        lambda value: value["execution_freeze"]["runtime_replay"].__setitem__("sha256", "0" * 64),
        lambda value: value["candidate"].__setitem__("sha256", "0" * 64),
    ):
        tampered = copy.deepcopy(opened_boundary)
        mutate(tampered)
        tampered_values.append(tampered)
    assert all(
        _canonical_projection_sha256(value, BOUNDARY_EXCLUDED_PATHS)
        != EXPECTED_BOUNDARY_NON_LIFECYCLE_SHA256
        for value in tampered_values
    )

    tampered_registry = copy.deepcopy(opened_registry)
    tampered_registry["next_boundary_reservations"]["Fa04_top_trace_guard_development"]["start"] = (
        40001
    )
    assert (
        _canonical_projection_sha256(tampered_registry, REGISTRY_EXCLUDED_PATHS)
        != EXPECTED_REGISTRY_NON_LIFECYCLE_SHA256
    )
