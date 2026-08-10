from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from kaggriculture_lab.candidates.kag04_sheep_first import (
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


def _observation(*, own_animal: bool = False) -> dict[str, object]:
    tile: dict[str, object] = {"kind": "PASTURE"}
    if own_animal:
        tile["animal"] = "COW"
    return {
        "player": 0,
        "farms": [{"tiles": [[tile]]}],
        "private": {"shed": {"COW": 0, "SHEEP": 0, "GOOSE": 0}},
    }


def _opening_action() -> dict[str, object]:
    return {
        "farmer": ["NORTH"],
        "hands": [["EAST"]],
        "market": [
            ["HIRE"],
            ["BUY_ANIMAL", "COW", 2],
            ["SELL", "WHEAT", 1],
            ["BUY_ANIMAL", "SHEEP", 2],
        ],
    }


def test_pinned_base_hash_and_build_are_deterministic() -> None:
    base_bytes = _base_bytes()
    assert hashlib.sha256(base_bytes).hexdigest().upper() == TETSU_V16_SHA256
    first = build_source(base_bytes)
    assert first == build_source(base_bytes)
    compile(first, "kag04.py", "exec")


def test_opening_sheep_delta_preserves_non_market_actions_and_other_orders() -> None:
    namespace = _namespace()
    namespace["reset_kag04_metrics"]()
    base_action = _opening_action()
    original = deepcopy(base_action)
    observation = _observation()
    original_observation = deepcopy(observation)

    candidate = namespace["_kag04_overlay"](observation, base_action)

    assert candidate is not base_action
    assert candidate["farmer"] is base_action["farmer"]
    assert candidate["hands"] is base_action["hands"]
    assert candidate["market"] == [
        ["HIRE"],
        ["BUY_ANIMAL", "COW", 1],
        ["SELL", "WHEAT", 1],
        ["BUY_ANIMAL", "SHEEP", 3],
    ]
    assert len(candidate["market"]) == len(base_action["market"])
    assert base_action == original
    assert observation == original_observation
    assert namespace["kag04_metrics"]()["applied"] == 1
    assert namespace["get_metrics"]() == namespace["kag04_metrics"]()
    assert namespace["rescue_metrics"]() == namespace["kag04_metrics"]()
    assert namespace["reset_rescue_metrics"]() == {
        "calls": 0,
        "applied": 0,
        "fallback_malformed": 0,
        "fallback_ambiguous": 0,
        "fallback_owned_animals": 0,
    }


@pytest.mark.parametrize(
    "base_action",
    [
        {"farmer": ["NORTH"], "hands": [], "market": [["BUY_ANIMAL", "COW", 1]]},
        {
            "farmer": ["NORTH"],
            "hands": [],
            "market": [
                ["BUY_ANIMAL", "COW", 2],
                ["BUY_ANIMAL", "SHEEP", 2],
                ["BUY_ANIMAL", "GOOSE", 1],
            ],
        },
        {"farmer": ["NORTH"], "hands": [], "market": (['BUY_ANIMAL', 'COW', 2],)},
    ],
)
def test_malformed_or_ambiguous_market_returns_exact_base_object(
    base_action: dict[str, object],
) -> None:
    namespace = _namespace()
    namespace["reset_kag04_metrics"]()
    original = deepcopy(base_action)

    result = namespace["_kag04_overlay"](_observation(), base_action)

    assert result is base_action
    assert base_action == original
    metrics = namespace["kag04_metrics"]()
    assert metrics["fallback_malformed"] + metrics["fallback_ambiguous"] == 1


def test_owned_animal_and_malformed_observation_return_exact_base_object() -> None:
    namespace = _namespace()
    namespace["reset_kag04_metrics"]()
    base_action = _opening_action()

    assert namespace["_kag04_overlay"](_observation(own_animal=True), base_action) is base_action
    assert namespace["_kag04_overlay"]({"farms": []}, base_action) is base_action
    metrics = namespace["kag04_metrics"]()
    assert metrics["fallback_owned_animals"] == 1
    assert metrics["fallback_malformed"] == 1


def test_runtime_does_not_read_prohibited_context_fields() -> None:
    for prohibited in ("step", "day", "seed", "replay", "opponent", "team_name", "episode"):
        assert prohibited not in _RUNTIME


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
