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


_RESCUE_MAX_UNITS = 11
_RESCUE_COUNTERS = {
    "opportunities": 0,
    "assignments": 0,
    "completed_rescues": 0,
    "weed_or_escape_events": 0,
}
_RESCUE_PENDING = {}
_RESCUE_SEEN = set()
_RESCUE_ASSIGNED_SEEN = set()
_RESCUE_COMPLETED_SEEN = set()


def rescue_metrics():
    """Return cumulative, decision-neutral rescue instrumentation."""
    return dict(_RESCUE_COUNTERS)


def reset_rescue_metrics():
    for key in _RESCUE_COUNTERS:
        _RESCUE_COUNTERS[key] = 0
    _RESCUE_PENDING.clear()
    _RESCUE_SEEN.clear()
    _RESCUE_ASSIGNED_SEEN.clear()
    _RESCUE_COMPLETED_SEEN.clear()


def _distance_map(tiles, source):
    source = tuple(source)
    n = len(tiles)
    queue = deque([(source, 0)])
    distances = {source: 0}
    while queue:
        current, distance = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (current[0] + dx, current[1] + dy)
            if not (0 <= nxt[0] < n and 0 <= nxt[1] < n):
                continue
            if nxt in distances or tiles[nxt[1]][nxt[0]] == "LOCKED":
                continue
            distances[nxt] = distance + 1
            queue.append((nxt, distance + 1))
    return distances


def _path_length(tiles, source, target):
    return _distance_map(tiles, source).get(tuple(target), 10000)


def _is_rescue_task(farm, task):
    action = task.get("action", [])
    if not action or action[0] not in ("WATER", "FEED"):
        return False
    x, y = task["pos"]
    tile = farm["tiles"][y][x]
    if action[0] == "WATER":
        return bool(
            isinstance(tile, dict)
            and tile.get("kind") == "PLANT"
            and not tile.get("watered_today", False)
            and int(tile.get("consecutive_unwatered", 0)) == 1
        )
    return bool(
        isinstance(tile, dict)
        and tile.get("animal") in ("COW", "SHEEP")
        and not tile.get("fed_today", False)
        and int(tile.get("consecutive_unfed", 0)) == 1
    )


def _rescue_route(farm, pos, inv, shed, task, distance_maps=None):
    """Return exact path action count and the selected shed, if needed."""
    target = tuple(task["pos"])
    tiles = farm["tiles"]
    action = task["action"][0]
    if distance_maps is None:
        distance_maps = {}

    def distance(source, destination):
        source = tuple(source)
        distances = distance_maps.get(source)
        if distances is None:
            distances = _distance_map(tiles, source)
            distance_maps[source] = distances
        return distances.get(tuple(destination), 10000)

    if action == "WATER" or int(inv.get("WHEAT", 0)) > 0:
        travel = distance(pos, target)
        return (travel + 1, None) if travel < 10000 else (10000, None)
    if int(shed.get("WHEAT", 0)) <= 0:
        return 10000, None
    routes = []
    for shed_pos in _shed_tiles(len(tiles), tiles):
        first = distance(pos, shed_pos)
        second = distance(shed_pos, target)
        if first < 10000 and second < 10000:
            routes.append((first + 1 + second + 1, shed_pos[1], shed_pos[0], shed_pos))
    if not routes:
        return 10000, None
    length, _, _, shed_pos = min(routes)
    return length, shed_pos


def _rescue_action(farm, pos, inv, shed, task, shed_pos):
    if task["action"][0] == "FEED" and int(inv.get("WHEAT", 0)) <= 0:
        if int(shed.get("WHEAT", 0)) <= 0 or shed_pos is None:
            return ["PASS"]
        if tuple(pos) == tuple(shed_pos):
            return ["PICKUP", "WHEAT", 1]
        return _move(farm["tiles"], pos, shed_pos)
    if tuple(pos) == tuple(task["pos"]):
        return list(task["action"])
    return _move(farm["tiles"], pos, task["pos"])


def _reserve_emitted_wheat(action, shed_remaining):
    """Reserve only what the official engine consumes on this exact turn."""
    if action[:2] == ["PICKUP", "WHEAT"]:
        if int(shed_remaining.get("WHEAT", 0)) <= 0:
            return False
        shed_remaining["WHEAT"] = int(shed_remaining.get("WHEAT", 0)) - 1
    return True


def _observe_rescue_outcomes(obs, farm):
    player = int(obs.get("player", 0))
    day = int(obs.get("day", 0))
    previous = _RESCUE_PENDING.get(player)
    if previous is None or previous[0] == day:
        return
    previous_day, hazards = previous
    if day == previous_day + 1:
        for operation, pos, animal in hazards:
            tile = farm["tiles"][pos[1]][pos[0]]
            if operation == "WATER":
                event = isinstance(tile, dict) and tile.get("kind") == "WEED"
            else:
                event = not (isinstance(tile, dict) and tile.get("animal") == animal)
            if event:
                _RESCUE_COUNTERS["weed_or_escape_events"] += 1
    _RESCUE_PENDING.pop(player, None)
    if day <= previous_day:
        stale = {key for key in _RESCUE_SEEN if key[0] == player}
        _RESCUE_SEEN.difference_update(stale)
        stale = {key for key in _RESCUE_ASSIGNED_SEEN if key[0] == player}
        _RESCUE_ASSIGNED_SEEN.difference_update(stale)
        stale = {key for key in _RESCUE_COMPLETED_SEEN if key[0] == player}
        _RESCUE_COMPLETED_SEEN.difference_update(stale)


