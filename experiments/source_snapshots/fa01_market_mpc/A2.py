from collections import deque
import math

CROP_RULES = {
    "WHEAT": (10, 2, 4, 24, False),
    "CARROT": (20, 2, 3, 25, False),
    "TOMATO": (50, 8, 0, 19, True),
    "STRAWBERRY": (100, 10, 0, 16, True),
    "MELON": (80, 10, 12, 16, False),
}

COW_COST = 400
TARGET_HANDS_CORE = 10
TARGET_HANDS_EXPANDED = 10
LAND_DAY = 4
EXPANSION_DEADLINE = 16
EXPANSION_BUFFER = 500
SELL_ORDER = (
    "MILK", "FERTILIZER", "MELON", "STRAWBERRY",
    "TOMATO", "CARROT", "WHEAT", "EGG", "WOOL",
)


def _cow_slots(board_size, expanded):
    h = board_size // 2
    slots = [(h - 1, h - 1), (h - 1, h - 2), (h - 2, h - 1)]
    if expanded:
        slots.extend([
            (h, h - 1),
            (h + 1, h - 1),
            (h + 2, h - 1),
            (h + 3, h - 1),
            (h + 4, h - 1),
            (h, h - 2),
        ])
    return [p for p in slots if 0 <= p[0] < board_size and 0 <= p[1] < board_size]


def _shed_tiles(board_size, tiles):
    h = board_size // 2
    out = []
    for p in ((h - 1, h - 1), (h, h - 1), (h - 1, h), (h, h)):
        if 0 <= p[0] < board_size and 0 <= p[1] < board_size and tiles[p[1]][p[0]] != "LOCKED":
            out.append(p)
    return out


def _dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _nearest_shed(board_size, tiles, pos):
    cells = _shed_tiles(board_size, tiles)
    return min(cells, key=lambda p: (_dist(pos, p), p[1], p[0])) if cells else tuple(pos)


def _move(tiles, source, target):
    source = tuple(source)
    target = tuple(target)
    if source == target:
        return ["PASS"]
    n = len(tiles)
    q = deque([source])
    parent = {source: None}
    move_to = {}
    directions = ((1, 0, "EAST"), (-1, 0, "WEST"), (0, 1, "SOUTH"), (0, -1, "NORTH"))
    while q:
        cur = q.popleft()
        if cur == target:
            break
        ranked = sorted(
            directions,
            key=lambda d: abs(cur[0] + d[0] - target[0]) + abs(cur[1] + d[1] - target[1]),
        )
        for dx, dy, name in ranked:
            nxt = (cur[0] + dx, cur[1] + dy)
            if not (0 <= nxt[0] < n and 0 <= nxt[1] < n):
                continue
            if tiles[nxt[1]][nxt[0]] == "LOCKED" or nxt in parent:
                continue
            parent[nxt] = cur
            move_to[nxt] = name
            q.append(nxt)
    if target not in parent:
        return ["PASS"]
    cur = target
    while parent[cur] != source:
        cur = parent[cur]
        if cur is None:
            return ["PASS"]
    return [move_to[cur]]


def _inventories(private):
    return [dict(x or {}) for x in (private.get("inventories", []) or [])]


def _total(private, item):
    value = int((private.get("shed", {}) or {}).get(item, 0))
    for inv in private.get("inventories", []) or []:
        value += int((inv or {}).get(item, 0))
    return value


def _placed_cows(farm):
    return sum(
        1
        for row in farm.get("tiles", []) or []
        for tile in row
        if isinstance(tile, dict) and tile.get("animal") == "COW"
    )


def _count_public_animals(farm, animal):
    return sum(
        1
        for row in farm.get("tiles", []) or []
        for tile in row
        if isinstance(tile, dict) and tile.get("animal") == animal
    )


