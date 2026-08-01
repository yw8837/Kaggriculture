from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

from kaggriculture_lab.candidates.last_chance_tiebreak import (
    _function_span,
    build_last_chance_tiebreak,
)

FORMAL = Path("artifacts/candidates/final_day_labor/main.py")
SNAPSHOT = Path("experiments/source_snapshots/fa02_last_chance_tiebreak/BT1.py")
RUNTIME = Path("experiments/evaluations/fa02_last_chance_tiebreak/BT1_runtime.json")
REPLAY = Path("artifacts/submission_replays/episode-89143277-replay.json")
FORMAL_SHA256 = "112AF9EC28030B53CE852927CEE986834F18F0245F3A88FB2E06F423291C9F8B"
COUNTERS = {
    "eligible_opportunity",
    "rank_tiebreak_activated",
    "action_changed_vs_old_comparator_on_same_state",
    "last_chance_action_emitted_on_exact_target",
    "tiebreak_to_exact_target_action_emitted",
    "formal_fallback_due_assignment_set_mismatch",
    "next_day_weed_or_escape_outcome",
}
ADDED_FUNCTIONS = {
    "rescue_metrics",
    "reset_rescue_metrics",
    "_last_chance_rank",
    "_bfs_distance",
    "_real_task_path_cost",
    "_allocation_trace",
    "_trace_tiebreak_displacement",
    "_trace_tiebreak_event",
    "_safe_allocation_actions",
    "_observe_last_chance_outcomes",
    "_record_last_chance_actions",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _namespace(source: str | None = None) -> dict[str, object]:
    built = source or build_last_chance_tiebreak(FORMAL.read_text(encoding="utf-8"))
    namespace: dict[str, object] = {}
    exec(compile(built, "<last-chance-test>", "exec"), namespace)  # noqa: S102
    return namespace


def _farm(size: int = 10, farmer: tuple[int, int] = (0, 0)) -> dict[str, object]:
    return {
        "tiles": [[None for _ in range(size)] for _ in range(size)],
        "farmer": list(farmer),
        "hands": [],
        "money": 3000,
        "hires_today": 0,
        "unlocked_quadrants": ["NW"],
    }


def _plant(counter: int = 1, watered: bool = False) -> dict[str, object]:
    return {
        "kind": "PLANT",
        "crop": "WHEAT",
        "watered_today": watered,
        "consecutive_unwatered": counter,
    }


def _animal(animal: str = "COW", counter: int = 1, fed: bool = False) -> dict[str, object]:
    return {
        "kind": "PASTURE",
        "animal": animal,
        "fed_today": fed,
        "consecutive_unfed": counter,
        "fertilizer_available": False,
        "cared_today": True,
        "yield_units": 0,
    }


def _task(
    operation: str, pos: tuple[int, int], *, priority: int = 0, cost: int = 0
) -> dict[str, object]:
    return {
        "priority": priority,
        "pos": pos,
        "action": [operation],
        "need": "WHEAT" if operation == "FEED" else None,
        "test_cost": cost,
    }


def _trace_step(unit: int, task: int, rank: int, *, eligible: bool = False) -> tuple[object, ...]:
    return (unit, task, 0, rank, 0, 0, None, 0, eligible)


def _top_functions(source: str) -> dict[str, ast.FunctionDef]:
    return {node.name: node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}


def test_parent_is_exact_frozen_source_and_snapshot_is_deterministic() -> None:
    formal = FORMAL.read_text(encoding="utf-8")

    assert _sha256(FORMAL) == FORMAL_SHA256
    assert build_last_chance_tiebreak(formal) == build_last_chance_tiebreak(formal)
    assert SNAPSHOT.read_text(encoding="utf-8") == build_last_chance_tiebreak(formal)


def test_ast_allowlist_preserves_every_formal_function_except_unit_allocator() -> None:
    formal = FORMAL.read_text(encoding="utf-8")
    built = build_last_chance_tiebreak(formal)
    formal_functions = _top_functions(formal)
    built_functions = _top_functions(built)

    assert set(built_functions) - set(formal_functions) == ADDED_FUNCTIONS
    for name, node in formal_functions.items():
        if name != "_unit_actions":
            assert ast.dump(node, include_attributes=False) == ast.dump(
                built_functions[name], include_attributes=False
            )

    formal_start, formal_end = _function_span(formal, "_unit_actions")
    lines = formal.splitlines(keepends=True)
    assert built.startswith("".join(lines[:formal_start]))
    assert built.endswith("".join(lines[formal_end:]))
    choice_source = ast.unparse(built_functions["_allocation_trace"])
    assert "(priority, cost, task['pos'][1], task['pos'][0], i, j)" in choice_source
    assert "(priority, rank, cost, task['pos'][1], task['pos'][0], i, j)" in choice_source


def test_rank_zero_matches_only_exact_auditor_definitions() -> None:
    namespace = _namespace()
    rank = namespace["_last_chance_rank"]
    farm = _farm()
    cases = [
        ((0, 0), _plant(1, False), "WATER", 0),
        ((1, 0), _plant(0, False), "WATER", 1),
        ((2, 0), _plant(2, False), "WATER", 1),
        ((3, 0), _plant(1, True), "WATER", 1),
        ((0, 1), _animal("COW", 1, False), "FEED", 0),
        ((1, 1), _animal("SHEEP", 1, False), "FEED", 0),
        ((2, 1), _animal("GOOSE", 1, False), "FEED", 1),
        ((3, 1), _animal("COW", 0, False), "FEED", 1),
        ((4, 1), _animal("SHEEP", 2, False), "FEED", 1),
        ((0, 2), _animal("COW", 1, True), "FEED", 1),
    ]
    for pos, tile, operation, expected in cases:
        farm["tiles"][pos[1]][pos[0]] = tile
        assert rank(farm, _task(operation, pos)) == expected
    assert rank(farm, _task("HARVEST", (0, 0))) == 1


def test_choice_property_is_exact_new_key_with_zero_priority_inversions() -> None:
    namespace = _namespace()
    namespace["_task_cost"] = lambda farm, pos, inv, shed, task: task["test_cost"]
    allocate = namespace["_allocation_trace"]

    for ordinary_priority in range(4):
        for last_chance_priority in range(4):
            for ordinary_cost in (0, 3, 9):
                for last_chance_cost in (0, 4, 10):
                    farm = _farm()
                    farm["tiles"][0][0] = _plant(0)
                    farm["tiles"][1][1] = _plant(1)
                    tasks = [
                        _task(
                            "WATER",
                            (0, 0),
                            priority=ordinary_priority,
                            cost=ordinary_cost,
                        ),
                        _task(
                            "WATER",
                            (1, 1),
                            priority=last_chance_priority,
                            cost=last_chance_cost,
                        ),
                    ]
                    _, old_trace = allocate(farm, {"seeds": {}}, [(0, 0)], [{}], {}, tasks, False)
                    _, new_trace = allocate(farm, {"seeds": {}}, [(0, 0)], [{}], {}, tasks, True)
                    expected_old = min(
                        range(2),
                        key=lambda j: (
                            tasks[j]["priority"],
                            tasks[j]["test_cost"],
                            tasks[j]["pos"][1],
                            tasks[j]["pos"][0],
                            0,
                            j,
                        ),
                    )
                    expected_new = min(
                        range(2),
                        key=lambda j: (
                            tasks[j]["priority"],
                            namespace["_last_chance_rank"](farm, tasks[j]),
                            tasks[j]["test_cost"],
                            tasks[j]["pos"][1],
                            tasks[j]["pos"][0],
                            0,
                            j,
                        ),
                    )
                    assert old_trace[0][1] == expected_old
                    assert new_trace[0][1] == expected_new
                    assert tasks[new_trace[0][1]]["priority"] == min(
                        task["priority"] for task in tasks
                    )


def test_activation_and_causal_terminal_counter_follow_accepted_full_trace() -> None:
    namespace = _namespace()
    namespace["reset_rescue_metrics"]()
    namespace["_task_cost"] = lambda farm, pos, inv, shed, task: task["test_cost"]
    namespace["_task_action"] = lambda farm, pos, inv, shed, task: task["action"]
    farm = _farm()
    farm["tiles"][0][0] = _plant(0)
    farm["tiles"][1][1] = _animal()
    positions = [(1, 1), (0, 0)]
    tasks = [_task("WATER", (0, 0), cost=0), _task("FEED", (1, 1), cost=5)]

    result = namespace["_safe_allocation_actions"](
        farm, {"seeds": {}}, positions, [{}, {}], {"WHEAT": 1}, tasks
    )
    actions, trace, formal_actions = result[:3]
    assert result[7] is True
    namespace["_record_last_chance_actions"](
        {"player": 0, "day": 3},
        farm,
        positions,
        tasks,
        trace,
        actions,
        formal_actions,
        result[4],
        result[5],
        result[7],
    )

    assert namespace["rescue_metrics"]() == {
        "eligible_opportunity": 1,
        "rank_tiebreak_activated": 1,
        "action_changed_vs_old_comparator_on_same_state": 1,
        "last_chance_action_emitted_on_exact_target": 1,
        "tiebreak_to_exact_target_action_emitted": 1,
        "formal_fallback_due_assignment_set_mismatch": 0,
        "next_day_weed_or_escape_outcome": 0,
    }


def test_eligible_counts_formal_decision_even_when_old_already_selects_rank_zero() -> None:
    namespace = _namespace()
    namespace["reset_rescue_metrics"]()
    namespace["_task_cost"] = lambda farm, pos, inv, shed, task: task["test_cost"]
    namespace["_real_task_path_cost"] = lambda farm, pos, inv, shed, task: 0
    namespace["_task_action"] = lambda farm, pos, inv, shed, task: ["EAST"]
    farm = _farm()
    farm["tiles"][0][0] = _plant(1, False)
    farm["tiles"][0][1] = _plant(0, False)
    tasks = [_task("WATER", (0, 0), cost=0), _task("WATER", (1, 0), cost=5)]

    result = namespace["_safe_allocation_actions"](farm, {"seeds": {}}, [(0, 0)], [{}], {}, tasks)

    assert result[4][0][1] == result[5][0][1] == 0
    assert result[4][0][8] is True
    assert result[6] is False
    assert result[7] is True
    metrics = namespace["rescue_metrics"]()
    assert metrics["eligible_opportunity"] == 1
    assert metrics["rank_tiebreak_activated"] == 0
    assert metrics["action_changed_vs_old_comparator_on_same_state"] == 0


def test_changed_assignment_with_identical_final_vector_is_not_action_change() -> None:
    namespace = _namespace()
    namespace["reset_rescue_metrics"]()
    namespace["_task_cost"] = lambda farm, pos, inv, shed, task: task["test_cost"]
    namespace["_real_task_path_cost"] = lambda farm, pos, inv, shed, task: 0
    namespace["_task_action"] = lambda farm, pos, inv, shed, task: ["EAST"]
    farm = _farm()
    farm["tiles"][0][0] = _plant(0, False)
    farm["tiles"][1][1] = _plant(1, False)
    tasks = [_task("WATER", (0, 0), cost=0), _task("WATER", (1, 1), cost=5)]

    result = namespace["_safe_allocation_actions"](
        farm, {"seeds": {}}, [(0, 0), (1, 0)], [{}, {}], {}, tasks
    )

    assert result[4] != result[5]
    assert result[2] == result[3] == [["EAST"], ["EAST"]]
    assert result[6] is True
    assert result[7] is True
    metrics = namespace["rescue_metrics"]()
    assert metrics["eligible_opportunity"] == 1
    assert metrics["rank_tiebreak_activated"] == 1
    assert metrics["action_changed_vs_old_comparator_on_same_state"] == 0


def test_causal_token_survives_hours_until_original_unit_terminal_action() -> None:
    namespace = _namespace()
    namespace["reset_rescue_metrics"]()
    namespace["_task_cost"] = lambda farm, pos, inv, shed, task: task["test_cost"]
    namespace["_real_task_path_cost"] = lambda farm, pos, inv, shed, task: 0
    namespace["_task_action"] = lambda farm, pos, inv, shed, task: ["EAST"]
    farm = _farm()
    farm["tiles"][0][0] = _plant(0, False)
    farm["tiles"][0][2] = _plant(1, False)
    farm["tiles"][0][3] = _plant(1, False)
    tasks = [
        _task("WATER", (0, 0), cost=0),
        _task("WATER", (2, 0), cost=5),
        _task("WATER", (3, 0), cost=6),
    ]
    positions = [(0, 0), (4, 0)]
    h17 = {"player": 0, "day": 6, "hour": 17}
    namespace["_observe_last_chance_outcomes"](h17, farm)
    result = namespace["_safe_allocation_actions"](
        farm, {"seeds": {}}, positions, [{}, {}], {}, tasks[:2]
    )
    namespace["_record_last_chance_actions"](
        h17,
        farm,
        positions,
        tasks[:2],
        result[1],
        result[0],
        result[2],
        result[4],
        result[5],
        result[7],
    )
    assert result[2] == result[3] == [["EAST"], ["EAST"]]
    assert namespace["rescue_metrics"]()["rank_tiebreak_activated"] == 1
    assert namespace["rescue_metrics"]()["action_changed_vs_old_comparator_on_same_state"] == 0

    same_trace = (_trace_step(0, 1, 0), _trace_step(1, 0, 1))
    h18 = {"player": 0, "day": 6, "hour": 18}
    namespace["_observe_last_chance_outcomes"](h18, farm)
    namespace["_record_last_chance_actions"](
        h18,
        farm,
        [(1, 0), (4, 0)],
        tasks[:2],
        same_trace,
        [["EAST"], ["PASS"]],
        [["WEST"], ["PASS"]],
        same_trace,
        same_trace,
        True,
    )

    h19 = {"player": 0, "day": 6, "hour": 19}
    namespace["_observe_last_chance_outcomes"](h19, farm)
    other_terminal_trace = (_trace_step(0, 1, 0), _trace_step(1, 2, 0))
    namespace["_record_last_chance_actions"](
        h19,
        farm,
        [(1, 0), (3, 0)],
        tasks,
        other_terminal_trace,
        [["EAST"], ["WATER"]],
        [["EAST"], ["WATER"]],
        other_terminal_trace,
        other_terminal_trace,
        True,
    )
    assert namespace["rescue_metrics"]()["tiebreak_to_exact_target_action_emitted"] == 0

    h20 = {"player": 0, "day": 6, "hour": 20}
    namespace["_observe_last_chance_outcomes"](h20, farm)
    terminal_trace = (_trace_step(0, 1, 0),)
    namespace["_record_last_chance_actions"](
        h20,
        farm,
        [(2, 0), (3, 0)],
        tasks,
        terminal_trace,
        [["WATER"], ["PASS"]],
        [["WATER"], ["PASS"]],
        terminal_trace,
        terminal_trace,
        True,
    )
    metrics = namespace["rescue_metrics"]()
    assert metrics["last_chance_action_emitted_on_exact_target"] == 2
    assert metrics["tiebreak_to_exact_target_action_emitted"] == 1
    assert namespace["_LAST_CHANCE_CAUSAL_PENDING"] == {}


def test_causal_pending_lifecycle_clears_on_all_abandonment_boundaries() -> None:
    namespace = _namespace()
    farm = _farm()
    target = (2, 0)
    farm["tiles"][0][target[0]] = _plant(1, False)
    tasks = [_task("WATER", (0, 0)), _task("WATER", target)]
    formal_trace = (_trace_step(0, 0, 1, eligible=True), _trace_step(1, 1, 0))
    candidate_trace = (_trace_step(0, 1, 0, eligible=True), _trace_step(1, 0, 1))

    def seed(day: int = 5) -> None:
        namespace["reset_rescue_metrics"]()
        farm["tiles"][0][target[0]] = _plant(1, False)
        obs = {"player": 0, "day": day, "hour": 17}
        namespace["_observe_last_chance_outcomes"](obs, farm)
        namespace["_record_last_chance_actions"](
            obs,
            farm,
            [(0, 0), (4, 0)],
            tasks,
            candidate_trace,
            [["EAST"], ["EAST"]],
            [["EAST"], ["EAST"]],
            formal_trace,
            candidate_trace,
            True,
        )
        assert len(namespace["_LAST_CHANCE_CAUSAL_PENDING"]) == 1

    seed()
    namespace["reset_rescue_metrics"]()
    assert namespace["_LAST_CHANCE_CAUSAL_PENDING"] == {}

    seed()
    namespace["_record_last_chance_actions"](
        {"player": 0, "day": 5, "hour": 18},
        farm,
        [(1, 0), (4, 0)],
        tasks,
        candidate_trace,
        [["EAST"], ["EAST"]],
        [["EAST"], ["EAST"]],
        formal_trace,
        candidate_trace,
        False,
    )
    assert namespace["_LAST_CHANCE_CAUSAL_PENDING"] == {}

    seed()
    abandoned_trace = (_trace_step(0, 0, 1), _trace_step(1, 1, 0))
    namespace["_record_last_chance_actions"](
        {"player": 0, "day": 5, "hour": 18},
        farm,
        [(1, 0), (4, 0)],
        tasks,
        abandoned_trace,
        [["WEST"], ["EAST"]],
        [["WEST"], ["EAST"]],
        abandoned_trace,
        abandoned_trace,
        True,
    )
    assert namespace["_LAST_CHANCE_CAUSAL_PENDING"] == {}

    seed()
    namespace["_observe_last_chance_outcomes"]({"player": 1, "day": 5, "hour": 18}, farm)
    assert namespace["_LAST_CHANCE_CAUSAL_PENDING"] == {}

    seed()
    namespace["_observe_last_chance_outcomes"]({"player": 0, "day": 0, "hour": 0}, farm)
    assert namespace["_LAST_CHANCE_CAUSAL_PENDING"] == {}

    seed()
    namespace["_observe_last_chance_outcomes"]({"player": 0, "day": 6, "hour": 0}, farm)
    assert namespace["_LAST_CHANCE_CAUSAL_PENDING"] == {}

    seed()
    farm["tiles"][0][target[0]] = {"kind": "WEED"}
    namespace["_observe_last_chance_outcomes"]({"player": 0, "day": 5, "hour": 18}, farm)
    assert namespace["_LAST_CHANCE_CAUSAL_PENDING"] == {}


def test_scarce_sheep_wheat_assignment_set_change_falls_back_exactly() -> None:
    namespace = _namespace()
    namespace["reset_rescue_metrics"]()
    namespace["_task_cost"] = lambda farm, pos, inv, shed, task: task["costs"][pos[0]]
    namespace["_task_action"] = lambda farm, pos, inv, shed, task: [
        task["action"][0],
        str(task["id"]),
    ]
    farm = _farm()
    farm["tiles"][1][1] = _animal("SHEEP", 1, False)
    farm["tiles"][2][2] = _animal("COW", 0, False)
    tasks = [
        {
            "id": 0,
            "priority": 0,
            "pos": (0, 0),
            "action": ["PLACE", "SHEEP"],
            "need": "SHEEP",
            "costs": [0, 10],
        },
        {
            "id": 1,
            "priority": 0,
            "pos": (1, 1),
            "action": ["FEED"],
            "need": "WHEAT",
            "costs": [5, 5],
        },
        {
            "id": 2,
            "priority": 0,
            "pos": (2, 2),
            "action": ["FEED"],
            "need": "WHEAT",
            "costs": [1, 1],
        },
    ]
    result = namespace["_safe_allocation_actions"](
        farm,
        {"seeds": {}},
        [(0, 0), (1, 0)],
        [{}, {}],
        {"SHEEP": 1, "WHEAT": 1},
        tasks,
    )
    actions, trace, formal_actions, candidate_actions, formal_trace, candidate_trace = result[:6]

    assert {step[1] for step in formal_trace} == {0, 2}
    assert {step[1] for step in candidate_trace} == {1, 2}
    assert candidate_actions != formal_actions
    assert result[7] is False
    assert actions == formal_actions
    assert trace == formal_trace
    metrics = namespace["rescue_metrics"]()
    assert metrics["formal_fallback_due_assignment_set_mismatch"] == 1
    assert metrics["rank_tiebreak_activated"] == 0
    assert metrics["action_changed_vs_old_comparator_on_same_state"] == 0


def test_same_task_set_harvest_terminal_swap_falls_back_exactly() -> None:
    namespace = _namespace()
    namespace["reset_rescue_metrics"]()
    namespace["_task_cost"] = lambda farm, pos, inv, shed, task: task["costs"][pos[0]]
    namespace["_task_action"] = lambda farm, pos, inv, shed, task: (
        list(task["action"]) if tuple(pos) == tuple(task["pos"]) else ["MOVE", str(task["id"])]
    )
    farm = _farm()
    farm["tiles"][1][0] = _plant(1, False)
    tasks = [
        {
            "id": 0,
            "priority": 0,
            "pos": (0, 0),
            "action": ["HARVEST"],
            "need": None,
            "costs": [0, 2],
        },
        {
            "id": 1,
            "priority": 0,
            "pos": (0, 1),
            "action": ["WATER"],
            "need": None,
            "costs": [1, 3],
        },
    ]
    result = namespace["_safe_allocation_actions"](
        farm, {"seeds": {}}, [(0, 0), (1, 0)], [{}, {}], {}, tasks
    )
    actions, trace, formal_actions, candidate_actions, formal_trace, candidate_trace = result[:6]

    assert {step[1] for step in formal_trace} == {step[1] for step in candidate_trace}
    assert formal_actions[0] == ["HARVEST"]
    assert candidate_actions[0] == ["MOVE", "1"]
    assert result[7] is False
    assert actions == formal_actions
    assert trace == formal_trace
    assert namespace["rescue_metrics"]()["formal_fallback_due_assignment_set_mismatch"] == 1


def test_locked_equal_manhattan_unreachable_swap_falls_back_exactly() -> None:
    namespace = _namespace()
    namespace["reset_rescue_metrics"]()
    farm = _farm()
    farm["tiles"][0][1] = "LOCKED"
    farm["tiles"][0][3] = "LOCKED"
    farm["tiles"][1][2] = "LOCKED"
    farm["tiles"][2][0] = _plant(1, False)
    tasks = [
        {
            "priority": 0,
            "pos": (1, 1),
            "action": ["HARVEST"],
            "need": None,
        },
        {
            "priority": 0,
            "pos": (0, 2),
            "action": ["WATER"],
            "need": None,
        },
    ]
    result = namespace["_safe_allocation_actions"](
        farm, {"seeds": {}}, [(0, 0), (2, 0)], [{}, {}], {}, tasks
    )
    actions, trace, formal_actions, candidate_actions, formal_trace, candidate_trace = result[:6]
    formal_paths = {step[1]: step[5] for step in formal_trace}
    candidate_paths = {step[1]: step[5] for step in candidate_trace}

    formal_costs = {step[1]: step[4] for step in formal_trace}
    candidate_costs = {step[1]: step[4] for step in candidate_trace}
    assert candidate_costs[0] == formal_costs[0] == 2
    assert all(candidate_costs[j] <= formal_costs[j] for j in formal_costs)
    assert formal_paths[0] == 2
    assert candidate_paths[0] == 10000
    assert candidate_actions[1] == ["PASS"]
    assert result[7] is False
    assert actions == formal_actions
    assert trace == formal_trace
    assert namespace["rescue_metrics"]()["formal_fallback_due_assignment_set_mismatch"] == 1


def test_shared_shed_pickup_demand_cannot_increase_on_same_task_set() -> None:
    namespace = _namespace()
    namespace["reset_rescue_metrics"]()
    namespace["_task_cost"] = lambda farm, pos, inv, shed, task: 0
    farm = _farm()
    farm["tiles"][4][4] = _animal("SHEEP", 1, False)
    tasks = [
        {
            "priority": 0,
            "pos": (0, 0),
            "action": ["HARVEST"],
            "need": None,
        },
        {
            "priority": 0,
            "pos": (4, 4),
            "action": ["FEED"],
            "need": "WHEAT",
        },
    ]
    result = namespace["_safe_allocation_actions"](
        farm,
        {"seeds": {}},
        [(4, 4), (0, 0)],
        [{}, {"WHEAT": 1}],
        {"WHEAT": 4},
        tasks,
    )
    actions, trace, formal_actions, _, formal_trace, candidate_trace = result[:6]
    candidate_trace_by_task = {item[1]: item for item in candidate_trace}

    assert {step[1] for step in formal_trace} == {step[1] for step in candidate_trace}
    assert all(candidate_trace_by_task[step[1]][5] <= step[5] for step in formal_trace)
    assert sum(step[7] for step in formal_trace if step[6] == "WHEAT") == 0
    assert sum(step[7] for step in candidate_trace if step[6] == "WHEAT") == 4
    assert result[7] is False
    assert actions == formal_actions
    assert trace == formal_trace
    assert namespace["rescue_metrics"]()["formal_fallback_due_assignment_set_mismatch"] == 1


def test_post_seed_nonpass_task_identity_is_preserved() -> None:
    namespace = _namespace()
    namespace["reset_rescue_metrics"]()
    namespace["_task_cost"] = lambda farm, pos, inv, shed, task: task["costs"][pos[0]]
    namespace["_task_action"] = lambda farm, pos, inv, shed, task: list(task["action"])
    farm = _farm()
    farm["tiles"][2][0] = _plant(1, False)
    tasks = [
        {
            "priority": 0,
            "pos": (0, 0),
            "action": ["PLANT", "WHEAT"],
            "need": None,
            "costs": [0, 10, 0],
        },
        {
            "priority": 0,
            "pos": (1, 0),
            "action": ["PLANT", "WHEAT"],
            "need": None,
            "costs": [10, 0, 10],
        },
        {
            "priority": 0,
            "pos": (0, 2),
            "action": ["WATER"],
            "need": None,
            "costs": [1, 9, 9],
        },
    ]
    result = namespace["_safe_allocation_actions"](
        farm,
        {"seeds": {"WHEAT": 1}},
        [(0, 0), (1, 0), (2, 0)],
        [{}, {}, {}],
        {},
        tasks,
    )
    actions, trace, formal_actions, candidate_actions, formal_trace, candidate_trace = result[:6]
    formal_units = {step[1]: step[0] for step in formal_trace}
    candidate_units = {step[1]: step[0] for step in candidate_trace}

    assert {step[1] for step in formal_trace} == {step[1] for step in candidate_trace}
    assert formal_actions[formal_units[0]] == ["PLANT", "WHEAT"]
    assert candidate_actions[candidate_units[0]] == ["PASS"]
    assert result[7] is False
    assert actions == formal_actions
    assert trace == formal_trace


def test_exact_terminal_action_and_next_day_outcome_are_observed_then_reset() -> None:
    namespace = _namespace()
    namespace["reset_rescue_metrics"]()
    farm = _farm(farmer=(4, 4))
    farm["tiles"][4][4] = _animal()
    private = {"inventories": [{"WHEAT": 1}], "shed": {}, "seeds": {}}

    actions = namespace["_unit_actions"](
        {"player": 1, "day": 7, "hour": 20, "market": {"prices": {}}},
        farm,
        private,
        [(4, 4)],
        {},
    )
    assert actions == [["FEED"]]
    metrics = namespace["rescue_metrics"]()
    assert metrics["eligible_opportunity"] == 0
    assert metrics["rank_tiebreak_activated"] == 0
    assert metrics["last_chance_action_emitted_on_exact_target"] == 1

    farm["tiles"][4][4] = {"kind": "PASTURE"}
    namespace["_unit_actions"](
        {"player": 1, "day": 8, "hour": 0, "market": {"prices": {}}},
        farm,
        private,
        [(4, 4)],
        {},
    )
    assert namespace["rescue_metrics"]()["next_day_weed_or_escape_outcome"] == 1

    namespace["reset_rescue_metrics"]()
    assert namespace["rescue_metrics"]() == {name: 0 for name in COUNTERS}
    assert namespace["_LAST_CHANCE_PENDING"] == {}
    assert namespace["_LAST_CHANCE_CAUSAL_PENDING"] == {}
    assert namespace["_LAST_CHANCE_CAUSAL_CONTEXT"] == {}


def test_old_and_new_actions_match_when_no_tiebreak_activation() -> None:
    formal_namespace = _namespace(FORMAL.read_text(encoding="utf-8"))
    built_namespace = _namespace()
    farm = _farm(farmer=(4, 4))
    farm["tiles"][4][4] = _animal(counter=0)
    private = {"inventories": [{"WHEAT": 1}], "shed": {}, "seeds": {}}
    observation = {"player": 0, "day": 2, "hour": 2, "market": {"prices": {}}}

    formal_action = formal_namespace["_unit_actions"](observation, farm, private, [(4, 4)], {})
    built_action = built_namespace["_unit_actions"](observation, farm, private, [(4, 4)], {})

    assert built_action == formal_action
    assert built_namespace["rescue_metrics"]()["rank_tiebreak_activated"] == 0


def test_agent_schema_and_raw_counter_values_are_runner_compatible() -> None:
    namespace = _namespace()
    namespace["reset_rescue_metrics"]()
    action = namespace["agent"]({"player": 1, "farms": []})

    assert action == {"farmer": ["PASS"], "hands": [], "market": []}
    metrics = namespace["rescue_metrics"]()
    assert set(metrics) == COUNTERS
    assert all(isinstance(value, int) and value >= 0 for value in metrics.values())


def test_historical_replay_runtime_and_action_diff_report_passes() -> None:
    report = json.loads(RUNTIME.read_text(encoding="utf-8"))

    assert report["source"] == SNAPSHOT.as_posix()
    assert report["source_sha256"] == _sha256(SNAPSHOT)
    assert report["replay"] == REPLAY.as_posix()
    assert report["replay_sha256"] == _sha256(REPLAY)
    assert report["calls"] == report["action_comparison_calls"] == 720
    assert report["invalid_outputs"] == 0
    assert report["p95_ms"] <= 8.0
    assert report["p99_ms"] <= 15.0
    assert report["max_ms"] <= 50.0
    assert report["priority_inversions"] == 0
    assert set(report["instrumentation"]) == COUNTERS
    assert report["gate_result"] == "PASS"
