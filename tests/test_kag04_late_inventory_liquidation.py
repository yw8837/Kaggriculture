from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from kaggriculture_lab.research.kag04_late_inventory_liquidation import (
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


def _observation(*, day: int = 29, hour: int = 20, fertilizer: int = 2, wheat: int = 5) -> dict[str, object]:
    return {
        "day": day,
        "hour": hour,
        "private": {"shed": {"FERTILIZER": fertilizer, "WHEAT": wheat}},
    }


def _action(market: list[list[object]] | None = None) -> dict[str, object]:
    return {
        "farmer": ["PASS"],
        "hands": [["NORTH"]],
        "market": [["HIRE"]] if market is None else market,
    }


def test_pinned_base_hash_and_build_are_deterministic() -> None:
    base_bytes = _base_bytes()
    assert hashlib.sha256(base_bytes).hexdigest().upper() == TETSU_V16_SHA256
    first = build_source(base_bytes)
    assert first == build_source(base_bytes)
    compile(first, "kag04.py", "exec")


def test_late_liquidation_appends_only_unreserved_stock_and_preserves_base() -> None:
    namespace = _namespace()
    namespace["reset_kag04_metrics"]()
    observation = _observation(fertilizer=2, wheat=5)
    base_action = _action([["SELL", "WHEAT", 2], ["HIRE"]])
    original_action = deepcopy(base_action)
    original_observation = deepcopy(observation)

    candidate = namespace["_kag04_overlay"](observation, base_action)

    assert candidate is not base_action
    assert candidate["farmer"] is base_action["farmer"]
    assert candidate["hands"] is base_action["hands"]
    assert candidate["market"] == [
        ["SELL", "WHEAT", 2],
        ["HIRE"],
        ["SELL", "FERTILIZER", 2],
        ["SELL", "WHEAT", 3],
    ]
    assert base_action == original_action
    assert observation == original_observation
    assert namespace["kag04_metrics"]() == {
        "calls": 1,
        "terminal_window": 1,
        "applied": 1,
        "added_orders": 2,
        "added_fertilizer_units": 2,
        "added_wheat_units": 3,
        "fallback_not_terminal": 0,
        "fallback_malformed": 0,
        "fallback_conflict": 0,
        "fallback_order_limit": 0,
        "fallback_no_inventory": 0,
    }


@pytest.mark.parametrize(
    "observation",
    [
        _observation(day=28),
        _observation(hour=19),
        _observation(hour=24),
        {"day": 29, "hour": 20, "private": {"shed": {"WHEAT": True}}},
    ],
)
def test_nonterminal_or_malformed_observation_returns_exact_base_object(
    observation: dict[str, object],
) -> None:
    namespace = _namespace()
    namespace["reset_kag04_metrics"]()
    base_action = _action()
    original = deepcopy(base_action)

    assert namespace["_kag04_overlay"](observation, base_action) is base_action
    assert base_action == original


@pytest.mark.parametrize(
    "market",
    [
        [["BUY_PRODUCT", "WHEAT", 1]],
        [["SELL", "WHEAT", 6]],
        [["SELL", "UNKNOWN", 1]],
        [["HIRE", "unexpected"]],
        [["SELL", "WHEAT", True]],
    ],
)
def test_conflicted_or_malformed_market_returns_exact_base_object(market: list[list[object]]) -> None:
    namespace = _namespace()
    namespace["reset_kag04_metrics"]()
    base_action = _action(market)
    original = deepcopy(base_action)

    assert namespace["_kag04_overlay"](_observation(), base_action) is base_action
    assert base_action == original


def test_order_cap_and_empty_stock_return_exact_base_object() -> None:
    namespace = _namespace()
    namespace["reset_kag04_metrics"]()
    capped = _action([["HIRE"] for _ in range(9)])
    empty = _action()

    assert namespace["_kag04_overlay"](_observation(), capped) is capped
    assert namespace["_kag04_overlay"](_observation(fertilizer=0, wheat=0), empty) is empty
    metrics = namespace["kag04_metrics"]()
    assert metrics["fallback_order_limit"] == 1
    assert metrics["fallback_no_inventory"] == 1


def test_runner_metrics_aliases_and_prohibited_context_scope() -> None:
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