def _crop_plan(board_size, unlocked_quadrants, animal_slots):
    h = board_size // 2
    quadrants = set(unlocked_quadrants or ["NW"])
    shed = (h - 1, h - 1)
    mixes = {
        "NW": (("MELON", 11), ("STRAWBERRY", 5), ("CARROT", 2), ("WHEAT", 4)),
        "NE": (("STRAWBERRY", 14), ("WHEAT", 4), ("CARROT", 1)),
        "SW": (("STRAWBERRY", 20), ("WHEAT", 4), ("CARROT", 1)),
        "SE": (("STRAWBERRY", 18), ("WHEAT", 5), ("CARROT", 2)),
    }
    bounds = {
        "NW": (range(0, h), range(0, h)),
        "NE": (range(h, board_size), range(0, h)),
        "SW": (range(0, h), range(h, board_size)),
        "SE": (range(h, board_size), range(h, board_size)),
    }
    plan = {}
    for quadrant in ("NW", "NE", "SW", "SE"):
        if quadrant not in quadrants:
            continue
        xs, ys = bounds[quadrant]
        cells = [(x, y) for y in ys for x in xs if (x, y) not in animal_slots]
        cells.sort(key=lambda p: (_dist(p, shed), p[1], p[0]))
        crops = []
        for crop, count in mixes[quadrant]:
            crops.extend([crop] * count)
        while len(crops) < len(cells):
            crops.append("STRAWBERRY")
        plan.update(zip(cells, crops[:len(cells)]))
    return plan

def _add(tasks, priority, pos, action, need=None):
    tasks.append({"priority": priority, "pos": tuple(pos), "action": list(action), "need": need})


def _animal_for_slot(position, slots):
    index = slots.index(position)
    return "SHEEP" if index in (1, 2) else "COW"


def _animal_tasks(obs, farm, private, slots):
    day = int(obs.get("day", 0))
    prices = ((obs.get("market", {}) or {}).get("prices", {}) or {})
    tasks = []
    tiles = farm["tiles"]
    planned_animals = _planned_animals_for_slots(obs, farm, private, slots)
    for pos in slots:
        x, y = pos
        tile = tiles[y][x]
        planned = planned_animals.get(tuple(pos))
        if planned is None:
            continue
        if tile == "LOCKED":
            continue
        if isinstance(tile, dict) and tile.get("animal") in ("COW", "SHEEP"):
            animal = tile["animal"]
            product = "MILK" if animal == "COW" else "WOOL"
            if not tile.get("fed_today", False):
                _add(tasks, 0, pos, ["FEED"], "WHEAT")
            if tile.get("fertilizer_available", False):
                _add(tasks, 1, pos, ["COLLECT_FERTILIZER"])
            if day <= 27 and int(prices.get(product, 100)) >= 20 and not tile.get("cared_today", False):
                _add(tasks, 2, pos, ["CARE"])
            held = int(tile.get("yield_units", 0))
            if held >= 3 or (day >= 27 and held > 0):
                _add(tasks, 1, pos, ["HARVEST"])
        elif tile is None:
            _add(tasks, 0, pos, ["BUILD_PASTURE"])
        elif isinstance(tile, dict) and tile.get("kind") == "WEED":
            _add(tasks, 0, pos, ["DIG"])
        elif isinstance(tile, dict) and tile.get("kind") == "PASTURE" and not tile.get("animal"):
            _add(tasks, 0, pos, ["PLACE", planned], planned)
        elif isinstance(tile, dict) and tile.get("kind") == "PLANT":
            _add(tasks, 0, pos, ["DIG"])
    return tasks

def _crop_tasks(obs, farm, private, plan, cow_slots):
    day = int(obs.get("day", 0))
    hour = int(obs.get("hour", 0))
    seeds = private.get("seeds", {}) or {}
    tasks = []
    for pos, planned in plan.items():
        if pos in cow_slots:
            continue
        x, y = pos
        tile = farm["tiles"][y][x]
        if tile == "LOCKED":
            continue
        if tile is None:
            if day <= CROP_RULES[planned][3] and hour <= 19 and int(seeds.get(planned, 0)) > 0:
                _add(tasks, 8, pos, ["PLANT", planned])
            continue
        if not isinstance(tile, dict):
            continue
        if tile.get("kind") == "WEED":
            _add(tasks, 7, pos, ["DIG"])
            continue
        if tile.get("kind") != "PLANT":
            continue
        crop = tile.get("crop", planned)
        _, first, harvest_day, _, ongoing = CROP_RULES.get(crop, CROP_RULES[planned])
        age = day - int(tile.get("planted_day", day))
        held = int(tile.get("yield_units", 0))
        risk = int(tile.get("consecutive_unwatered", 0)) >= 1
        if not tile.get("watered_today", False):
            _add(tasks, 3 if risk or hour >= 17 else 5, pos, ["WATER"])
            continue
        if not ongoing:
            if age >= harvest_day and held > 0:
                _add(tasks, 4, pos, ["HARVEST"])
        elif age >= first and (held >= 3 or (day >= 27 and held > 0)):
            _add(tasks, 4, pos, ["HARVEST"])
    return tasks


