from __future__ import annotations

import ast
import copy
import hashlib
import json
import runpy
from pathlib import Path

import pytest

from kaggriculture_lab.candidates.kag03_terminal_market import (
    CONTROL_SHA256,
    RUNTIME_MARKER,
    build_file,
    build_source,
    materialize_freeze,
    sha256_bytes,
    sha256_text,
)

CONTROL = Path("research/campaign_3000/06_candidates/snapshots/tetsu_v16.py")
_FORBIDDEN_OBSERVATION_FIELDS = frozenset(
    {
        "step",
        "day",
        "hour",
        "player",
        "seat",
        "seed",
        "episode",
        "replay",
        "team",
        "opponent",
    }
)
_ALLOWED_OBSERVATION_FIELDS = frozenset({"private", "market"})


class _OverlayObservationBoundary(ast.NodeVisitor):
    """Reject direct and aliased observation reads outside the two allowed fields."""

    def __init__(self) -> None:
        self.aliases = {"obs"}
        self.violations: list[str] = []

    def _is_observation_alias(self, node: ast.AST) -> bool:
        return isinstance(node, ast.Name) and node.id in self.aliases

    def _record(self, field: ast.AST) -> None:
        if not isinstance(field, ast.Constant) or not isinstance(field.value, str):
            self.violations.append("dynamic")
        elif field.value not in _ALLOWED_OBSERVATION_FIELDS:
            self.violations.append(field.value)

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        if self._is_observation_alias(node.value):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.aliases.add(target.id)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            self.visit(node.value)
            if isinstance(node.target, ast.Name) and self._is_observation_alias(node.value):
                self.aliases.add(node.target.id)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if self._is_observation_alias(node.value):
            self._record(node.slice)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if self._is_observation_alias(node.value) and node.attr != "get":
            self._record(ast.Constant(node.attr))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute) and node.func.attr == "get":
            if self._is_observation_alias(node.func.value):
                self._record(node.args[0] if node.args else ast.Constant(None))
        elif isinstance(node.func, ast.Name) and node.func.id == "getattr":
            if node.args and self._is_observation_alias(node.args[0]):
                self._record(node.args[1] if len(node.args) > 1 else ast.Constant(None))
        elif (
            isinstance(node.func, ast.Name)
            and node.func.id in {"_get", "get", "lookup", "read_field"}
            and len(node.args) > 1
            and self._is_observation_alias(node.args[0])
        ):
            self._record(node.args[1])
        self.generic_visit(node)


def _forbidden_observation_accesses(source: str) -> list[str]:
    boundary = _OverlayObservationBoundary()
    boundary.visit(ast.parse(source))
    return boundary.violations


def _mutable_ids(value: object) -> tuple[int, ...]:
    if isinstance(value, dict):
        return (
            id(value),
            *(identifier for child in value.values() for identifier in _mutable_ids(child)),
        )
    if isinstance(value, list):
        return (
            id(value),
            *(identifier for child in value for identifier in _mutable_ids(child)),
        )
    return ()


def _assert_control_unchanged(
    control: dict[str, object], before: dict[str, object], mutable_ids: tuple[int, ...]
) -> None:
    assert control == before
    assert _mutable_ids(control) == mutable_ids


def _observation(**overrides: object) -> dict[str, object]:
    observation: dict[str, object] = {
        "private": {"shed": {"WHEAT": 7, "MELON": 5, "CARROT": 3}},
        "market": {"inventory": {"WHEAT": 10_010, "MELON": 10_080, "CARROT": 9_990}},
    }
    observation.update(overrides)
    return observation


def _control_action(market: list[list[object]] | None = None) -> dict[str, object]:
    return {
        "farmer": ["HARVEST"],
        "hands": [["WEST"], ["DROP"]],
        "market": market
        or [
            ["SELL", "WHEAT", 7],
            ["BUY_SEED", "CARROT", 1],
            ["SELL", "MELON", 5],
            ["HIRE"],
        ],
    }


def _candidate_namespace(tmp_path: Path) -> tuple[dict[str, object], str]:
    source = build_source(CONTROL.read_text(encoding="utf-8"))
    path = tmp_path / "kag03.py"
    path.write_text(source, encoding="utf-8", newline="")
    return runpy.run_path(str(path)), source


def _stub_control(namespace: dict[str, object], action: dict[str, object]) -> None:
    namespace["agent"].__globals__["_kag03_control_agent"] = lambda _obs: action


def test_builder_requires_the_exact_kag01_control_and_writes_receipt(tmp_path: Path) -> None:
    control = CONTROL.read_text(encoding="utf-8")
    assert sha256_text(control) == CONTROL_SHA256
    with pytest.raises(ValueError, match="exact pinned"):
        build_source(f"{control}\n# drift")

    output = tmp_path / "main.py"
    receipt = build_file(CONTROL, output)
    assert output.exists()
    assert receipt["control_sha256"] == CONTROL_SHA256
    assert receipt["control_bytes"] == len(CONTROL.read_bytes())
    assert receipt["candidate_sha256"] == sha256_text(output.read_text(encoding="utf-8"))
    assert receipt["candidate_bytes"] == len(output.read_bytes())


