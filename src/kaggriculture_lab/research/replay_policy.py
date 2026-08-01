"""Render one replay seat as a deterministic standalone fixed-schedule agent."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import pprint
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

RECORDED_ACTIONS = 719
EPISODE_STEPS = 720
MODES = ("fixed", "sell_guard", "terminal_guard")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def extract_actions(replay: Mapping[str, Any], player: int) -> list[dict[str, Any]]:
    """Extract the 719 recorded actions at replay indices 1..719."""
    if player < 0:
        raise ValueError("player must be non-negative")
    steps = replay.get("steps")
    if not isinstance(steps, list):
        raise TypeError("replay steps must be a list")
    action_steps = steps[1:]
    if len(action_steps) != RECORDED_ACTIONS:
        raise ValueError(
            f"expected {RECORDED_ACTIONS} action states in replay['steps'][1:], "
            f"found {len(action_steps)}"
        )

    actions: list[dict[str, Any]] = []
    for replay_index, state in enumerate(action_steps, start=1):
        if not isinstance(state, list) or player >= len(state):
            raise ValueError(f"replay state {replay_index} does not contain player {player}")
        agent_state = state[player]
        if not isinstance(agent_state, Mapping):
            raise TypeError(f"replay state {replay_index} player {player} is not a mapping")
        action = agent_state.get("action")
        if not isinstance(action, dict):
            raise TypeError(f"replay state {replay_index} player {player} action is not a dict")
        actions.append(copy.deepcopy(action))
    return actions


def _metadata(replay: Mapping[str, Any], player: int, replay_sha256: str) -> dict[str, Any]:
    info = replay.get("info")
    if not isinstance(info, Mapping):
        raise TypeError("replay info must be a mapping")
    teams = info.get("TeamNames")
    if not isinstance(teams, list) or player >= len(teams):
        raise ValueError(f"replay info does not contain team name for player {player}")
    team = teams[player]
    if not isinstance(team, str):
        raise TypeError(f"team name for player {player} must be a string")
    episode_id = info.get("EpisodeId", replay.get("id"))
    if episode_id is None:
        raise ValueError("replay has no episode id")
    return {
        "episode_id": episode_id,
        "team": team,
        "player": player,
        "replay_sha256": replay_sha256,
    }


def render_fixed_schedule(
    actions: Sequence[Mapping[str, Any]],
    metadata: Mapping[str, Any],
    mode: str = "fixed",
) -> str:
    """Render a self-contained Python agent from validated actions and metadata."""
    if len(actions) != RECORDED_ACTIONS or not all(isinstance(action, dict) for action in actions):
        raise ValueError(f"schedule must contain exactly {RECORDED_ACTIONS} dict actions")
    required = {"episode_id", "team", "player", "replay_sha256"}
    missing = required - metadata.keys()
    if missing:
        raise ValueError(f"missing metadata fields: {sorted(missing)}")
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")

    normalized = json.loads(
        json.dumps(list(actions), ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    )
    schedule = pprint.pformat(normalized, width=100, sort_dicts=True)
    team = str(metadata["team"])
    comment_team = " ".join(team.splitlines())
    source = f"""# Fixed schedule extracted from a Kaggriculture replay.
# Source episode: {metadata["episode_id"]}
# Source team: {comment_team}
# Source player: {metadata["player"]}
# Source replay SHA256: {metadata["replay_sha256"]}
from copy import deepcopy

SOURCE_EPISODE_ID = {metadata["episode_id"]!r}
SOURCE_TEAM = {team!r}
SOURCE_PLAYER = {int(metadata["player"])}
SOURCE_REPLAY_SHA256 = {str(metadata["replay_sha256"])!r}
RECORDED_ACTIONS = {RECORDED_ACTIONS}
EPISODE_STEPS = {EPISODE_STEPS}
SCHEDULE = {schedule}

"""
    if mode == "fixed":
        source += """
def agent(obs, config=None):
    try:
        step = int(obs.get("step", 0) or 0)
    except (AttributeError, TypeError, ValueError):
        step = 0
    index = min(max(step, 0), RECORDED_ACTIONS - 1)
    return deepcopy(SCHEDULE[index])
"""
    else:
        source += (
            f"\nSOURCE_MODE = {mode!r}\n"
            + """PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
_METRIC_KEYS = ("actions_changed", "hands_adjusted", "sell_clamped", "sell_dropped", "terminal_rewritten")
_RESCUE_METRICS = {key: 0 for key in _METRIC_KEYS}


def rescue_metrics():
    return dict(_RESCUE_METRICS)


def reset_rescue_metrics():
    for key in _METRIC_KEYS:
        _RESCUE_METRICS[key] = 0
    return rescue_metrics()


def _nonnegative_int(value, default=0):
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _private(obs):
    value = obs.get("private", {}) if isinstance(obs, dict) else {}
    return value if isinstance(value, dict) else {}


def _expected_hands(obs):
    farms = obs.get("farms", []) if isinstance(obs, dict) else []
    player = _nonnegative_int(obs.get("player", 0)) if isinstance(obs, dict) else 0
    if not isinstance(farms, list) or player >= len(farms) or not isinstance(farms[player], dict):
        return 0
    hands = farms[player].get("hands", [])
    return len(hands) if isinstance(hands, list) else 0


def _current_farm(obs):
    farms = obs.get("farms", []) if isinstance(obs, dict) else []
    player = _nonnegative_int(obs.get("player", 0)) if isinstance(obs, dict) else 0
    if not isinstance(farms, list) or player >= len(farms) or not isinstance(farms[player], dict):
        return {}
    return farms[player]


