from __future__ import annotations

import ast
from pathlib import Path

import pytest
from kaggle_environments import make

from kaggriculture_lab.candidates.task_bundle import MODES, build_task_bundle

FORMAL = Path("artifacts/candidates/final_day_labor/main.py")


def _namespace(mode: str) -> dict[str, object]:
    source = build_task_bundle(FORMAL.read_text(encoding="utf-8"), mode)
    namespace: dict[str, object] = {}
    exec(compile(source, f"<task-bundle-{mode}>", "exec"), namespace)  # noqa: S102
    return namespace


def _function(source: str, name: str) -> ast.FunctionDef:
    tree = ast.parse(source)
    return next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )


def _terminal_branch(source: str) -> ast.If:
    function = _function(source, "_unit_actions")
    for node in function.body:
        if isinstance(node, ast.If) and "day >= 29" in ast.unparse(node.test):
            return node
    raise AssertionError("formal day-29 terminal branch was not found")


def _empty_farm(size: int = 12) -> dict[str, object]:
    return {
        "tiles": [[None for _ in range(size)] for _ in range(size)],
        "farmer": [0, 0],
        "hands": [],
    }


def test_b1_exact_assignment_beats_local_greedy_counterexample() -> None:
    namespace = _namespace("B1")
    farm = _empty_farm()
    positions = [(0, 0), (0, 2)]
    inventories = [{}, {}]
    tasks = [
        {"priority": 0, "pos": (0, 1), "action": ["DIG"], "need": None},
        {"priority": 0, "pos": (10, 0), "action": ["DIG"], "need": None},
    ]

    assignment = namespace["_global_assignment"](
        farm, positions, inventories, {}, tasks, mode="B1"
    )
    assigned_tasks = [task for _, task in assignment]
    exact_cost = sum(
        namespace["_task_cost"](farm, positions[unit], inventories[unit], {}, tasks[task])
        for unit, task in assignment
    )

    # The formal repeated local choice takes unit 0 -> task 0 first: 1 + 12.
    formal_greedy_cost = 13
    assert exact_cost == 11
    assert exact_cost < formal_greedy_cost
    assert len(assigned_tasks) == len(set(assigned_tasks)) == 2


def test_b1_top18_pruning_uses_priority_distance_before_coordinates() -> None:
    namespace = _namespace("B1")
    farm = _empty_farm(10)
    positions = [(4, 4)]
    inventories = [{}]
    early_cells = [(x, y) for y in range(3) for x in range(5)] + [(0, 3), (1, 3)]
    targets = early_cells + [(3, 4), (4, 4)]
    tasks = []
    for target in targets:
        farm["tiles"][target[1]][target[0]] = {
            "kind": "PLANT",
            "crop": "WHEAT",
            "watered_today": False,
            "consecutive_unwatered": 0,
        }
        tasks.append(
            {"priority": 5, "pos": target, "action": ["WATER"], "need": None}
        )

    assignment = namespace["_global_assignment"](
        farm, positions, inventories, {}, tasks, mode="B1"
    )

    assert len(tasks) == namespace["_TASK_BUNDLE_MAX_TASKS"] + 1
    assert assignment == [(0, 18)]
    assert namespace["_task_cost"](farm, positions[0], {}, {}, tasks[18]) == 0
    assert namespace["_task_cost"](farm, positions[0], {}, {}, tasks[17]) == 1


@pytest.mark.parametrize(
    ("operation", "tile", "need"),
    [
        (
            "WATER",
            {
                "kind": "PLANT",
                "crop": "WHEAT",
                "watered_today": False,
                "consecutive_unwatered": 1,
            },
            None,
        ),
        (
            "FEED",
            {
                "kind": "PASTURE",
                "animal": "COW",
                "fed_today": False,
                "consecutive_unfed": 1,
            },
            "WHEAT",
        ),
    ],
)
def test_b2_hard_second_miss_deadline_beats_near_formal_priority(
    operation: str, tile: dict[str, object], need: str | None
) -> None:
    namespace = _namespace("B2")
    farm = _empty_farm()
    farm["tiles"][0][8] = tile
    positions = [(0, 0)]
    inventories = [{"WHEAT": 1}] if need else [{}]
    tasks = [
        {"priority": 0, "pos": (0, 1), "action": ["DIG"], "need": None},
        {"priority": 5, "pos": (8, 0), "action": [operation], "need": need},
    ]
    marked = namespace["_mark_deadlines"](farm, tasks, "B2")

    assignment = namespace["_global_assignment"](
        farm,
        positions,
        inventories,
        {"WHEAT": 1},
        marked,
        day=7,
        hour=10,
        mode="B2",
    )

    assert marked[1]["hard_deadline"] is True
    assert assignment == [(0, 1)]
    assert namespace["_bundle_length"](
        farm, positions[0], inventories[0], {"WHEAT": 1}, marked[1]
    ) <= 14


