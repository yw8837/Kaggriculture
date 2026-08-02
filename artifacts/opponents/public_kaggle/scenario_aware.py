"""Deterministic scenario-aware economic policy for Kaggriculture."""

from collections import deque
import math


# Domain constants

CROPS = {
    "WHEAT": {
        "seed": 10,
        "first": 2,
        "max_day": 4,
        "max_yield": 6,
        "ongoing": False,
        "ripe": 4,
        "last_plant": 24,
    },
    "CARROT": {
        "seed": 20,
        "first": 2,
        "max_day": 3,
        "max_yield": 4,
        "ongoing": False,
        "ripe": 3,
        "last_plant": 25,
    },
    "TOMATO": {
        "seed": 50,
        "first": 8,
        "max_day": 8,
        "max_yield": 4,
        "ongoing": True,
        "ripe": 8,
        "last_plant": 19,
    },
    "STRAWBERRY": {
        "seed": 100,
        "first": 10,
        "max_day": 10,
        "max_yield": 4,
        "ongoing": True,
        "ripe": 10,
        "last_plant": 18,
    },
    "MELON": {
        "seed": 80,
        "first": 10,
        "max_day": 12,
        "max_yield": 6,
        "ongoing": False,
        "ripe": 10,
        "last_plant": 18,
    },
}

ANIMALS = {
    "GOOSE": {
        "cost": 300,
        "structure": "COOP",
        "product": "EGG",
        "max_held": 4,
    }
}

PRODUCTS = (
    "WHEAT",
    "CARROT",
    "TOMATO",
    "STRAWBERRY",
    "MELON",
    "EGG",
    "MILK",
    "WOOL",
    "FERTILIZER",
)

MARKET = {
    "WHEAT": (25, 400, "sqrt", 0.80, "log", 0.20),
    "CARROT": (35, 450, "log", 0.20, "sqrt", 0.70),
    "TOMATO": (60, 200, "linear", 0.40, "sqrt", 0.60),
    "STRAWBERRY": (120, 100, "sqrt", 0.70, "linear", 1.60),
    "MELON": (250, 300, "log", 0.20, "sq", 3.60),
    "EGG": (50, 332, "linear", 0.40, "log", 0.20),
    "MILK": (160, 122, "sqrt", 0.60, "linear", 1.60),
    "WOOL": (200, 105, "log", 0.20, "sq", 3.20),
    "FERTILIZER": (100, 200, "linear", 0.40, "linear", 0.40),
}

SHOPS = {
    "BAKERY": ("EGG", "WHEAT"),
    "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
    "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"),
    "YARN_STORE": ("WOOL",),
    "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"),
    "PET_CAFE": ("CARROT",),
    "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"),
    "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY"),
}

RESERVE_FRACTION = {
    "WHEAT": 0.68,
    "CARROT": 0.55,
    "TOMATO": 0.50,
    "STRAWBERRY": 0.48,
    "MELON": 0.58,
    "EGG": 0.65,
    "MILK": 0.42,
    "WOOL": 0.40,
    "FERTILIZER": 0.18,
}

MOVES = (
    ("NORTH", 0, -1),
    ("WEST", -1, 0),
    ("SOUTH", 0, 1),
    ("EAST", 1, 0),
)

LAND_PRICES = (1000, 2000, 4000)
MARKET_I0 = 10000
TOTAL_DAYS = 30
MAX_MARKET_ORDERS = 10
MAX_HANDS = 12
TARGET_GEESE = 11
MELON_TILES_MIN = 12
MELON_TILES_BASE = 16
MELON_TILES_MAX = 18
WHEAT_TILES = 45
ANIMAL_START_DAY = 5
MAX_EXTRA_LAND = 2
CASH_RESERVE = 250
LIQUIDATION_TURNS = 38
SHED_CAPACITY = 100
TRAVEL_COST = 8.0
ANIMAL_RAMP_PER_DAY = 2.5
FEED_STOCK_DAYS = 2
PRIORITY_BONUS = {
    -1: 120_000.0,
    0: 100_000.0,
    1: 1_500.0,
    2: 750.0,
    3: 250.0,
    4: 0.0,
    5: -100.0,
}


# Configuration, pricing, and routing helpers

def _cfg(config, key, default):
    if config is None:
        return default
    if isinstance(config, dict):
        return config.get(key, default)
    return getattr(config, key, default)


def _shape(name, value):
    value = max(0.0, float(value))
    if name == "linear":
        return value
    if name == "sq":
        return value * value
    if name == "sqrt":
        return math.sqrt(value)
    if name == "log":
        return math.log1p(value)
    if name == "log10":
        return math.log10(1.0 + value)
    return value


def _market_parameters(obs, item):
    base, throughput, below_fn, below_move, above_fn, above_move = MARKET[item]
    custom = (((obs or {}).get("market", {}) or {}).get("params", {}) or {}).get(
        item, {}
    )
    return (
        float(custom.get("base", base)),
        float(custom.get("T", throughput)),
        str(custom.get("below_func", below_fn)),
        float(custom.get("below_target", below_move)),
        str(custom.get("above_func", above_fn)),
        float(custom.get("above_target", above_move)),
        float(custom.get("I0", MARKET_I0)),
    )