def _record_rescue_opportunities(obs, farm, tasks):
    player = int(obs.get("player", 0))
    day = int(obs.get("day", 0))
    hazards = []
    for task in tasks:
        if not _is_rescue_task(farm, task):
            continue
        operation = task["action"][0]
        pos = tuple(task["pos"])
        tile = farm["tiles"][pos[1]][pos[0]]
        animal = tile.get("animal") if isinstance(tile, dict) else None
        key = (player, day, operation, pos)
        if key not in _RESCUE_SEEN:
            _RESCUE_SEEN.add(key)
            _RESCUE_COUNTERS["opportunities"] += 1
        hazards.append((operation, pos, animal))
    _RESCUE_PENDING[player] = (day, tuple(hazards))


def _assign_rescues(
    obs,
    farm,
    positions,
    invs,
    shed,
    tasks,
    actions,
    free_units,
    free_tasks,
):
    """Bounded polynomial greedy: at most 11 assignment rounds."""
    hour = int(obs.get("hour", 0))
    turns_left = max(1, 24 - hour)
    shed_remaining = dict(shed)
    planned_wheat = int(shed.get("WHEAT", 0))
    rescue_tasks = {
        index for index, task in enumerate(tasks) if _is_rescue_task(farm, task)
    }
    distance_maps = {}
    distance_sources = set(tuple(position) for position in positions)
    distance_sources.update(_shed_tiles(len(farm["tiles"]), farm["tiles"]))
    for source in sorted(distance_sources, key=lambda pos: (pos[1], pos[0])):
        distance_maps[source] = _distance_map(farm["tiles"], source)
    candidates = []
    for unit in sorted(free_units):
        for task_index in sorted(rescue_tasks & free_tasks):
            task = tasks[task_index]
            needs_shared_wheat = (
                task["action"][0] == "FEED"
                and int(invs[unit].get("WHEAT", 0)) <= 0
            )
            if needs_shared_wheat and planned_wheat <= 0:
                continue
            bundle, shed_pos = _rescue_route(
                farm,
                positions[unit],
                invs[unit],
                shed_remaining,
                task,
                distance_maps,
            )
            if bundle > turns_left:
                continue
            key = (
                bundle,
                task["pos"][1],
                task["pos"][0],
                unit,
                task_index,
            )
            candidates.append((key, unit, task_index, shed_pos, needs_shared_wheat))
    candidates.sort(key=lambda candidate: candidate[0])

    rounds = 0
    for _, unit, task_index, shed_pos, needs_shared_wheat in candidates:
        if rounds >= _RESCUE_MAX_UNITS:
            break
        if unit not in free_units or task_index not in free_tasks:
            continue
        if needs_shared_wheat and planned_wheat <= 0:
            continue
        task = tasks[task_index]
        action = _rescue_action(
            farm,
            positions[unit],
            invs[unit],
            shed_remaining,
            task,
            shed_pos,
        )
        if action == ["PASS"]:
            continue
        if not _reserve_emitted_wheat(action, shed_remaining):
            continue
        if needs_shared_wheat:
            planned_wheat -= 1
        actions[unit] = action
        free_units.remove(unit)
        free_tasks.remove(task_index)
        key = (
            int(obs.get("player", 0)),
            int(obs.get("day", 0)),
            task["action"][0],
            tuple(task["pos"]),
        )
        if key not in _RESCUE_ASSIGNED_SEEN:
            _RESCUE_ASSIGNED_SEEN.add(key)
            _RESCUE_COUNTERS["assignments"] += 1
        if action[0] in ("WATER", "FEED") and key not in _RESCUE_COMPLETED_SEEN:
            _RESCUE_COMPLETED_SEEN.add(key)
            _RESCUE_COUNTERS["completed_rescues"] += 1
        rounds += 1
    # The official shed changes only for emitted PICKUP actions, while the
    # following ordinary allocator must also respect WHEAT promised to moving
    # rescue bundles.  Return a planning view without mutating private shed.
    ordinary_available = dict(shed_remaining)
    ordinary_available["WHEAT"] = min(
        int(shed_remaining.get("WHEAT", 0)),
        planned_wheat,
    )
    return ordinary_available


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
    _observe_rescue_outcomes(obs, farm)
    _record_rescue_opportunities(obs, farm, tasks)

    if day >= 29 and hour >= 14:
        for i, pos in enumerate(positions):
            carried = sum(int(v) for v in invs[i].values())
            s = _nearest_shed(len(farm["tiles"]), farm["tiles"], pos)
            if carried:
                actions[i] = ["DROP"] if pos == s else _move(farm["tiles"], pos, s)
            elif pos != s:
                actions[i] = _move(farm["tiles"], pos, s)
        return actions

    shed_remaining = _assign_rescues(
        obs,
        farm,
        positions,
        invs,
        shed,
        tasks,
        actions,
        free_units,
        free_tasks,
    )

    while free_units and free_tasks:
        best = None
        for i in free_units:
            for j in free_tasks:
                task = tasks[j]
                cost = _task_cost(farm, positions[i], invs[i], shed_remaining, task)
                if cost >= 10000:
                    continue
                key = (task["priority"], cost, task["pos"][1], task["pos"][0], i, j)
                if best is None or key < best[0]:
                    best = (key, i, j)
        if best is None:
            break
        _, i, j = best
        actions[i] = _task_action(farm, positions[i], invs[i], shed_remaining, tasks[j])
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