def test_b2_rescuable_nineteenth_deadline_is_selected_before_top_task_cap() -> None:
    namespace = _namespace("B2")
    farm = _empty_farm(20)
    positions = [(19, 19)]
    inventories = [{}]
    tasks = []
    for x in range(18):
        farm["tiles"][0][x] = {
            "kind": "PLANT",
            "crop": "WHEAT",
            "watered_today": False,
            "consecutive_unwatered": 1,
        }
        tasks.append(
            {"priority": 5, "pos": (x, 0), "action": ["WATER"], "need": None}
        )
    farm["tiles"][19][19] = {
        "kind": "PLANT",
        "crop": "WHEAT",
        "watered_today": False,
        "consecutive_unwatered": 1,
    }
    tasks.append(
        {"priority": 5, "pos": (19, 19), "action": ["WATER"], "need": None}
    )
    marked = namespace["_mark_deadlines"](farm, tasks, "B2")

    assignment = namespace["_global_assignment"](
        farm,
        positions,
        inventories,
        {},
        marked,
        day=7,
        hour=23,
        mode="B2",
    )

    assert len(tasks) == namespace["_TASK_BUNDLE_MAX_TASKS"] + 1
    assert assignment == [(0, 18)]


def test_b4_farmer_first_reservation_prevents_duplicate_pickups_and_atomic_plant() -> None:
    namespace = _namespace("B4")
    farm = _empty_farm(10)
    positions = [(4, 4)] * 6 + [(0, 0), (1, 0)]
    inventories = [{} for _ in positions]
    tasks = []
    for item in ("WHEAT", "COW", "SHEEP"):
        tasks.extend(
            [
                {
                    "priority": 0,
                    "pos": (8, 8),
                    "action": ["FEED"] if item == "WHEAT" else ["PLACE", item],
                    "need": item,
                    "hard_deadline": False,
                },
                {
                    "priority": 0,
                    "pos": (8, 7),
                    "action": ["FEED"] if item == "WHEAT" else ["PLACE", item],
                    "need": item,
                    "hard_deadline": False,
                },
            ]
        )
    tasks.extend(
        [
            {
                "priority": 8,
                "pos": (0, 0),
                "action": ["PLANT", "STRAWBERRY"],
                "need": None,
                "hard_deadline": False,
            },
            {
                "priority": 8,
                "pos": (1, 0),
                "action": ["PLANT", "STRAWBERRY"],
                "need": None,
                "hard_deadline": False,
            },
        ]
    )
    private = {
        "shed": {"WHEAT": 1, "COW": 1, "SHEEP": 1},
        "seeds": {"STRAWBERRY": 1},
    }

    actions = namespace["_resource_safe_actions"](
        {"day": 3, "hour": 4},
        farm,
        private,
        positions,
        inventories,
        private["shed"],
        tasks,
        list(enumerate(range(len(tasks)))),
    )

    pickups = [action for action in actions if action and action[0] == "PICKUP"]
    plants = [action for action in actions if action[:2] == ["PLANT", "STRAWBERRY"]]
    for item in ("WHEAT", "COW", "SHEEP"):
        item_pickups = [action for action in pickups if action[1] == item]
        assert item_pickups == [["PICKUP", item, 1]]
    assert plants == [["PLANT", "STRAWBERRY"]]


