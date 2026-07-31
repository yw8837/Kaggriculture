"""Build deterministic task-bundle allocator variants from the formal champion.

Only ``_unit_actions`` is replaced.  Market policy, crop plan, herd sizing,
hire constants, and the formal day-29 terminal branch remain source-equivalent.
The generated agents use only the Python standard library already used by the
parent agent.
"""

from __future__ import annotations

import ast
from pathlib import Path

MODES = ("B0", "B1", "B2", "B4")


def _function_span(source: str, name: str) -> tuple[int, int]:
    """Return zero-based whole-line bounds for one top-level function."""
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


def _allocator_source(mode: str) -> str:
    """Return the self-contained allocator injected into a single-file agent."""
    return f'''_TASK_BUNDLE_MODE = {mode!r}
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
    dp = {{0: (0, empty_mapping)}}
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
    selected = {{unit: task for unit, task in assignments}}
    initially_occupied = set(selected.values())
    used = set()
    released = set()
    shed_remaining = dict(shed)
    seed_remaining = dict(private.get("seeds", {{}}) or {{}})

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
        invs.append({{}})
    shed = dict(private.get("shed", {{}}) or {{}})
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
    remaining = dict(private.get("seeds", {{}}) or {{}})
    for i, action in enumerate(actions):
        if len(action) >= 2 and action[0] == "PLANT":
            crop = action[1]
            if int(remaining.get(crop, 0)) <= 0:
                actions[i] = ["PASS"]
            else:
                remaining[crop] -= 1
    return actions
'''


def build_task_bundle(source_agent: str, mode: str) -> str:
    """Build one named B-mode agent from a formal single-file source."""
    normalized_mode = mode.upper()
    if normalized_mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
    ast.parse(source_agent)
    if normalized_mode == "B0":
        return source_agent

    start, end = _function_span(source_agent, "_unit_actions")
    lines = source_agent.splitlines(keepends=True)
    replacement = _allocator_source(normalized_mode).rstrip() + "\n\n"
    built = "".join(lines[:start]) + replacement + "".join(lines[end:])
    compile(built, f"<task_bundle_{normalized_mode}>", "exec")
    return built


def build_task_bundles(source_agent: str) -> dict[str, str]:
    """Build all registered modes without touching the filesystem."""
    return {mode: build_task_bundle(source_agent, mode) for mode in MODES}


def build_task_bundle_file(parent: Path, output: Path, mode: str) -> Path:
    """Explicit file helper for callers that own artifact creation."""
    source = parent.read_text(encoding="utf-8")
    built = build_task_bundle(source, mode)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(built, encoding="utf-8", newline="\n")
    return output