def _price_at(item, inventory, obs=None):
    (
        base,
        throughput,
        below_fn,
        below_move,
        above_fn,
        above_move,
        equilibrium,
    ) = _market_parameters(obs, item)
    if inventory < equilibrium:
        amplitude = below_move * base / max(1e-9, _shape(below_fn, throughput))
        value = base + amplitude * _shape(below_fn, equilibrium - inventory)
    else:
        amplitude = above_move * base / max(1e-9, _shape(above_fn, throughput))
        value = base - amplitude * _shape(above_fn, inventory - equilibrium)
    return max(1, int(round(value)))


def _town_demand_per_day(obs, item):
    day = int((obs or {}).get("day", 0) or 0)
    center = 0 if item == "FERTILIZER" else 2 * (
        4 if day >= 20 else 2 if day >= 10 else 1
    )
    shop = 0
    for name in (((obs or {}).get("town", {}) or {}).get(
        "unlocked_shops", []
    ) or []):
        products = SHOPS.get(name, ())
        if item in products:
            shop += 12 if len(products) == 1 else 6
    return center + shop


def _opponent_visible_supply(obs, item, horizon=1):
    player = int((obs or {}).get("player", 0) or 0)
    day = int((obs or {}).get("day", 0) or 0)
    animal_for = {"EGG": "GOOSE", "MILK": "COW", "WOOL": "SHEEP"}
    total = 0
    for index, farm in enumerate((obs or {}).get("farms", []) or []):
        if index == player:
            continue
        for row in farm.get("tiles", []) or []:
            for tile in row:
                if not isinstance(tile, dict):
                    continue
                if (
                    item in CROPS
                    and tile.get("kind") == "PLANT"
                    and tile.get("crop") == item
                ):
                    rule = CROPS[item]
                    age = day - int(tile.get("planted_day", day) or day)
                    held = int(tile.get("yield_units", 0) or 0)
                    if held > 0 and age >= rule["first"]:
                        total += held
                    elif age + horizon >= rule["ripe"]:
                        total += max(1, min(rule["max_yield"], held + horizon))
                elif item in animal_for and tile.get("animal") == animal_for[item]:
                    total += int(tile.get("yield_units", 0) or 0)
                    if horizon > 0:
                        total += min(2 * horizon, ANIMALS.get(
                            tile.get("animal"), {"max_held": 4}
                        )["max_held"])
    return total


def _distance(a, b):
    return abs(int(a[0]) - int(b[0])) + abs(int(a[1]) - int(b[1]))


def _shed_tiles(board_size, tiles=None):
    half = board_size // 2
    candidates = (
        (half - 1, half - 1),
        (half, half - 1),
        (half - 1, half),
        (half, half),
    )
    if tiles is None:
        return candidates
    accessible = tuple(
        position
        for position in candidates
        if tiles[position[1]][position[0]] != "LOCKED"
    )
    return accessible or candidates[:1]


def _nearest_shed(position, board_size, tiles=None):
    return min(
        _shed_tiles(board_size, tiles),
        key=lambda target: (_distance(position, target), target[1], target[0]),
    )


def _bfs_first_step(tiles, source, target):
    source = (int(source[0]), int(source[1]))
    target = (int(target[0]), int(target[1]))
    if source == target:
        return ["PASS"]
    board_size = len(tiles)
    queue = deque([source])
    parent = {source: None}
    parent_move = {}
    while queue:
        current = queue.popleft()
        if current == target:
            break
        for name, dx, dy in MOVES:
            nxt = (current[0] + dx, current[1] + dy)
            if not (0 <= nxt[0] < board_size and 0 <= nxt[1] < board_size):
                continue
            if nxt in parent or tiles[nxt[1]][nxt[0]] == "LOCKED":
                continue
            parent[nxt] = current
            parent_move[nxt] = name
            queue.append(nxt)
    if target not in parent:
        return ["PASS"]
    current = target
    while parent[current] != source:
        current = parent[current]
        if current is None:
            return ["PASS"]
    return [parent_move[current]]


def _melon_target(obs):
    prices = ((obs.get("market", {}) or {}).get("prices", {}) or {})
    price = int(prices.get("MELON", MARKET["MELON"][0]) or MARKET["MELON"][0])
    opponent_tiles = 0
    player = int(obs.get("player", 0) or 0)
    for index, other in enumerate(obs.get("farms", []) or []):
        if index == player:
            continue
        for row in other.get("tiles", []) or []:
            opponent_tiles += sum(
                isinstance(tile, dict)
                and tile.get("kind") == "PLANT"
                and tile.get("crop") == "MELON"
                for tile in row
            )
    if price >= 300 and opponent_tiles <= 8:
        return MELON_TILES_MAX
    if price <= 160 or opponent_tiles >= 20:
        return MELON_TILES_MIN
    if opponent_tiles >= 17:
        return MELON_TILES_BASE - 1
    return MELON_TILES_BASE


def _specialty_sequence(obs):
    day = int(obs.get("day", 0) or 0)
    prices = ((obs.get("market", {}) or {}).get("prices", {}) or {})
    expected = {"CARROT": 3, "TOMATO": 4, "STRAWBERRY": 4}
    delay = {"CARROT": 3, "TOMATO": 12, "STRAWBERRY": 16}
    safe_last = {"CARROT": 25, "TOMATO": 17, "STRAWBERRY": 12}
    wheat_price = float(
        prices.get("WHEAT", MARKET["WHEAT"][0]) or MARKET["WHEAT"][0]
    )
    wheat_score = (4 * wheat_price - CROPS["WHEAT"]["seed"]) / 4.0
    scored = []
    for crop in ("CARROT", "TOMATO", "STRAWBERRY"):
        if day > safe_last[crop]:
            continue
        price = float(prices.get(crop, MARKET[crop][0]) or MARKET[crop][0])
        margin_rate = (
            expected[crop] * price - CROPS[crop]["seed"]
        ) / float(delay[crop])
        demand_bonus = 0.20 * _town_demand_per_day(obs, crop)
        opponent_penalty = 0.35 * _opponent_visible_supply(
            obs, crop, horizon=delay[crop]
        )
        score = margin_rate + demand_bonus - opponent_penalty
        if score >= 1.15 * wheat_score:
            scored.append((score, crop))
    scored.sort(reverse=True)
    if not scored:
        return []
    if len(scored) == 1:
        return [scored[0][1]] * 7
    first, second = scored[0][1], scored[1][1]
    return [first, first, second, first, second, first, second]