def test_b4_moving_unit_does_not_reserve_seed_and_releases_task_for_repair() -> None:
    namespace = _namespace("B4")
    farm = _empty_farm(10)
    positions = [(0, 0), (2, 0)]
    inventories = [{}, {}]
    tasks = [
        {
            "priority": 8,
            "pos": (2, 0),
            "action": ["PLANT", "STRAWBERRY"],
            "need": None,
            "hard_deadline": False,
        }
    ]
    private = {"shed": {}, "seeds": {"STRAWBERRY": 1}}

    actions = namespace["_resource_safe_actions"](
        {"day": 3, "hour": 4},
        farm,
        private,
        positions,
        inventories,
        private["shed"],
        tasks,
        [(0, 0)],
    )

    assert actions[0] == ["EAST"]
    assert actions[1] == ["PLANT", "STRAWBERRY"]
    assert sum(action[:1] == ["PLANT"] for action in actions) == 1


def test_b4_moving_unit_does_not_reserve_shared_wheat_before_later_pickup() -> None:
    namespace = _namespace("B4")
    farm = _empty_farm(10)
    positions = [(0, 0), (4, 4)]
    inventories = [{}, {}]
    tasks = []
    for target in ((8, 8), (8, 7)):
        farm["tiles"][target[1]][target[0]] = {
            "kind": "PASTURE",
            "animal": "COW",
            "fed_today": False,
            "consecutive_unfed": 1,
        }
        tasks.append(
            {
                "priority": 0,
                "pos": target,
                "action": ["FEED"],
                "need": "WHEAT",
                "hard_deadline": True,
            }
        )
    private = {"shed": {"WHEAT": 1}, "seeds": {}}

    actions = namespace["_resource_safe_actions"](
        {"day": 3, "hour": 20},
        farm,
        private,
        positions,
        inventories,
        private["shed"],
        tasks,
        [(0, 0), (1, 1)],
    )

    assert actions == [["EAST"], ["PICKUP", "WHEAT", 1]]


def test_all_modes_preserve_formal_market_crop_plan_and_terminal_branch_ast() -> None:
    formal = FORMAL.read_text(encoding="utf-8")
    market_ast = ast.dump(_function(formal, "_market_actions"), include_attributes=False)
    crop_plan_ast = ast.dump(_function(formal, "_crop_plan"), include_attributes=False)
    terminal_ast = ast.dump(_terminal_branch(formal), include_attributes=False)

    for mode in MODES:
        built = build_task_bundle(formal, mode)
        if mode == "B0":
            assert built == formal
        assert ast.dump(
            _function(built, "_market_actions"), include_attributes=False
        ) == market_ast
        assert ast.dump(_function(built, "_crop_plan"), include_attributes=False) == crop_plan_ast
        assert ast.dump(_terminal_branch(built), include_attributes=False) == terminal_ast
        assert "TARGET_HANDS_CORE = 10" in built
        assert "TARGET_HANDS_EXPANDED = 10" in built
        assert 'target = {"COW": 7, "SHEEP": 2}' in built


def test_build_is_deterministic_and_agents_return_action_schema() -> None:
    formal = FORMAL.read_text(encoding="utf-8")
    invalid_observation = {"player": 1, "farms": []}
    for mode in MODES:
        first = build_task_bundle(formal, mode)
        second = build_task_bundle(formal, mode)
        assert first == second
        namespace: dict[str, object] = {}
        exec(compile(first, f"<task-bundle-{mode}>", "exec"), namespace)  # noqa: S102
        action = namespace["agent"](invalid_observation)
        assert set(action) == {"farmer", "hands", "market"}
        assert isinstance(action["farmer"], list)
        assert isinstance(action["hands"], list)
        assert isinstance(action["market"], list)


def test_b2_and_b4_run_together_in_official_engine() -> None:
    agents = [_namespace(mode)["agent"] for mode in ("B2", "B4")]
    environment = make(
        "kaggriculture",
        configuration={"episodeSteps": 6, "seed": 123},
        debug=True,
    )

    steps = environment.run(agents)

    assert len(steps) == 6
    assert [state.status for state in environment.state] == ["DONE", "DONE"]
    assert all(state.reward is not None for state in environment.state)
