from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


def _expand(pool: dict) -> set[int]:
    values = set(range(pool["start"], pool["end_inclusive"] + 1))
    assert len(values) == pool["count"]
    return values


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _collect_seed_values(value: object, *, seed_context: bool = False) -> set[int]:
    found: set[int] = set()
    if isinstance(value, dict):
        if seed_context and {"start", "end_inclusive"} <= value.keys():
            found.update(range(int(value["start"]), int(value["end_inclusive"]) + 1))
        for key, item in value.items():
            found.update(
                _collect_seed_values(item, seed_context=seed_context or "seed" in key.lower())
            )
    elif isinstance(value, list):
        for item in value:
            found.update(_collect_seed_values(item, seed_context=seed_context))
    elif seed_context and isinstance(value, int) and not isinstance(value, bool):
        found.add(value)
    elif seed_context and isinstance(value, str):
        match = re.fullmatch(r"(\d+)-(\d+)", value)
        if match:
            found.update(range(int(match.group(1)), int(match.group(2)) + 1))
    return found


def test_fa_ab_seed_pools_are_exact_disjoint_and_closed() -> None:
    registry = json.loads(
        Path("configs/fa_ab_seed_registry.json").read_text(encoding="utf-8")
    )
    assert "Every pool remains CLOSED" not in registry["next_boundary_reservations"][
        "policy"
    ]
    expected = {
        "A": {
            "development": (23000, 23015, 16),
            "sealed_strength": (24000, 24063, 64),
            "robustness": (25000, 25031, 32),
        },
        "B": {
            "development": (26000, 26015, 16),
            "sealed_strength": (27000, 27063, 64),
            "robustness": (28000, 28031, 32),
        },
    }
    pools: list[set[int]] = []
    for candidate, partitions in expected.items():
        for partition, bounds in partitions.items():
            pool = registry["candidates"][candidate][partition]
            assert (pool["start"], pool["end_inclusive"], pool["count"]) == bounds
            if partition == "development":
                assert pool["opened"] is pool["consumed"] is True
                assert pool["opened_at_utc"]
                assert pool["completed_at_utc"]
                assert pool["result"]
            else:
                assert pool["opened"] is False
                assert pool["consumed"] is False
                assert pool["status"] == "RETIRED_UNUSED"
                assert pool["promotion_eligible"] is False
            pools.append(_expand(pool))
    assert sum(map(len, pools)) == len(set().union(*pools))

    a_pool = registry["next_boundary_reservations"][
        "A_formal_scenario_confirmation"
    ]
    assert a_pool["promotion_eligible"] is True
    assert a_pool["opened_at_utc"] == "2026-07-31T19:56:01.417366+00:00"
    assert a_pool["completed_at_utc"] == "2026-07-31T20:31:30.162939+00:00"
    assert a_pool["evaluated_candidate_games"] == 1024
    assert a_pool["evaluated_control_games"] == 1024
    assert a_pool["evaluated_games"] == 2048
    assert a_pool["evaluated_paired_cells"] == 1024
    for path_field, hash_field in (
        ("candidate_report", "candidate_report_sha256"),
        ("control_report", "control_report_sha256"),
        ("evidence", "evidence_sha256"),
    ):
        assert a_pool[hash_field] == _sha256(Path(a_pool[path_field]))

    legacy = registry["retired_legacy_pools"][0]
    assert legacy["promotion_eligible"] is False
    assert legacy["opened"] is legacy["consumed"] is True


def test_next_boundary_pool_history_and_runtime_gate_are_preserved() -> None:
    registry = json.loads(
        Path("configs/fa_ab_seed_registry.json").read_text(encoding="utf-8")
    )
    expected = {
        "A_formal_scenario_confirmation": (30000, 30031, 32),
        "B_greedy_development": (31000, 31015, 16),
        "B_greedy_confirmation": (32000, 32063, 64),
        "B_greedy_robustness": (33000, 33031, 32),
    }
    lifecycle = {
        "A_formal_scenario_confirmation": ("CONSUMED_PASS", True, True),
        "B_greedy_development": ("CONSUMED_NO_GO", True, True),
        "B_greedy_confirmation": ("RETIRED_UNUSED", False, False),
        "B_greedy_robustness": ("RETIRED_UNUSED", False, False),
    }
    pools = []
    for name, bounds in expected.items():
        pool = registry["next_boundary_reservations"][name]
        assert (pool["start"], pool["end_inclusive"], pool["count"]) == bounds
        status, opened, consumed = lifecycle[name]
        assert (pool["status"], pool["opened"], pool["consumed"]) == (
            status,
            opened,
            consumed,
        )
        pools.append(_expand(pool))
    assert sum(map(len, pools)) == len(set().union(*pools))

    draft = json.loads(Path("configs/fa_next_boundary_draft.json").read_text(encoding="utf-8"))
    assert draft["status"] == "DRAFT_CLOSED_PENDING_CORRECTIVE_AUDIT_PASS"
    assert draft["analysis"]["aggregate_cluster_unit"] == "seed"
    assert draft["analysis"]["paired_delta_cluster_unit"] == "seed"
    assert draft["runtime_gate_ms"] == {
        "p95_max": 8.0,
        "p99_max": 15.0,
        "absolute_max": 50.0,
        "invalid_outputs": 0,
    }
    assert draft["B_greedy"]["algorithm_constraint"].startswith("bounded greedy")
    assert draft["B_greedy"]["development_pool"]["status"] == "CLOSED"
    assert draft["B_greedy"]["confirmation_pool"]["status"] == "CLOSED"
    assert draft["B_greedy"]["robustness_pool"]["status"] == "CLOSED"


def test_next_boundary_reservations_do_not_collide_with_historical_evidence() -> None:
    registry = json.loads(
        Path("configs/fa_ab_seed_registry.json").read_text(encoding="utf-8")
    )
    proposed = set().union(
        *(
            _expand(pool)
            for name, pool in registry["next_boundary_reservations"].items()
            if name != "policy"
            and isinstance(pool, dict)
            and pool.get("evaluated_games") == 0
        )
    )
    historical: set[int] = set()
    excluded = {
        Path("configs/fa_ab_seed_registry.json"),
        Path("configs/fa_next_boundary_draft.json"),
        Path("configs/fa02_last_chance_boundary.json"),
        Path("configs/fa04_top_trace_guard_boundary.json"),
        Path("experiments/source_snapshots/fa_next_boundary_manifest.json"),
        Path("experiments/source_snapshots/fa02_last_chance_manifest.json"),
    }
    json_paths = [
        *Path("configs").glob("*.json"),
        *Path("experiments").rglob("*.json"),
    ]
    for path in json_paths:
        if path in excluded:
            continue
        historical.update(
            _collect_seed_values(json.loads(path.read_text(encoding="utf-8")))
        )
    for path in (Path("experiments/ledger.jsonl"), Path("submissions/ledger.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            historical.update(_collect_seed_values(json.loads(line)))
    assert proposed.isdisjoint(historical)
