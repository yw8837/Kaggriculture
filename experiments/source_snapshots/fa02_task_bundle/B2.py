from collections import deque

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
    for pos in slots:
        x, y = pos
        tile = tiles[y][x]
        planned = _animal_for_slot(pos, slots)
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


_TASK_BUNDLE_MODE = 'B2'
_TASK_BUNDLE_MAX_TASKS = 18
_TASK_BUNDLE_SHARED_ITEMS = ("WHEAT", "COW", "SHEEP")


def _task_sort_key(index, task, mode):
    action = task.get("action", [])
    target = tuple(task.get("pos", (0, 0)))
    hard = 0
    if mode in ("B2", "B4"):
        hard = 0 if task.get("hard_deadline", False) else 1
    return (
        hard,
        int(task.get("priority", 999)),
        target[1],
        target[0],
        tuple(str(value) for value in action),
        index,
    )


def _mark_deadlines(farm, tasks, mode):
    """Copy tasks and mark only official second-miss crop/animal failures."""
    marked = []
    for task in tasks:
        item = dict(task)
        item["action"] = list(task.get("action", []))
        action = item["action"]
        target = tuple(item.get("pos", (0, 0)))
        tile = farm["tiles"][target[1]][target[0]]
        hard = False
        if mode in ("B2", "B4") and action:
            if action[0] == "WATER" and isinstance(tile, dict):
                hard = int(tile.get("consecutive_unwatered", 0)) >= 1
            elif action[0] == "FEED" and isinstance(tile, dict):
                hard = int(tile.get("consecutive_unfed", 0)) >= 1
        item["hard_deadline"] = hard
        marked.append(item)
    return marked


def _bundle_length(farm, pos, inv, shed, task):
    """Movement + optional pickup + terminal task action."""
    cost = _task_cost(farm, pos, inv, shed, task)
    return cost if cost >= 10000 else cost + 1


def _assignment_weight(farm, pos, inv, shed, task, day, hour, mode):
    """Scalar objective preserving formal priorities with deadline rescue credits."""
    cost = _task_cost(farm, pos, inv, shed, task)
    if cost >= 10000:
        return None
    if mode in ("B2", "B4") and task.get("hard_deadline", False):
        bundle = _bundle_length(farm, pos, inv, shed, task)
        turns_left = max(1, 24 - int(hour))
        if bundle <= turns_left:
            # Each rescuable second-miss task dominates every ordinary task.
            # Slack is the hard feasibility gate; among rescuable pairs, the
            # shorter bundle is preferred so a distant unit is not selected
            # merely because it has less slack.
            return -10000000 + cost
    # BUILD/DIG and other actions keep the formal heuristic prior.  Their cash
    # value is not observable, so this deliberately does not invent one.
    return int(task.get("priority", 999)) * 10000 + cost


