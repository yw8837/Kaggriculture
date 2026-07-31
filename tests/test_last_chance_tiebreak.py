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
    "next_day_weed_or_escape_outcome",
}
ADDED_FUNCTIONS = {
    "rescue_metrics",
    "reset_rescue_metrics",
    "_last_chance_rank",
    "_last_chance_choices",
    "_old_comparator_actions",
    "_observe_last_chance_outcomes",
    "_record_last_chance_action",
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
    choice_source = ast.unparse(built_functions["_last_chance_choices"])
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
    choose = namespace["_last_chance_choices"]

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
                    new, old, _, activated = choose(farm, [(0, 0)], [{}], {}, tasks, {0}, {0, 1})
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
                    assert old[2] == expected_old
                    assert new[2] == expected_new
                    assert tasks[new[2]]["priority"] == min(task["priority"] for task in tasks)
                    if activated:
                        assert tasks[new[2]]["priority"] == tasks[old[2]]["priority"]
                        assert namespace["_last_chance_rank"](farm, tasks[new[2]]) == 0
                        assert namespace["_last_chance_rank"](farm, tasks[old[2]]) == 1


def test_activation_counts_actual_displacement_not_presence_or_travel_assignment() -> None:
    namespace = _namespace()
    namespace["reset_rescue_metrics"]()
    farm = _farm(farmer=(0, 0))
    farm["tiles"][4][4] = _animal()
    private = {"inventories": [{"WHEAT": 1}], "shed": {}, "seeds": {}}
    observation = {"player": 0, "day": 3, "hour": 0, "market": {"prices": {}}}

    action = namespace["_unit_actions"](observation, farm, private, [(0, 0), (4, 4)], {})[0]

    assert action not in (["BUILD_PASTURE"], ["FEED"])
    assert namespace["rescue_metrics"]() == {
        "eligible_opportunity": 1,
        "rank_tiebreak_activated": 1,
        "action_changed_vs_old_comparator_on_same_state": 1,
        "last_chance_action_emitted_on_exact_target": 0,
        "next_day_weed_or_escape_outcome": 0,
    }


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