def _role_plan(obs, farm):
    day = int(obs.get("day", 0) or 0)
    left = TOTAL_DAYS - day
    tiles = farm.get("tiles", []) or []
    board_size = len(tiles)
    sheds = _shed_tiles(board_size, tiles)
    cells = []
    for y, row in enumerate(tiles):
        for x, tile in enumerate(row):
            if tile == "LOCKED":
                continue
            distance = min(_distance((x, y), shed) for shed in sheds)
            cells.append((distance, y, x))
    cells.sort()

    fixed_animal = []
    animals = 0
    for _, y, x in cells:
        tile = tiles[y][x]
        if isinstance(tile, dict) and (
            "animal" in tile or tile.get("kind") == "COOP"
        ):
            fixed_animal.append((x, y))
            animals += int("animal" in tile)

    private = obs.get("private", {}) or {}
    goose_pipeline = int((private.get("shed", {}) or {}).get("GOOSE", 0) or 0)
    for inventory in private.get("inventories", []) or []:
        goose_pipeline += int((inventory or {}).get("GOOSE", 0) or 0)

    ramp = max(0, int((day - ANIMAL_START_DAY) * ANIMAL_RAMP_PER_DAY))
    affordable = (
        animals
        + goose_pipeline
        + max(0, int((float(farm.get("money", 0) or 0) - 600) // 350))
    )
    desired_animals = min(
        TARGET_GEESE,
        max(0, len(cells) - 12),
        max(len(fixed_animal), min(ramp, affordable)),
    )
    if left < 8:
        desired_animals = len(fixed_animal)

    animal_positions = set(fixed_animal)
    for _, y, x in cells:
        if len(animal_positions) >= desired_animals:
            break
        animal_positions.add((x, y))

    melon_tiles = min(
        _melon_target(obs),
        max(0, len(cells) - len(animal_positions)),
    )
    specialties = _specialty_sequence(obs)
    roles = {}
    crop_index = 0
    specialty_index = 0
    for _, y, x in cells:
        position = (x, y)
        if position in animal_positions:
            roles[position] = ("ANIMAL", "GOOSE")
        elif crop_index < melon_tiles:
            roles[position] = ("CROP", "MELON")
            crop_index += 1
        elif crop_index < melon_tiles + WHEAT_TILES:
            roles[position] = ("CROP", "WHEAT")
            crop_index += 1
        elif specialty_index < len(specialties):
            roles[position] = ("CROP", specialties[specialty_index])
            specialty_index += 1
    return roles


# Observation summaries and job generation

def _inventory_total(inventory, excluded=()):
    return sum(
        int(value)
        for item, value in (inventory or {}).items()
        if item not in excluded and isinstance(value, (int, float)) and value > 0
    )


def _survey(farm, private, roles=None, day=0):
    summary = {
        "animals": 0,
        "unfed": 0,
        "at_risk_animals": 0,
        "at_risk_crops": 0,
        "open_coops": 0,
        "coops_todo": 0,
        "plants": 0,
        "plantable": 0,
        "weeds": 0,
    }
    for row in farm.get("tiles", []) or []:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if "animal" in tile:
                summary["animals"] += 1
                if not tile.get("fed_today", False):
                    summary["unfed"] += 1
                if int(tile.get("consecutive_unfed", 0) or 0) >= 1:
                    summary["at_risk_animals"] += 1
            elif tile.get("kind") == "COOP":
                summary["open_coops"] += 1
            elif tile.get("kind") == "PLANT":
                summary["plants"] += 1
                if int(tile.get("consecutive_unwatered", 0) or 0) >= 1:
                    summary["at_risk_crops"] += 1
            elif tile.get("kind") == "WEED":
                summary["weeds"] += 1

    if roles:
        for (x, y), (kind, item) in roles.items():
            tile = farm["tiles"][y][x]
            if kind == "ANIMAL" and tile is None:
                summary["coops_todo"] += 1
            elif (
                kind == "CROP"
                and tile is None
                and day <= CROPS[item]["last_plant"]
            ):
                summary["plantable"] += 1

    summary["wheat_stock"] = int((private.get("shed", {}) or {}).get("WHEAT", 0))
    summary["goose_stock"] = int((private.get("shed", {}) or {}).get("GOOSE", 0))
    summary["shed_load"] = sum(
        max(0, int(value or 0))
        for value in (private.get("shed", {}) or {}).values()
    )
    summary["carried_load"] = 0
    for inventory in private.get("inventories", []) or []:
        summary["wheat_stock"] += int((inventory or {}).get("WHEAT", 0))
        summary["goose_stock"] += int((inventory or {}).get("GOOSE", 0))
        summary["carried_load"] += _inventory_total(inventory)
    return summary


def _policy_phase(obs, farm, private, summary):
    day = int(obs.get("day", 0) or 0)
    step = int(obs.get("step", day * 24 + int(obs.get("hour", 0) or 0)) or 0)
    actions_left = max(0, 719 - step)
    if actions_left <= LIQUIDATION_TURNS:
        return "LIQUIDATE"
    workers = 1 + len(farm.get("hands", []) or [])
    if (
        summary["at_risk_animals"] + summary["at_risk_crops"] > workers
        or summary["shed_load"] + summary["carried_load"] >= 95
    ):
        return "CRISIS"
    if day <= 4:
        return "BOOTSTRAP"
    if day <= 21:
        return "COMPOUND"
    return "REALIZE"


def _add_job(
    jobs,
    priority,
    value,
    target,
    action,
    need=None,
    reason="",
    latest_hour=23,
):
    jobs.append(
        {
            "priority": int(priority),
            "value": float(value),
            "target": tuple(target),
            "action": list(action),
            "need": need,
            "reason": str(reason),
            "latest_hour": int(latest_hour),
        }
    )


def _crop_jobs(obs, jobs, tile, target, day, liquidation):
    crop = tile.get("crop")
    rule = CROPS.get(crop)
    if rule is None:
        return
    prices = ((obs.get("market", {}) or {}).get("prices", {}) or {})
    price = float(prices.get(crop, MARKET[crop][0]) or MARKET[crop][0])
    age = day - int(tile.get("planted_day", day))
    amount = int(tile.get("yield_units", 0) or 0)
    watered = bool(tile.get("watered_today", False))
    drought = int(tile.get("consecutive_unwatered", 0) or 0)
    critical = drought >= 1

    if liquidation:
        if amount > 0 and age >= rule["first"]:
            _add_job(
                jobs,
                0,
                amount * price,
                target,
                ("HARVEST",),
                reason="terminal_harvest",
            )
        return

    if critical and not watered:
        protected = max(amount, rule["max_yield"] * 0.7) * price
        _add_job(
            jobs,
            0,
            protected,
            target,
            ("WATER",),
            reason="critical_water",
        )
        return

    if rule["ongoing"]:
        if amount >= rule["max_yield"] - 1 or (amount > 0 and day >= 27):
            _add_job(
                jobs,
                2,
                amount * price,
                target,
                ("HARVEST",),
                reason="ongoing_harvest",
            )
        elif not watered and age >= rule["first"] - 1:
            _add_job(
                jobs,
                3,
                price,
                target,
                ("WATER",),
                reason="ongoing_water",
            )
        return

    ripe = age >= rule["ripe"] and amount > 0
    in_growth_window = (rule["max_day"] + 1) // 2 <= age <= rule["max_day"]
    if ripe:
        if in_growth_window and not watered and amount < rule["max_yield"]:
            _add_job(
                jobs,
                1,
                price,
                target,
                ("WATER",),
                reason="final_growth_water",
            )
        else:
            _add_job(
                jobs,
                2,
                amount * price,
                target,
                ("HARVEST",),
                reason="ripe_harvest",
            )
    elif in_growth_window and not watered:
        _add_job(
            jobs,
            3,
            price,
            target,
            ("WATER",),
            reason="yield_water",
        )


def _field_jobs(obs, farm, private, roles, liquidation):
    day = int(obs.get("day", 0) or 0)
    hour = int(obs.get("hour", 0) or 0)
    left = TOTAL_DAYS - day
    tiles = farm["tiles"]
    seeds = dict(private.get("seeds", {}) or {})
    prices = ((obs.get("market", {}) or {}).get("prices", {}) or {})
    jobs = []
    planned_roles = dict(roles)
    for y, row in enumerate(tiles):
        for x, tile in enumerate(row):
            if not isinstance(tile, dict) or (x, y) in planned_roles:
                continue
            if tile.get("kind") == "PLANT" and tile.get("crop") in CROPS:
                planned_roles[(x, y)] = ("CROP", tile["crop"])
            elif "animal" in tile:
                planned_roles[(x, y)] = ("ANIMAL", "GOOSE")

    for target, role in planned_roles.items():
        x, y = target
        tile = tiles[y][x]
        role_kind, role_item = role

        if tile is None:
            if liquidation:
                continue
            if role_kind == "ANIMAL":
                if left >= 8:
                    _add_job(
                        jobs,
                        5,
                        240,
                        target,
                        ("BUILD_COOP",),
                        reason="build_coop",
                        latest_hour=22,
                    )
            elif (
                hour <= 22
                and day <= CROPS[role_item]["last_plant"]
                and seeds.get(role_item, 0) > 0
            ):
                rule = CROPS[role_item]
                expected = 4 if role_item == "WHEAT" else rule["max_yield"]
                price = float(
                    prices.get(role_item, MARKET[role_item][0])
                    or MARKET[role_item][0]
                )
                value = max(40, 0.65 * expected * price - rule["seed"])
                _add_job(
                    jobs,
                    4,
                    value,
                    target,
                    ("PLANT", role_item),
                    reason="plant_" + role_item,
                    latest_hour=22,
                )
            continue

        if not isinstance(tile, dict):
            continue
        kind = tile.get("kind")
        if kind == "WEED":
            if not liquidation:
                _add_job(
                    jobs,
                    4,
                    120 if left > 5 else 10,
                    target,
                    ("DIG",),
                    reason="dig_weed",
                    latest_hour=22,
                )
            continue
        if kind == "PLANT":
            _crop_jobs(obs, jobs, tile, target, day, liquidation)
            continue
        if kind == "COOP" and "animal" not in tile:
            if not liquidation:
                _add_job(
                    jobs,
                    1,
                    700,
                    target,
                    ("PLACE", "GOOSE"),
                    need="GOOSE",
                    reason="place_goose",
                )
            continue
        if "animal" not in tile:
            continue
        if liquidation:
            if int(tile.get("yield_units", 0) or 0) > 0:
                product = ANIMALS.get(
                    tile.get("animal"), ANIMALS["GOOSE"]
                )["product"]
                value = int(tile.get("yield_units", 0) or 0) * float(
                    prices.get(product, MARKET[product][0])
                    or MARKET[product][0]
                )
                _add_job(
                    jobs,
                    0,
                    value,
                    target,
                    ("HARVEST",),
                    reason="terminal_animal",
                )
            if tile.get("fertilizer_available", False):
                _add_job(
                    jobs,
                    0,
                    float(
                        prices.get("FERTILIZER", MARKET["FERTILIZER"][0])
                        or MARKET["FERTILIZER"][0]
                    ),
                    target,
                    ("COLLECT_FERTILIZER",),
                    reason="terminal_fertilizer",
                )
            continue
        if not tile.get("fed_today", False):
            risk = int(tile.get("consecutive_unfed", 0) or 0) >= 1
            _add_job(
                jobs,
                0 if risk else 1,
                900 if risk else 260,
                target,
                ("FEED",),
                need="WHEAT",
                reason="critical_feed" if risk else "feed",
            )
        held = int(tile.get("yield_units", 0) or 0)
        animal_rule = ANIMALS.get(tile.get("animal"), ANIMALS["GOOSE"])
        product = animal_rule["product"]
        if held >= animal_rule["max_held"] or (held > 0 and day >= 27):
            _add_job(
                jobs,
                2,
                held
                * float(
                    prices.get(product, MARKET[product][0])
                    or MARKET[product][0]
                ),
                target,
                ("HARVEST",),
                reason="animal_harvest",
            )
        if tile.get("fertilizer_available", False):
            _add_job(
                jobs,
                2,
                float(
                    prices.get("FERTILIZER", MARKET["FERTILIZER"][0])
                    or MARKET["FERTILIZER"][0]
                ),
                target,
                ("COLLECT_FERTILIZER",),
                reason="fertilizer",
            )
        if not tile.get("cared_today", False):
            _add_job(
                jobs,
                3,
                float(
                    prices.get(product, MARKET[product][0])
                    or MARKET[product][0]
                ),
                target,
                ("CARE",),
                reason="care",
            )
    return jobs


def _terminal_feasible(position, target, tiles, actions_left):
    board_size = len(tiles)
    return (
        _distance(position, target)
        + 1
        + min(
            _distance(target, shed)
            for shed in _shed_tiles(board_size, tiles)
        )
        + 1
        <= actions_left
    )


# Duplicate-target-aware field assignment

def _unit_actions(obs, config, farm, private, roles):
    tiles = farm["tiles"]
    board_size = len(tiles)
    day = int(obs.get("day", 0) or 0)
    hour = int(obs.get("hour", 0) or 0)
    step = int(obs.get("step", day * 24 + hour) or 0)
    final_step = int(_cfg(config, "episodeSteps", 720)) - 2
    actions_left = max(0, final_step - step + 1)
    liquidation = actions_left <= LIQUIDATION_TURNS

    positions = [farm["farmer"], *(farm.get("hands", []) or [])]
    inventories = [dict(inv or {}) for inv in private.get("inventories", []) or []]
    while len(inventories) < len(positions):
        inventories.append({})

    summary = _survey(farm, private, roles, day)
    jobs = _field_jobs(obs, farm, private, roles, liquidation)
    seed_budget = dict(private.get("seeds", {}) or {})
    actions = [["PASS"] for _ in positions]

    feed_jobs = [job for job in jobs if job["need"] == "WHEAT"]
    place_jobs = [job for job in jobs if job["need"] == "GOOSE"]
    shed_wheat = int((private.get("shed", {}) or {}).get("WHEAT", 0) or 0)
    shed_geese = int((private.get("shed", {}) or {}).get("GOOSE", 0) or 0)
    carried_wheat = sum(int(inv.get("WHEAT", 0) or 0) for inv in inventories)
    carried_geese = sum(int(inv.get("GOOSE", 0) or 0) for inv in inventories)

    missions = []
    for job in jobs:
        mission = dict(job)
        mission.update({"kind": "FIELD"})
        missions.append(mission)

    wheat_missing = max(0, len(feed_jobs) - carried_wheat)
    wheat_pickups = min(
        len(positions),
        int(math.ceil(min(wheat_missing, shed_wheat) / 6.0)),
    )
    wheat_remaining = min(wheat_missing, shed_wheat)
    critical_feed = any(job["priority"] == 0 for job in feed_jobs)
    for _ in range(wheat_pickups):
        amount = min(6, wheat_remaining)
        wheat_remaining -= amount
        missions.append(
            {
                "kind": "PICKUP",
                "item": "WHEAT",
                "amount": amount,
                "priority": 0 if critical_feed else 1,
                "value": 900 if critical_feed else 500,
                "target": None,
            }
        )

    goose_pickups = min(
        max(0, len(place_jobs) - carried_geese),
        shed_geese,
        2,
        len(positions),
    )
    for _ in range(goose_pickups):
        missions.append(
            {
                "kind": "PICKUP",
                "item": "GOOSE",
                "amount": 1,
                "priority": 1,
                "value": 700,
                "target": None,
            }
        )

    market_prices = ((obs.get("market", {}) or {}).get("prices", {}) or {})
    pressure = summary["shed_load"] + summary["carried_load"]
    for index, inventory in enumerate(inventories):
        cash_units = sum(
            max(0, int(inventory.get(item, 0) or 0)) for item in PRODUCTS
        )
        if cash_units <= 0:
            continue
        cash_value = sum(
            max(0, int(inventory.get(item, 0) or 0))
            * float(market_prices.get(item, MARKET[item][0]) or MARKET[item][0])
            for item in PRODUCTS
        )
        has_feed_mission = (
            int(inventory.get("WHEAT", 0) or 0) > 0 and bool(feed_jobs)
        )
        should_drop = (
            liquidation
            or hour >= 20
            or pressure >= 80
            or cash_units >= 4
            or (
                tuple(positions[index]) in _shed_tiles(board_size, tiles)
                and not has_feed_mission
            )
        )
        if should_drop:
            missions.append(
                {
                    "kind": "DROP",
                    "eligible": index,
                    "priority": -1 if liquidation else 2,
                    "value": max(120.0, 0.22 * cash_value),
                    "target": None,
                }
            )

    pairs = []
    for worker_index, raw_position in enumerate(positions):
        position = (int(raw_position[0]), int(raw_position[1]))
        inventory = inventories[worker_index]
        for mission_index, mission in enumerate(missions):
            kind = mission["kind"]
            if kind == "DROP" and mission["eligible"] != worker_index:
                continue
            if kind == "FIELD":
                need = mission.get("need")
                if need is not None and int(inventory.get(need, 0) or 0) <= 0:
                    continue
                target = mission["target"]
                distance = _distance(position, target)
                if hour + distance > mission.get("latest_hour", 23):
                    continue
                if liquidation and not _terminal_feasible(
                    position, target, tiles, actions_left
                ):
                    continue
            else:
                target = _nearest_shed(position, board_size, tiles)
                distance = _distance(position, target)
                if kind == "PICKUP" and int(
                    inventory.get(mission["item"], 0) or 0
                ) > 0:
                    continue

            priority = int(mission["priority"])
            score = (
                PRIORITY_BONUS.get(priority, -1000.0 * priority)
                + float(mission["value"])
                - TRAVEL_COST * distance
            )
            pairs.append(
                (
                    -score,
                    distance,
                    worker_index,
                    mission_index,
                    target[1],
                    target[0],
                    target,
                )
            )

    used_workers = set()
    used_missions = set()
    used_targets = set()
    shed_capacity = int(_cfg(config, "shedCapacity", SHED_CAPACITY))
    drop_room = max(0, shed_capacity - summary["shed_load"])
    for _, distance, worker_index, mission_index, _, _, target in sorted(pairs):
        if worker_index in used_workers or mission_index in used_missions:
            continue
        mission = missions[mission_index]
        target_key = target
        if mission["kind"] == "FIELD":
            operation = mission["action"][0]
            if liquidation and operation in {"HARVEST", "COLLECT_FERTILIZER"}:
                target_key = (target, operation)
            if target_key in used_targets:
                continue

        action = None
        plant_crop = None
        if mission["kind"] == "FIELD":
            planned = mission["action"]
            if planned[0] == "PLANT":
                plant_crop = planned[1]
                if int(seed_budget.get(plant_crop, 0) or 0) <= 0:
                    continue
            action = (
                list(planned)
                if distance == 0
                else _bfs_first_step(tiles, positions[worker_index], target)
            )
        elif mission["kind"] == "PICKUP":
            action = (
                ["PICKUP", mission["item"], int(mission["amount"])]
                if distance == 0
                else _bfs_first_step(tiles, positions[worker_index], target)
            )
        else:
            inventory = inventories[worker_index]
            product_counts = {
                item: max(0, int(inventory.get(item, 0) or 0))
                for item in PRODUCTS
                if int(inventory.get(item, 0) or 0) > 0
            }
            if distance:
                action = _bfs_first_step(
                    tiles, positions[worker_index], target
                )
            else:
                cash_units = sum(product_counts.values())
                noncash = _inventory_total(inventory) - cash_units
                if cash_units <= 0 or drop_room <= 0:
                    continue
                if noncash <= 0 and cash_units <= drop_room:
                    action = ["DROP"]
                    drop_room -= cash_units
                else:
                    item = max(
                        product_counts,
                        key=lambda name: (
                            float(
                                market_prices.get(name, MARKET[name][0])
                                or MARKET[name][0]
                            ),
                            name,
                        ),
                    )
                    quantity = min(product_counts[item], drop_room)
                    if quantity <= 0:
                        continue
                    action = ["PLACE", item, quantity]
                    drop_room -= quantity

        if not action or (action == ["PASS"] and distance > 0):
            continue
        if plant_crop is not None:
            seed_budget[plant_crop] -= 1
        if mission["kind"] == "FIELD":
            used_targets.add(target_key)
        actions[worker_index] = action
        used_workers.add(worker_index)
        used_missions.add(mission_index)

    return {
        "farmer": actions[0] if actions else ["PASS"],
        "hands": actions[1:],
        "liquidation": liquidation,
    }


# Market and capital allocation

def _fib(index):
    a, b = 1, 1
    for _ in range(index):
        a, b = b, a + b
    return a


def _pending_drop(private, field, capacity=SHED_CAPACITY):
    pending = {}
    inventories = list(private.get("inventories", []) or [])
    actions = [field["farmer"], *field["hands"]]
    room = max(
        0,
        int(capacity)
        - sum(
            max(0, int(value or 0))
            for value in (private.get("shed", {}) or {}).values()
        ),
    )
    for index, action in enumerate(actions):
        if index >= len(inventories) or not action or room <= 0:
            continue
        inventory = inventories[index] or {}
        if action[0] == "DROP":
            for item, count in inventory.items():
                accepted = min(max(0, int(count or 0)), room)
                if item in PRODUCTS and accepted > 0:
                    pending[item] = pending.get(item, 0) + accepted
                room -= accepted
                if room <= 0:
                    break
        elif action[0] == "PLACE" and len(action) >= 2:
            item = action[1]
            requested = int(action[2]) if len(action) >= 3 else 1
            accepted = min(
                max(0, requested),
                max(0, int(inventory.get(item, 0) or 0)),
                room,
            )
            if item in PRODUCTS and accepted > 0:
                pending[item] = pending.get(item, 0) + accepted
            room -= accepted
    return pending


def _sell_quantity(item, have, inventory, day, shed_load, obs=None):
    left = TOTAL_DAYS - day
    if left <= 1:
        return have
    base = _market_parameters(obs, item)[0]
    reserve = base * RESERVE_FRACTION[item]
    if left <= 7:
        reserve *= max(0.0, (left - 1) / 6.0)
    if shed_load >= 0.75:
        reserve *= 0.55

    opponent_supply = _opponent_visible_supply(obs, item, horizon=1)
    town_demand = _town_demand_per_day(obs, item)
    if opponent_supply > town_demand:
        reserve *= max(0.72, 1.0 - 0.015 * (opponent_supply - town_demand))
    projected_inventory = inventory + opponent_supply - town_demand
    future_price = _price_at(item, projected_inventory, obs)
    threshold = reserve
    if shed_load < 0.75 and left > 7:
        threshold = max(threshold, 0.88 * future_price)

    quantity = 0
    while (
        quantity < have
        and _price_at(item, inventory + quantity, obs) >= threshold
    ):
        quantity += 1
    if left <= 12:
        forced = int(math.ceil(have / float(max(1, left - 1))))
        quantity = max(quantity, min(have, forced))
    return quantity


def _seed_needs(obs, farm, private, roles):
    day = int(obs.get("day", 0) or 0)
    seeds = private.get("seeds", {}) or {}
    needs = {}
    for (x, y), (kind, item) in roles.items():
        if (
            kind == "CROP"
            and (
                farm["tiles"][y][x] is None
                or (
                    isinstance(farm["tiles"][y][x], dict)
                    and farm["tiles"][y][x].get("kind") == "WEED"
                )
            )
            and day <= CROPS[item]["last_plant"]
        ):
            needs[item] = needs.get(item, 0) + 1
    return {
        crop: max(0, count - int(seeds.get(crop, 0) or 0))
        for crop, count in needs.items()
    }


def _target_hands(obs, farm, private, roles):
    day = int(obs.get("day", 0) or 0)
    summary = _survey(farm, private, roles, day)
    workload = (
        summary["plants"] * 1.3
        + summary["animals"] * 3.2
        + summary["plantable"] * 1.4
        + summary["weeds"] * 0.8
        + summary["at_risk_animals"] * 2.0
        + summary["at_risk_crops"] * 1.5
    )
    return max(4, min(MAX_HANDS, int(math.ceil(workload / 10.5))))


def _market_actions(obs, config, farm, private, roles, field):
    day = int(obs.get("day", 0) or 0)
    hour = int(obs.get("hour", 0) or 0)
    left = TOTAL_DAYS - day
    money = float(farm.get("money", 0) or 0)
    shed_capacity = int(_cfg(config, "shedCapacity", SHED_CAPACITY))
    shed = dict(private.get("shed", {}) or {})
    for item, count in _pending_drop(private, field, shed_capacity).items():
        shed[item] = int(shed.get(item, 0) or 0) + count
    market_inventory = dict(
        ((obs.get("market", {}) or {}).get("inventory", {}) or {})
    )
    max_orders = int(_cfg(config, "maxMarketOrdersPerTurn", MAX_MARKET_ORDERS))
    summary = _survey(farm, private, roles, day)
    phase = _policy_phase(obs, farm, private, summary)
    orders = []
    occupancy = sum(max(0, int(value or 0)) for value in shed.values())
    shed_load = occupancy / float(max(1, shed_capacity))

    sells = []
    for item in PRODUCTS:
        have = int(shed.get(item, 0) or 0)
        if item == "WHEAT" and left > 2:
            have = max(0, have - summary["animals"] * 2)
        if have <= 0:
            continue
        inventory = int(market_inventory.get(item, MARKET_I0) or MARKET_I0)
        quantity = _sell_quantity(
            item, have, inventory, day, shed_load, obs
        )
        if quantity <= 0:
            continue
        proceeds = sum(
            _price_at(item, inventory + offset, obs)
            for offset in range(quantity)
        )
        sells.append((proceeds, item, quantity))
    sells.sort(reverse=True)
    for proceeds, item, quantity in sells:
        if len(orders) >= max_orders:
            break
        orders.append(["SELL", item, quantity])
        money += 0.85 * proceeds
        occupancy = max(0, occupancy - quantity)

    if field["liquidation"] or left <= 1:
        if day >= 29 and hour <= 1:
            terminal_jobs = _field_jobs(
                obs, farm, private, roles, liquidation=True
            )
            target = min(8, len(terminal_jobs))
            hires = int(farm.get("hires_today", 0) or 0)
            while hires < target and len(orders) < max_orders:
                cost = _fib(hires)
                if money < cost + 20:
                    break
                orders.append(["HIRE"])
                money -= cost
                hires += 1
        return orders[:max_orders]

    total_wheat = summary["wheat_stock"]
    desired_wheat = summary["animals"] * FEED_STOCK_DAYS
    if (
        desired_wheat > total_wheat
        and len(orders) < max_orders
        and summary["animals"] > 0
    ):
        inventory = int(market_inventory.get("WHEAT", MARKET_I0) or MARKET_I0)
        emergency_reserve = 0 if summary["at_risk_animals"] else CASH_RESERVE
        quantity = 0
        cost = 0
        limit = min(
            desired_wheat - total_wheat,
            max(0, shed_capacity - occupancy),
        )
        for offset in range(limit):
            unit = _price_at("WHEAT", inventory - offset - 1, obs)
            if money - cost - unit < emergency_reserve:
                break
            cost += unit
            quantity += 1
        if quantity > 0:
            orders.append(["BUY_PRODUCT", "WHEAT", quantity])
            money -= cost
            occupancy += quantity

    extra_land = max(0, len(farm.get("unlocked_quadrants", ["NW"])) - 1)
    usable_tiles = sum(
        tile != "LOCKED"
        for row in farm.get("tiles", []) or []
        for tile in row
    )
    developed_tiles = (
        summary["plants"]
        + summary["animals"]
        + summary["open_coops"]
    )
    utilization = developed_tiles / float(max(1, usable_tiles))
    land_ready = (
        extra_land == 0
        or (extra_land == 1 and day >= 4 and utilization >= 0.65)
    )
    if (
        phase in {"BOOTSTRAP", "COMPOUND"}
        and extra_land < MAX_EXTRA_LAND
        and land_ready
        and left >= 11
        and len(orders) < max_orders
    ):
        cost = LAND_PRICES[extra_land]
        reserve = 550 if extra_land == 0 else 120
        if money >= cost + reserve:
            orders.append(["BUY_LAND"])
            money -= cost

    if hour <= 2:
        target_hands = _target_hands(obs, farm, private, roles)
        hires = int(farm.get("hires_today", 0) or 0)
        while hires < target_hands and len(orders) < max_orders:
            cost = _fib(hires)
            if money < max(40, 4 * cost):
                break
            orders.append(["HIRE"])
            money -= cost
            hires += 1

    needs = _seed_needs(obs, farm, private, roles)
    for crop in ("MELON", "WHEAT", "CARROT", "TOMATO", "STRAWBERRY"):
        if len(orders) >= max_orders or needs.get(crop, 0) <= 0:
            continue
        cost = CROPS[crop]["seed"]
        quantity = min(
            needs[crop],
            25,
            max(0, int((money - CASH_RESERVE) // cost)),
        )
        if quantity > 0:
            orders.append(["BUY_SEED", crop, quantity])
            money -= quantity * cost

    target_geese = sum(kind == "ANIMAL" for kind, _ in roles.values())
    geese_pipeline = summary["animals"] + summary["goose_stock"]
    goose_need = max(0, target_geese - geese_pipeline)
    pending_builds = sum(
        bool(action) and action[0] == "BUILD_COOP"
        for action in [field["farmer"], *field["hands"]]
    )
    ready_space = max(
        0,
        summary["open_coops"] + pending_builds - summary["goose_stock"],
    )
    if (
        phase == "COMPOUND"
        and goose_need > 0
        and left >= 8
        and len(orders) < max_orders
        and ready_space > 0
        and occupancy < shed_capacity
        and summary["wheat_stock"] >= max(2, summary["animals"])
    ):
        quantity = min(
            goose_need,
            ready_space,
            2,
            max(0, shed_capacity - occupancy),
            max(
                0,
                int(
                    (money - CASH_RESERVE - 150)
                    // ANIMALS["GOOSE"]["cost"]
                ),
            ),
        )
        if quantity > 0:
            orders.append(["BUY_ANIMAL", "GOOSE", quantity])
            money -= quantity * ANIMALS["GOOSE"]["cost"]
            occupancy += quantity

    return orders[:max_orders]


def _decide(obs, config=None):
    farms = obs.get("farms", []) or []
    player = int(obs.get("player", 0) or 0)
    if not (0 <= player < len(farms)):
        return {"farmer": ["PASS"], "hands": [], "market": []}
    farm = farms[player]
    private = obs.get("private", {}) or {}
    roles = _role_plan(obs, farm)
    field = _unit_actions(obs, config, farm, private, roles)
    return {
        "farmer": field["farmer"],
        "hands": field["hands"],
        "market": _market_actions(obs, config, farm, private, roles, field),
    }


def agent(obs, config=None):
    try:
        return _decide(obs, config)
    except Exception:
        farms = obs.get("farms", []) if hasattr(obs, "get") else []
        player = int(obs.get("player", 0)) if hasattr(obs, "get") else 0
        hand_count = (
            len(farms[player].get("hands", []) or [])
            if 0 <= player < len(farms)
            else 0
        )
        return {
            "farmer": ["PASS"],
            "hands": [["PASS"] for _ in range(hand_count)],
            "market": [],
        }
