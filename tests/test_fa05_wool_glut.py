from __future__ import annotations

import hashlib
import runpy
from copy import deepcopy
from pathlib import Path

import pytest

from kaggriculture_lab.research.wool_glut_buffer import (
    UPSTREAM_G1_SHA256,
    render_source,
)

G1 = Path("experiments/source_snapshots/fa04_top_trace/G1_sell_guard.py")
W1 = Path("experiments/source_snapshots/fa05_wool_glut/W1_wool_glut_buffer.py")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _tiles(size: int = 4) -> list[list[object]]:
    return [[None for _ in range(size)] for _ in range(size)]


def _obs(
    *,
    step: int = 1,
    day: int = 1,
    hour: int = 1,
    player: int = 0,
    sheep: int = 4,
    price: object = 150,
    market_inventory: object = 10001,
    shed: dict[str, int] | None = None,
    inventories: list[dict[str, int]] | None = None,
    positions: list[list[int]] | None = None,
) -> dict[str, object]:
    own_tiles = _tiles()
    opponent_tiles = _tiles()
    for index in range(sheep):
        opponent_tiles[index // 4][index % 4] = {
            "kind": "PASTURE",
            "animal": "SHEEP",
        }
    units = inventories if inventories is not None else [{}]
    unit_positions = positions or [[1, 1] for _ in units]
    own = {
        "farmer": unit_positions[0],
        "hands": unit_positions[1:],
        "tiles": own_tiles,
    }
    opponent = {"farmer": [1, 1], "hands": [], "tiles": opponent_tiles}
    farms = [own, opponent] if player == 0 else [opponent, own]
    return {
        "step": step,
        "day": day,
        "hour": hour,
        "player": player,
        "farms": farms,
        "private": {
            "shed": deepcopy(shed if shed is not None else {"WOOL": 0}),
            "inventories": deepcopy(units),
        },
        "market": {
            "prices": {"WOOL": price},
            "inventory": {"WOOL": market_inventory},
        },
    }


def _action(
    market: list[list[object]],
    *,
    farmer: list[object] | None = None,
    hands: list[list[object]] | None = None,
) -> dict[str, object]:
    return {
        "farmer": farmer or ["PASS"],
        "hands": hands or [],
        "market": deepcopy(market),
    }


@pytest.fixture()
def candidate() -> dict[str, object]:
    namespace = runpy.run_path(str(W1))
    namespace["reset_rescue_metrics"]()
    return namespace


def test_snapshot_is_exact_reproducible_append_to_pinned_g1() -> None:
    upstream = G1.read_bytes()
    generated = W1.read_bytes()
    assert _sha256(upstream) == UPSTREAM_G1_SHA256
    assert generated == render_source(upstream)
    assert generated.startswith(upstream)
    text = generated.decode("utf-8")
    assert "# Upstream license: Apache-2.0" in text
    assert "PRVSIYAN" in text
    assert "WOOL_GLUT_MODE = \"wool_glut_buffer\"" in text
    compile(generated, str(W1), "exec")


def test_trigger_suppresses_only_sell_wool_and_records_requested_not_observed(
    candidate: dict[str, object],
) -> None:
    action = _action(
        [["SELL", "WOOL", 25], ["SELL", "WHEAT", 2], ["HIRE"]],
        farmer=["PASS"],
    )
    observed = candidate["_apply_wool_glut_buffer"](
        action,
        _obs(shed={"WOOL": 25, "WHEAT": 2}),
        {"shedCapacity": 100, "maxMarketOrdersPerTurn": 10, "boardSize": 4},
    )
    assert observed == {
        "farmer": ["PASS"],
        "hands": [],
        "market": [["SELL", "WOOL", 5], ["SELL", "WHEAT", 2], ["HIRE"]],
    }
    metrics = candidate["rescue_metrics"]()
    assert metrics["eligible_trigger_turns"] == 1
    assert metrics["sell_suppressed_orders"] == 1
    assert metrics["create_requested_units"] == 20
    assert metrics["create_observed_units"] == 0
    assert metrics["causal_completed_reserve_release_units"] == 0
    assert metrics["protected_lane_action_diff"] == 0


@pytest.mark.parametrize(
    ("changes", "sheep"),
    [
        ({"price": 200}, 4),
        ({"market_inventory": 10000}, 4),
        ({"day": 28}, 4),
        ({}, 3),
    ],
)
def test_false_trigger_without_pending_is_exact_g1(
    candidate: dict[str, object], changes: dict[str, object], sheep: int
) -> None:
    action = _action([["SELL", "WOOL", 7], ["BUY_PRODUCT", "WHEAT", 2]])
    assert candidate["_apply_wool_glut_buffer"](
        action,
        _obs(sheep=sheep, shed={"WOOL": 7}, **changes),
        {"boardSize": 4},
    ) == action
    assert candidate["rescue_metrics"]()["false_trigger_count"] == 0


