from __future__ import annotations

import ast
import hashlib
import runpy
from pathlib import Path

import pytest

from kaggriculture_lab.candidates.meta_expansion import (
    FORMAL_PARENT_SHA256,
    VALID_MODES,
    build_meta_expansion,
)
from kaggriculture_lab.evaluation.runtime import benchmark

FORMAL = Path("artifacts/candidates/final_day_labor/main.py")
SNAPSHOT_DIR = Path("experiments/source_snapshots/fa03_meta_expansion")
REPLAY = Path("artifacts/submission_replays/episode-89143277-replay.json")

NORMAL_HIRE = '        missing = max(0, 10 - len(farm.get("hands", []) or []))\n'
META_HIRE = '        missing = max(0, 12 - len(farm.get("hands", []) or []))\n'
FORMAL_SLOT_TAIL = """            (h + 4, h - 1),
            (h, h - 2),
"""
BALANCED_SLOT_TAIL = """            (h + 4, h - 1),
            (h, h - 2),
            (h + 1, h - 2),
"""
FORMAL_MAPPING = '    return "SHEEP" if index in (1, 2) else "COW"\n'
BALANCED_MAPPING = '    return "SHEEP" if index in (1, 2, 7, 8, 9) else "COW"\n'
FORMAL_TARGET = '{"COW": 7, "SHEEP": 2}'
BALANCED_TARGET = '{"COW": 5, "SHEEP": 5}'


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _function_source(source: str, name: str) -> str:
    tree = ast.parse(source)
    node = next(
        item
        for item in tree.body
        if isinstance(item, ast.FunctionDef) and item.name == name
    )
    assert node.end_lineno is not None
    return "".join(source.splitlines(keepends=True)[node.lineno - 1 : node.end_lineno])


def _terminal_branch(source: str) -> str:
    tree = ast.parse(_function_source(source, "_market_actions"))
    function = tree.body[0]
    assert isinstance(function, ast.FunctionDef)
    branch = next(
        node
        for node in function.body
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and ast.unparse(node.test) == "day >= 29"
    )
    return ast.dump(branch, include_attributes=False)


def _namespace(mode: str) -> dict[str, object]:
    return runpy.run_path(str(SNAPSHOT_DIR / f"{mode}.py"))


def _normalize_to_formal(source: str, mode: str) -> str:
    normalized = source
    if mode in {"M1", "M2"}:
        assert normalized.count(META_HIRE) == 1
        prefix, suffix = normalized.rsplit(META_HIRE, 1)
        normalized = prefix + NORMAL_HIRE + suffix
    if mode in {"M1", "M3"}:
        assert normalized.count(BALANCED_SLOT_TAIL) == 1
        assert normalized.count(BALANCED_MAPPING) == 1
        assert normalized.count(BALANCED_TARGET) == 2
        normalized = normalized.replace(BALANCED_SLOT_TAIL, FORMAL_SLOT_TAIL)
        normalized = normalized.replace(BALANCED_MAPPING, FORMAL_MAPPING)
        normalized = normalized.replace(BALANCED_TARGET, FORMAL_TARGET)
    return normalized


def _farm(*, hands: int) -> dict[str, object]:
    return {
        "money": 100_000,
        "farmer": [0, 0],
        "hands": [[0, 0] for _ in range(hands)],
        "hires_today": 0,
        "unlocked_quadrants": ["NW", "NE", "SW"],
        "tiles": [[None for _ in range(10)] for _ in range(10)],
    }


def test_parent_snapshots_and_modes_are_exact_and_deterministic() -> None:
    formal = FORMAL.read_text(encoding="utf-8")
    assert _sha256(FORMAL.read_bytes()) == FORMAL_PARENT_SHA256
    assert VALID_MODES == ("M1", "M2", "M3")

    snapshots = []
    for mode in VALID_MODES:
        built = build_meta_expansion(formal, mode)
        assert build_meta_expansion(formal, mode) == built
        assert (SNAPSHOT_DIR / f"{mode}.py").read_text(encoding="utf-8") == built
        snapshots.append(built.encode())
    assert len({_sha256(payload) for payload in snapshots}) == 3


