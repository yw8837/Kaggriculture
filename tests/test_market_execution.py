from __future__ import annotations

import copy
from types import SimpleNamespace
from typing import Any

from kaggle_environments.envs.kaggriculture import kaggriculture as official

from kaggriculture_lab.research.market_execution import reconstruct_market_turn

CONFIGURATION = {
    "boardSize": 10,
    "farmHandCostMult": 1,
    "maxMarketOrdersPerTurn": 10,
    "shedCapacity": 100,
    "townCenterSellInterval": 12,
    "townShopSellInterval": 4,
    "turnsPerDay": 24,
}


def _farm(money: int = 3_000) -> dict[str, Any]:
    return {
        "money": money,
        "farmer": [4, 4],
        "hands": [],
        "hires_today": 0,
        "unlocked_quadrants": ["NW"],
        "tiles": [[None for _ in range(10)] for _ in range(10)],
    }


def _private(**shed: int) -> dict[str, Any]:
    return {
        "inventories": [{}],
        "seeds": {crop: 0 for crop in official.CROPS},
        "shed": {item: shed.get(item, 0) for item in [*official.PRODUCTS, *official.ANIMALS]},
    }


def _market(inventory: int = 10_000) -> dict[str, Any]:
    market = {
        "inventory": {item: inventory for item in official.PRODUCTS},
        "prices": {},
    }
    official._refresh_prices(market)
    return market


def _observations(
    *,
    money0: int = 3_000,
    money1: int = 3_000,
    private0: dict[str, Any] | None = None,
    private1: dict[str, Any] | None = None,
    market: dict[str, Any] | None = None,
    step: int = 1,
) -> list[dict[str, Any]]:
    farms = [_farm(money0), _farm(money1)]
    shared_market = market or _market()
    return [
        {
            "step": step,
            "day": step // 24,
            "hour": step % 24,
            "farms": copy.deepcopy(farms),
            "market": copy.deepcopy(shared_market),
            "town": {"unlocked_shops": []},
            "private": copy.deepcopy(private0 or _private()),
        },
        {
            "day": step // 24,
            "hour": step % 24,
            "farms": copy.deepcopy(farms),
            "market": copy.deepcopy(shared_market),
            "town": {"unlocked_shops": []},
            "private": copy.deepcopy(private1 or _private()),
        },
    ]


def _actions(market0: list[Any], market1: list[Any]) -> list[dict[str, Any]]:
    return [
        {"farmer": ["PASS"], "hands": [], "market": market0},
        {"farmer": ["PASS"], "hands": [], "market": market1},
    ]