@pytest.mark.parametrize("case", ["malformed", "overflow", "order_cap"])
def test_protected_malformed_overflow_and_order_cap_fall_back_exactly(
    candidate: dict[str, object], case: str
) -> None:
    market = [["SELL", "WOOL", 20]]
    observation = _obs(shed={"WOOL": 20})
    if case == "malformed":
        observation["farms"][1]["tiles"] = None
    elif case == "overflow":
        observation["private"]["shed"] = {"WOOL": 20, "WHEAT": 61}
    else:
        market.extend([["HIRE"] for _ in range(10)])
    action = _action(market)
    assert candidate["_apply_wool_glut_buffer"](
        action, observation, {"boardSize": 4}
    ) == action
    assert candidate["rescue_metrics"]()["create_requested_units"] == 0


def test_pending_release_is_lot_four_merges_earliest_then_can_append(
    candidate: dict[str, object],
) -> None:
    apply = candidate["_apply_wool_glut_buffer"]
    config = {"boardSize": 4}
    reserved = apply(
        _action([["SELL", "WOOL", 25]]),
        _obs(step=5, shed={"WOOL": 25}),
        config,
    )
    assert reserved["market"] == [["SELL", "WOOL", 5]]

    merged = apply(
        _action([["SELL", "WOOL", 2], ["HIRE"]]),
        _obs(step=6, price=210, shed={"WOOL": 20}),
        config,
    )
    assert merged["market"] == [["SELL", "WOOL", 6], ["HIRE"]]

    appended = apply(
        _action([["HIRE"] for _ in range(9)]),
        _obs(step=7, price=210, shed={"WOOL": 14}),
        config,
    )
    assert appended["market"] == [["HIRE"] for _ in range(9)] + [
        ["SELL", "WOOL", 4]
    ]
    metrics = candidate["rescue_metrics"]()
    assert metrics["release_orders"] == 2
    apply(_action([]), _obs(step=8, price=150, shed={"WOOL": 10}), config)
    metrics = candidate["rescue_metrics"]()
    assert metrics["release_requested_units"] == 8
    assert metrics["release_observed_units"] == 8
    assert metrics["causal_completed_reserve_release_units"] == 8
    assert metrics["pending_end"] == 12
    assert (
        metrics["create_observed_units"]
        - metrics["release_observed_units"]
        == metrics["pending_end"]
    )


def test_release_requires_live_sheep_and_strict_inventory_recovery(
    candidate: dict[str, object],
) -> None:
    apply = candidate["_apply_wool_glut_buffer"]
    config = {"boardSize": 4}
    apply(_action([["SELL", "WOOL", 25]]), _obs(step=5, shed={"WOOL": 25}), config)
    apply(_action([]), _obs(step=6, price=150, shed={"WOOL": 20}), config)

    unchanged = _action([])
    assert apply(
        unchanged,
        _obs(step=7, sheep=3, price=210, shed={"WOOL": 20}),
        config,
    ) == unchanged
    assert apply(
        unchanged,
        _obs(step=8, price=150, market_inventory=10000, shed={"WOOL": 20}),
        config,
    ) == unchanged
    released = apply(
        unchanged,
        _obs(step=9, price=150, market_inventory=9999, shed={"WOOL": 20}),
        config,
    )
    assert released["market"] == [["SELL", "WOOL", 4]]


def test_unobserved_create_is_counted_as_false_trigger_without_pending(
    candidate: dict[str, object],
) -> None:
    apply = candidate["_apply_wool_glut_buffer"]
    config = {"boardSize": 4}
    apply(
        _action([["SELL", "WOOL", 25]]),
        _obs(step=5, shed={"WOOL": 25}),
        config,
    )
    apply(
        _action([]),
        _obs(step=6, price=150, shed={"WOOL": 19}),
        config,
    )
    metrics = candidate["rescue_metrics"]()
    assert metrics["create_requested_units"] == 20
    assert metrics["create_observed_units"] == 0
    assert metrics["pending_end"] == 0
    assert metrics["false_trigger_count"] == 1