def test_materialize_freeze_records_exact_hash_compile_and_metrics_hooks(tmp_path: Path) -> None:
    output = tmp_path / "main.py"
    receipt_path = tmp_path / "freeze_receipt.json"

    receipt = materialize_freeze(CONTROL, output, receipt_path)

    assert json.loads(receipt_path.read_text(encoding="utf-8")) == receipt
    assert receipt["control"] == {
        "path": "research/campaign_3000/06_candidates/snapshots/tetsu_v16.py",
        "sha256": CONTROL_SHA256,
        "bytes": len(CONTROL.read_bytes()),
    }
    assert receipt["candidate"]["sha256"] == sha256_bytes(output.read_bytes())
    assert receipt["candidate"]["bytes"] == len(output.read_bytes())
    assert receipt["compile"] == {"filename": "<kag03_freeze>", "ok": True}
    assert receipt["metrics_hooks"] == [
        "kag03_metrics",
        "get_metrics",
        "rescue_metrics",
        "reset_rescue_metrics",
    ]
    assert receipt["metrics_initial"] == receipt["metrics_after_reset"]
    assert receipt["metrics_after_reset"] == receipt["metrics_generic"]
    assert all(value == 0 for value in receipt["metrics_initial"].values())


def test_generated_prefix_is_exact_control_except_for_the_single_entrypoint_rename() -> None:
    control_bytes = CONTROL.read_bytes()
    assert hashlib.sha256(control_bytes).hexdigest().upper() == CONTROL_SHA256
    control_source = control_bytes.decode("utf-8")
    expected_prefix = control_source.replace(
        "\ndef agent(obs):", "\ndef _kag03_control_agent(obs):", 1
    )

    generated = build_source(control_source)
    prefix, _ = generated.split(RUNTIME_MARKER, maxsplit=1)

    assert prefix == f"{expected_prefix}\n\n"


def test_non_market_actions_equal_control_and_only_sell_slots_reorder(tmp_path: Path) -> None:
    namespace, _ = _candidate_namespace(tmp_path)
    control = _control_action()
    before = copy.deepcopy(control)
    mutable_ids = _mutable_ids(control)
    _stub_control(namespace, control)

    observed = namespace["agent"](_observation())

    assert observed is not control
    _assert_control_unchanged(control, before, mutable_ids)
    assert observed["farmer"] == control["farmer"]
    assert observed["hands"] == control["hands"]
    assert len(observed["market"]) == len(control["market"])
    assert observed["market"] == [
        ["SELL", "MELON", 5],
        ["BUY_SEED", "CARROT", 1],
        ["SELL", "WHEAT", 7],
        ["HIRE"],
    ]
    for before, after in zip(control["market"], observed["market"]):
        if before[0] != "SELL":
            assert after == before
    assert sorted(tuple(order) for order in observed["market"] if order[0] == "SELL") == sorted(
        tuple(order) for order in control["market"] if order[0] == "SELL"
    )
    assert namespace["kag03_metrics"]()["reordered"] == 1


@pytest.mark.parametrize(
    ("market", "counter"),
    [
        ([["SELL", "WHEAT", True], ["SELL", "MELON", 5]], "rejected_malformed"),
        ([["SELL", "WHEAT", 2], ["SELL", "WHEAT", 1]], "rejected_ambiguous"),
        ([["SELL", "WHEAT", 8], ["SELL", "MELON", 5]], "rejected_illegal"),
    ],
)
def test_malformed_ambiguous_or_illegal_market_is_exact_control_fallback(
    tmp_path: Path, market: list[list[object]], counter: str
) -> None:
    namespace, _ = _candidate_namespace(tmp_path)
    control = _control_action(market)
    before = copy.deepcopy(control)
    mutable_ids = _mutable_ids(control)
    _stub_control(namespace, control)

    observed = namespace["agent"](_observation())

    assert observed is control
    _assert_control_unchanged(control, before, mutable_ids)
    assert namespace["kag03_metrics"]()[counter] == 1


def test_legal_already_ranked_market_is_an_exact_no_op(tmp_path: Path) -> None:
    namespace, _ = _candidate_namespace(tmp_path)
    control = _control_action(
        [["SELL", "MELON", 5], ["BUY_SEED", "CARROT", 1], ["SELL", "WHEAT", 7]]
    )
    before = copy.deepcopy(control)
    mutable_ids = _mutable_ids(control)
    _stub_control(namespace, control)

    observed = namespace["agent"](_observation())

    assert observed is control
    _assert_control_unchanged(control, before, mutable_ids)
    assert namespace["kag03_metrics"]()["no_op"] == 1