def _task_cost(farm, pos, inv, shed, task):
    need = task["need"]
    target = task["pos"]
    if need is None or int(inv.get(need, 0)) > 0:
        return _dist(pos, target)
    if int(shed.get(need, 0)) <= 0:
        return 10000
    s = _nearest_shed(len(farm["tiles"]), farm["tiles"], pos)
    return _dist(pos, s) + 1 + _dist(s, target)


def _task_action(farm, pos, inv, shed, task):
    need = task["need"]
    if need is not None and int(inv.get(need, 0)) <= 0:
        if int(shed.get(need, 0)) <= 0:
            return ["PASS"]
        s = _nearest_shed(len(farm["tiles"]), farm["tiles"], pos)
        if tuple(pos) == tuple(s):
            return ["PICKUP", need, 1 if need in ("COW", "SHEEP") else 4]
        return _move(farm["tiles"], pos, s)
    if tuple(pos) == task["pos"]:
        return list(task["action"])
    return _move(farm["tiles"], pos, task["pos"])


def _unit_actions(obs, farm, private, cow_slots, crop_plan):
    day = int(obs.get("day", 0))
    hour = int(obs.get("hour", 0))
    positions = [tuple(farm.get("farmer", [0, 0]))] + [tuple(p) for p in farm.get("hands", [])]
    invs = _inventories(private)
    while len(invs) < len(positions):
        invs.append({})
    shed = dict(private.get("shed", {}) or {})
    tasks = _animal_tasks(obs, farm, private, cow_slots) + _crop_tasks(obs, farm, private, crop_plan, set(cow_slots))
    actions = [["PASS"] for _ in positions]
    free_units = set(range(len(positions)))
    free_tasks = set(range(len(tasks)))

    if day >= 29 and hour >= 14:
        for i, pos in enumerate(positions):
            carried = sum(int(v) for v in invs[i].values())
            s = _nearest_shed(len(farm["tiles"]), farm["tiles"], pos)
            if carried:
                actions[i] = ["DROP"] if pos == s else _move(farm["tiles"], pos, s)
            elif pos != s:
                actions[i] = _move(farm["tiles"], pos, s)
        return actions

    while free_units and free_tasks:
        best = None
        for i in free_units:
            for j in free_tasks:
                task = tasks[j]
                cost = _task_cost(farm, positions[i], invs[i], shed, task)
                if cost >= 10000:
                    continue
                key = (task["priority"], cost, task["pos"][1], task["pos"][0], i, j)
                if best is None or key < best[0]:
                    best = (key, i, j)
        if best is None:
            break
        _, i, j = best
        actions[i] = _task_action(farm, positions[i], invs[i], shed, tasks[j])
        free_units.remove(i)
        free_tasks.remove(j)

    remaining = dict(private.get("seeds", {}) or {})
    for i, action in enumerate(actions):
        if len(action) >= 2 and action[0] == "PLANT":
            crop = action[1]
            if int(remaining.get(crop, 0)) <= 0:
                actions[i] = ["PASS"]
            else:
                remaining[crop] -= 1
    return actions


def _fib(n):
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a



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