def _unit_is_on_shed(farm, index):
    tiles = farm.get("tiles", [])
    if not isinstance(tiles, list) or not tiles:
        return False
    positions = [farm.get("farmer"), *(farm.get("hands", []) or [])]
    if index >= len(positions):
        return False
    position = positions[index]
    if not isinstance(position, (list, tuple)) or len(position) < 2:
        return False
    x, y = position[0], position[1]
    if not isinstance(x, int) or not isinstance(y, int):
        return False
    board_size = len(tiles)
    half = board_size // 2
    shed_tiles = ((half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half))
    if (x, y) not in shed_tiles or not (0 <= y < len(tiles)):
        return False
    row = tiles[y]
    return isinstance(row, list) and 0 <= x < len(row) and row[x] != "LOCKED"


def _normalize_hands(action, obs):
    expected = _expected_hands(obs)
    original = action.get("hands")
    hands = deepcopy(original) if isinstance(original, list) else []
    hands = hands[:expected]
    hands.extend([["PASS"] for _ in range(expected - len(hands))])
    if hands == original:
        return False
    action["hands"] = hands
    _RESCUE_METRICS["hands_adjusted"] += 1
    return True


def _predicted_shed(action, obs):
    private = _private(obs)
    raw_shed = private.get("shed", {})
    shed = {
        str(item): _nonnegative_int(quantity)
        for item, quantity in (raw_shed.items() if isinstance(raw_shed, dict) else ())
    }
    inventories = private.get("inventories", [])
    if not isinstance(inventories, list):
        inventories = []
    farm = _current_farm(obs)
    units = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
    for index, unit_action in enumerate(units):
        inventory = inventories[index] if index < len(inventories) else {}
        if not isinstance(inventory, dict) or not isinstance(unit_action, list) or not unit_action:
            continue
        if not _unit_is_on_shed(farm, index):
            continue
        if unit_action[0] == "DROP":
            for item, quantity in inventory.items():
                amount = _nonnegative_int(quantity)
                if amount:
                    shed[str(item)] = shed.get(str(item), 0) + amount
        elif unit_action[0] == "PICKUP" and len(unit_action) >= 2:
            item = str(unit_action[1])
            quantity = _nonnegative_int(unit_action[2], 1) if len(unit_action) >= 3 else 1
            shed[item] = max(0, shed.get(item, 0) - quantity)
    return shed


def _guard_sells(market, shed):
    guarded = []
    for original in market if isinstance(market, list) else []:
        if not isinstance(original, list) or not original or original[0] != "SELL":
            guarded.append(deepcopy(original))
            continue
        if len(original) < 2:
            _RESCUE_METRICS["sell_dropped"] += 1
            continue
        item = str(original[1])
        requested = _nonnegative_int(original[2], 1) if len(original) >= 3 else 1
        available = shed.get(item, 0)
        quantity = min(requested, available)
        if quantity <= 0:
            _RESCUE_METRICS["sell_dropped"] += 1
            continue
        order = deepcopy(original)
        if quantity < requested:
            if len(order) >= 3:
                order[2] = quantity
            else:
                order.append(quantity)
            _RESCUE_METRICS["sell_clamped"] += 1
        guarded.append(order)
        shed[item] = available - quantity
    return guarded


def _terminal_market(market, shed, obs):
    preserved = [
        deepcopy(order)
        for order in (market if isinstance(market, list) else [])
        if not (isinstance(order, list) and order and order[0] == "SELL")
    ][:10]
    prices = (obs.get("market", {}) or {}).get("prices", {}) if isinstance(obs, dict) else {}
    prices = prices if isinstance(prices, dict) else {}
    products = [item for item in PRODUCTS if shed.get(item, 0) > 0]
    products.sort(key=lambda item: (-shed[item] * _nonnegative_int(prices.get(item, 0)), item))
    for item in products[: 10 - len(preserved)]:
        preserved.append(["SELL", item, shed[item]])
    return preserved


def agent(obs, config=None):
    try:
        step = int(obs.get("step", 0) or 0)
    except (AttributeError, TypeError, ValueError):
        step = 0
    index = min(max(step, 0), RECORDED_ACTIONS - 1)
    original = deepcopy(SCHEDULE[index])
    action = deepcopy(original)
    _normalize_hands(action, obs)
    shed = _predicted_shed(action, obs)
    market = action.get("market", [])
    if SOURCE_MODE == "terminal_guard" and _nonnegative_int(obs.get("day", 0)) >= 29:
        rewritten = _terminal_market(market, shed, obs)
        if rewritten != market:
            _RESCUE_METRICS["terminal_rewritten"] += 1
        action["market"] = rewritten
    else:
        action["market"] = _guard_sells(market, shed)
    if action != original:
        _RESCUE_METRICS["actions_changed"] += 1
    return action
"""
        )
    compile(source, "<fixed_replay_schedule>", "exec")
    return source


def build_file(replay_path: Path, player: int, output: Path, mode: str = "fixed") -> dict[str, Any]:
    raw = replay_path.read_bytes()
    replay = json.loads(raw)
    replay_sha256 = _sha256(raw)
    actions = extract_actions(replay, player)
    metadata = _metadata(replay, player, replay_sha256)
    source = render_fixed_schedule(actions, metadata, mode=mode)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(source, encoding="utf-8", newline="\n")
    source_bytes = output.read_bytes()
    return {
        **metadata,
        "recorded_actions": len(actions),
        "episode_steps": EPISODE_STEPS,
        "mode": mode,
        "output": output.as_posix(),
        "output_sha256": _sha256(source_bytes),
        "output_bytes": len(source_bytes),
    }


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Render a replay seat as a fixed agent")
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--player", type=int, choices=(0, 1), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=MODES, default="fixed")
    args = parser.parse_args(argv)
    print(
        json.dumps(
            build_file(args.replay, args.player, args.output, mode=args.mode),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
