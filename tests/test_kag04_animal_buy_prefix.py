from __future__ import annotations

import hashlib
from copy import deepcopy

import pytest

from kaggriculture_lab.research.kag04_animal_buy_prefix import (
    _RUNTIME,
    TETSU_V16_BASE_PATH,
    TETSU_V16_SHA256,
    build_source,
)


def _namespace() -> dict[str, object]:
    namespace: dict[str, object] = {}
    exec(build_source(TETSU_V16_BASE_PATH.read_bytes()), namespace)  # noqa: S102
    return namespace


def _observation(*, cows: int = 0) -> dict[str, object]:
    return {
        "player": 0,
        "farms": [{"tiles": [[None]]}],
        "private": {"shed": {"COW": cows, "SHEEP": 0, "GOOSE": 0}},
    }


def _action(market: list[list[object]]) -> dict[str, object]:
    return {"farmer": ["PASS"], "hands": [["NORTH"]], "market": market}


def test_pinned_base_builds_deterministically() -> None:
    base = TETSU_V16_BASE_PATH.read_bytes()
    assert hashlib.sha256(base).hexdigest().upper() == TETSU_V16_SHA256
    assert build_source(base) == build_source(base)


def test_prefix_move_preserves_target_and_non_target_relative_orders() -> None:
    namespace = _namespace()
    namespace["reset_kag04_metrics"]()
    action = _action(
        [
            ["BUY_SEED", "WHEAT", 1],
            ["BUY_ANIMAL", "SHEEP", 2],
            ["SELL", "WHEAT", 1],
            ["BUY_ANIMAL", "COW", 2],
            ["HIRE"],
        ]
    )
    original = deepcopy(action)

    candidate = namespace["_kag04_overlay"](_observation(), action)

    assert candidate["market"] == [
        ["BUY_ANIMAL", "SHEEP", 2],
        ["BUY_ANIMAL", "COW", 2],
        ["BUY_SEED", "WHEAT", 1],
        ["SELL", "WHEAT", 1],
        ["HIRE"],
    ]
    assert candidate["farmer"] is action["farmer"]
    assert candidate["hands"] is action["hands"]
    assert action == original
    assert namespace["kag04_metrics"]()["moved_slots_total"] == 3


@pytest.mark.parametrize(
    "observation,market",
    [
        (_observation(cows=1), [["BUY_ANIMAL", "COW", 2], ["BUY_ANIMAL", "SHEEP", 2]]),
        (_observation(), [["BUY_ANIMAL", "COW", 2], ["BUY_ANIMAL", "SHEEP", 2]]),
        (_observation(), [["BUY_ANIMAL", "COW", 2], ["BUY_ANIMAL", "GOOSE", 1]]),
        (_observation(), [["HIRE"] for _ in range(11)]),
    ],
)
def test_ineligible_shapes_return_exact_base_object(
    observation: dict[str, object], market: list[list[object]]
) -> None:
    namespace = _namespace()
    action = _action(market)

    assert namespace["_kag04_overlay"](observation, action) is action


def test_metrics_aliases_and_prohibited_context_scope() -> None:
    namespace = _namespace()
    for prohibited in ("seed", "episode", "replay", "opponent", "identity", "step", "price"):
        assert prohibited not in _RUNTIME
    assert namespace["get_metrics"]() == namespace["rescue_metrics"]()
    assert namespace["reset_rescue_metrics"]()["calls"] == 0
