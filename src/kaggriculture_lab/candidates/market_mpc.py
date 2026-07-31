"""Build isolated exact-market/herd-planning ablations from the formal agent.

The builder deliberately works on source text.  Kaggle agents must be self-contained,
so every helper used by a generated mode is injected into the resulting ``main.py``.
No generated agent imports this laboratory package.
"""

from __future__ import annotations

from pathlib import Path

VALID_MODES = ("A0", "A1", "A2", "A4")


_MARKET_HELPERS = r'''
# Official Kaggriculture price defaults.  A custom observation may carry either a
# full table or sparse per-item patches, so patches are merged onto these values.
_MPC_PRICE_FLOOR = 1
_MPC_MARKET_PARAMS = {
    "WHEAT": {"base": 25, "I0": 10000, "T": 400, "below_func": "sqrt", "below_target": 0.80, "above_func": "log", "above_target": 0.20},
    "CARROT": {"base": 35, "I0": 10000, "T": 450, "below_func": "log", "below_target": 0.20, "above_func": "sqrt", "above_target": 0.70},
    "TOMATO": {"base": 60, "I0": 10000, "T": 200, "below_func": "linear", "below_target": 0.40, "above_func": "sqrt", "above_target": 0.60},
    "STRAWBERRY": {"base": 120, "I0": 10000, "T": 100, "below_func": "sqrt", "below_target": 0.70, "above_func": "linear", "above_target": 1.60},
    "MELON": {"base": 250, "I0": 10000, "T": 300, "below_func": "log", "below_target": 0.20, "above_func": "sq", "above_target": 3.60},
    "EGG": {"base": 50, "I0": 10000, "T": 332, "below_func": "linear", "below_target": 0.40, "above_func": "log", "above_target": 0.20},
    "MILK": {"base": 160, "I0": 10000, "T": 122, "below_func": "sqrt", "below_target": 0.60, "above_func": "linear", "above_target": 1.60},
    "WOOL": {"base": 200, "I0": 10000, "T": 105, "below_func": "log", "below_target": 0.20, "above_func": "sq", "above_target": 3.20},
    "FERTILIZER": {"base": 100, "I0": 10000, "T": 200, "below_func": "linear", "below_target": 0.40, "above_func": "linear", "above_target": 0.40},
}


def _mpc_shape(name, value):
    value = max(0.0, value)
    if name == "linear":
        return value
    if name == "sq":
        return value * value
    if name == "sqrt":
        return math.sqrt(value)
    if name == "log":
        return math.log(1.0 + value)
    if name == "log10":
        return math.log10(1.0 + value)
    return value


def _mpc_params(overrides=None):
    resolved = {item: dict(values) for item, values in _MPC_MARKET_PARAMS.items()}
    if isinstance(overrides, dict):
        for item, patch in overrides.items():
            if item in resolved and isinstance(patch, dict):
                resolved[item].update(patch)
    return resolved


def _mpc_market_price(item, inventory, params):
    p = params[item]
    base = p["base"]
    midpoint = p["I0"]
    scale = p["T"]
    if inventory < midpoint:
        shape = p["below_func"]
        amplitude = p["below_target"] * base / _mpc_shape(shape, scale)
        price = base + amplitude * _mpc_shape(shape, midpoint - inventory)
    else:
        shape = p["above_func"]
        amplitude = p["above_target"] * base / _mpc_shape(shape, scale)
        price = base - amplitude * _mpc_shape(shape, inventory - midpoint)
    return max(_MPC_PRICE_FLOOR, int(round(price)))


def _self_sale_quote(item, inventory, quantity, overrides=None):
    """Nominal revenue/next inventory if only our units change this item.

    The official engine quotes simultaneous players from one pre-commit inventory.
    Their hidden order is unknowable here, so this is intentionally not described as
    realized revenue.  It is exact for our own unit loop and implements the official
    rule that a sale at the $1 floor does not increase market inventory.
    """
    params = _mpc_params(overrides)
    next_inventory = int(inventory)
    revenue = 0
    for _ in range(max(0, int(quantity))):
        price = _mpc_market_price(item, next_inventory, params)
        revenue += price
        if price > _MPC_PRICE_FLOOR:
            next_inventory += 1
    return revenue, next_inventory


def _self_sale_revenue(obs, item, quantity):
    market = obs.get("market", {}) or {}
    inventory = market.get("inventory", {}) or {}
    if item not in inventory:
        # Legacy/minimal observations do not expose inventory.  Retain the formal
        # current-price estimate instead of inventing a curve position.
        prices = market.get("prices", {}) or {}
        return max(0, int(quantity)) * max(1, int(prices.get(item, 1)))
    revenue, _ = _self_sale_quote(
        item,
        inventory[item],
        quantity,
        market.get("params"),
    )
    return revenue


def _self_buy_quote(item, inventory, quantity, overrides=None, cash=None):
    """Nominal accepted cost/inventory for our own BUY_PRODUCT unit loop.

    The official engine quotes each unit at post-buy inventory.  If ``cash`` is
    supplied, the loop stops at the first unaffordable unit exactly as the engine
    does.  A simultaneous opponent order remains hidden, just as for sales.
    """
    params = _mpc_params(overrides)
    next_inventory = int(inventory)
    spent = 0
    accepted = 0
    limit = None if cash is None else max(0.0, float(cash))
    for _ in range(max(0, int(quantity))):
        price = _mpc_market_price(item, next_inventory - 1, params)
        if limit is not None and spent + price > limit:
            break
        spent += price
        next_inventory -= 1
        accepted += 1
    return spent, next_inventory, accepted


def _self_buy_cost(item, inventory, quantity, overrides=None):
    cost, _, _ = _self_buy_quote(item, inventory, quantity, overrides)
    return cost


def _self_buy_product_cost(obs, item, quantity, cash):
    market = obs.get("market", {}) or {}
    inventory = market.get("inventory", {}) or {}
    if item not in inventory:
        prices = market.get("prices", {}) or {}
        return min(
            max(0.0, float(cash)),
            max(0, int(quantity)) * max(1, int(prices.get(item, 1))),
        )
    cost, _, _ = _self_buy_quote(
        item,
        inventory[item],
        quantity,
        market.get("params"),
        cash,
    )
    return cost


def _funded_day29_orders(obs, farm, sell_orders, hire_orders):
    """Move only the sale prefix needed to fund the planned day-29 hires.

    HIRE is atomic and is attempted before later list entries.  Keeping an
    unfunded HIRE before its funding sale makes that hire fail permanently for
    the turn.  Sales retain their original relative order and quantities.
    """
    if not hire_orders:
        return sell_orders[:10]
    hire_index = int(farm.get("hires_today", 0))
    required = 20.0
    for offset in range(len(hire_orders)):
        required += _fib(hire_index + offset)
    available = float(farm.get("money", 0))
    funding_count = 0
    while available < required and funding_count < len(sell_orders):
        order = sell_orders[funding_count]
        if len(order) >= 3 and order[0] == "SELL":
            available += _self_sale_revenue(obs, order[1], order[2])
        funding_count += 1
    return (
        sell_orders[:funding_count]
        + hire_orders
        + sell_orders[funding_count:]
    )[:10]
'''.strip()


