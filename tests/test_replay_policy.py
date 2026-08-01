from __future__ import annotations

import hashlib
import json
import runpy
from pathlib import Path

import pytest

from kaggriculture_lab.research.replay_policy import (
    EPISODE_STEPS,
    RECORDED_ACTIONS,
    build_file,
    extract_actions,
    main,
    render_fixed_schedule,
)

FA04_REPLAY = Path("references/fa04_teacher_replays/episode-89256171-replay.json")
FA04_G1 = Path("experiments/source_snapshots/fa04_top_trace/G1_sell_guard.py")
SUBMISSION_REPLAY = Path("artifacts/submission_replays/episode-89143277-replay.json")
ACTUAL_REPLAY = SUBMISSION_REPLAY if SUBMISSION_REPLAY.is_file() else FA04_REPLAY
FA04_SOURCE_METADATA = {
    "title": "Kaggriculture Frontier Lab | High-Score + Visuals",
    "author": "PRVSIYAN",
    "url": "https://www.kaggle.com/code/prvsiyan/kaggriculture-frontier-lab-high-score-visuals",
    "license": "Apache-2.0",
    "license_context": "as displayed on the public Kaggle Competition Notebook",
    "modifications": [
        "independently regenerated from the attributed public replay and added",
        "observation-based hand normalization plus impossible-SELL drift guards.",
    ],
}


def _action(index: int, player: int) -> dict[str, object]:
    return {
        "farmer": ["PASS"],
        "hands": [],
        "market": [["SELL", "WHEAT", index + player]],
    }


def _replay(action_states: int = RECORDED_ACTIONS) -> dict[str, object]:
    steps = [
        [
            {"action": {"ignored": [0]}},
            {"action": {"ignored": [1]}},
        ]
    ]
    for index in range(action_states):
        steps.append(
            [
                {"action": _action(index, 0)},
                {"action": _action(index, 1)},
            ]
        )
    return {
        "id": 991,
        "info": {"EpisodeId": 991, "TeamNames": ["Alpha", "Beta"]},
        "steps": steps,
    }


