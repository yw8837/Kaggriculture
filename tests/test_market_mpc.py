from __future__ import annotations

import ast
import copy
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest
from kaggle_environments.envs.kaggriculture import kaggriculture as engine

from kaggriculture_lab.candidates.market_mpc import VALID_MODES, build_file, build_source

FORMAL = Path("artifacts/candidates/final_day_labor/main.py")


def _namespace(tmp_path: Path, mode: str) -> tuple[dict[str, object], str]:
    source = build_file(FORMAL, mode)
    path = tmp_path / f"{mode}.py"
    path.write_text(source, encoding="utf-8", newline="")
    return runpy.run_path(str(path)), source


def _official_single_sale(
    item: str,
    inventory: int,
    quantity: int,
    overrides: dict[str, dict[str, object]] | None = None,
) -> tuple[int, int]:
    params = engine._resolve_market_params(overrides)
    market = {
        "inventory": {item: inventory},
        "params": params,
    }
    farm = {"money": 0}
    private = {"shed": {item: quantity}}
    for _ in range(quantity):
        price = engine.market_price(item, market["inventory"][item], params)
        assert engine._commit_unit("SELL", item, price, farm, private, market)
    return int(farm["money"]), int(market["inventory"][item])


@pytest.mark.parametrize(
    ("item", "inventory", "quantity", "overrides"),
    [
        ("WHEAT", 9_700, 1, None),
        ("MILK", 10_000, 20, None),
        ("WOOL", 10_150, 11, None),
        ("MELON", 10**9, 19, None),
        ("CARROT", 10_020, 9, {"CARROT": {"above_target": 0.15}}),
        (
            "STRAWBERRY",
            10_010,
            7,
            {
                "STRAWBERRY": {
                    "base": 90,
                    "I0": 10_100,
                    "T": 80,
                    "below_func": "linear",
                    "below_target": 0.5,
                    "above_func": "log10",
                    "above_target": 0.4,
                }
            },
        ),
    ],
)
def test_self_sale_quote_matches_official_single_seller_unit_loop(
    tmp_path: Path,
    item: str,
    inventory: int,
    quantity: int,
    overrides: dict[str, dict[str, object]] | None,
) -> None:
    namespace, _ = _namespace(tmp_path, "A1")
    quote = namespace["_self_sale_quote"]

    assert quote(item, inventory, quantity, overrides) == _official_single_sale(
        item, inventory, quantity, overrides
    )


def test_one_dollar_sales_do_not_move_inventory(tmp_path: Path) -> None:
    namespace, _ = _namespace(tmp_path, "A1")
    quote = namespace["_self_sale_quote"]
    inventory = 10**9

    revenue, next_inventory = quote("MELON", inventory, 37)

    assert engine.market_price("MELON", inventory) == 1
    assert (revenue, next_inventory) == (37, inventory)
    assert (revenue, next_inventory) == _official_single_sale("MELON", inventory, 37)


def _official_single_buy(
    item: str,
    inventory: int,
    quantity: int,
    overrides: dict[str, dict[str, object]] | None = None,
    cash: float = 1_000_000,
) -> tuple[int, int, int]:
    params = engine._resolve_market_params(overrides)
    market = {"inventory": {item: inventory}, "params": params}
    farm = {"money": cash}
    private = {"shed": {item: 0}}
    accepted = 0
    for _ in range(quantity):
        price = engine.market_price(item, market["inventory"][item] - 1, params)
        if not engine._commit_unit("BUY_PRODUCT", item, price, farm, private, market):
            break
        accepted += 1
    return int(cash - farm["money"]), int(market["inventory"][item]), accepted


@pytest.mark.parametrize(
    ("item", "inventory", "quantity", "overrides", "cash"),
    [
        ("WHEAT", 10_000, 8, None, 1_000_000),
        ("FERTILIZER", 9_950, 13, None, 1_000_000),
        ("WHEAT", 10_000, 6, {"WHEAT": {"below_target": 10.0, "T": 1}}, 250),
        (
            "WHEAT",
            10_020,
            9,
            {
                "WHEAT": {
                    "base": 30,
                    "I0": 10_050,
                    "T": 75,
                    "below_func": "log10",
                    "below_target": 0.5,
                    "above_func": "linear",
                    "above_target": 0.4,
                }
            },
            1_000_000,
        ),
    ],
)
def test_self_buy_quote_matches_official_post_buy_unit_loop(
    tmp_path: Path,
    item: str,
    inventory: int,
    quantity: int,
    overrides: dict[str, dict[str, object]] | None,
    cash: float,
) -> None:
    namespace, _ = _namespace(tmp_path, "A1")
    quote = namespace["_self_buy_quote"]

    assert quote(item, inventory, quantity, overrides, cash) == _official_single_buy(
        item, inventory, quantity, overrides, cash
    )