_HERD_HELPERS = r'''
_MPC_HERD_TARGETS = ((9, 0), (7, 2), (5, 4), (3, 6))
_MPC_FORMAL_HERD = (7, 2)
_MPC_HERD_SWITCH_MARGIN = 500.0
_MPC_LAST_SELL_DAY = 29
_MPC_ANIMALS = {
    "COW": {"cost": 400, "first_yield_day": 8, "interval": 2, "max_held": 6, "product": "MILK"},
    "SHEEP": {"cost": 500, "first_yield_day": 6, "interval": 3, "max_held": 6, "product": "WOOL"},
}


def _mpc_animal_units(animal, placement_day, care_enabled):
    """Forecast sellable units using the official production and CARE +1 bank.

    A not-yet-placed animal is assumed to become usable on the next day.
    Production appearing after the end of day 28 cannot be harvested and sold on
    day 29, so it is excluded.  Daily care adds one banked unit; a production day
    consumes the bank before the current day's care is banked again.
    """
    rule = _MPC_ANIMALS[animal]
    pending_care = 0
    produced = 0
    for refresh_day in range(int(placement_day), _MPC_LAST_SELL_DAY):
        next_day = refresh_day + 1
        since_first = next_day - int(placement_day) - rule["first_yield_day"]
        if since_first >= 0 and since_first % rule["interval"] == 0:
            produced += min(rule["max_held"], 1 + pending_care)
            pending_care = 0
        if care_enabled and refresh_day <= 27:
            pending_care += 1
    return produced


def _mpc_feasible_targets(placed):
    return [
        (cows, sheep)
        for cows, sheep in _MPC_HERD_TARGETS
        if cows >= placed["COW"] and sheep >= placed["SHEEP"]
    ]


def _mpc_herd_fallback(placed, feasible):
    if _MPC_FORMAL_HERD in feasible:
        return _MPC_FORMAL_HERD
    if not feasible:
        return (max(placed["COW"], 7), max(placed["SHEEP"], 2))
    # A malformed/external state can already exceed 7C/2S.  Keep the placement
    # lower bound and choose the feasible mix closest to the formal target.
    return min(
        feasible,
        key=lambda mix: (
            abs(mix[0] - _MPC_FORMAL_HERD[0]) + abs(mix[1] - _MPC_FORMAL_HERD[1]),
            abs(mix[1] - _MPC_FORMAL_HERD[1]),
            -mix[0],
        ),
    )


def _mpc_herd_score(obs, private, placed, target):
    """Visible-state nominal value of pasture slots not yet occupied."""
    day = int(obs.get("day", 0))
    placement_day = day + 1
    market = obs.get("market", {}) or {}
    inventories = market.get("inventory", {}) or {}
    prices = market.get("prices", {}) or {}
    required_items = ("WHEAT", "MILK", "WOOL")
    if any(item not in inventories or item not in prices for item in required_items):
        raise ValueError("market inventory/price is incomplete")

    overrides = market.get("params")
    shed = private.get("shed", {}) or {}
    carried = private.get("inventories", []) or []
    available = {
        animal: int(shed.get(animal, 0))
        + sum(int((inv or {}).get(animal, 0)) for inv in carried)
        for animal in ("COW", "SHEEP")
    }

    total_revenue = 0.0
    purchase_cost = 0.0
    feed_units = 0
    for animal in ("COW", "SHEEP"):
        new_slots = max(0, int(target[animal]) - int(placed[animal]))
        if new_slots <= 0:
            continue
        rule = _MPC_ANIMALS[animal]
        care_enabled = int(prices[rule["product"]]) >= 20
        units_each = _mpc_animal_units(animal, placement_day, care_enabled)
        product_units = new_slots * units_each
        revenue, _ = _self_sale_quote(
            rule["product"], inventories[rule["product"]], product_units, overrides
        )
        total_revenue += revenue
        purchase_cost += max(0, new_slots - available[animal]) * rule["cost"]
        # Charge every remaining feeding day; home-grown wheat is not credited to
        # any candidate mix in this nominal comparison.
        feed_units += new_slots * max(0, _MPC_LAST_SELL_DAY - placement_day)

    feed_cost = _self_buy_cost("WHEAT", inventories["WHEAT"], feed_units, overrides)
    return total_revenue - purchase_cost - feed_cost


def _select_herd_target(obs, farm, private):
    placed = {
        animal: _count_public_animals(farm, animal)
        for animal in ("COW", "SHEEP")
    }
    feasible = _mpc_feasible_targets(placed)
    fallback = _mpc_herd_fallback(placed, feasible)
    if len(farm.get("unlocked_quadrants", []) or ["NW"]) < 2 or not feasible:
        return {"COW": fallback[0], "SHEEP": fallback[1]}

    try:
        scored = [
            (_mpc_herd_score(obs, private, placed, {"COW": cows, "SHEEP": sheep}), cows, sheep)
            for cows, sheep in feasible
        ]
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        return {"COW": fallback[0], "SHEEP": fallback[1]}

    formal_score = next(
        (score for score, cows, sheep in scored if (cows, sheep) == fallback),
        None,
    )
    if formal_score is None:
        return {"COW": fallback[0], "SHEEP": fallback[1]}
    best_score, best_cows, best_sheep = max(scored, key=lambda row: (row[0], row[1], -row[2]))
    # A tie or an improvement below the preregistered safety margin stays formal.
    if (best_cows, best_sheep) == fallback or best_score - formal_score < _MPC_HERD_SWITCH_MARGIN:
        return {"COW": fallback[0], "SHEEP": fallback[1]}
    return {"COW": best_cows, "SHEEP": best_sheep}


def _planned_animals_for_slots(obs, farm, private, slots):
    target = _select_herd_target(obs, farm, private)
    tiles = farm.get("tiles", []) or []
    assignment = {}
    placed = {"COW": 0, "SHEEP": 0}
    empty = []
    for index, slot in enumerate(slots):
        x, y = slot
        tile = tiles[y][x]
        animal = tile.get("animal") if isinstance(tile, dict) else None
        if animal in placed:
            assignment[tuple(slot)] = animal
            placed[animal] += 1
        else:
            empty.append((index, tuple(slot)))

    need_sheep = max(0, target["SHEEP"] - placed["SHEEP"])
    need_cows = max(0, target["COW"] - placed["COW"])
    # Indices 1 and 2 reproduce formal 7C/2S.  Extra sheep expand outward from
    # those slots, keeping the mapping stable while the selected target changes.
    sheep_rank = {index: rank for rank, index in enumerate((1, 2, 8, 7, 6, 5, 4, 3, 0))}
    ranked_empty = sorted(empty, key=lambda row: (sheep_rank.get(row[0], 99), row[0]))
    sheep_slots = {slot for _, slot in ranked_empty[:need_sheep]}
    for _, slot in empty:
        if slot in sheep_slots:
            assignment[slot] = "SHEEP"
        elif need_cows > 0:
            assignment[slot] = "COW"
            need_cows -= 1
        else:
            assignment[slot] = None
    return assignment
'''.strip()


