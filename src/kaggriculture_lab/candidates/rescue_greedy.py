"""Build a single-delta bounded rescue-greedy agent from the formal champion.

The generated source replaces only ``_unit_actions`` and inserts its private
helpers at that location.  Market policy, crop plan, herd/hire policy, agent
entrypoint, and the formal terminal branch remain unchanged.
"""

from __future__ import annotations

import ast
from pathlib import Path


def _function_span(source: str, name: str) -> tuple[int, int]:
    tree = ast.parse(source)
    matches = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one top-level {name}(), found {len(matches)}")
    node = matches[0]
    if node.end_lineno is None:
        raise ValueError(f"Python AST did not provide an end line for {name}()")
    return node.lineno - 1, node.end_lineno


_ALLOCATOR_SOURCE = '''_RESCUE_MAX_UNITS = 11
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


def _path_length(tiles, source, target):
    source = tuple(source)
    target = tuple(target)
    if source == target:
        return 0
    n = len(tiles)
    queue = deque([(source, 0)])
    seen = {source}
    while queue:
        current, distance = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (current[0] + dx, current[1] + dy)
            if not (0 <= nxt[0] < n and 0 <= nxt[1] < n):
                continue
            if nxt in seen or tiles[nxt[1]][nxt[0]] == "LOCKED":
                continue
            if nxt == target:
                return distance + 1
            seen.add(nxt)
            queue.append((nxt, distance + 1))
    return 10000


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


def _rescue_route(farm, pos, inv, shed, task):
    """Return exact path action count and the selected shed, if needed."""
    target = tuple(task["pos"])
    tiles = farm["tiles"]
    action = task["action"][0]
    if action == "WATER" or int(inv.get("WHEAT", 0)) > 0:
        travel = _path_length(tiles, pos, target)
        return (travel + 1, None) if travel < 10000 else (10000, None)
    if int(shed.get("WHEAT", 0)) <= 0:
        return 10000, None
    routes = []
    for shed_pos in _shed_tiles(len(tiles), tiles):
        first = _path_length(tiles, pos, shed_pos)
        second = _path_length(tiles, shed_pos, target)
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
    rounds = 0
    while free_units and rescue_tasks and rounds < _RESCUE_MAX_UNITS:
        best = None
        for unit in sorted(free_units):
            for task_index in sorted(rescue_tasks):
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
                )
                if bundle > turns_left:
                    continue
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
                key = (
                    bundle,
                    task["pos"][1],
                    task["pos"][0],
                    unit,
                    task_index,
                )
                if best is None or key < best[0]:
                    best = (key, unit, task_index, action, needs_shared_wheat)
        if best is None:
            break
        _, unit, task_index, action, needs_shared_wheat = best
        if not _reserve_emitted_wheat(action, shed_remaining):
            rescue_tasks.remove(task_index)
            continue
        if needs_shared_wheat:
            planned_wheat -= 1
        actions[unit] = action
        free_units.remove(unit)
        free_tasks.remove(task_index)
        rescue_tasks.remove(task_index)
        task = tasks[task_index]
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
'''


def build_rescue_greedy(source_agent: str) -> str:
    """Return the deterministic single-file rescue-greedy candidate source."""
    ast.parse(source_agent)
    start, end = _function_span(source_agent, "_unit_actions")
    lines = source_agent.splitlines(keepends=True)
    replacement = _ALLOCATOR_SOURCE.rstrip() + "\n\n"
    built = "".join(lines[:start]) + replacement + "".join(lines[end:])
    compile(built, "<rescue_greedy>", "exec")
    return built


def build_rescue_greedy_file(parent: Path, output: Path) -> Path:
    source = parent.read_text(encoding="utf-8")
    built = build_rescue_greedy(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(built, encoding="utf-8", newline="\n")
    return output