def _market_actions(obs, farm, private, animal_slots, crop_plan):
    day = int(obs.get("day", 0))
    hour = int(obs.get("hour", 0))
    shed = private.get("shed", {}) or {}
    prices = ((obs.get("market", {}) or {}).get("prices", {}) or {})
    orders = []
    budget = float(farm.get("money", 0))

    placed = {
        animal: _count_public_animals(farm, animal)
        for animal in ("COW", "SHEEP")
    }
    owned = {
        animal: placed[animal] + _total(private, animal)
        for animal in ("COW", "SHEEP")
    }
    quadrants = list(farm.get("unlocked_quadrants", []) or ["NW"])
    expanded = len(quadrants) >= 2
    target = _select_herd_target(obs, farm, private) if expanded else {"COW": 1, "SHEEP": 2}
    animal_count = placed["COW"] + placed["SHEEP"]
    wheat_reserve = max(8, animal_count * 3)

    for item in SELL_ORDER:
        if len(orders) >= 6:
            break
        amount = int(shed.get(item, 0))
        if item == "WHEAT" and day < 29:
            amount = max(0, amount - wheat_reserve)
        if amount <= 0:
            continue
        cap = amount if day >= 29 else 20 if item in ("MILK", "WOOL", "FERTILIZER") else 28
        quantity = min(amount, cap)
        orders.append(["SELL", item, quantity])
        budget += quantity * max(1, int(prices.get(item, 1)))

    if day >= 29:
        hire_orders = []
        if hour <= 3:
            missing = max(0, 10 - len(farm.get("hands", []) or []))
            hire_index = int(farm.get("hires_today", 0))
            while missing > 0 and len(hire_orders) < 10:
                cost = _fib(hire_index)
                if budget < cost + 20:
                    break
                hire_orders.append(["HIRE"])
                budget -= cost
                hire_index += 1
                missing -= 1
        return (hire_orders + orders)[:10]

    extra_land = max(0, len(quadrants) - 1)
    land_costs = (1000, 2000, 4000)
    earliest = 5 if extra_land == 0 else 9 if extra_land == 1 else 15
    if (
        extra_land < 2
        and earliest <= day <= 18
        and len(orders) < 10
        and budget >= land_costs[extra_land] + (300 if extra_land == 0 else 500)
    ):
        orders.append(["BUY_LAND"])
        budget -= land_costs[extra_land]
        extra_land += 1
        expanded = True
        target = {"COW": 7, "SHEEP": 2}

    costs = {"COW": 400, "SHEEP": 500}
    for animal in ("COW", "SHEEP"):
        if len(orders) >= 10:
            break
        missing = max(0, target[animal] - owned[animal])
        affordable = max(0, int((budget - 220) // costs[animal]))
        quantity = min(missing, 2, affordable)
        if quantity > 0:
            orders.append(["BUY_ANIMAL", animal, quantity])
            budget -= quantity * costs[animal]
            owned[animal] += quantity

    wheat_total = _total(private, "WHEAT")
    wanted_wheat = max(0, max(8, (placed["COW"] + placed["SHEEP"]) * 3 + 3) - wheat_total)
    if wanted_wheat > 0 and len(orders) < 10:
        price = max(1, int(prices.get("WHEAT", 25)))
        quantity = min(wanted_wheat, max(0, int((budget - 100) // price)))
        if quantity > 0:
            orders.append(["BUY_PRODUCT", "WHEAT", quantity])
            budget -= quantity * price

    seeds = private.get("seeds", {}) or {}
    needs = {crop: 0 for crop in CROP_RULES}
    for (x, y), crop in crop_plan.items():
        tile = farm["tiles"][y][x]
        if tile is None and day <= CROP_RULES[crop][3]:
            needs[crop] += 1
    for crop in ("MELON", "STRAWBERRY", "CARROT", "WHEAT"):
        if len(orders) >= 10:
            break
        wanted = max(0, needs[crop] - int(seeds.get(crop, 0)))
        if wanted <= 0:
            continue
        cost = CROP_RULES[crop][0]
        quantity = min(wanted, 20, max(0, int((budget - 80) // cost)))
        if quantity > 0:
            orders.append(["BUY_SEED", crop, quantity])
            budget -= quantity * cost

    if hour <= 3:
        missing = max(0, 10 - len(farm.get("hands", []) or []))
        hire_index = int(farm.get("hires_today", 0))
        while missing > 0 and len(orders) < 10:
            cost = _fib(hire_index)
            if budget < cost + 20:
                break
            orders.append(["HIRE"])
            budget -= cost
            hire_index += 1
            missing -= 1
    return orders[:10]

def agent(obs):
    farms = obs.get("farms", []) or []
    player = int(obs.get("player", 0))
    if player < 0 or player >= len(farms):
        return {"farmer": ["PASS"], "hands": [], "market": []}
    farm = farms[player]
    private = obs.get("private", {}) or {}
    board_size = len(farm.get("tiles", [])) or 10
    quadrants = list(farm.get("unlocked_quadrants", []) or ["NW"])
    expanded = len(quadrants) >= 2
    all_animal_slots = _cow_slots(board_size, expanded)
    animals_owned = sum(
        _count_public_animals(farm, animal) + _total(private, animal)
        for animal in ("COW", "SHEEP")
    )
    active_count = min(len(all_animal_slots), max(3, animals_owned))
    animal_slots = all_animal_slots[:active_count]
    crop_plan = _crop_plan(board_size, quadrants, set(all_animal_slots))
    actions = _unit_actions(obs, farm, private, animal_slots, crop_plan)
    return {
        "farmer": actions[0] if actions else ["PASS"],
        "hands": actions[1:] if len(actions) > 1 else [],
        "market": _market_actions(obs, farm, private, all_animal_slots, crop_plan),
    }