def test_overlay_ast_rejects_forbidden_observation_reads_and_aliases(tmp_path: Path) -> None:
    namespace, source = _candidate_namespace(tmp_path)
    assert callable(namespace["get_metrics"])
    assert callable(namespace["rescue_metrics"])
    assert callable(namespace["reset_rescue_metrics"])
    assert "def rescue_metrics(" in source
    assert "def reset_rescue_metrics(" in source
    control_prefix, runtime = source.split(RUNTIME_MARKER, maxsplit=1)
    assert "def _kag03_control_agent" in control_prefix
    assert _forbidden_observation_accesses(runtime) == []
    probe = """
alias = obs
obs["step"]
obs.get("day")
getattr(obs, "hour")
alias["player"]
lookup(alias, "seat")
alias.get("seed")
getattr(alias, "episode")
obs.replay
alias["team"]
lookup(obs, "opponent")
"""
    violations = set(_forbidden_observation_accesses(probe))
    assert violations == _FORBIDDEN_OBSERVATION_FIELDS


def test_constant_control_is_metamorphic_under_forbidden_observation_fields(tmp_path: Path) -> None:
    namespace, _ = _candidate_namespace(tmp_path)
    control = _control_action()
    before = copy.deepcopy(control)
    mutable_ids = _mutable_ids(control)
    _stub_control(namespace, control)
    first = namespace["agent"](
        _observation(
            step=0,
            day=0,
            hour=0,
            player=0,
            seat=0,
            seed=1,
            episode="first",
            replay="one",
            team="alpha",
            opponent="left",
        )
    )
    second = namespace["agent"](
        _observation(
            step=719,
            day=29,
            hour=23,
            player=1,
            seat=1,
            seed=999_999,
            episode="second",
            replay="two",
            team="beta",
            opponent="right",
        )
    )

    assert first == second
    _assert_control_unchanged(control, before, mutable_ids)


class _ExplodingShed(dict[str, int]):
    def get(self, key: object, default: object = None) -> object:
        raise RuntimeError(f"unexpected shed read for {key!r}")


@pytest.mark.parametrize(
    ("market", "observation", "counter"),
    [
        ([["HIRE"]] * 11, _observation(), "rejected_resize"),
        (
            [["SELL", "WHEAT", 7], ["SELL", "MELON", 5]],
            _observation(private={"shed": _ExplodingShed()}),
            "exception_fallback",
        ),
    ],
)
def test_resize_or_exception_fallback_keeps_every_control_value_immutable(
    tmp_path: Path,
    market: list[list[object]],
    observation: dict[str, object],
    counter: str,
) -> None:
    namespace, _ = _candidate_namespace(tmp_path)
    control = _control_action(market)
    before = copy.deepcopy(control)
    mutable_ids = _mutable_ids(control)
    _stub_control(namespace, control)

    observed = namespace["agent"](observation)

    assert observed is control
    _assert_control_unchanged(control, before, mutable_ids)
    assert namespace["kag03_metrics"]()[counter] == 1


def test_optional_metrics_hook_is_a_copy_and_does_not_affect_actions(tmp_path: Path) -> None:
    namespace, _ = _candidate_namespace(tmp_path)
    control = _control_action()
    _stub_control(namespace, control)
    initial = namespace["get_metrics"]()
    initial["calls"] = -1

    first = namespace["agent"](_observation())
    after_first = namespace["get_metrics"]()
    assert namespace["rescue_metrics"]() == after_first
    reset = namespace["reset_rescue_metrics"]()
    second = namespace["agent"](_observation())

    assert all(value == 0 for value in reset.values())
    assert namespace["kag03_metrics"]()["calls"] == 1
    assert after_first["calls"] == 1
    assert first == second
    assert namespace["get_metrics"]() == namespace["kag03_metrics"]()
    assert namespace["rescue_metrics"]() == namespace["kag03_metrics"]()


def test_exact_control_path_keeps_non_market_output_when_delta_cannot_observe_sells(
    tmp_path: Path,
) -> None:
    control_source = CONTROL.read_text(encoding="utf-8")
    control_path = tmp_path / "control.py"
    control_path.write_text(control_source, encoding="utf-8", newline="")
    control_namespace = runpy.run_path(str(control_path))
    candidate_namespace, _ = _candidate_namespace(tmp_path)
    observation = {"step": 0, "player": 0, "farms": [], "private": {}, "market": {}}

    expected = control_namespace["agent"](copy.deepcopy(observation))
    observed = candidate_namespace["agent"](copy.deepcopy(observation))

    assert observed == expected
    assert observed["farmer"] == expected["farmer"]
    assert observed["hands"] == expected["hands"]
