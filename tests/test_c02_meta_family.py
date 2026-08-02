from __future__ import annotations

import ast
import hashlib
import json
import runpy
from collections import Counter
from pathlib import Path

import pytest

from kaggriculture_lab.candidates.c02_meta_family import (
    _CORE_SEQUENCE_B1,
    _CORE_SEQUENCE_V0,
    _CROP_MIX_A1,
    _CROP_MIX_V0,
    _FEED_STOCK_D2,
    _FEED_STOCK_V0,
    _FIXED_CROPS_E1,
    _FIXED_CROPS_V0,
    _HERD_TARGETS_B1,
    _HERD_TARGETS_V0,
    _LAND_C1,
    _LAND_V0,
    _ROLE_DAY_E1,
    _ROLE_DAY_V0,
    _SELL_RETURN_D1,
    _SELL_RETURN_V0,
    SOURCE_CONTROL_SHA256,
    VALID_MODES,
    build_c02_meta_family,
)
from kaggriculture_lab.evaluation.runtime import benchmark

SNAPSHOT_DIR = Path("experiments/source_snapshots/fa04_c02_meta")
REPLAY = Path("artifacts/submission_replays/episode-89143277-replay.json")
ATTRIBUTION = (
    '# Derived from the public Kaggle notebook "Scenario-Aware Economic Policy"',
    "# by Pilkwang Kim: https://www.kaggle.com/code/pilkwang/",
    "# kaggriculture-scenario-aware-economic-policy",
)
HERD_TIMING_CONSTANTS = (
    "CORE_HERD",
    "MID_HERD",
    "TARGET_HERD",
    "HERD_EXPANSION_DAY",
    "HERD_FINAL_DAY",
    "ANIMAL_PURCHASE_LAST_DAY",
    "ANIMAL_SLOTS",
    "MAX_HANDS",
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _payload(mode: str) -> bytes:
    return (SNAPSHOT_DIR / f"{mode}.py").read_bytes()


def _source(mode: str) -> str:
    return _payload(mode).decode("utf-8")


def _namespace(mode: str) -> dict[str, object]:
    return runpy.run_path(str(SNAPSHOT_DIR / f"{mode}.py"))


def _marker(marker: str, source: str) -> str:
    newline = "\r\n" if "\r\n" in source else "\n"
    return marker.replace("\n", newline)


def _normalize_to_v0(source: str, mode: str) -> str:
    pairs = {
        "V0": (),
        "A1": ((_CROP_MIX_A1, _CROP_MIX_V0),),
        "B1": (
            (_HERD_TARGETS_B1, _HERD_TARGETS_V0),
            (_CORE_SEQUENCE_B1, _CORE_SEQUENCE_V0),
        ),
        "C1": ((_LAND_C1, _LAND_V0),),
        "D1": ((_SELL_RETURN_D1, _SELL_RETURN_V0),),
        "D2": ((_FEED_STOCK_D2, _FEED_STOCK_V0),),
        "E1": (
            (_ROLE_DAY_E1, _ROLE_DAY_V0),
            (_FIXED_CROPS_E1, _FIXED_CROPS_V0),
        ),
    }[mode]
    normalized = source
    for changed, control in pairs:
        changed = _marker(changed, normalized)
        control = _marker(control, normalized)
        assert normalized.count(changed) == 1
        normalized = normalized.replace(changed, control)
    return normalized


def _function_source(source: str, name: str) -> str:
    node = next(
        item
        for item in ast.parse(source).body
        if isinstance(item, ast.FunctionDef) and item.name == name
    )
    assert node.end_lineno is not None
    return "".join(source.splitlines(keepends=True)[node.lineno - 1 : node.end_lineno])


def _farm(*, quadrants: tuple[str, ...] = ("NW",)) -> dict[str, object]:
    return {
        "money": 100_000,
        "farmer": [0, 0],
        "hands": [],
        "hires_today": 0,
        "unlocked_quadrants": list(quadrants),
        "tiles": [[None for _ in range(10)] for _ in range(10)],
    }


def _herd_observation(*, day: int, milk: int, wool: int) -> tuple[dict, dict, dict]:
    own = _farm()
    opponent = _farm()
    private = {"shed": {}, "seeds": {}, "inventories": []}
    observation = {
        "player": 0,
        "day": day,
        "hour": 0,
        "farms": [own, opponent],
        "private": private,
        "market": {"prices": {"MILK": milk, "WOOL": wool}},
        "town": {"unlocked_shops": []},
    }
    return observation, own, private


def _assert_action_schema(action: object, observation: dict) -> None:
    assert isinstance(action, dict)
    assert set(action) == {"farmer", "hands", "market"}
    assert isinstance(action["farmer"], list) and action["farmer"]
    assert isinstance(action["farmer"][0], str)
    assert isinstance(action["hands"], list)
    player = int(observation.get("player", 0) or 0)
    farms = observation.get("farms", []) or []
    expected_hands = len(farms[player].get("hands", []) or []) if player < len(farms) else 0
    assert len(action["hands"]) == expected_hands
    assert all(isinstance(unit, list) and unit and isinstance(unit[0], str) for unit in action["hands"])
    assert isinstance(action["market"], list)
    assert len(action["market"]) <= 10
    assert all(isinstance(order, list) and order and isinstance(order[0], str) for order in action["market"])


def test_source_control_provenance_and_snapshots_are_exact() -> None:
    control = _payload("V0")
    assert VALID_MODES == ("V0", "A1", "B1", "C1", "D1", "D2", "E1")
    assert _sha256(control) == SOURCE_CONTROL_SHA256
    assert control.count(b"\r\n") == control.count(b"\n") > 0
    assert control.endswith(b"\r\n")

    control_lines = _source("V0").splitlines()
    assert tuple(control_lines[:3]) == ATTRIBUTION
    for mode in VALID_MODES:
        candidate = _payload(mode)
        assert build_c02_meta_family(control, mode) == candidate
        assert tuple(candidate.decode("utf-8").splitlines()[:3]) == ATTRIBUTION
        compile(candidate, f"{mode}.py", "exec")
    assert len({_sha256(_payload(mode)) for mode in VALID_MODES}) == 7


@pytest.mark.parametrize("mode", VALID_MODES)
def test_byte_allowlist_and_function_diff_are_exact(mode: str) -> None:
    control = _source("V0")
    candidate = _source(mode)
    assert _normalize_to_v0(candidate, mode) == control

    changed_functions = {
        "B1": {"_herd_targets", "_role_plan"},
        "D1": {"_sell_quantity"},
        "E1": {"_role_plan"},
    }.get(mode, set())
    for node in ast.parse(control).body:
        if isinstance(node, ast.FunctionDef) and node.name not in changed_functions:
            assert _function_source(candidate, node.name) == _function_source(control, node.name)


def test_a1_changes_only_the_three_fixed_wheat_counts() -> None:
    control = _namespace("V0")
    candidate = _namespace("A1")
    expected = {
        quadrant: dict(mix)
        for quadrant, mix in control["CROP_MIX"].items()
    }
    expected["NW"]["WHEAT"] = 2
    expected["NE"]["WHEAT"] = 0
    expected["SW"]["WHEAT"] = 0
    assert candidate["CROP_MIX"] == expected
    assert sum(candidate["CROP_MIX"][q]["WHEAT"] for q in ("NW", "NE", "SW")) == 2
    assert candidate["CROP_MIX"]["SE"] == control["CROP_MIX"]["SE"]
    assert _function_source(_source("A1"), "_market_actions") == _function_source(
        _source("V0"), "_market_actions"
    )


@pytest.mark.parametrize(
    ("milk", "wool", "expected"),
    ((1600, 1, {"COW": 3, "SHEEP": 1}), (1, 2000, {"COW": 1, "SHEEP": 3})),
)
def test_b1_keeps_both_core_lines_and_adapts_two_slots(
    milk: int, wool: int, expected: dict[str, int]
) -> None:
    namespace = _namespace("B1")
    observation, farm, private = _herd_observation(day=0, milk=milk, wool=wool)
    targets = namespace["_herd_targets"](observation, farm, private, 4)
    assert targets == expected
    assert targets["COW"] >= 1 and targets["SHEEP"] >= 1
    assert sum(targets.values()) == 4

    roles = namespace["_role_plan"](observation, farm)
    core = Counter(item for kind, item in roles.values() if kind == "ANIMAL")
    assert core == Counter(expected)
    assert core["COW"] >= 1 and core["SHEEP"] >= 1


@pytest.mark.parametrize("mode", VALID_MODES)
def test_hand_herd_capacity_and_stage_timing_are_unchanged(mode: str) -> None:
    control = _namespace("V0")
    candidate = _namespace(mode)
    for name in HERD_TIMING_CONSTANTS:
        assert candidate[name] == control[name]
    assert _function_source(_source(mode), "_target_hands") == _function_source(
        _source("V0"), "_target_hands"
    )

    for day, expected_total in ((0, 4), (8, 8), (12, 12)):
        observation, farm, private = _herd_observation(day=day, milk=1600, wool=1)
        targets = candidate["_herd_targets"](observation, farm, private, 12)
        assert sum(targets.values()) == expected_total


def test_c1_changes_only_land_open_days() -> None:
    control = _namespace("V0")
    candidate = _namespace("C1")
    assert control["LAND_OPEN_DAYS"] == (5, 9)
    assert candidate["LAND_OPEN_DAYS"] == (8, 9)


def test_d1_caps_only_nonterminal_wheat_sell_quantity() -> None:
    control = _namespace("V0")
    candidate = _namespace("D1")
    observation = {"market": {"params": {}}, "town": {"unlocked_shops": []}}

    assert control["_sell_quantity"]("WHEAT", 20, 10_000, 28, 0.5, observation) == 20
    assert candidate["_sell_quantity"]("WHEAT", 20, 10_000, 28, 0.5, observation) == 4
    assert candidate["_sell_quantity"]("WHEAT", 3, 10_000, 28, 0.5, observation) == 3

    assert candidate["_sell_quantity"]("WHEAT", 20, 10_000, 29, 0.5, observation) == 20
    assert candidate["_sell_quantity"]("MELON", 20, 10_000, 28, 0.5, observation) == control[
        "_sell_quantity"
    ]("MELON", 20, 10_000, 28, 0.5, observation)
    assert _function_source(_source("D1"), "_market_actions") == _function_source(
        _source("V0"), "_market_actions"
    )


def test_d2_changes_only_feed_stock_days() -> None:
    control = _namespace("V0")
    candidate = _namespace("D2")
    assert control["FEED_STOCK_DAYS"] == 3
    assert candidate["FEED_STOCK_DAYS"] == 1
    assert _function_source(_source("D2"), "_market_actions") == _function_source(
        _source("V0"), "_market_actions"
    )


def _crop_role_counts(namespace: dict[str, object], observation: dict) -> dict[str, Counter]:
    roles = namespace["_role_plan"](observation, observation["farms"][0])
    counts: dict[str, Counter] = {}
    for position, (kind, item) in roles.items():
        if kind != "CROP":
            continue
        quadrant = namespace["_quadrant_of"](position, 10)
        counts.setdefault(quadrant, Counter())[item] += 1
    return counts


def test_e1_keeps_day_four_roles_and_reduces_day_five_fixed_wheat() -> None:
    control = _namespace("V0")
    candidate = _namespace("E1")
    assert candidate["CROP_MIX"] == control["CROP_MIX"]

    for day in (0, 4):
        observation, _, _ = _herd_observation(day=day, milk=160, wool=200)
        observation["farms"][0]["unlocked_quadrants"] = ["NW", "NE", "SW", "SE"]
        assert candidate["_role_plan"](
            observation, observation["farms"][0]
        ) == control["_role_plan"](observation, observation["farms"][0])

    observation, _, _ = _herd_observation(day=5, milk=160, wool=200)
    observation["farms"][0]["unlocked_quadrants"] = ["NW", "NE", "SW", "SE"]
    control_counts = _crop_role_counts(control, observation)
    candidate_counts = _crop_role_counts(candidate, observation)
    assert {q: candidate_counts[q]["WHEAT"] for q in ("NW", "NE", "SW", "SE")} == {
        "NW": 2,
        "NE": 0,
        "SW": 0,
        "SE": 0,
    }
    assert sum(candidate_counts[q]["STRAWBERRY"] for q in candidate_counts) == sum(
        control_counts[q]["STRAWBERRY"] for q in control_counts
    ) + 15


def test_e1_actual_crop_and_weed_precede_the_new_role() -> None:
    namespace = _namespace("E1")
    control = _namespace("V0")
    observation, farm, private = _herd_observation(day=5, milk=160, wool=200)
    farm["unlocked_quadrants"] = ["NW", "NE", "SW", "SE"]
    private["seeds"] = {"STRAWBERRY": 1}
    candidate_roles = namespace["_role_plan"](observation, farm)
    control_roles = control["_role_plan"](observation, farm)
    target = next(
        position
        for position, role in candidate_roles.items()
        if role == ("CROP", "STRAWBERRY")
        and control_roles.get(position) == ("CROP", "WHEAT")
    )
    x, y = target

    farm["tiles"][y][x] = {
        "kind": "PLANT",
        "crop": "WHEAT",
        "planted_day": 0,
        "yield_units": 6,
        "watered_today": True,
        "consecutive_unwatered": 0,
    }
    jobs = namespace["_field_jobs"](observation, farm, private, candidate_roles, False)
    assert any(job["target"] == target and job["action"] == ["HARVEST"] for job in jobs)

    farm["tiles"][y][x] = {"kind": "WEED"}
    jobs = namespace["_field_jobs"](observation, farm, private, candidate_roles, False)
    assert any(job["target"] == target and job["action"] == ["DIG"] for job in jobs)

    farm["tiles"][y][x] = None
    jobs = namespace["_field_jobs"](observation, farm, private, candidate_roles, False)
    assert any(
        job["target"] == target and job["action"] == ["PLANT", "STRAWBERRY"]
        for job in jobs
    )


@pytest.mark.parametrize("mode", VALID_MODES)
def test_all_720_replay_actions_have_valid_shape_for_both_players(mode: str) -> None:
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    agent = _namespace(mode)["agent"]
    for player in (0, 1):
        observations = [state[player]["observation"] for state in replay["steps"]]
        assert len(observations) == 720
        for observation in observations:
            _assert_action_schema(agent(observation), observation)


@pytest.mark.parametrize("mode", VALID_MODES)
@pytest.mark.parametrize("player", (0, 1))
def test_720_replay_runtime_for_both_players(mode: str, player: int) -> None:
    report = benchmark(SNAPSHOT_DIR / f"{mode}.py", REPLAY, player)
    assert report["calls"] == 720
    assert report["invalid_outputs"] == 0
    assert report["p95_ms"] < 20
    assert report["p99_ms"] < 30
    assert report["max_ms"] < 100
