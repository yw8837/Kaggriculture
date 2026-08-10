from __future__ import annotations

import copy
import json
import runpy
from pathlib import Path

import pytest

from kaggriculture_lab.research.kag03_preempt_horizon import (
    AGENT_ANCHOR,
    CALL_METRICS,
    CANDIDATE_HORIZON,
    CONTROL_HORIZON,
    CONTROL_SHA256,
    METRICS_ANCHOR,
    METRICS_BLOCK,
    PREEMPT_METRICS,
    PREEMPT_SUCCESS_ANCHOR,
    build_source,
    materialize_freeze,
    sha256_bytes,
    sha256_text,
)

CONTROL = Path("research/campaign_3000/06_candidates/snapshots/tetsu_v16.py")


def _namespace(tmp_path: Path) -> dict[str, object]:
    generated = tmp_path / "kag03.py"
    generated.write_text(build_source(CONTROL.read_text(encoding="utf-8")), encoding="utf-8")
    return runpy.run_path(str(generated))


def _without_metrics(source: str) -> str:
    source = source.replace(f"{METRICS_ANCHOR}\n{METRICS_BLOCK}", METRICS_ANCHOR)
    source = source.replace(
        f"{PREEMPT_SUCCESS_ANCHOR}{PREEMPT_METRICS}", PREEMPT_SUCCESS_ANCHOR
    )
    source = source.replace(f"{AGENT_ANCHOR}{CALL_METRICS}", AGENT_ANCHOR)
    return source.replace(CANDIDATE_HORIZON, CONTROL_HORIZON)


def test_exact_control_and_only_horizon_semantic_replacement() -> None:
    control_bytes = CONTROL.read_bytes()
    control = control_bytes.decode("utf-8")
    candidate = build_source(control)

    assert sha256_bytes(control_bytes) == CONTROL_SHA256
    assert candidate.count(CONTROL_HORIZON) == 0
    assert candidate.count(CANDIDATE_HORIZON) == 1
    assert _without_metrics(candidate) == control

    with pytest.raises(ValueError, match="exact pinned"):
        build_source(f"{control}\n# drift")
    with pytest.raises(ValueError, match="exact pinned"):
        build_source(control.replace(CONTROL_HORIZON, "    for horizon in (3, 2):"))


def test_horizon_four_is_the_only_new_preemption_choice_and_metrics_record_it(
    tmp_path: Path,
) -> None:
    candidate = _namespace(tmp_path)
    control = runpy.run_path(str(CONTROL))
    candidate_globals = candidate["_preempt_shift"].__globals__
    control_globals = control["_preempt_shift"].__globals__
    states = ({"due": {}}, {"due": {}})

    for namespace, state in zip((candidate_globals, control_globals), states, strict=True):
        namespace["_PREEMPT_ENABLED"] = True
        namespace["_shift_state"] = lambda _obs, _step, state=state: state
        namespace["_clone_distance"] = lambda _obs: 0
        namespace["_projected_shed"] = lambda _obs, _action: {"STRAWBERRY": 10}
        namespace["_future_sells_at"] = (
            lambda _step, horizon: {"STRAWBERRY": 4} if horizon == 4 else {}
        )

    action = {"farmer": ["PASS"], "hands": [], "market": []}
    candidate["reset_rescue_metrics"]()
    candidate_action = candidate["_preempt_shift"](
        {"market": {"prices": {"STRAWBERRY": 100}}}, copy.deepcopy(action), 120
    )
    control_action = control["_preempt_shift"](
        {"market": {"prices": {"STRAWBERRY": 100}}}, copy.deepcopy(action), 120
    )

    assert control_action == action
    assert candidate_action["farmer"] == action["farmer"]
    assert candidate_action["hands"] == action["hands"]
    assert candidate_action["market"] == [["SELL", "STRAWBERRY", 4]]
    assert candidate["rescue_metrics"]() == {
        "calls": 0,
        "preemptions": 1,
        "horizon4_preemptions": 1,
    }


def test_metrics_hooks_do_not_change_agent_action(tmp_path: Path) -> None:
    namespace = _namespace(tmp_path)
    agent_globals = namespace["agent"].__globals__
    action = {"farmer": ["PASS"], "hands": [], "market": []}
    agent_globals["_ACTIONS"] = [action]
    agent_globals["_weed_repair_action"] = lambda _obs, value, _step: value
    agent_globals["_repay_shift"] = lambda _obs, value, _step: value
    agent_globals["_rank_sell_slots"] = lambda _obs, value, _configuration: value
    agent_globals["_preempt_shift"] = lambda _obs, value, _step: value
    agent_globals["_terminal_liquidation"] = lambda _obs, value, _step: value
    agent_globals["_align_hands"] = lambda value, _obs: value

    namespace["reset_rescue_metrics"]()
    first = namespace["agent"]({"step": 0})
    snapshot = namespace["rescue_metrics"]()
    assert namespace["kag03_metrics"]() == namespace["get_metrics"]() == snapshot
    assert namespace["reset_rescue_metrics"]() == {
        "calls": 0,
        "preemptions": 0,
        "horizon4_preemptions": 0,
    }
    second = namespace["agent"]({"step": 0})

    assert first == second == action


def test_materialize_freeze_is_deterministic_and_has_runner_hook(tmp_path: Path) -> None:
    main = tmp_path / "main.py"
    receipt_path = tmp_path / "freeze_receipt.json"

    first = materialize_freeze(CONTROL, main, receipt_path)
    second = materialize_freeze(CONTROL, main, receipt_path)

    assert first == second == json.loads(receipt_path.read_text(encoding="utf-8"))
    assert first["control"]["sha256"] == CONTROL_SHA256
    assert first["candidate"]["sha256"] == sha256_text(main.read_text(encoding="utf-8"))
    assert first["semantic_replacement"] == {
        "from": "for horizon in (3, 2, 1):",
        "to": "for horizon in (4, 3, 2, 1):",
    }
    assert first["compile"] == {
        "filename": "<kag03_preempt_horizon_freeze>",
        "ok": True,
    }
    assert first["metrics_hooks"] == [
        "kag03_metrics",
        "get_metrics",
        "rescue_metrics",
        "reset_rescue_metrics",
    ]
    assert all(value == 0 for value in first["metrics_initial"].values())
