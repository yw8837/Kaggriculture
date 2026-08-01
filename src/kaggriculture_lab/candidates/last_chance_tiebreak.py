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
    "tiebreak_to_exact_target_action_emitted": 0,
    "formal_fallback_due_assignment_set_mismatch": 0,
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


def _bfs_distance(tiles, source, target):
    source = tuple(source)
    target = tuple(target)
    if source == target:
        return 0
    n = len(tiles)
    queue = deque([(source, 0)])
    visited = {source}
    while queue:
        current, distance = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (current[0] + dx, current[1] + dy)
            if not (0 <= nxt[0] < n and 0 <= nxt[1] < n):
                continue
            if nxt in visited or tiles[nxt[1]][nxt[0]] == "LOCKED":
                continue
            if nxt == target:
                return distance + 1
            visited.add(nxt)
            queue.append((nxt, distance + 1))
    return 10000


def _real_task_path_cost(farm, position, inventory, shed, task):
    need = task["need"]
    target = task["pos"]
    tiles = farm["tiles"]
    if need is None or int(inventory.get(need, 0)) > 0:
        return _bfs_distance(tiles, position, target)
    if int(shed.get(need, 0)) <= 0:
        return 10000
    pickup = _nearest_shed(len(tiles), tiles, position)
    to_pickup = _bfs_distance(tiles, position, pickup)
    to_target = _bfs_distance(tiles, pickup, target)
    if to_pickup >= 10000 or to_target >= 10000:
        return 10000
    return to_pickup + 1 + to_target


def _allocation_trace(farm, private, positions, invs, shed, tasks, ranked):
    """Run one complete allocator trajectory and retain assigned task ids."""
    actions = [["PASS"] for _ in positions]
    free_units = set(range(len(positions)))
    free_tasks = set(range(len(tasks)))
    trace = []
    while free_units and free_tasks:
        best = None
        feasible_priority_ranks = []
        for i in free_units:
            for j in free_tasks:
                task = tasks[j]
                cost = _task_cost(farm, positions[i], invs[i], shed, task)
                if cost >= 10000:
                    continue
                priority = task["priority"]
                rank = _last_chance_rank(farm, task)
                feasible_priority_ranks.append((priority, rank))
                if ranked:
                    key = (priority, rank, cost, task["pos"][1], task["pos"][0], i, j)
                else:
                    key = (priority, cost, task["pos"][1], task["pos"][0], i, j)
                if best is None or key < best[0]:
                    best = (key, i, j, priority, rank, cost)
        if best is None:
            break
        _, i, j, priority, rank, cost = best
        minimum_priority = min(item[0] for item in feasible_priority_ranks)
        minimum_priority_ranks = {
            item[1] for item in feasible_priority_ranks if item[0] == minimum_priority
        }
        eligible_at_decision = minimum_priority_ranks >= {0, 1}
        actions[i] = _task_action(farm, positions[i], invs[i], shed, tasks[j])
        need = tasks[j]["need"]
        pickup_quantity = 0
        if (
            need is not None
            and int(invs[i].get(need, 0)) <= 0
            and int(shed.get(need, 0)) > 0
        ):
            pickup_quantity = 1 if need in ("COW", "SHEEP") else 4
        trace.append(
            (
                i,
                j,
                priority,
                rank,
                cost,
                _real_task_path_cost(farm, positions[i], invs[i], shed, tasks[j]),
                need if pickup_quantity else None,
                pickup_quantity,
                eligible_at_decision,
            )
        )
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
    return actions, tuple(trace)


def _trace_tiebreak_event(formal_trace, candidate_trace):
    """Identify the first causal rank-zero displacement on full trajectories."""
    for formal_step, candidate_step in zip(formal_trace, candidate_trace):
        if formal_step[:2] == candidate_step[:2]:
            continue
        return bool(
            formal_step[2] == candidate_step[2]
            and formal_step[3] == 1
            and candidate_step[3] == 0
        )
    return False


