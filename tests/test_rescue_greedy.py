from __future__ import annotations

import ast
import copy
from pathlib import Path

from kaggle_environments.envs.kaggriculture import kaggriculture as engine

from kaggriculture_lab.candidates.rescue_greedy import (
    _function_span,
    build_rescue_greedy,
)

FORMAL = Path("artifacts/candidates/final_day_labor/main.py")


def _namespace() -> dict[str, object]:
    built = build_rescue_greedy(FORMAL.read_text(encoding="utf-8"))
    namespace: dict[str, object] = {}
    exec(compile(built, "<rescue-greedy-test>", "exec"), namespace)  # noqa: S102
    return namespace


def _farm(size: int = 10) -> dict[str, object]:
    return {
        "tiles": [[None for _ in range(size)] for _ in range(size)],
        "farmer": [0, 0],
        "hands": [],
        "money": 3000,
        "hires_today": 0,
        "unlocked_quadrants": ["NW"],
    }


def _plant(counter: int = 1, watered: bool = False) -> dict[str, object]:
    return {
        "kind": "PLANT",
        "crop": "WHEAT",
        "planted_day": 0,
        "watered_today": watered,
        "consecutive_unwatered": counter,
        "yield_units": 1,
        "max_lifespan_step": 120,
        "fertilized_until_day": -1,
    }


def _cow(counter: int = 1, fed: bool = False) -> dict[str, object]:
    return {
        "kind": "PASTURE",
        "animal": "COW",
        "placed_day": 0,
        "yield_units": 0,
        "consecutive_unfed": counter,
        "fed_today": fed,
        "cared_today": False,
        "fertilizer_available": False,
        "pending_care_bonus": 0,
    }


def _task(operation: str, pos: tuple[int, int]) -> dict[str, object]:
    return {
        "priority": 0 if operation == "FEED" else 3,
        "pos": pos,
        "action": [operation],
        "need": "WHEAT" if operation == "FEED" else None,
    }


def _function(source: str, name: str) -> ast.FunctionDef:
    tree = ast.parse(source)
    return next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )


def _terminal_branch(source: str) -> ast.If:
    function = _function(source, "_unit_actions")
    return next(
        node
        for node in function.body
        if isinstance(node, ast.If) and "day >= 29" in ast.unparse(node.test)
    )


def test_official_second_miss_semantics_are_weed_and_escape() -> None:
    unwatered = engine._new_plant("WHEAT", 0, 24)
    assert unwatered["consecutive_unwatered"] == 1
    plant_farm = {"tiles": [[unwatered]]}
    engine._daily_refresh_plants(plant_farm, 0, 24)
    assert plant_farm["tiles"][0][0] == {"kind": "WEED"}

    watered = engine._new_plant("WHEAT", 0, 24)
    watered["watered_today"] = True
    watered_farm = {"tiles": [[watered]]}
    engine._daily_refresh_plants(watered_farm, 0, 24)
    assert watered_farm["tiles"][0][0]["kind"] == "PLANT"

    unfed = engine._new_animal("COW", 0)
    unfed["consecutive_unfed"] = 1
    animal_farm = {"tiles": [[unfed]]}
    engine._daily_refresh_animals(animal_farm, 0)
    assert animal_farm["tiles"][0][0] == {"kind": "PASTURE"}

    fed = engine._new_animal("COW", 0)
    fed["consecutive_unfed"] = 1
    fed["fed_today"] = True
    fed_farm = {"tiles": [[fed]]}
    engine._daily_refresh_animals(fed_farm, 0)
    assert fed_farm["tiles"][0][0]["animal"] == "COW"


def test_rescue_requires_counter_exactly_one_and_not_already_serviced() -> None:
    namespace = _namespace()
    farm = _farm()
    checks = [
        ((0, 0), _plant(0), False),
        ((1, 0), _plant(1), True),
        ((2, 0), _plant(2), False),
        ((3, 0), _plant(1, watered=True), False),
        ((0, 1), _cow(0), False),
        ((1, 1), _cow(1), True),
        ((2, 1), _cow(2), False),
        ((3, 1), _cow(1, fed=True), False),
    ]
    for pos, tile, expected in checks:
        farm["tiles"][pos[1]][pos[0]] = tile
        operation = "WATER" if tile.get("kind") == "PLANT" else "FEED"
        assert namespace["_is_rescue_task"](farm, _task(operation, pos)) is expected


