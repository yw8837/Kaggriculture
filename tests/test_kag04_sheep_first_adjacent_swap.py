from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from kaggriculture_lab.research.kag04_sheep_first_adjacent_swap import (
    _RUNTIME,
    TETSU_V16_BASE_PATH,
    TETSU_V16_SHA256,
    build_source,
    materialize_file,
)


def _base_bytes() -> bytes:
    return TETSU_V16_BASE_PATH.read_bytes()


def _namespace() -> dict[str, object]:
    namespace: dict[str, object] = {}
    exec(build_source(_base_bytes()), namespace)  # noqa: S102
    return namespace


def _observation(*, animal_count: int = 0) -> dict[str, object]:
    return {
        "player": 0,
        "farms": [{"tiles": [[None]]}],
        "private": {"shed": {"COW": animal_count, "SHEEP": 0, "GOOSE": 0}},
    }


def _action(market: list[list[object]]) -> dict[str, object]:
    return {
        "farmer": ["PASS"],
        "hands": [["NORTH"]],
        "market": market,
    }


def test_pinned_base_hash_and_build_are_deterministic() -> None:
    base_bytes = _base_bytes()
    assert hashlib.sha256(base_bytes).hexdigest().upper() == TETSU_V16_SHA256
    first = build_source(base_bytes)
    assert first == build_source(base_bytes)
    compile(first, "kag04.py", "exec")


def test_adjacent_swap_changes_only_the_two_target_order_positions() -> None:
    namespace = _namespace()
    namespace["reset_kag04_metrics"]()
    observation = _observation()
    base_action = _action(
        [
            ["BUY_SEED", "WHEAT", 1],
            ["BUY_ANIMAL", "COW", 2],
            ["BUY_ANIMAL", "SHEEP", 2],
            ["SELL", "WHEAT", 1],
        ]
    )
    original_action = deepcopy(base_action)
    original_observation = deepcopy(observation)

    candidate = namespace["_kag04_overlay"](observation, base_action)

    assert candidate is not base_action
    assert candidate["farmer"] is base_action["farmer"]
    assert candidate["hands"] is base_action["hands"]
    assert candidate["market"] == [
        ["BUY_SEED", "WHEAT", 1],
        ["BUY_ANIMAL", "SHEEP", 2],
        ["BUY_ANIMAL", "COW", 2],
        ["SELL", "WHEAT", 1],
    ]
    assert base_action == original_action
    assert observation == original_observation
    assert namespace["kag04_metrics"]() == {
        "calls": 1,
        "eligible": 1,
        "applied": 1,
        "fallback_malformed": 0,
        "fallback_ambiguous": 0,
        "fallback_owned_animals": 0,
        "fallback_not_adjacent": 0,
        "fallback_order_limit": 0,
    }


@pytest.mark.parametrize(
    "observation",
    [
        {"player": 0, "farms": [], "private": {"shed": {}}},
        {"player": 0, "farms": [{"tiles": "bad"}], "private": {"shed": {}}},
        {"player": True, "farms": [{"tiles": [[None]]}], "private": {"shed": {}}},
    ],
)
def test_malformed_observation_returns_exact_base_object(observation: dict[str, object]) -> None:
    namespace = _namespace()
    base_action = _action([["BUY_ANIMAL", "COW", 2], ["BUY_ANIMAL", "SHEEP", 2]])

    assert namespace["_kag04_overlay"](observation, base_action) is base_action
    assert namespace["kag04_metrics"]()["fallback_malformed"] == 1


@pytest.mark.parametrize(
    "market",
    [
        [["BUY_ANIMAL", "SHEEP", 2], ["BUY_ANIMAL", "COW", 2]],
        [["BUY_ANIMAL", "COW", 2], ["HIRE"], ["BUY_ANIMAL", "SHEEP", 2]],
        [["BUY_ANIMAL", "COW", 2], ["BUY_ANIMAL", "SHEEP", 2], ["BUY_ANIMAL", "GOOSE", 1]],
        [["BUY_ANIMAL", "COW", 2], ["BUY_ANIMAL", "SHEEP", 2], ["HIRE", "bad"]],
    ],
)
def test_ambiguous_or_not_adjacent_market_returns_exact_base_object(
    market: list[list[object]],
) -> None:
    namespace = _namespace()
    base_action = _action(market)
    original = deepcopy(base_action)

    assert namespace["_kag04_overlay"](_observation(), base_action) is base_action
    assert base_action == original


def test_owned_animals_and_market_cap_return_exact_base_object() -> None:
    namespace = _namespace()
    base_action = _action([["BUY_ANIMAL", "COW", 2], ["BUY_ANIMAL", "SHEEP", 2]])
    capped = _action([["HIRE"] for _ in range(11)])

    assert namespace["_kag04_overlay"](_observation(animal_count=1), base_action) is base_action
    assert namespace["_kag04_overlay"](_observation(), capped) is capped
    metrics = namespace["kag04_metrics"]()
    assert metrics["fallback_owned_animals"] == 1
    assert metrics["fallback_order_limit"] == 1


def test_metrics_aliases_and_prohibited_context_scope() -> None:
    namespace = _namespace()
    for prohibited in ("seed", "episode", "replay", "opponent", "identity", "step", "price"):
        assert prohibited not in _RUNTIME
    assert namespace["get_metrics"]() == namespace["rescue_metrics"]() == namespace["kag04_metrics"]()
    assert namespace["reset_rescue_metrics"]()["calls"] == 0


def test_wrong_base_bytes_are_rejected() -> None:
    with pytest.raises(ValueError, match="pinned Tetsu v16"):
        build_source(b"def agent(obs):\n    return {}\n")


def test_materialization_receipt_binds_exact_base_and_output(tmp_path: Path) -> None:
    output_path = tmp_path / "main.py"
    receipt_path = tmp_path / "receipt.json"

    receipt = materialize_file(TETSU_V16_BASE_PATH, output_path, receipt_path)

    assert receipt["base_sha256"] == TETSU_V16_SHA256
    assert receipt["output_sha256"] == hashlib.sha256(output_path.read_bytes()).hexdigest().upper()
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == receipt