def test_one_dollar_buys_still_reduce_market_inventory(tmp_path: Path) -> None:
    namespace, _ = _namespace(tmp_path, "A1")
    quote = namespace["_self_buy_quote"]
    inventory = 10**9

    assert quote("MELON", inventory, 7, None, 100) == (7, inventory - 7, 7)
    assert quote("MELON", inventory, 7, None, 100) == _official_single_buy(
        "MELON", inventory, 7, cash=100
    )


def _official_simultaneous_sales(
    item: str, inventory: int, quantities: tuple[int, int]
) -> tuple[tuple[int, int], int, list[tuple[int, int]]]:
    market = {"inventory": {item: inventory}}
    farms = [{"money": 0}, {"money": 0}]
    privates = [{"shed": {item: quantity}} for quantity in quantities]
    remaining = list(quantities)
    quote_pairs: list[tuple[int, int]] = []
    while any(remaining):
        # This is the official _process_market lockstep: both players see the same
        # pre-commit inventory for the current unit.
        prices = tuple(
            engine.market_price(item, market["inventory"][item]) if remaining[player] else 0
            for player in range(2)
        )
        quote_pairs.append(prices)
        for player, price in enumerate(prices):
            if not remaining[player]:
                continue
            assert engine._commit_unit("SELL", item, price, farms[player], privates[player], market)
            remaining[player] -= 1
    return (
        (int(farms[0]["money"]), int(farms[1]["money"])),
        int(market["inventory"][item]),
        quote_pairs,
    )


def test_simultaneous_interleave_uses_shared_precommit_quote(tmp_path: Path) -> None:
    namespace, _ = _namespace(tmp_path, "A1")
    quote = namespace["_self_sale_quote"]

    revenues, final_inventory, quote_pairs = _official_simultaneous_sales("MILK", 10_000, (4, 4))
    self_revenue, self_inventory = quote("MILK", 10_000, 4)

    assert all(left == right for left, right in quote_pairs)
    assert quote_pairs[0][0] == engine.market_price("MILK", 10_000)
    assert final_inventory == 10_008
    assert self_inventory == 10_004
    # The helper is deliberately a self-only nominal forecast.  It must not be
    # mistaken for realized revenue when a hidden opponent also supplies MILK.
    assert revenues[0] < self_revenue


