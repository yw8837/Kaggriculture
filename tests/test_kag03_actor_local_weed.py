from __future__ import annotations

import ast
import copy
import hashlib
import json
import runpy
from pathlib import Path

import pytest

from kaggriculture_lab.research.kag03_actor_local_weed import (
    CONTROL_SHA256,
    RUNTIME_MARKER,
    build_file,
    build_source,
    materialize_freeze,
    sha256_bytes,
    sha256_text,
)

CONTROL = Path("research/campaign_3000/06_candidates/snapshots/tetsu_v16.py")
_FORBIDDEN_RUNTIME_FIELDS = frozenset(
    {
        "step",
        "day",
        "hour",
        "seat",
        "seed",
        "episode",
        "replay",
        "team",
        "opponent",
    }
)
_ALLOWED_RUNTIME_FIELDS = frozenset({"player", "farms"})


class _ObservationBoundary(ast.NodeVisitor):
    """Collect literal observation fields read by the appended runtime only."""

    def __init__(self) -> None:
        self.aliases = {"obs"}
        self.fields: list[str] = []

    def _is_alias(self, node: ast.AST) -> bool:
        return isinstance(node, ast.Name) and node.id in self.aliases

    def _record(self, node: ast.AST) -> None:
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            self.fields.append("<dynamic>")
        else:
            self.fields.append(node.value)

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        if self._is_alias(node.value):
            self.aliases.update(
                target.id for target in node.targets if isinstance(target, ast.Name)
            )

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if self._is_alias(node.value):
            self._record(node.slice)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if self._is_alias(node.value) and node.attr != "get":
            self._record(ast.Constant(node.attr))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and self._is_alias(node.func.value)
        ):
            self._record(node.args[0] if node.args else ast.Constant(None))
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and node.args
            and self._is_alias(node.args[0])
        ):
            self._record(node.args[1] if len(node.args) > 1 else ast.Constant(None))
        self.generic_visit(node)


def _runtime_observation_fields(source: str) -> list[str]:
    runtime = source.split(RUNTIME_MARKER, maxsplit=1)[1]
    visitor = _ObservationBoundary()
    visitor.visit(ast.parse(runtime))
    return visitor.fields


def _flatten_ids(value: object) -> tuple[int, ...]:
    if isinstance(value, dict):
        return (id(value), *(item for child in value.values() for item in _flatten_ids(child)))
    if isinstance(value, list):
        return (id(value), *(item for child in value for item in _flatten_ids(child)))
    return ()


def _control_action() -> dict[str, object]:
    return {
        "farmer": ["PASS"],
        "hands": [["PLANT", "WHEAT"], ["PASS"]],
        "market": [["SELL", "WHEAT", 3], ["HIRE"]],
    }


def _farm(*, farmer_tile: object = None, hand_tiles: tuple[object, object] = (None, None)) -> dict[str, object]:
    tiles: list[list[object]] = [[farmer_tile, hand_tiles[0], hand_tiles[1]]]
    return {"farmer": [0, 0], "hands": [[1, 0], [2, 0]], "tiles": tiles}


def _observation(
    *,
    player: int = 0,
    own_farm: dict[str, object] | None = None,
    other_farm: dict[str, object] | None = None,
    **extra: object,
) -> dict[str, object]:
    own = own_farm or _farm()
    other = other_farm or _farm()
    farms = [own, other] if player == 0 else [other, own]
    result: dict[str, object] = {"player": player, "farms": farms}
    result.update(extra)
    return result


def _candidate_namespace(tmp_path: Path) -> tuple[dict[str, object], str]:
    source = build_source(CONTROL.read_text(encoding="utf-8"))
    generated = tmp_path / "kag03.py"
    generated.write_text(source, encoding="utf-8", newline="")
    return runpy.run_path(str(generated)), source


def _stub_control(namespace: dict[str, object], action: dict[str, object]) -> None:
    namespace["agent"].__globals__["_kag03_control_agent"] = lambda _obs: action


def _assert_control_immutable(control: dict[str, object], before: dict[str, object], ids: tuple[int, ...]) -> None:
    assert control == before
    assert _flatten_ids(control) == ids