def test_movement_does_not_reserve_shared_wheat_but_pickup_does() -> None:
    namespace = _namespace()
    remaining = {"WHEAT": 1}

    assert namespace["_reserve_emitted_wheat"](["EAST"], remaining) is True
    assert remaining == {"WHEAT": 1}
    assert namespace["_reserve_emitted_wheat"](
        ["PICKUP", "WHEAT", 1], remaining
    ) is True
    assert remaining == {"WHEAT": 0}
    assert namespace["_reserve_emitted_wheat"](
        ["PICKUP", "WHEAT", 1], remaining
    ) is False


def test_shared_wheat_allows_only_one_emitted_pickup() -> None:
    namespace = _namespace()
    namespace["reset_rescue_metrics"]()
    farm = _farm()
    farm["tiles"][8][8] = _cow()
    farm["tiles"][7][8] = _cow()
    positions = [(4, 4), (4, 4)]
    inventories = [{}, {}]
    tasks = [_task("FEED", (8, 8)), _task("FEED", (8, 7))]
    actions = [["PASS"], ["PASS"]]
    free_units = {0, 1}
    free_tasks = {0, 1}

    remaining = namespace["_assign_rescues"](
        {"hour": 0},
        farm,
        positions,
        inventories,
        {"WHEAT": 1},
        tasks,
        actions,
        free_units,
        free_tasks,
    )

    pickups = [action for action in actions if action[:2] == ["PICKUP", "WHEAT"]]
    assert pickups == [["PICKUP", "WHEAT", 1]]
    assert remaining["WHEAT"] == 0
    assert namespace["rescue_metrics"]()["assignments"] == 1


def test_shortest_shed_unit_gets_virtual_wheat_before_distant_mover() -> None:
    namespace = _namespace()
    namespace["reset_rescue_metrics"]()
    farm = _farm()
    farm["tiles"][8][8] = _cow()
    farm["tiles"][4][5] = _cow()
    positions = [(0, 0), (4, 4)]
    tasks = [_task("FEED", (8, 8)), _task("FEED", (5, 4))]
    actions = [["PASS"], ["PASS"]]

    remaining = namespace["_assign_rescues"](
        {"player": 0, "day": 3, "hour": 0},
        farm,
        positions,
        [{}, {}],
        {"WHEAT": 1},
        tasks,
        actions,
        {0, 1},
        {0, 1},
    )

    assert actions == [["PASS"], ["PICKUP", "WHEAT", 1]]
    assert remaining["WHEAT"] == 0
    assert namespace["rescue_metrics"]()["assignments"] == 1


def test_two_movers_leave_zero_wheat_for_following_ordinary_allocator() -> None:
    namespace = _namespace()
    namespace["reset_rescue_metrics"]()
    farm = _farm()
    farm["tiles"][8][8] = _cow()
    farm["tiles"][7][8] = _cow()
    actions = [["PASS"], ["PASS"]]

    shed = {"WHEAT": 1}
    free_units = {0, 1}
    free_tasks = {0, 1}
    tasks = [_task("FEED", (8, 8)), _task("FEED", (8, 7))]
    ordinary_available = namespace["_assign_rescues"](
        {"player": 0, "day": 3, "hour": 0},
        farm,
        [(0, 0), (0, 1)],
        [{}, {}],
        shed,
        tasks,
        actions,
        free_units,
        free_tasks,
    )

    moving = [action for action in actions if action[0] in ("NORTH", "SOUTH", "EAST", "WEST")]
    assert len(moving) == 1
    assert actions.count(["PASS"]) == 1
    assert shed == {"WHEAT": 1}  # no official PICKUP was emitted this turn
    assert ordinary_available["WHEAT"] == 0  # moving rescue owns the virtual unit
    ordinary_unit = next(iter(free_units))
    ordinary_task = next(iter(free_tasks))
    assert namespace["_task_cost"](
        farm,
        [(0, 0), (0, 1)][ordinary_unit],
        {},
        ordinary_available,
        tasks[ordinary_task],
    ) == 10000
    assert namespace["rescue_metrics"]()["assignments"] == 1