def test_sheep_ineligible_noop_does_not_count_as_false_trigger(
    candidate: dict[str, object],
) -> None:
    action = _action([["SELL", "WOOL", 5]])
    assert candidate["_apply_wool_glut_buffer"](
        action,
        _obs(step=5, sheep=3, shed={"WOOL": 5}),
        {"boardSize": 4},
    ) == action
    assert candidate["rescue_metrics"]()["false_trigger_count"] == 0


def test_duplicate_or_invalid_wool_sell_is_a0_with_no_state_mutation(
    candidate: dict[str, object],
) -> None:
    apply = candidate["_apply_wool_glut_buffer"]
    config = {"boardSize": 4}
    apply(_action([["SELL", "WOOL", 25]]), _obs(step=5, shed={"WOOL": 25}), config)
    state_before = deepcopy(candidate["_WOOL_STATE"])
    metrics_before = candidate["rescue_metrics"]()

    duplicate = _action([["SELL", "WOOL", 1], ["SELL", "WOOL", 1]])
    assert apply(duplicate, _obs(step=6, shed={"WOOL": 20}), config) == duplicate
    assert candidate["_WOOL_STATE"] == state_before
    assert candidate["rescue_metrics"]() == metrics_before

    invalid = _action([["SELL", "WOOL", True]])
    assert apply(invalid, _obs(step=6, shed={"WOOL": 20}), config) == invalid
    assert candidate["_WOOL_STATE"] == state_before
    assert candidate["rescue_metrics"]() == metrics_before


@pytest.mark.parametrize("case", ["invalid_player", "missing_opponent", "too_many_orders"])
def test_other_protected_inputs_do_not_mutate_state_or_metrics(
    candidate: dict[str, object], case: str
) -> None:
    apply = candidate["_apply_wool_glut_buffer"]
    config = {"boardSize": 4}
    apply(_action([["SELL", "WOOL", 25]]), _obs(step=5, shed={"WOOL": 25}), config)
    state_before = deepcopy(candidate["_WOOL_STATE"])
    metrics_before = candidate["rescue_metrics"]()
    action = _action([["SELL", "WOOL", 1]])
    observation = _obs(step=6, shed={"WOOL": 20})
    if case == "invalid_player":
        observation["player"] = 2
    elif case == "missing_opponent":
        observation["farms"][1]["tiles"] = None
    else:
        action = _action([["SELL", "WOOL", 1], *[["HIRE"] for _ in range(10)]])
    assert apply(action, observation, config) == action
    assert candidate["_WOOL_STATE"] == state_before
    assert candidate["rescue_metrics"]() == metrics_before


def test_hour_23_candidate_retention_cannot_cause_end_day_discard(
    candidate: dict[str, object],
) -> None:
    action = _action([["SELL", "WOOL", 25]])
    observation = _obs(
        step=23,
        day=0,
        hour=23,
        shed={"WOOL": 25},
        inventories=[{"WHEAT": 81}],
        positions=[[0, 0]],
    )
    assert candidate["_apply_wool_glut_buffer"](
        action, observation, {"boardSize": 4, "shedCapacity": 100}
    ) == action
    metrics = candidate["rescue_metrics"]()
    assert metrics["create_requested_units"] == 0
    assert metrics["candidate_caused_overflow_or_discard_units"] == 0


def test_hour_23_capacity_check_excludes_carried_seed_marker(
    candidate: dict[str, object],
) -> None:
    action = _action([["SELL", "WOOL", 25]])
    observed = candidate["_apply_wool_glut_buffer"](
        action,
        _obs(
            step=23,
            day=0,
            hour=23,
            shed={"WOOL": 25},
            inventories=[{"SEED": 1000}],
            positions=[[0, 0]],
        ),
        {"boardSize": 4, "shedCapacity": 100},
    )
    assert observed["market"] == [["SELL", "WOOL", 5]]


def test_place_animal_with_explicit_none_is_not_officially_empty(
    candidate: dict[str, object],
) -> None:
    action = _action([], farmer=["PLACE", "SHEEP"])
    observation = _obs(
        shed={"WOOL": 0},
        inventories=[{"SHEEP": 1}],
        positions=[[0, 0]],
    )
    observation["farms"][0]["tiles"] = _tiles(6)
    observation["farms"][0]["tiles"][0][0] = {
        "kind": "PASTURE",
        "animal": None,
    }
    projected = candidate["_wool_project_official"](
        action, observation, {"boardSize": 6}
    )
    assert projected["shed"] == {"WOOL": 0}
    assert projected["inventories"] == [{"SHEEP": 1}]
    assert projected["tiles"][0][0]["animal"] is None