def _safe_allocation_actions(farm, private, positions, invs, shed, tasks):
    """Adopt BT1 only when its complete assigned task-id set is unchanged."""
    formal_actions, formal_trace = _allocation_trace(
        farm, private, positions, invs, shed, tasks, False
    )
    candidate_actions, candidate_trace = _allocation_trace(
        farm, private, positions, invs, shed, tasks, True
    )
    tie_event = _trace_tiebreak_event(formal_trace, candidate_trace)
    _LAST_CHANCE_COUNTERS["eligible_opportunity"] += sum(
        step[8] for step in formal_trace
    )
    formal_costs = {step[1]: step[4] for step in formal_trace}
    candidate_costs = {step[1]: step[4] for step in candidate_trace}
    formal_path_costs = {step[1]: step[5] for step in formal_trace}
    candidate_path_costs = {step[1]: step[5] for step in candidate_trace}
    formal_units = {step[1]: step[0] for step in formal_trace}
    candidate_units = {step[1]: step[0] for step in candidate_trace}
    same_tasks = formal_costs.keys() == candidate_costs.keys()
    cost_nonworsening = same_tasks and all(
        candidate_costs[j] <= formal_costs[j] for j in formal_costs
    )
    path_nonworsening = same_tasks and all(
        candidate_path_costs[j] <= formal_path_costs[j] for j in formal_path_costs
    )
    formal_pickups = {}
    candidate_pickups = {}
    for trace, totals in ((formal_trace, formal_pickups), (candidate_trace, candidate_pickups)):
        for step in trace:
            need, quantity = step[6], step[7]
            if need is not None:
                count, total_quantity = totals.get(need, (0, 0))
                totals[need] = (count + 1, total_quantity + quantity)
    pickup_nonincreasing = all(
        candidate_pickups.get(need, (0, 0))[0] <= formal_pickups.get(need, (0, 0))[0]
        and candidate_pickups.get(need, (0, 0))[1]
        <= formal_pickups.get(need, (0, 0))[1]
        for need in set(formal_pickups) | set(candidate_pickups)
    )
    nonpass_preserved = same_tasks and all(
        formal_actions[formal_units[j]] == ["PASS"]
        or candidate_actions[candidate_units[j]] != ["PASS"]
        for j in formal_units
    )
    terminal_preserved = same_tasks and all(
        not tasks[j].get("action")
        or formal_actions[formal_units[j]][0] != tasks[j]["action"][0]
        or candidate_actions[candidate_units[j]][0] == tasks[j]["action"][0]
        for j in formal_units
    )
    accepted = (
        cost_nonworsening
        and path_nonworsening
        and pickup_nonincreasing
        and nonpass_preserved
        and terminal_preserved
    )
    if accepted:
        actions, trace = candidate_actions, candidate_trace
        if tie_event:
            _LAST_CHANCE_COUNTERS["rank_tiebreak_activated"] += 1
    else:
        actions, trace = formal_actions, formal_trace
        _LAST_CHANCE_COUNTERS["formal_fallback_due_assignment_set_mismatch"] += 1
    if actions != formal_actions:
        _LAST_CHANCE_COUNTERS["action_changed_vs_old_comparator_on_same_state"] += 1
    return (
        actions,
        trace,
        formal_actions,
        candidate_actions,
        formal_trace,
        candidate_trace,
        tie_event,
        accepted,
    )


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


def _record_last_chance_actions(
    obs, farm, positions, tasks, trace, actions, formal_actions, activated
):
    for i, j, _, rank, *_ in trace:
        task = tasks[j]
        operation = task["action"][0]
        pos = tuple(task["pos"])
        action = actions[i]
        if rank != 0 or tuple(positions[i]) != pos or not action or action[0] != operation:
            continue
        _LAST_CHANCE_COUNTERS["last_chance_action_emitted_on_exact_target"] += 1
        if activated and action != formal_actions[i]:
            _LAST_CHANCE_COUNTERS["tiebreak_to_exact_target_action_emitted"] += 1
        tile = farm["tiles"][pos[1]][pos[0]]
        animal = tile.get("animal") if isinstance(tile, dict) else None
        key = (int(obs.get("player", 0)), int(obs.get("day", 0)))
        _LAST_CHANCE_PENDING.setdefault(key, {})[(operation, pos)] = animal
'''


_ALLOCATION_SOURCE = """    (
        actions,
        emitted_trace,
        formal_actions,
        _,
        _,
        _,
        tie_event,
        accepted,
    ) = _safe_allocation_actions(
        farm,
        private,
        positions,
        invs,
        shed,
        tasks,
    )
    _record_last_chance_actions(
        obs,
        farm,
        positions,
        tasks,
        emitted_trace,
        actions,
        formal_actions,
        tie_event and accepted,
    )
    return actions
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

    remaining = dict(private.get("seeds", {}) or {})
    for i, action in enumerate(actions):
        if len(action) >= 2 and action[0] == "PLANT":
            crop = action[1]
            if int(remaining.get(crop, 0)) <= 0:
                actions[i] = ["PASS"]
            else:
                remaining[crop] -= 1
    return actions
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
