from __future__ import annotations

import json
from pathlib import Path


def _expand(pool: dict) -> set[int]:
    values = set(range(pool["start"], pool["end_inclusive"] + 1))
    assert len(values) == pool["count"]
    return values


def test_fa_ab_seed_pools_are_exact_disjoint_and_closed() -> None:
    registry = json.loads(
        Path("configs/fa_ab_seed_registry.json").read_text(encoding="utf-8")
    )
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
            pools.append(_expand(pool))
    assert sum(map(len, pools)) == len(set().union(*pools))

    legacy = registry["retired_legacy_pools"][0]
    assert legacy["promotion_eligible"] is False
    assert legacy["opened"] is legacy["consumed"] is True
