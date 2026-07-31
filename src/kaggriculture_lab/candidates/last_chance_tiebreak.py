"""Build the BT1 last-chance comparator from the frozen formal champion.

BT1 preserves the formal allocator and inserts one behavioral dimension into
its candidate key: ``(priority, rank, cost, y, x, i, j)``.  Rank zero is
limited to the official second-miss WATER/FEED states; all other tasks are rank
one.  The additional helpers are decision-neutral instrumentation.
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


_HELPERS_SOURCE = '''_LAST_CHANCE_COUNTERS = {
    "eligible_opportunity": 0,
    "rank_tiebreak_activated": 0,
    "action_changed_vs_old_comparator_on_same_state": 0,
    "last_chance_action_emitted_on_exact_target": 0,
    "next_day_weed_or_escape_outcome": 0,
}
_LAST_CHANCE_PENDING = {}


def rescue_metrics():
    """Return raw per-game BT1 comparator instrumentation."""
    return dict(_LAST_CHANCE_COUNTERS)


def reset_rescue_metrics():
    for key in _LAST_CHANCE_COUNTERS:
        _LAST_CHANCE_COUNTERS[key] = 0
    _LAST_CHANCE_PENDING.clear()


def _last_chance_rank(farm, task):
    action = task.get("action", [])
    if not action or action[0] not in ("WATER", "FEED"):
        return 1
    x, y = task["pos"]
    tile = farm["tiles"][y][x]
    if action[0] == "WATER":
        return 0 if (
            isinstance(tile, dict)
            and tile.get("kind") == "PLANT"
            and not tile.get("watered_today", False)
            and int(tile.get("consecutive_unwatered", 0)) == 1
        ) else 1
    return 0 if (
        isinstance(tile, dict)
        and tile.get("animal") in ("COW", "SHEEP")
        and not tile.get("fed_today", False)
        and int(tile.get("consecutive_unfed", 0)) == 1
    ) else 1


def _last_chance_choices(farm, positions, invs, shed, tasks, free_units, free_tasks):
    old_best = None
    new_best = None
    feasible = []
    for i in free_units:
        for j in free_tasks:
            task = tasks[j]
            cost = _task_cost(farm, positions[i], invs[i], shed, task)
            if cost >= 10000:
                continue
            priority = task["priority"]
            rank = _last_chance_rank(farm, task)
            old_key = (priority, cost, task["pos"][1], task["pos"][0], i, j)
            new_key = (priority, rank, cost, task["pos"][1], task["pos"][0], i, j)
            old_candidate = (old_key, i, j)
            new_candidate = (new_key, i, j)
            feasible.append((priority, rank))
            if old_best is None or old_key < old_best[0]:
                old_best = old_candidate
            if new_best is None or new_key < new_best[0]:
                new_best = new_candidate
    if new_best is None:
        return None, old_best, False, False
    selected_priority = new_best[0][0]
    ranks = {rank for priority, rank in feasible if priority == selected_priority}
    eligible = ranks == {0, 1}
    activated = bool(
        old_best is not None
        and (new_best[1], new_best[2]) != (old_best[1], old_best[2])
        and new_best[0][0] == old_best[0][0]
        and _last_chance_rank(farm, tasks[new_best[2]]) == 0
        and _last_chance_rank(farm, tasks[old_best[2]]) == 1
    )
    return new_best, old_best, eligible, activated


def _old_comparator_actions(farm, private, positions, invs, shed, tasks):
    """Replay the frozen allocator on the same state for instrumentation only."""
    actions = [["PASS"] for _ in positions]
    free_units = set(range(len(positions)))
    free_tasks = set(range(len(tasks)))
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


def _observe_last_chance_outcomes(obs, farm):
    player = int(obs.get("player", 0))
    day = int(obs.get("day", 0))
    for key in sorted(_LAST_CHANCE_PENDING):
        pending_player, pending_day = key
        if pending_player != player or day <= pending_day:
            continue
        targets = _LAST_CHANCE_PENDING.pop(key)
        if day != pending_day + 1:
            continue
        for (operation, pos), animal in targets.items():
            tile = farm["tiles"][pos[1]][pos[0]]
            if operation == "WATER":
                adverse = isinstance(tile, dict) and tile.get("kind") == "WEED"
            else:
                adverse = not (isinstance(tile, dict) and tile.get("animal") == animal)
            if adverse:
                _LAST_CHANCE_COUNTERS["next_day_weed_or_escape_outcome"] += 1


def _record_last_chance_action(obs, farm, position, task, action):
    if _last_chance_rank(farm, task) != 0:
        return
    operation = task["action"][0]
    pos = tuple(task["pos"])
    if tuple(position) != pos or not action or action[0] != operation:
        return
    _LAST_CHANCE_COUNTERS["last_chance_action_emitted_on_exact_target"] += 1
    tile = farm["tiles"][pos[1]][pos[0]]
    animal = tile.get("animal") if isinstance(tile, dict) else None
    key = (int(obs.get("player", 0)), int(obs.get("day", 0)))
    _LAST_CHANCE_PENDING.setdefault(key, {})[(operation, pos)] = animal
'''


_ALLOCATION_SOURCE = """    old_comparator_actions = _old_comparator_actions(
        farm,
        private,
        positions,
        invs,
        shed,
        tasks,
    )
    while free_units and free_tasks:
        best, _, eligible, activated = _last_chance_choices(
            farm,
            positions,
            invs,
            shed,
            tasks,
            free_units,
            free_tasks,
        )
        if best is None:
            break
        if eligible:
            _LAST_CHANCE_COUNTERS["eligible_opportunity"] += 1
        _, i, j = best
        action = _task_action(farm, positions[i], invs[i], shed, tasks[j])
        if activated:
            _LAST_CHANCE_COUNTERS["rank_tiebreak_activated"] += 1
        actions[i] = action
        _record_last_chance_action(obs, farm, positions[i], tasks[j], action)
        free_units.remove(i)
        free_tasks.remove(j)