def test_water_rescue_requires_full_path_plus_action_before_eod() -> None:
    namespace = _namespace()
    farm = _farm()
    farm["tiles"][0][1] = _plant()
    task = _task("WATER", (1, 0))

    def allocate(position: tuple[int, int]) -> list[str]:
        actions = [["PASS"]]
        namespace["reset_rescue_metrics"]()
        namespace["_assign_rescues"](
            {"hour": 23},
            farm,
            [position],
            [{}],
            {},
            [task],
            actions,
            {0},
            {0},
        )
        return actions[0]

    assert allocate((0, 0)) == ["PASS"]  # move + WATER needs two actions
    assert allocate((1, 0)) == ["WATER"]


def test_feed_rescue_counts_pickup_travel_and_terminal_action_before_eod() -> None:
    namespace = _namespace()
    farm = _farm()
    farm["tiles"][4][5] = _cow()
    task = _task("FEED", (5, 4))
    bundle, shed_pos = namespace["_rescue_route"](
        farm, (4, 4), {}, {"WHEAT": 1}, task
    )
    assert (bundle, shed_pos) == (3, (4, 4))

    for hour, expected in ((22, ["PASS"]), (21, ["PICKUP", "WHEAT", 1])):
        actions = [["PASS"]]
        namespace["reset_rescue_metrics"]()
        namespace["_assign_rescues"](
            {"hour": hour},
            farm,
            [(4, 4)],
            [{}],
            {"WHEAT": 1},
            [task],
            actions,
            {0},
            {0},
        )
        assert actions[0] == expected


def test_metrics_cover_opportunity_assignment_completion_and_observed_event() -> None:
    namespace = _namespace()
    namespace["reset_rescue_metrics"]()
    farm = _farm()
    farm["tiles"][0][0] = _plant()
    task = _task("WATER", (0, 0))
    observation = {"player": 0, "day": 0, "hour": 23}

    namespace["_record_rescue_opportunities"](observation, farm, [task])
    namespace["_record_rescue_opportunities"](observation, farm, [task])
    actions = [["PASS"]]
    namespace["_assign_rescues"](
        observation, farm, [(0, 0)], [{}], {}, [task], actions, {0}, {0}
    )
    assert actions == [["WATER"]]
    metrics = namespace["rescue_metrics"]()
    assert metrics == {
        "opportunities": 1,
        "assignments": 1,
        "completed_rescues": 1,
        "weed_or_escape_events": 0,
    }

    # Re-evaluating the same opportunity in a later call must not inflate the
    # assignment or terminal-completion fractions.
    repeated_actions = [["PASS"]]
    namespace["_assign_rescues"](
        observation,
        farm,
        [(0, 0)],
        [{}],
        {},
        [task],
        repeated_actions,
        {0},
        {0},
    )
    assert repeated_actions == [["WATER"]]
    assert namespace["rescue_metrics"]() == metrics

    farm["tiles"][0][0] = {"kind": "WEED"}
    namespace["_observe_rescue_outcomes"]({"player": 0, "day": 1}, farm)
    assert namespace["rescue_metrics"]()["weed_or_escape_events"] == 1


def test_assignment_and_terminal_completion_are_unique_across_travel_hours() -> None:
    namespace = _namespace()
    namespace["reset_rescue_metrics"]()
    farm = _farm()
    farm["tiles"][0][2] = _plant()
    task = _task("WATER", (2, 0))

    def assign(hour: int, position: tuple[int, int]) -> list[str]:
        actions = [["PASS"]]
        namespace["_assign_rescues"](
            {"player": 0, "day": 4, "hour": hour},
            farm,
            [position],
            [{}],
            {},
            [task],
            actions,
            {0},
            {0},
        )
        return actions[0]

    assert assign(10, (0, 0)) == ["EAST"]
    assert assign(11, (1, 0)) == ["EAST"]
    assert namespace["rescue_metrics"]()["assignments"] == 1
    assert namespace["rescue_metrics"]()["completed_rescues"] == 0

    assert assign(12, (2, 0)) == ["WATER"]
    assert assign(12, (2, 0)) == ["WATER"]
    assert namespace["rescue_metrics"]()["assignments"] == 1
    assert namespace["rescue_metrics"]()["completed_rescues"] == 1