def test_build_requires_exact_control_and_preserves_its_prefix(tmp_path: Path) -> None:
    control_bytes = CONTROL.read_bytes()
    control = control_bytes.decode("utf-8")
    assert sha256_bytes(control_bytes) == CONTROL_SHA256
    with pytest.raises(ValueError, match="exact pinned"):
        build_source(f"{control}\n# drift")

    generated = build_source(control)
    prefix, _ = generated.split(RUNTIME_MARKER, maxsplit=1)
    assert prefix == f"{control.replace(chr(10) + 'def agent(obs):', chr(10) + 'def _kag03_control_agent(obs):', 1)}\n\n"

    receipt = build_file(CONTROL, tmp_path / "main.py")
    assert receipt["control_sha256"] == CONTROL_SHA256
    assert receipt["candidate_sha256"] == sha256_bytes((tmp_path / "main.py").read_bytes())


def test_runtime_reads_only_own_farm_locator_and_no_forbidden_trigger() -> None:
    source = build_source(CONTROL.read_text(encoding="utf-8"))
    fields = _runtime_observation_fields(source)
    assert set(fields) <= _ALLOWED_RUNTIME_FIELDS
    assert not (_FORBIDDEN_RUNTIME_FIELDS & set(fields))
    assert "player" in fields and "farms" in fields


def test_one_farmer_action_changes_to_legal_dig_and_every_other_lane_is_equal(tmp_path: Path) -> None:
    namespace, _ = _candidate_namespace(tmp_path)
    control = _control_action()
    before = copy.deepcopy(control)
    ids = _flatten_ids(control)
    _stub_control(namespace, control)
    observed = namespace["agent"](
        _observation(own_farm=_farm(farmer_tile={"kind": "WEED"}))
    )

    _assert_control_immutable(control, before, ids)
    assert observed is not control
    assert observed["farmer"] == ["DIG"]
    assert observed["hands"] == control["hands"]
    assert observed["market"] == control["market"]
    assert namespace["rescue_metrics"]() == {
        "calls": 1,
        "obstructions_observed": 1,
        "repairs_applied": 1,
        "farmer_repairs": 1,
        "hand_repairs": 0,
        "no_op": 0,
        "rejected_malformed": 0,
        "rejected_ambiguous": 0,
        "rejected_illegal": 0,
        "exception_fallback": 0,
    }


def test_exactly_one_eligible_hand_is_the_only_changed_actor(tmp_path: Path) -> None:
    namespace, _ = _candidate_namespace(tmp_path)
    control = _control_action()
    before = copy.deepcopy(control)
    ids = _flatten_ids(control)
    _stub_control(namespace, control)

    observed = namespace["agent"](
        _observation(own_farm=_farm(hand_tiles=({"kind": "WEED"}, None)))
    )

    _assert_control_immutable(control, before, ids)
    assert observed["farmer"] == control["farmer"]
    assert observed["hands"] == [["DIG"], ["PASS"]]
    assert observed["market"] == control["market"]
    metrics = namespace["rescue_metrics"]()
    assert metrics["repairs_applied"] == metrics["hand_repairs"] == 1
    assert metrics["farmer_repairs"] == 0


@pytest.mark.parametrize(
    "observation",
    [
        _observation(),
        _observation(player=True),
        {"player": 0, "farms": []},
        _observation(own_farm={"farmer": [0, 0], "hands": [], "tiles": []}),
    ],
)
def test_noop_and_malformed_paths_return_the_exact_control_object_without_mutation(
    tmp_path: Path, observation: dict[str, object]
) -> None:
    namespace, _ = _candidate_namespace(tmp_path)
    control = _control_action()
    before = copy.deepcopy(control)
    ids = _flatten_ids(control)
    _stub_control(namespace, control)

    observed = namespace["agent"](observation)

    assert observed is control
    _assert_control_immutable(control, before, ids)