def _global_assignment(farm, positions, invs, shed, tasks, day=0, hour=0, mode="B1"):
    """Top-18-pruned exact global min-cost assignment over <=11 units.

    The dynamic program scans tasks while its bitmask represents assigned
    units.  Skipping a task is the idle-dummy equivalent.  The final state first
    maximizes assignment cardinality, then minimizes total policy cost.
    """
    unit_count = min(len(positions), 11)
    if unit_count <= 0 or not tasks:
        return []
    # Evaluate every task before applying the cap.  In B2/B4 a hard task can be
    # marked correctly yet be impossible for distant units before end-of-day;
    # a rescuable 19th task must not be hidden by 18 such tasks.
    candidates = []
    for original_index, task in enumerate(tasks):
        weights = [
            _assignment_weight(
                farm,
                positions[unit],
                invs[unit],
                shed,
                task,
                day,
                hour,
                mode,
            )
            for unit in range(unit_count)
        ]
        weights = [weight for weight in weights if weight is not None]
        if not weights:
            continue
        rescue = [weight for weight in weights if weight < 0]
        # Rescuable deadlines come first.  Ordinary pruning still uses the
        # best full priority+distance weight before coordinate tie-breakers.
        rescue_key = (0, min(rescue)) if rescue else (1, min(weights))
        candidates.append(
            (rescue_key, _task_sort_key(original_index, task, mode), original_index, task)
        )
    candidates.sort(key=lambda item: (item[0], item[1]))
    feasible = [
        (original_index, task)
        for _, _, original_index, task in candidates[:_TASK_BUNDLE_MAX_TASKS]
    ]
    if not feasible:
        return []

    empty_mapping = tuple(-1 for _ in range(unit_count))
    # mask -> (total cost, task index for each unit)
    dp = {0: (0, empty_mapping)}
    for original_index, task in feasible:
        updated = dict(dp)
        for mask, (total, mapping) in dp.items():
            for unit in range(unit_count):
                if mask & (1 << unit):
                    continue
                weight = _assignment_weight(
                    farm,
                    positions[unit],
                    invs[unit],
                    shed,
                    task,
                    day,
                    hour,
                    mode,
                )
                if weight is None:
                    continue
                new_mask = mask | (1 << unit)
                new_mapping = list(mapping)
                new_mapping[unit] = original_index
                candidate = (total + weight, tuple(new_mapping))
                incumbent = updated.get(new_mask)
                if incumbent is None or candidate < incumbent:
                    updated[new_mask] = candidate
        dp = updated

    _, (_, mapping) = min(
        dp.items(),
        key=lambda item: (
            -item[0].bit_count(),
            item[1][0],
            tuple(value if value >= 0 else 1000000 for value in item[1][1]),
        ),
    )
    return [(unit, task) for unit, task in enumerate(mapping) if task >= 0]


def _can_reserve(task, action, pos, inv, shed_remaining, seed_remaining):
    need = task.get("need")
    if (
        action
        and action[0] == "PICKUP"
        and need in _TASK_BUNDLE_SHARED_ITEMS
        and int(inv.get(need, 0)) <= 0
        and int(shed_remaining.get(need, 0)) <= 0
    ):
        return False
    # Seeds are consumed atomically by actual PLANT requests this turn.  A unit
    # that is merely moving toward a plant task must not reserve a seed.
    if action and action[0] == "PLANT":
        crop = action[1]
        if int(seed_remaining.get(crop, 0)) <= 0:
            return False
    return True


def _reserve(task, action, inv, shed_remaining, seed_remaining):
    need = task.get("need")
    if (
        action
        and action[0] == "PICKUP"
        and need in _TASK_BUNDLE_SHARED_ITEMS
        and int(inv.get(need, 0)) <= 0
    ):
        shed_remaining[need] = int(shed_remaining.get(need, 0)) - 1
    if action and action[0] == "PLANT":
        crop = action[1]
        seed_remaining[crop] = int(seed_remaining.get(crop, 0)) - 1


def _reserved_task_action(farm, pos, inv, shed, task):
    """Emit a one-unit pickup so an earlier reservation cannot drain later ones."""
    need = task.get("need")
    if need in _TASK_BUNDLE_SHARED_ITEMS and int(inv.get(need, 0)) <= 0:
        if int(shed.get(need, 0)) <= 0:
            return ["PASS"]
        shed_pos = _nearest_shed(len(farm["tiles"]), farm["tiles"], pos)
        if tuple(pos) == tuple(shed_pos):
            return ["PICKUP", need, 1]
        return _move(farm["tiles"], pos, shed_pos)
    return _task_action(farm, pos, inv, shed, task)