def _official_market_oracle(
    observations: list[dict[str, Any]], actions: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    farms = copy.deepcopy(observations[0]["farms"])
    market = copy.deepcopy(observations[0]["market"])
    privates = [copy.deepcopy(observation["private"]) for observation in observations]
    state = [
        SimpleNamespace(
            action=copy.deepcopy(actions[seat]),
            observation=SimpleNamespace(
                farms=farms if seat == 0 else None,
                market=market if seat == 0 else None,
                private=privates[seat],
            ),
        )
        for seat in range(2)
    ]
    env = SimpleNamespace(configuration=CONFIGURATION)
    official._process_market(state, env)
    return farms, privates, market


def _assert_public_state_matches_oracle(
    reconstructed: dict[str, Any],
    oracle_farms: list[dict[str, Any]],
    oracle_market: dict[str, Any],
) -> None:
    assert reconstructed["cash_after_market"] == [farm["money"] for farm in oracle_farms]
    assert reconstructed["market_inventory_after"] == oracle_market["inventory"]


def test_requested_quantity_can_exceed_accepted_inventory() -> None:
    observations = _observations(private0=_private(WHEAT=2))
    actions = _actions([["SELL", "WHEAT", 5]], [])

    result = reconstruct_market_turn(observations, actions, CONFIGURATION)
    oracle_farms, oracle_privates, oracle_market = _official_market_oracle(observations, actions)

    order = result["orders"][0]
    assert order["requested_quantity"] == 5
    assert order["accepted_quantity"] == 2
    assert order["rejected_quantity"] == 3
    assert order["status"] == "partial"
    assert order["failure_reason"] == "inventory"
    assert oracle_privates[0]["shed"]["WHEAT"] == 0
    _assert_public_state_matches_oracle(result, oracle_farms, oracle_market)


def test_simultaneous_sells_use_same_precommit_quote_per_unit() -> None:
    observations = _observations(private0=_private(WHEAT=2), private1=_private(WHEAT=2))
    actions = _actions([["SELL", "WHEAT", 2]], [["SELL", "WHEAT", 2]])

    result = reconstruct_market_turn(observations, actions, CONFIGURATION)
    oracle_farms, oracle_privates, oracle_market = _official_market_oracle(observations, actions)

    seat0, seat1 = result["orders"]
    assert seat0["accepted_quantity"] == seat1["accepted_quantity"] == 2
    assert seat0["unit_price_counts"] == seat1["unit_price_counts"]
    assert oracle_privates[0]["shed"]["WHEAT"] == 0
    assert oracle_privates[1]["shed"]["WHEAT"] == 0
    _assert_public_state_matches_oracle(result, oracle_farms, oracle_market)


def test_cash_short_buy_product_is_partially_filled_at_post_buy_quote() -> None:
    market = _market()
    first_unit_price = official.market_price("WHEAT", market["inventory"]["WHEAT"] - 1)
    observations = _observations(money0=first_unit_price, market=market)
    actions = _actions([["BUY_PRODUCT", "WHEAT", 3]], [])

    result = reconstruct_market_turn(observations, actions, CONFIGURATION)
    oracle_farms, oracle_privates, oracle_market = _official_market_oracle(observations, actions)

    order = result["orders"][0]
    assert market["prices"]["WHEAT"] != first_unit_price
    assert order["requested_quantity"] == 3
    assert order["accepted_quantity"] == 1
    assert order["failure_reason"] == "cash"
    assert order["cash_delta"] == -first_unit_price
    assert oracle_privates[0]["shed"]["WHEAT"] == 1
    _assert_public_state_matches_oracle(result, oracle_farms, oracle_market)


def test_eleventh_order_is_reported_as_order_cap_drop() -> None:
    observations = _observations()
    actions = _actions([["BUY_SEED", "WHEAT", 1] for _ in range(11)], [])

    result = reconstruct_market_turn(observations, actions, CONFIGURATION)
    oracle_farms, oracle_privates, oracle_market = _official_market_oracle(observations, actions)

    assert sum(order["accepted_quantity"] for order in result["orders"]) == 10
    dropped = result["orders"][-1]
    assert dropped["slot"] == 10
    assert dropped["dropped_by_order_cap"] is True
    assert dropped["failure_reason"] == "order_cap"
    assert oracle_privates[0]["seeds"]["WHEAT"] == 10
    _assert_public_state_matches_oracle(result, oracle_farms, oracle_market)


def test_day29_hire_before_sell_fails_before_sale_cash_arrives() -> None:
    observations = _observations(
        money0=0,
        private0=_private(WHEAT=1),
        step=29 * 24 + 1,
    )
    actions = _actions([["HIRE"], ["SELL", "WHEAT", 1]], [])

    result = reconstruct_market_turn(observations, actions, CONFIGURATION)
    oracle_farms, oracle_privates, oracle_market = _official_market_oracle(observations, actions)

    hire, sale = result["orders"]
    assert hire["accepted_quantity"] == 0
    assert hire["failure_reason"] == "cash"
    assert sale["accepted_quantity"] == 1
    assert oracle_farms[0]["hands"] == []
    assert oracle_privates[0]["shed"]["WHEAT"] == 0
    _assert_public_state_matches_oracle(result, oracle_farms, oracle_market)


def test_buy_land_is_atomic_and_matches_official_transition() -> None:
    observations = _observations(money0=1_000)
    actions = _actions([["BUY_LAND"]], [])

    result = reconstruct_market_turn(observations, actions, CONFIGURATION)
    oracle_farms, _, oracle_market = _official_market_oracle(observations, actions)

    order = result["orders"][0]
    assert order["accepted_quantity"] == 1
    assert order["cash_delta"] == -1_000
    assert oracle_farms[0]["unlocked_quadrants"] == ["NW", "NE"]
    _assert_public_state_matches_oracle(result, oracle_farms, oracle_market)


def test_valid_shape_with_unsupported_market_item_is_invalid() -> None:
    observations = _observations(private0=_private())
    actions = _actions([["SELL", "COW", 2]], [])

    result = reconstruct_market_turn(observations, actions, CONFIGURATION)
    oracle_farms, _, oracle_market = _official_market_oracle(observations, actions)

    order = result["orders"][0]
    assert order["requested_quantity"] == 2
    assert order["accepted_quantity"] == 0
    assert order["failure_reason"] == "invalid"
    _assert_public_state_matches_oracle(result, oracle_farms, oracle_market)


def test_one_dollar_sale_does_not_move_market_inventory() -> None:
    observations = _observations(private0=_private(MELON=2), market=_market(inventory=10**9))
    actions = _actions([["SELL", "MELON", 2]], [])

    result = reconstruct_market_turn(observations, actions, CONFIGURATION)
    oracle_farms, _, oracle_market = _official_market_oracle(observations, actions)

    order = result["orders"][0]
    assert order["unit_price_counts"] == [{"price": 1, "accepted_quantity": 2}]
    assert order["market_inventory_delta"] == {}
    _assert_public_state_matches_oracle(result, oracle_farms, oracle_market)


def test_buy_animal_has_no_market_inventory_key_or_delta() -> None:
    observations = _observations()
    actions = _actions([["BUY_ANIMAL", "COW", 1]], [])

    result = reconstruct_market_turn(observations, actions, CONFIGURATION)
    oracle_farms, oracle_privates, oracle_market = _official_market_oracle(observations, actions)

    order = result["orders"][0]
    assert order["accepted_quantity"] == 1
    assert order["market_inventory_delta"] == {}
    assert oracle_privates[0]["shed"]["COW"] == 1
    _assert_public_state_matches_oracle(result, oracle_farms, oracle_market)


def test_missing_opponent_is_not_guessed() -> None:
    observations = _observations(private0=_private(WHEAT=1))
    actions = _actions([["SELL", "WHEAT", 1]], [])

    result = reconstruct_market_turn(observations[:1], actions[:1], CONFIGURATION)

    order = result["orders"][0]
    assert result["exact"] is False
    assert order["accepted_quantity"] is None
    assert order["status"] == "unknown"
    assert order["failure_reason"] == "unknown_opponent_interleave"