def test_last_action_is_exact_g1_so_no_unreconciled_request_is_created(
    candidate: dict[str, object],
) -> None:
    action = _action([["SELL", "WOOL", 25]])
    observed = candidate["_apply_wool_glut_buffer"](
        action,
        _obs(step=718, day=29, hour=22, shed={"WOOL": 25}),
        {"boardSize": 4, "episodeSteps": 720},
    )
    assert observed == action
    metrics = candidate["rescue_metrics"]()
    assert metrics["create_requested_units"] == 0
    assert metrics["release_requested_units"] == 0
    assert metrics["terminal_pending"] == 0


def test_player_state_isolated_during_interleaved_calls(
    candidate: dict[str, object],
) -> None:
    apply = candidate["_apply_wool_glut_buffer"]
    config = {"boardSize": 4}
    apply(
        _action([["SELL", "WOOL", 25]]),
        _obs(step=5, player=0, shed={"WOOL": 25}),
        config,
    )
    apply(
        _action([]),
        _obs(step=5, player=1, price=210, shed={"WOOL": 0}),
        config,
    )
    apply(
        _action([]),
        _obs(step=6, player=0, price=150, shed={"WOOL": 20}),
        config,
    )
    assert candidate["_WOOL_STATE"][0]["pending_confirmed"] == 20
    assert candidate["_WOOL_STATE"][1]["pending_confirmed"] == 0


def test_terminal_attempts_pending_only_and_counts_unsellable_carry(
    candidate: dict[str, object],
) -> None:
    apply = candidate["_apply_wool_glut_buffer"]
    apply(_action([["SELL", "WOOL", 25]]), _obs(step=5, shed={"WOOL": 25}), {"boardSize": 4})
    terminal = apply(
        _action([], farmer=["DROP"]),
        _obs(
            step=6,
            day=28,
            hour=4,
            price=150,
            shed={"WOOL": 20},
            inventories=[{"WOOL": 5}],
        ),
        {"boardSize": 4},
    )
    assert terminal["market"] == [["SELL", "WOOL", 20]]
    metrics = candidate["rescue_metrics"]()
    assert metrics["create_observed_units"] == 20
    assert metrics["release_requested_units"] == 20
    assert metrics["release_observed_units"] == 0
    assert metrics["terminal_wool_remaining"] == 5
    assert metrics["terminal_pending"] == 20


def test_full_order_list_without_wool_clears_pending_via_exact_fallback(
    candidate: dict[str, object],
) -> None:
    apply = candidate["_apply_wool_glut_buffer"]
    apply(_action([["SELL", "WOOL", 25]]), _obs(step=5, shed={"WOOL": 25}), {"boardSize": 4})
    full = _action([["HIRE"] for _ in range(10)])
    assert apply(full, _obs(step=6, price=210, shed={"WOOL": 20}), {"boardSize": 4}) == full
    metrics = candidate["rescue_metrics"]()
    assert metrics["fallback_count"] == 0
    assert metrics["blocked_release_units"] == 4
    assert metrics["pending_end"] == 20


def test_step_zero_and_rollback_reset_pending(candidate: dict[str, object]) -> None:
    apply = candidate["_apply_wool_glut_buffer"]
    apply(_action([["SELL", "WOOL", 25]]), _obs(step=5, shed={"WOOL": 25}), {"boardSize": 4})
    apply(_action([]), _obs(step=6, price=150, shed={"WOOL": 20}), {"boardSize": 4})
    no_pending_release = _action([])
    assert apply(
        no_pending_release,
        _obs(step=0, price=210, shed={"WOOL": 20}),
        {"boardSize": 4},
    ) == no_pending_release
    assert candidate["rescue_metrics"]()["pending_end"] == 0
    assert candidate["_WOOL_STATE"][0]["pending_confirmed"] == 0