"""


_FORMAL_ALLOCATION_SOURCE = """    while free_units and free_tasks:
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
"""


def build_last_chance_tiebreak(source_agent: str) -> str:
    """Return the deterministic BT1 single-file source."""
    ast.parse(source_agent)
    start, end = _function_span(source_agent, "_unit_actions")
    lines = source_agent.splitlines(keepends=True)
    formal_function = "".join(lines[start:end])
    if formal_function.count(_FORMAL_ALLOCATION_SOURCE) != 1:
        raise ValueError("formal _unit_actions comparator block did not match exactly once")
    modified = formal_function.replace(_FORMAL_ALLOCATION_SOURCE, _ALLOCATION_SOURCE)
    observation_marker = "    free_tasks = set(range(len(tasks)))\n"
    if modified.count(observation_marker) != 1:
        raise ValueError("formal _unit_actions setup marker did not match exactly once")
    modified = modified.replace(
        observation_marker,
        observation_marker + "    _observe_last_chance_outcomes(obs, farm)\n",
    )
    final_return = "    return actions\n"
    prefix, separator, suffix = modified.rpartition(final_return)
    if not separator:
        raise ValueError("formal _unit_actions final return marker was not found")
    modified = (
        prefix
        + "    if actions != old_comparator_actions:\n"
        + '        _LAST_CHANCE_COUNTERS["action_changed_vs_old_comparator_on_same_state"] += 1\n'
        + separator
        + suffix
    )
    replacement = _HELPERS_SOURCE.rstrip() + "\n\n\n" + modified.rstrip() + "\n\n"
    built = "".join(lines[:start]) + replacement + "".join(lines[end:])
    compile(built, "<last_chance_tiebreak_BT1>", "exec")
    return built


def build_last_chance_tiebreak_file(parent: Path, output: Path) -> Path:
    source = parent.read_text(encoding="utf-8")
    built = build_last_chance_tiebreak(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(built, encoding="utf-8", newline="\n")
    return output