def _function_asts(source: str) -> dict[str, str]:
    return {
        node.name: ast.dump(node, include_attributes=False)
        for node in ast.parse(source).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_a0_is_byte_identical_and_all_modes_are_deterministic() -> None:
    formal_bytes = FORMAL.read_bytes()
    formal_source = formal_bytes.decode("utf-8")

    assert build_file(FORMAL, "A0").encode("utf-8") == formal_bytes
    for mode in VALID_MODES:
        assert build_source(formal_source, mode) == build_source(formal_source, mode)


def test_modes_have_isolated_formal_function_diffs() -> None:
    formal = FORMAL.read_bytes().decode("utf-8")
    formal_functions = _function_asts(formal)
    expected_changed = {
        "A1": {"_market_actions"},
        "A2": {"_animal_tasks", "_market_actions"},
        "A4": {"_animal_tasks", "_market_actions"},
    }

    for mode, expected in expected_changed.items():
        built = build_source(formal, mode)
        built_functions = _function_asts(built)
        actual = {
            name
            for name, formal_ast in formal_functions.items()
            if built_functions[name] != formal_ast
        }
        assert actual == expected

    a1 = build_source(formal, "A1")
    a2 = build_source(formal, "A2")
    a4 = build_source(formal, "A4")
    assert "budget += _self_sale_revenue(obs, item, quantity)" in a1
    assert "return _funded_day29_orders(obs, farm, orders, hire_orders)" in a1
    assert 'budget -= _self_buy_product_cost(obs, "WHEAT", quantity, budget)' in a1
    assert 'target = {"COW": 7, "SHEEP": 2} if expanded' in a1
    assert "budget += quantity * max(1, int(prices.get(item, 1)))" in a2
    assert "budget -= quantity * price" in a2
    assert "return (hire_orders + orders)[:10]" in a2
    assert "_select_herd_target(obs, farm, private) if expanded" in a2
    assert "budget += _self_sale_revenue(obs, item, quantity)" in a4
    assert 'budget -= _self_buy_product_cost(obs, "WHEAT", quantity, budget)' in a4
    assert "_select_herd_target(obs, farm, private) if expanded" in a4


def test_a1_preserves_unit_crop_and_agent_ast() -> None:
    formal = FORMAL.read_bytes().decode("utf-8")
    a1 = build_source(formal, "A1")
    formal_functions = _function_asts(formal)
    a1_functions = _function_asts(a1)

    for name in (
        "_cow_slots",
        "_crop_plan",
        "_animal_for_slot",
        "_animal_tasks",
        "_crop_tasks",
        "_task_cost",
        "_task_action",
        "_unit_actions",
        "agent",
    ):
        assert a1_functions[name] == formal_functions[name]


def _blank_farm(*, expanded: bool = False, money: float = 3_000) -> dict[str, object]:
    quadrants = ["NW", "NE"] if expanded else ["NW"]
    tiles: list[list[object]] = []
    for y in range(10):
        row = []
        for x in range(10):
            unlocked = x < 5 and y < 5
            if expanded:
                unlocked = y < 5
            row.append(None if unlocked else "LOCKED")
        tiles.append(row)
    return {
        "money": money,
        "tiles": tiles,
        "farmer": [4, 4],
        "hands": [],
        "unlocked_quadrants": quadrants,
        "hires_today": 0,
    }


def _private(**shed_patch: int) -> dict[str, object]:
    shed = {item: 0 for item in engine.PRODUCTS + list(engine.ANIMALS)}
    shed.update(shed_patch)
    return {
        "shed": shed,
        "seeds": {crop: 0 for crop in engine.CROPS},
        "inventories": [{}],
    }


def _market() -> dict[str, object]:
    return {
        "inventory": {item: values["I0"] for item, values in engine.MARKET_PARAMS.items()},
        "prices": {item: values["base"] for item, values in engine.MARKET_PARAMS.items()},
    }


def test_a2_keeps_crop_grid_worker_constants_and_terminal_unit_branch(tmp_path: Path) -> None:
    a0, source_a0 = _namespace(tmp_path, "A0")
    a2, source_a2 = _namespace(tmp_path, "A2")

    slots = set(a0["_cow_slots"](10, True))
    assert a2["_crop_plan"](10, ["NW", "NE"], slots) == a0["_crop_plan"](10, ["NW", "NE"], slots)
    assert ("TARGET_HANDS_CORE = 10" in source_a2) == ("TARGET_HANDS_CORE = 10" in source_a0)
    assert ("TARGET_HANDS_EXPANDED = 10" in source_a2) == (
        "TARGET_HANDS_EXPANDED = 10" in source_a0
    )

    farm = _blank_farm(expanded=True)
    farm["hands"] = [[4, 4], [5, 4]]
    private = _private()
    private["inventories"] = [{"MILK": 1}, {}, {}]
    obs = {"day": 29, "hour": 14, "market": _market()}
    plan = a0["_crop_plan"](10, ["NW", "NE"], slots)
    assert a2["_unit_actions"](obs, farm, private, list(slots), plan) == a0["_unit_actions"](
        obs, farm, private, list(slots), plan
    )


def test_a2_falls_back_on_uncertainty_and_respects_placed_lower_bound(
    tmp_path: Path,
) -> None:
    namespace, _ = _namespace(tmp_path, "A2")
    farm = _blank_farm(expanded=True)
    private = _private()
    incomplete = {"day": 5, "market": {"prices": {}}}
    assert namespace["_select_herd_target"](incomplete, farm, private) == {
        "COW": 7,
        "SHEEP": 2,
    }

    slots = namespace["_cow_slots"](10, True)
    for x, y in slots[:8]:
        farm["tiles"][y][x] = {
            "kind": "PASTURE",
            "animal": "COW",
            "placed_day": 0,
        }
    obs = {"day": 5, "market": _market()}
    selected = namespace["_select_herd_target"](obs, farm, private)
    assert selected["COW"] >= 8
    assert selected == {"COW": 9, "SHEEP": 0}


def _process_market_once(
    action: dict[str, object], farm: dict[str, object], private: dict[str, object]
) -> tuple[dict[str, object], dict[str, object]]:
    opponent_farm = _blank_farm()
    opponent_private = _private()
    market = _market()
    states = [
        SimpleNamespace(
            observation=SimpleNamespace(
                market=market,
                farms=[farm, opponent_farm],
                private=private,
            ),
            action=action,
        ),
        SimpleNamespace(
            observation=SimpleNamespace(private=opponent_private),
            action={"market": []},
        ),
    ]
    env = SimpleNamespace(
        configuration=SimpleNamespace(
            boardSize=10,
            maxMarketOrdersPerTurn=10,
            farmHandCostMult=1,
        )
    )
    engine._process_market(states, env)
    return farm, private


def test_a1_day29_sales_fund_hire_before_atomic_order_is_attempted(tmp_path: Path) -> None:
    formal, _ = _namespace(tmp_path, "A0")
    a1, _ = _namespace(tmp_path, "A1")
    farm = _blank_farm(money=0)
    farm["hands"] = [[4, 4] for _ in range(9)]
    private = _private(MILK=20)
    obs = {"day": 29, "hour": 0, "market": _market()}

    formal_orders = formal["_market_actions"](obs, farm, private, [], {})
    a1_orders = a1["_market_actions"](obs, farm, private, [], {})
    assert formal_orders[:2] == [["HIRE"], ["SELL", "MILK", 20]]
    assert a1_orders[:2] == [["SELL", "MILK", 20], ["HIRE"]]

    formal_farm, _ = _process_market_once(
        {"market": formal_orders}, copy.deepcopy(farm), copy.deepcopy(private)
    )
    a1_farm, _ = _process_market_once(
        {"market": a1_orders}, copy.deepcopy(farm), copy.deepcopy(private)
    )
    assert len(formal_farm["hands"]) == 9
    assert len(a1_farm["hands"]) == 10
    assert a1_farm["money"] == formal_farm["money"] - 1


def test_a1_keeps_hire_first_when_existing_cash_already_funds_it(tmp_path: Path) -> None:
    formal, _ = _namespace(tmp_path, "A0")
    a1, _ = _namespace(tmp_path, "A1")
    farm = _blank_farm(money=100)
    farm["hands"] = [[4, 4] for _ in range(9)]
    private = _private(MILK=20)
    obs = {"day": 29, "hour": 0, "market": _market()}

    formal_orders = formal["_market_actions"](obs, farm, private, [], {})
    a1_orders = a1["_market_actions"](obs, farm, private, [], {})
    assert a1_orders == formal_orders
    assert a1_orders[:2] == [["HIRE"], ["SELL", "MILK", 20]]


def test_a1_budget_tracks_partial_buy_before_following_hires(tmp_path: Path) -> None:
    formal, _ = _namespace(tmp_path, "A0")
    a1, _ = _namespace(tmp_path, "A1")
    farm = _blank_farm(money=250)
    private = _private(COW=1, SHEEP=2)
    private["seeds"] = {crop: 100 for crop in engine.CROPS}
    market = _market()
    market["params"] = {"WHEAT": {"below_target": 10.0, "T": 1}}
    obs = {"day": 0, "hour": 0, "market": market}

    formal_orders = formal["_market_actions"](obs, farm, private, [], {})
    a1_orders = a1["_market_actions"](obs, farm, private, [], {})
    assert formal_orders[0] == a1_orders[0] == ["BUY_PRODUCT", "WHEAT", 6]
    assert _official_single_buy("WHEAT", 10_000, 6, market["params"], cash=250) == (0, 10_000, 0)
    assert sum(order == ["HIRE"] for order in a1_orders) > sum(
        order == ["HIRE"] for order in formal_orders
    )


@pytest.mark.parametrize("mode", VALID_MODES)
def test_generated_output_imports_only_stdlib_and_agent_schema_smoke(
    tmp_path: Path, mode: str
) -> None:
    namespace, source = _namespace(tmp_path, mode)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
    }
    assert imports <= {"collections", "math"}

    farm = _blank_farm()
    obs = {
        "day": 0,
        "hour": 0,
        "player": 0,
        "farms": [farm],
        "private": _private(),
        "market": _market(),
    }
    action = namespace["agent"](obs)
    assert set(action) == {"farmer", "hands", "market"}
    assert isinstance(action["farmer"], list)
    assert isinstance(action["hands"], list)
    assert isinstance(action["market"], list)
    assert len(action["market"]) <= 10


def test_builder_rejects_unknown_parent_markers() -> None:
    with pytest.raises(ValueError, match="sale-budget"):
        build_source(
            "from collections import deque\n\n"
            "def _market_actions(obs, farm, private, animal_slots, crop_plan):\n"
            "    return (hire_orders + orders)[:10]\n",
            "A1",
        )
    with pytest.raises(ValueError, match="unknown mode"):
        build_source(FORMAL.read_text(encoding="utf-8"), "A3")