@pytest.mark.parametrize(
    ("farmer", "hands", "shed", "inventories", "truncation"),
    [
        (["DROP"], [["PICKUP", "WOOL", 3]], {"WOOL": 75}, [{"WOOL": 10}, {}], 5),
        (
            ["PLACE", "WOOL", 5],
            [["DROP"]],
            {"WOOL": 70},
            [{"WOOL": 5}, {"WHEAT": 8}],
            3,
        ),
        (
            ["PICKUP", "WOOL", 4],
            [["PLACE", "WOOL", 2]],
            {"WOOL": 79},
            [{}, {"WOOL": 2}],
            0,
        ),
    ],
)
def test_official_unit_phase_projection_parity(
    candidate: dict[str, object],
    farmer: list[object],
    hands: list[list[object]],
    shed: dict[str, int],
    inventories: list[dict[str, int]],
    truncation: int,
) -> None:
    from kaggle_environments.envs.kaggriculture.kaggriculture import (
        _apply_unit_action,
    )

    action = _action([], farmer=farmer, hands=hands)
    observation = _obs(
        shed=shed,
        inventories=inventories,
        positions=[[1, 1], [2, 1]],
    )
    config = {"boardSize": 4, "shedCapacity": 80}
    projected = candidate["_wool_project_official"](action, observation, config)

    farm = deepcopy(observation["farms"][0])
    private = deepcopy(observation["private"])
    _apply_unit_action(farm, private, 0, farmer, 4, 1, 24, 80)
    _apply_unit_action(farm, private, 1, hands[0], 4, 1, 24, 80)
    assert projected["shed"] == private["shed"]
    assert projected["inventories"] == private["inventories"]
    assert projected["total"] == sum(private["shed"].values())
    assert projected["truncation"] == truncation
    assert projected["tiles"] == farm["tiles"]


@pytest.mark.parametrize("scenario", ["plant", "animal", "place_animal"])
def test_inventory_mutating_unit_actions_follow_official_sequential_parity(
    candidate: dict[str, object], scenario: str
) -> None:
    from kaggle_environments.envs.kaggriculture.kaggriculture import (
        _apply_unit_action,
    )

    if scenario == "plant":
        actions = [["FERTILIZE"], ["HARVEST"]]
        inventories = [{"FERTILIZER": 1}, {}]
        tile = {
            "kind": "PLANT",
            "crop": "WHEAT",
            "planted_day": 0,
            "watered_today": True,
            "consecutive_unwatered": 0,
            "yield_units": 3,
            "max_lifespan_step": 120,
            "fertilized_until_day": -1,
        }
    elif scenario == "animal":
        actions = [["FEED"], ["COLLECT_FERTILIZER"], ["HARVEST"]]
        inventories = [{"WHEAT": 1}, {}, {}]
        tile = {
            "kind": "PASTURE",
            "animal": "SHEEP",
            "placed_day": 0,
            "yield_units": 3,
            "consecutive_unfed": 0,
            "fed_today": False,
            "cared_today": False,
            "fertilizer_available": True,
            "pending_care_bonus": 0,
        }
    else:
        actions = [["PLACE", "SHEEP"], ["FEED"]]
        inventories = [{"SHEEP": 1}, {"WHEAT": 1}]
        tile = {"kind": "PASTURE"}
    positions = [[0, 0] for _ in inventories]
    observation = _obs(
        day=3,
        shed={"WOOL": 0},
        inventories=inventories,
        positions=positions,
    )
    observation["farms"][0]["tiles"] = _tiles(6)
    observation["farms"][0]["tiles"][0][0] = tile
    action = _action([], farmer=actions[0], hands=actions[1:])
    config = {"boardSize": 6, "shedCapacity": 100}
    projected = candidate["_wool_project_official"](action, observation, config)

    farm = deepcopy(observation["farms"][0])
    private = deepcopy(observation["private"])
    for index, unit_action in enumerate(actions):
        _apply_unit_action(farm, private, index, unit_action, 6, 3, 24, 100)
    assert projected["shed"] == private["shed"]
    assert projected["inventories"] == private["inventories"]
    assert projected["tiles"] == farm["tiles"]


def test_only_wool_sell_can_differ_across_valid_trigger_quantities(
    candidate: dict[str, object],
) -> None:
    apply = candidate["_apply_wool_glut_buffer"]
    for available in range(81):
        candidate["reset_rescue_metrics"]()
        intended = min(30, available)
        original = _action(
            [["BUY_PRODUCT", "WHEAT", 1], ["SELL", "WOOL", intended or 1]]
        )
        if available == 0:
            original = _action([["BUY_PRODUCT", "WHEAT", 1]])
        observed = apply(
            original,
            _obs(shed={"WOOL": available}),
            {"boardSize": 4},
        )
        assert observed["farmer"] == original["farmer"]
        assert observed["hands"] == original["hands"]
        assert [order for order in observed["market"] if order[0:2] != ["SELL", "WOOL"]] == [
            order for order in original["market"] if order[0:2] != ["SELL", "WOOL"]
        ]
        sold = sum(
            order[2] if len(order) == 3 else 1
            for order in observed["market"]
            if order[0:2] == ["SELL", "WOOL"]
        )
        assert 0 <= sold <= available