def _write_replay(path: Path, replay: dict[str, object]) -> bytes:
    payload = (json.dumps(replay, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path.write_bytes(payload)
    return payload


def test_extract_actions_uses_steps_after_initial_state() -> None:
    replay = _replay()
    actions = extract_actions(replay, 1)
    assert len(actions) == 719
    assert actions[0] == _action(0, 1)
    assert actions[1] == _action(1, 1)
    assert actions[-1] == _action(718, 1)
    assert "ignored" not in actions[0]


def test_rendered_agent_indexes_clamps_and_deep_copies(tmp_path: Path) -> None:
    actions = extract_actions(_replay(), 0)
    source = render_fixed_schedule(
        actions,
        {
            "episode_id": 991,
            "team": "Alpha",
            "player": 0,
            "replay_sha256": "A" * 64,
        },
    )
    generated = tmp_path / "rendered.py"
    generated.write_text(source, encoding="utf-8")
    namespace = runpy.run_path(str(generated))
    agent = namespace["agent"]

    assert agent({"step": 0}) == _action(0, 0)
    assert agent({"step": 1}) == _action(1, 0)
    assert agent({"step": 718}) == _action(718, 0)
    assert agent({"step": 719}) == _action(718, 0)
    assert agent({"step": 720}) == _action(718, 0)
    assert agent({"step": 10_000}) == _action(718, 0)
    assert agent({"step": -5}) == _action(0, 0)

    mutated = agent({"step": 0})
    mutated["market"][0][2] = -1
    assert agent({"step": 0}) == _action(0, 0)


@pytest.mark.parametrize("action_states", (718, 720))
def test_extract_rejects_invalid_schedule_length(action_states: int) -> None:
    with pytest.raises(ValueError, match="expected 719 action states"):
        extract_actions(_replay(action_states), 0)


def test_extract_rejects_non_dict_action() -> None:
    replay = _replay()
    replay["steps"][17][0]["action"] = None
    with pytest.raises(TypeError, match="action is not a dict"):
        extract_actions(replay, 0)


def test_build_file_preserves_source_metadata_and_hash(tmp_path: Path) -> None:
    replay_path = tmp_path / "replay.json"
    output = tmp_path / "fixed.py"
    raw = _write_replay(replay_path, _replay())
    receipt = build_file(replay_path, 1, output)
    replay_hash = hashlib.sha256(raw).hexdigest().upper()

    assert receipt == {
        "episode_id": 991,
        "team": "Beta",
        "player": 1,
        "replay_sha256": replay_hash,
        "recorded_actions": RECORDED_ACTIONS,
        "episode_steps": EPISODE_STEPS,
        "mode": "fixed",
        "output": output.as_posix(),
        "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest().upper(),
        "output_bytes": output.stat().st_size,
    }
    namespace = runpy.run_path(str(output))
    assert namespace["SOURCE_EPISODE_ID"] == 991
    assert namespace["SOURCE_TEAM"] == "Beta"
    assert namespace["SOURCE_PLAYER"] == 1
    assert namespace["SOURCE_REPLAY_SHA256"] == replay_hash
    assert namespace["RECORDED_ACTIONS"] == 719
    assert namespace["EPISODE_STEPS"] == 720
    assert len(namespace["SCHEDULE"]) == 719
    rendered = output.read_text(encoding="utf-8")
    assert "# Source episode: 991" in rendered
    assert "# Source team: Beta" in rendered
    assert f"# Source replay SHA256: {replay_hash}" in rendered


def test_cli_generates_standalone_agent(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    replay_path = tmp_path / "replay.json"
    output = tmp_path / "generated" / "agent.py"
    _write_replay(replay_path, _replay())

    main(
        [
            "--replay",
            str(replay_path),
            "--player",
            "0",
            "--output",
            str(output),
        ]
    )
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["recorded_actions"] == RECORDED_ACTIONS
    assert receipt["episode_steps"] == EPISODE_STEPS
    assert receipt["mode"] == "fixed"
    assert receipt["team"] == "Alpha"
    assert Path(receipt["output"]) == output
    compile(output.read_bytes(), str(output), "exec")
    assert runpy.run_path(str(output))["agent"]({"step": 999}) == _action(718, 0)


def test_actual_retained_replay_builds_720_call_policy(tmp_path: Path) -> None:
    replay = json.loads(ACTUAL_REPLAY.read_text(encoding="utf-8"))
    assert len(replay["steps"]) == EPISODE_STEPS
    actions = extract_actions(replay, 0)
    assert len(actions) == RECORDED_ACTIONS
    assert actions[0] == replay["steps"][1][0]["action"]
    assert actions[-1] == replay["steps"][-1][0]["action"]

    output = tmp_path / "actual_fixed.py"
    receipt = build_file(ACTUAL_REPLAY, 0, output)
    assert receipt["recorded_actions"] == RECORDED_ACTIONS
    assert receipt["episode_steps"] == EPISODE_STEPS
    agent = runpy.run_path(str(output))["agent"]
    assert agent({"step": 0}) == actions[0]
    assert agent({"step": 718}) == actions[-1]
    assert agent({"step": 719}) == actions[-1]


def _guard_namespace(tmp_path: Path, action: dict[str, object], mode: str) -> dict[str, object]:
    actions = [action for _ in range(RECORDED_ACTIONS)]
    source = render_fixed_schedule(
        actions,
        {
            "episode_id": 991,
            "team": "Alpha",
            "player": 0,
            "replay_sha256": "A" * 64,
        },
        mode=mode,
    )
    generated = tmp_path / f"{mode}.py"
    generated.write_text(source, encoding="utf-8")
    return runpy.run_path(str(generated))


def _obs(
    *,
    hands: int = 0,
    shed: dict[str, int] | None = None,
    inventories: list[dict[str, int]] | None = None,
    day: int = 1,
    prices: dict[str, int] | None = None,
    positions: list[list[int]] | None = None,
) -> dict[str, object]:
    unit_positions = positions or [[1, 1] for _ in range(hands + 1)]
    tiles = [[None for _ in range(4)] for _ in range(4)]
    return {
        "step": 0,
        "day": day,
        "player": 0,
        "farms": [
            {
                "farmer": unit_positions[0],
                "hands": unit_positions[1:],
                "tiles": tiles,
            }
        ],
        "private": {
            "shed": shed or {},
            "inventories": inventories or [{} for _ in range(hands + 1)],
        },
        "market": {"prices": prices or {}},
    }


def test_fixed_mode_keeps_trace_bytes_behavior_with_mismatched_hands(
    tmp_path: Path,
) -> None:
    action = {
        "farmer": ["PASS"],
        "hands": [["NORTH"], ["SOUTH"]],
        "market": [["SELL", "WHEAT", 99]],
    }
    namespace = _guard_namespace(tmp_path, action, "fixed")
    assert namespace["agent"](_obs(hands=0, shed={"WHEAT": 1})) == action


def test_sell_guard_exact_no_change_and_resettable_counters(tmp_path: Path) -> None:
    action = {
        "farmer": ["PASS"],
        "hands": [["PASS"]],
        "market": [["BUY", "WHEAT_SEED", 1], ["SELL", "WHEAT", 2]],
    }
    namespace = _guard_namespace(tmp_path, action, "sell_guard")
    observed = namespace["agent"](_obs(hands=1, shed={"WHEAT": 2}))
    assert observed == action
    assert namespace["rescue_metrics"]() == {
        "actions_changed": 0,
        "hands_adjusted": 0,
        "sell_clamped": 0,
        "sell_dropped": 0,
        "terminal_rewritten": 0,
    }
    assert namespace["reset_rescue_metrics"]() == namespace["rescue_metrics"]()


def test_sell_guard_normalizes_hands_and_reserves_drop_and_pickup(tmp_path: Path) -> None:
    action = {
        "farmer": ["DROP"],
        "hands": [["PICKUP", "WHEAT", 2], ["PASS"]],
        "market": [["SELL", "WHEAT", 10], ["SELL", "CARROT", 1]],
    }
    namespace = _guard_namespace(tmp_path, action, "sell_guard")
    observed = namespace["agent"](
        _obs(
            hands=1,
            shed={"WHEAT": 5},
            inventories=[{"WHEAT": 3}, {}],
        )
    )
    assert observed["hands"] == [["PICKUP", "WHEAT", 2]]
    assert observed["market"] == [["SELL", "WHEAT", 6]]
    assert namespace["rescue_metrics"]() == {
        "actions_changed": 1,
        "hands_adjusted": 1,
        "sell_clamped": 1,
        "sell_dropped": 1,
        "terminal_rewritten": 0,
    }
    assert all(value >= 0 for value in namespace["rescue_metrics"]().values())
    assert not any(namespace["reset_rescue_metrics"]().values())


def test_sell_guard_pads_missing_hand_with_pass(tmp_path: Path) -> None:
    action = {"farmer": ["PASS"], "hands": [], "market": []}
    namespace = _guard_namespace(tmp_path, action, "sell_guard")
    assert namespace["agent"](_obs(hands=2))["hands"] == [["PASS"], ["PASS"]]


def test_sell_guard_ignores_off_shed_drop_and_pickup(tmp_path: Path) -> None:
    drop = {
        "farmer": ["DROP"],
        "hands": [],
        "market": [["SELL", "WHEAT", 4]],
    }
    drop_namespace = _guard_namespace(tmp_path, drop, "sell_guard")
    drop_observed = drop_namespace["agent"](
        _obs(
            shed={"WHEAT": 1},
            inventories=[{"WHEAT": 3}],
            positions=[[0, 0]],
        )
    )
    assert drop_observed["market"] == [["SELL", "WHEAT", 1]]

    pickup = {
        "farmer": ["PICKUP", "WHEAT", 3],
        "hands": [],
        "market": [["SELL", "WHEAT", 4]],
    }
    pickup_namespace = _guard_namespace(tmp_path, pickup, "sell_guard")
    pickup_observed = pickup_namespace["agent"](_obs(shed={"WHEAT": 4}, positions=[[0, 0]]))
    assert pickup_observed["market"] == [["SELL", "WHEAT", 4]]


def test_sell_guard_applies_on_shed_drop_and_pickup(tmp_path: Path) -> None:
    action = {
        "farmer": ["DROP"],
        "hands": [["PICKUP", "WHEAT", 2]],
        "market": [["SELL", "WHEAT", 6]],
    }
    namespace = _guard_namespace(tmp_path, action, "sell_guard")
    observed = namespace["agent"](
        _obs(
            hands=1,
            shed={"WHEAT": 5},
            inventories=[{"WHEAT": 3}, {}],
            positions=[[1, 1], [2, 1]],
        )
    )
    assert observed["market"] == [["SELL", "WHEAT", 6]]


def test_sell_guard_caps_same_turn_drop_at_official_shed_capacity(tmp_path: Path) -> None:
    action = {
        "farmer": ["DROP"],
        "hands": [],
        "market": [["SELL", "WHEAT", 104]],
    }
    namespace = _guard_namespace(tmp_path, action, "sell_guard")
    observed = namespace["agent"](
        _obs(shed={"WHEAT": 99}, inventories=[{"WHEAT": 5}]),
        {"shedCapacity": 100},
    )
    assert observed["market"] == [["SELL", "WHEAT", 100]]


def test_sell_guard_drop_capacity_follows_official_inventory_order(tmp_path: Path) -> None:
    action = {
        "farmer": ["DROP"],
        "hands": [],
        "market": [["SELL", "CARROT", 2], ["SELL", "WHEAT", 99]],
    }
    namespace = _guard_namespace(tmp_path, action, "sell_guard")
    observed = namespace["agent"](
        _obs(
            shed={"WHEAT": 99},
            inventories=[{"CARROT": 2, "WHEAT": 2}],
        ),
        {"shedCapacity": 100},
    )
    assert observed["market"] == [["SELL", "CARROT", 1], ["SELL", "WHEAT", 99]]


def test_official_simulator_drop_then_market_caps_guarded_sell_at_100(
    tmp_path: Path,
) -> None:
    from kaggle_environments import make

    trace_action = {
        "farmer": ["DROP"],
        "hands": [],
        "market": [["SELL", "WHEAT", 104]],
    }
    namespace = _guard_namespace(tmp_path, trace_action, "sell_guard")
    pass_action = {"farmer": ["PASS"], "hands": [], "market": []}

    def prepared_environment():
        environment = make(
            "kaggriculture",
            configuration={"episodeSteps": 3, "seed": 123, "shedCapacity": 100},
            debug=False,
        )
        private = environment.state[0].observation.private
        private.shed["WHEAT"] = 99
        private.inventories[0]["WHEAT"] = 5
        return environment

    guarded_environment = prepared_environment()
    guarded = namespace["agent"](
        guarded_environment.state[0].observation,
        guarded_environment.configuration,
    )
    assert guarded["market"] == [["SELL", "WHEAT", 100]]
    guarded_start_money = guarded_environment.state[0].observation.farms[0].money
    guarded_environment.step([guarded, pass_action])
    guarded_private = guarded_environment.state[0].observation.private
    guarded_end_money = guarded_environment.state[0].observation.farms[0].money
    assert guarded_private.shed["WHEAT"] == 0
    assert guarded_private.inventories[0] == {}
    assert guarded_end_money > guarded_start_money

    unguarded_environment = prepared_environment()
    unguarded_environment.step([trace_action, pass_action])
    assert unguarded_environment.state[0].observation.private.shed["WHEAT"] == 0
    assert unguarded_environment.state[0].observation.farms[0].money == guarded_end_money


def test_terminal_guard_preserves_non_sells_and_caps_market_at_ten(
    tmp_path: Path,
) -> None:
    products = (
        "WHEAT",
        "CARROT",
        "TOMATO",
        "STRAWBERRY",
        "MELON",
        "EGG",
        "MILK",
        "WOOL",
        "FERTILIZER",
    )
    action = {
        "farmer": ["PASS"],
        "hands": [],
        "market": [
            ["BUY", "WHEAT_SEED", 1],
            ["SELL", "WHEAT", 1],
            ["HIRE", "HAND", 1],
        ],
    }
    namespace = _guard_namespace(tmp_path, action, "terminal_guard")
    shed = {item: 1 for item in products}
    prices = {item: index + 1 for index, item in enumerate(products)}
    observed = namespace["agent"](_obs(day=29, shed=shed, prices=prices))
    assert observed["market"][:2] == [
        ["BUY", "WHEAT_SEED", 1],
        ["HIRE", "HAND", 1],
    ]
    assert len(observed["market"]) == 10
    assert observed["market"][2:] == [["SELL", item, 1] for item in reversed(products[1:])]
    assert namespace["rescue_metrics"]()["terminal_rewritten"] == 1
    assert namespace["rescue_metrics"]()["actions_changed"] == 1


def test_cli_accepts_guard_mode(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    replay_path = tmp_path / "replay.json"
    output = tmp_path / "guarded.py"
    _write_replay(replay_path, _replay())
    main(
        [
            "--replay",
            str(replay_path),
            "--player",
            "0",
            "--output",
            str(output),
            "--mode",
            "sell_guard",
            "--source-title",
            FA04_SOURCE_METADATA["title"],
            "--source-author",
            FA04_SOURCE_METADATA["author"],
            "--source-url",
            FA04_SOURCE_METADATA["url"],
            "--source-license",
            FA04_SOURCE_METADATA["license"],
            "--source-license-context",
            FA04_SOURCE_METADATA["license_context"],
            "--modification-line",
            FA04_SOURCE_METADATA["modifications"][0],
            "--modification-line",
            FA04_SOURCE_METADATA["modifications"][1],
        ]
    )
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["mode"] == "sell_guard"
    assert receipt["source_metadata"] == FA04_SOURCE_METADATA
    assert runpy.run_path(str(output))["SOURCE_MODE"] == "sell_guard"
    assert output.read_text(encoding="utf-8").startswith(
        '# Derived from "Kaggriculture Frontier Lab | High-Score + Visuals" by PRVSIYAN.\n'
    )


def test_fa04_g1_snapshot_is_exact_attributed_regeneration() -> None:
    raw = FA04_REPLAY.read_bytes()
    replay = json.loads(raw)
    source = render_fixed_schedule(
        extract_actions(replay, 0),
        {
            "episode_id": 89256171,
            "team": "radiant-allomancer",
            "player": 0,
            "replay_sha256": hashlib.sha256(raw).hexdigest().upper(),
            "source_metadata": FA04_SOURCE_METADATA,
        },
        mode="sell_guard",
    )
    assert source.encode() == FA04_G1.read_bytes()