def _replace_once(source: str, old: str, new: str, *, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise ValueError(f"expected one {label} marker, found {count}")
    return source.replace(old, new, 1)


def _inject_helpers(source: str, helpers: str) -> str:
    marker = "\ndef _market_actions(obs, farm, private, animal_slots, crop_plan):"
    if source.count(marker) != 1:
        raise ValueError("formal source must contain exactly one _market_actions function")
    return source.replace(marker, f"\n\n{helpers}\n\n{marker.lstrip()}", 1)


def _ensure_math_import(source: str) -> str:
    if "import math\n" in source or "import math\r\n" in source:
        return source
    marker = "from collections import deque"
    return _replace_once(source, marker, marker + "\nimport math", label="deque import")


def build_source(formal_source: str, mode: str) -> str:
    """Return a deterministic single-file source for ``A0``, ``A1``, ``A2`` or ``A4``.

    ``A0`` is returned without parsing or newline normalization, preserving the input
    bytes after UTF-8 encoding.  Other modes require the known formal-source markers;
    refusing an unfamiliar parent is safer than silently producing a partial ablation.
    """
    selected = mode.upper()
    if selected not in VALID_MODES:
        raise ValueError(f"unknown mode {mode!r}; expected one of {VALID_MODES}")
    if selected == "A0":
        return formal_source

    source = _ensure_math_import(formal_source)
    helpers = _MARKET_HELPERS
    if selected in ("A2", "A4"):
        helpers += "\n\n" + _HERD_HELPERS
    source = _inject_helpers(source, helpers)

    if selected in ("A1", "A4"):
        source = _replace_once(
            source,
            "budget += quantity * max(1, int(prices.get(item, 1)))",
            "budget += _self_sale_revenue(obs, item, quantity)",
            label="formal sale-budget expression",
        )
        source = _replace_once(
            source,
            "return (hire_orders + orders)[:10]",
            "return _funded_day29_orders(obs, farm, orders, hire_orders)",
            label="day-29 market-order return",
        )
        source = _replace_once(
            source,
            "budget -= quantity * price",
            'budget -= _self_buy_product_cost(obs, "WHEAT", quantity, budget)',
            label="formal buy-product budget expression",
        )

    if selected in ("A2", "A4"):
        source = _replace_once(
            source,
            'tiles = farm["tiles"]\n    for pos in slots:',
            'tiles = farm["tiles"]\n'
            "    planned_animals = _planned_animals_for_slots(obs, farm, private, slots)\n"
            "    for pos in slots:",
            label="formal animal-task loop",
        )
        source = _replace_once(
            source,
            "planned = _animal_for_slot(pos, slots)",
            "planned = planned_animals.get(tuple(pos))\n"
            "        if planned is None:\n"
            "            continue",
            label="formal animal-slot assignment",
        )
        source = _replace_once(
            source,
            'target = {"COW": 7, "SHEEP": 2} if expanded else {"COW": 1, "SHEEP": 2}',
            'target = _select_herd_target(obs, farm, private) if expanded else {"COW": 1, "SHEEP": 2}',
            label="formal herd target",
        )
    return source


def build_file(formal_path: str | Path, mode: str) -> str:
    """Read a UTF-8 formal source without newline conversion and build one mode."""
    source = Path(formal_path).read_bytes().decode("utf-8")
    return build_source(source, mode)


# Descriptive alias for callers that prefer the mechanism name.
build_market_mpc = build_source