def test_dense_rescue_runtime_precomputes_only_unique_source_distance_maps() -> None:
    namespace = _namespace()
    farm = _farm()
    tasks = []
    for y in range(10):
        for x in range(10):
            farm["tiles"][y][x] = _plant()
            tasks.append(_task("WATER", (x, y)))
    positions = [(4, 4)] * 11
    actions = [["PASS"] for _ in positions]
    calls = 0
    move_calls = 0
    original = namespace["_distance_map"]
    original_move = namespace["_move"]

    def counted_distance_map(tiles: list[object], source: tuple[int, int]) -> object:
        nonlocal calls
        calls += 1
        return original(tiles, source)

    def counted_move(tiles: list[object], source: object, target: object) -> object:
        nonlocal move_calls
        move_calls += 1
        return original_move(tiles, source, target)

    namespace["_distance_map"] = counted_distance_map
    namespace["_move"] = counted_move
    namespace["_assign_rescues"](
        {"player": 0, "day": 4, "hour": 0},
        farm,
        positions,
        [{} for _ in positions],
        {},
        tasks,
        actions,
        set(range(11)),
        set(range(100)),
    )

    # One worker position overlaps one of the four shed cells: four unique BFS
    # sources total, independent of 100 tasks and 11 greedy rounds.
    assert calls == 4
    assert move_calls <= 11
    assert sum(action != ["PASS"] for action in actions) == 11


def test_builder_changes_only_unit_allocator_and_preserves_terminal_ast() -> None:
    formal = FORMAL.read_text(encoding="utf-8")
    built = build_rescue_greedy(formal)
    formal_start, formal_end = _function_span(formal, "_unit_actions")
    lines = formal.splitlines(keepends=True)
    assert built.startswith("".join(lines[:formal_start]))
    assert built.endswith("".join(lines[formal_end:]))

    formal_tree = ast.parse(formal)
    built_tree = ast.parse(built)
    built_functions = {
        node.name: node for node in built_tree.body if isinstance(node, ast.FunctionDef)
    }
    for node in formal_tree.body:
        if isinstance(node, ast.FunctionDef) and node.name != "_unit_actions":
            assert ast.dump(node, include_attributes=False) == ast.dump(
                built_functions[node.name], include_attributes=False
            )
    assert ast.dump(_terminal_branch(built), include_attributes=False) == ast.dump(
        _terminal_branch(formal), include_attributes=False
    )
    assert "_global_assignment" not in built
    assert "bit_count" not in built


def test_build_is_deterministic_stdlib_only_and_returns_schema() -> None:
    formal = FORMAL.read_text(encoding="utf-8")
    first = build_rescue_greedy(formal)
    second = build_rescue_greedy(formal)
    assert first == second
    imports = [node for node in ast.parse(first).body if isinstance(node, (ast.Import, ast.ImportFrom))]
    assert [(node.module, node.names[0].name) for node in imports] == [("collections", "deque")]

    namespace = _namespace()
    action = namespace["agent"]({"player": 1, "farms": []})
    assert action == {"farmer": ["PASS"], "hands": [], "market": []}


def test_agent_does_not_mutate_input_observation() -> None:
    namespace = _namespace()
    namespace["reset_rescue_metrics"]()
    farm = _farm()
    farm["tiles"][0][0] = _plant()
    observation = {
        "player": 0,
        "day": 0,
        "hour": 23,
        "farms": [farm],
        "private": {
            "shed": {"WHEAT": 2},
            "inventories": [{}],
            "seeds": {"WHEAT": 1},
        },
        "market": {"prices": {"WHEAT": 20}},
    }
    original = copy.deepcopy(observation)

    action = namespace["agent"](observation)

    assert observation == original
    assert set(action) == {"farmer", "hands", "market"}
    assert isinstance(action["farmer"], list)
    assert isinstance(action["hands"], list)
    assert isinstance(action["market"], list)