def test_multiple_eligible_weed_actors_fall_back_exactly(tmp_path: Path) -> None:
    namespace, _ = _candidate_namespace(tmp_path)
    control = _control_action()
    before = copy.deepcopy(control)
    ids = _flatten_ids(control)
    _stub_control(namespace, control)
    farm = _farm(farmer_tile={"kind": "WEED"})
    farm["hands"] = [[0, 0], [2, 0]]

    observed = namespace["agent"](_observation(own_farm=farm))

    assert observed is control
    _assert_control_immutable(control, before, ids)
    metrics = namespace["rescue_metrics"]()
    assert metrics["obstructions_observed"] == 2
    assert metrics["rejected_ambiguous"] == 1


def test_colocated_actors_are_allowed_when_exactly_one_is_eligible(tmp_path: Path) -> None:
    namespace, _ = _candidate_namespace(tmp_path)
    control = _control_action()
    control["farmer"] = ["MOVE", "UP"]
    before = copy.deepcopy(control)
    ids = _flatten_ids(control)
    _stub_control(namespace, control)
    farm = _farm(farmer_tile={"kind": "WEED"})
    farm["hands"] = [[0, 0], [2, 0]]

    observed = namespace["agent"](_observation(own_farm=farm))

    _assert_control_immutable(control, before, ids)
    assert observed["farmer"] == ["MOVE", "UP"]
    assert observed["hands"] == [["DIG"], ["PASS"]]
    assert namespace["rescue_metrics"]()["rejected_ambiguous"] == 0


def test_forbidden_fields_vary_without_changing_the_action(tmp_path: Path) -> None:
    namespace, _ = _candidate_namespace(tmp_path)
    control = _control_action()
    _stub_control(namespace, control)
    base = _observation(own_farm=_farm(hand_tiles=({"kind": "WEED"}, None)))
    variants = [
        {"step": 0, "day": 0, "hour": 0, "seed": 1, "episode": 3, "opponent": "a", "team": "x"},
        {"step": 719, "day": 29, "hour": 23, "seed": 999, "episode": 999, "opponent": "b", "team": "y", "replay": "r"},
    ]

    actions = []
    for fields in variants:
        namespace["reset_rescue_metrics"]()
        observed = namespace["agent"]({**base, **fields})
        actions.append(copy.deepcopy(observed))
    assert actions[0] == actions[1] == {
        "farmer": ["PASS"],
        "hands": [["DIG"], ["PASS"]],
        "market": [["SELL", "WHEAT", 3], ["HIRE"]],
    }


def test_metrics_hooks_do_not_change_action_or_control_immutability(tmp_path: Path) -> None:
    namespace, _ = _candidate_namespace(tmp_path)
    control = _control_action()
    before = copy.deepcopy(control)
    ids = _flatten_ids(control)
    _stub_control(namespace, control)
    observation = _observation(own_farm=_farm(farmer_tile={"kind": "WEED"}))

    first = namespace["agent"](observation)
    snapshot = namespace["rescue_metrics"]()
    assert namespace["get_metrics"]() == snapshot
    assert namespace["reset_rescue_metrics"]() == {name: 0 for name in snapshot}
    second = namespace["agent"](observation)

    _assert_control_immutable(control, before, ids)
    assert first == second


def test_materialize_freeze_is_deterministic_compiles_and_exposes_runner_hooks(tmp_path: Path) -> None:
    main = tmp_path / "main.py"
    receipt_path = tmp_path / "freeze_receipt.json"

    first = materialize_freeze(CONTROL, main, receipt_path)
    second = materialize_freeze(CONTROL, main, receipt_path)

    assert first == second == json.loads(receipt_path.read_text(encoding="utf-8"))
    assert first["control"] == {
        "path": "research/campaign_3000/06_candidates/snapshots/tetsu_v16.py",
        "sha256": CONTROL_SHA256,
        "bytes": len(CONTROL.read_bytes()),
    }
    assert first["candidate"]["sha256"] == sha256_text(main.read_text(encoding="utf-8"))
    assert first["compile"] == {"filename": "<kag03_freeze>", "ok": True}
    assert first["metrics_hooks"] == [
        "kag03_metrics",
        "get_metrics",
        "rescue_metrics",
        "reset_rescue_metrics",
    ]
    assert all(value == 0 for value in first["metrics_initial"].values())
    assert hashlib.sha256(main.read_bytes()).hexdigest().upper() == first["candidate"]["sha256"]