def _resource_safe_actions(
    obs,
    farm,
    private,
    positions,
    invs,
    shed,
    tasks,
    assignments,
):
    """Reserve/repair in official farmer-then-hands execution order.

    This is deliberately history-free: every reservation is reconstructed from
    the current observation, so there is no unsafe cross-turn hysteresis state.
    """
    day = int(obs.get("day", 0))
    hour = int(obs.get("hour", 0))
    actions = [["PASS"] for _ in positions]
    selected = {unit: task for unit, task in assignments}
    initially_occupied = set(selected.values())
    used = set()
    released = set()
    shed_remaining = dict(shed)
    seed_remaining = dict(private.get("seeds", {}) or {})

    for unit in range(min(len(positions), 11)):
        primary = selected.get(unit)
        choices = [] if primary is None else [primary]
        repairs = [
            index
            for index in range(len(tasks))
            if index not in used
            and (index not in initially_occupied or index in released)
        ]
        repairs.sort(
            key=lambda index: (
                _assignment_weight(
                    farm,
                    positions[unit],
                    invs[unit],
                    shed_remaining,
                    tasks[index],
                    day,
                    hour,
                    "B4",
                )
                if _assignment_weight(
                    farm,
                    positions[unit],
                    invs[unit],
                    shed_remaining,
                    tasks[index],
                    day,
                    hour,
                    "B4",
                )
                is not None
                else 1000000000,
                _task_sort_key(index, tasks[index], "B4"),
            )
        )
        choices.extend(repairs)
        for task_index in choices:
            if task_index in used:
                continue
            task = tasks[task_index]
            if _task_cost(farm, positions[unit], invs[unit], shed_remaining, task) >= 10000:
                continue
            chosen_action = _reserved_task_action(
                farm,
                positions[unit],
                invs[unit],
                shed_remaining,
                task,
            )
            if not _can_reserve(
                task,
                chosen_action,
                positions[unit],
                invs[unit],
                shed_remaining,
                seed_remaining,
            ):
                continue
            _reserve(
                task,
                chosen_action,
                invs[unit],
                shed_remaining,
                seed_remaining,
            )
            actions[unit] = chosen_action
            requested = task.get("action", [])
            moving = bool(
                chosen_action
                and chosen_action[0] in ("NORTH", "SOUTH", "EAST", "WEST")
            )
            if (
                requested
                and requested[0] == "PLANT"
                and chosen_action[0] != "PLANT"
            ) or (task.get("need") in _TASK_BUNDLE_SHARED_ITEMS and moving):
                # A later unit already on the target may repair to this task.
                released.add(task_index)
            else:
                used.add(task_index)
                released.discard(task_index)
            break
    return actions


def _unit_actions(obs, farm, private, cow_slots, crop_plan):
    day = int(obs.get("day", 0))
    hour = int(obs.get("hour", 0))
    positions = [tuple(farm.get("farmer", [0, 0]))] + [
        tuple(p) for p in farm.get("hands", [])
    ]
    invs = _inventories(private)
    while len(invs) < len(positions):
        invs.append({})
    shed = dict(private.get("shed", {}) or {})
    tasks = _animal_tasks(obs, farm, private, cow_slots) + _crop_tasks(
        obs, farm, private, crop_plan, set(cow_slots)
    )
    tasks = _mark_deadlines(farm, tasks, _TASK_BUNDLE_MODE)
    actions = [["PASS"] for _ in positions]

    if day >= 29 and hour >= 14:
        for i, pos in enumerate(positions):
            carried = sum(int(v) for v in invs[i].values())
            s = _nearest_shed(len(farm["tiles"]), farm["tiles"], pos)
            if carried:
                actions[i] = ["DROP"] if pos == s else _move(farm["tiles"], pos, s)
            elif pos != s:
                actions[i] = _move(farm["tiles"], pos, s)
        return actions

    assignments = _global_assignment(
        farm,
        positions,
        invs,
        shed,
        tasks,
        day=day,
        hour=hour,
        mode=_TASK_BUNDLE_MODE,
    )
    if _TASK_BUNDLE_MODE == "B4":
        return _resource_safe_actions(
            obs,
            farm,
            private,
            positions,
            invs,
            shed,
            tasks,
            assignments,
        )

    for unit, task_index in assignments:
        actions[unit] = _task_action(
            farm,
            positions[unit],
            invs[unit],
            shed,
            tasks[task_index],
        )

    # Preserve formal atomic-PLANT protection for B1/B2.
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
    target = {"COW": 7, "SHEEP": 2} if expanded else {"COW": 1, "SHEEP": 2}
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