@pytest.mark.parametrize("mode", VALID_MODES)
def test_byte_level_delta_allowlist_and_formal_function_preservation(mode: str) -> None:
    formal = FORMAL.read_text(encoding="utf-8")
    candidate = (SNAPSHOT_DIR / f"{mode}.py").read_text(encoding="utf-8")
    assert _normalize_to_formal(candidate, mode) == formal

    changed_functions = {"_market_actions"}
    if mode in {"M1", "M3"}:
        changed_functions |= {"_cow_slots", "_animal_for_slot"}
    for node in ast.parse(formal).body:
        if isinstance(node, ast.FunctionDef) and node.name not in changed_functions:
            assert _function_source(candidate, node.name) == _function_source(formal, node.name)

    assert _function_source(candidate, "_unit_actions") == _function_source(
        formal, "_unit_actions"
    )
    assert _function_source(candidate, "_crop_plan") == _function_source(
        formal, "_crop_plan"
    )
    assert _terminal_branch(candidate) == _terminal_branch(formal)


@pytest.mark.parametrize(
    ("mode", "expected_hires", "expected_slots", "expected_cows", "expected_sheep"),
    [
        ("M1", 2, 10, 5, 5),
        ("M2", 2, 9, 7, 2),
        ("M3", 0, 10, 5, 5),
    ],
)
def test_labor_and_herd_axes_are_exact(
    mode: str,
    expected_hires: int,
    expected_slots: int,
    expected_cows: int,
    expected_sheep: int,
) -> None:
    namespace = _namespace(mode)
    slots = namespace["_cow_slots"](10, True)
    animals = [namespace["_animal_for_slot"](slot, slots) for slot in slots]
    assert len(slots) == expected_slots
    assert animals.count("COW") == expected_cows
    assert animals.count("SHEEP") == expected_sheep

    core_slots = namespace["_cow_slots"](10, False)
    core_animals = [
        namespace["_animal_for_slot"](slot, core_slots) for slot in core_slots
    ]
    assert core_animals == ["COW", "SHEEP", "SHEEP"]

    orders = namespace["_market_actions"](
        {"day": 20, "hour": 0, "market": {"prices": {}}},
        _farm(hands=10),
        {"shed": {"COW": 7, "SHEEP": 5, "WHEAT": 100}, "seeds": {}},
        slots,
        {},
    )
    assert sum(order == ["HIRE"] for order in orders) == expected_hires


@pytest.mark.parametrize(
    ("mode", "expected_order"),
    [
        ("M1", ["BUY_ANIMAL", "SHEEP", 2]),
        ("M2", ["BUY_ANIMAL", "COW", 2]),
        ("M3", ["BUY_ANIMAL", "SHEEP", 2]),
    ],
)
def test_expanded_herd_target_is_the_only_purchase_axis(
    mode: str, expected_order: list[object]
) -> None:
    namespace = _namespace(mode)
    farm = _farm(hands=12)
    private = {"shed": {"COW": 5, "SHEEP": 2, "WHEAT": 100}, "seeds": {}}
    slots = namespace["_cow_slots"](10, True)
    orders = namespace["_market_actions"](
        {"day": 20, "hour": 5, "market": {"prices": {}}},
        farm,
        private,
        slots,
        {},
    )
    animal_orders = [order for order in orders if order[0] == "BUY_ANIMAL"]
    assert animal_orders == [expected_order]


@pytest.mark.parametrize("mode", VALID_MODES)
def test_generated_agent_compiles_and_returns_schema(mode: str) -> None:
    source = (SNAPSHOT_DIR / f"{mode}.py").read_bytes()
    compile(source, f"{mode}.py", "exec")
    action = _namespace(mode)["agent"]({"player": 0, "farms": []})
    assert action == {"farmer": ["PASS"], "hands": [], "market": []}


@pytest.mark.parametrize("mode", VALID_MODES)
def test_tracked_replay_runtime_and_outputs(mode: str) -> None:
    source = SNAPSHOT_DIR / f"{mode}.py"
    for player in (0, 1):
        report = benchmark(source, REPLAY, player)
        assert report["calls"] == 720
        assert report["invalid_outputs"] == 0
        assert report["p95_ms"] < 20
        assert report["p99_ms"] < 30
        assert report["max_ms"] < 100
