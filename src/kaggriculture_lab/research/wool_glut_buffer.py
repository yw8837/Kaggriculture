"""Build the single-delta Fa05 Wool Glut Buffer from the frozen Fa04 G1 bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from pathlib import Path

UPSTREAM_G1_SHA256 = (
    "81159A18DF3CD1A5CAABE5EDBBA0A597561775F77A49465FA39DF6802A706922"
)
DEFAULT_UPSTREAM = Path(
    "experiments/source_snapshots/fa04_top_trace/G1_sell_guard.py"
)
DEFAULT_OUTPUT = Path(
    "experiments/source_snapshots/fa05_wool_glut/W1_wool_glut_buffer.py"
)


_SUFFIX = r'''

# Fa05 one-delta derivative: Wool Glut Buffer.
# The Apache-2.0 attribution and upstream replay provenance remain at the top.
# Only legal SELL WOOL quantities may differ from the frozen G1 action.
WOOL_GLUT_MODE = "wool_glut_buffer"
UPSTREAM_G1_SHA256 = "81159A18DF3CD1A5CAABE5EDBBA0A597561775F77A49465FA39DF6802A706922"
_WOOL_METRIC_KEYS = (
    "eligible_trigger_turns",
    "create_requested_units",
    "create_observed_units",
    "sell_suppressed_orders",
    "release_requested_units",
    "release_observed_units",
    "release_orders",
    "pending_start",
    "pending_end",
    "causal_completed_reserve_release_units",
    "blocked_release_units",
    "fallback_count",
    "false_trigger_count",
    "outside_allowed_action_diff",
    "protected_lane_action_diff",
    "candidate_caused_overflow_or_discard_units",
    "impossible_sell_units",
    "terminal_pending",
    "terminal_wool_remaining",
)
_WOOL_METRICS = {key: 0 for key in _WOOL_METRIC_KEYS}
_WOOL_STATE = {}
_g1_agent = agent
_g1_rescue_metrics = rescue_metrics
_g1_reset_rescue_metrics = reset_rescue_metrics


def rescue_metrics():
    combined = _g1_rescue_metrics()
    combined.update(_WOOL_METRICS)
    return combined


def reset_rescue_metrics():
    _g1_reset_rescue_metrics()
    for key in _WOOL_METRIC_KEYS:
        _WOOL_METRICS[key] = 0
    _WOOL_STATE.clear()
    return rescue_metrics()


def _wool_plain_dict(value):
    return value if isinstance(value, dict) else None


def _wool_exact_int(value, minimum=0):
    if type(value) is not int or value < minimum:
        return None
    return value


def _wool_number(value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value != value or value in (float("inf"), float("-inf")) or value < minimum:
        return None
    return value


def _wool_player_context(obs):
    if not isinstance(obs, dict):
        return None
    player = _wool_exact_int(obs.get("player"))
    step = _wool_exact_int(obs.get("step"))
    day = _wool_exact_int(obs.get("day"))
    hour = _wool_exact_int(obs.get("hour"))
    farms = obs.get("farms")
    if (
        player is None
        or step is None
        or day is None
        or hour is None
        or hour >= 24
        or not isinstance(farms, list)
        or len(farms) != 2
        or player >= len(farms)
        or not isinstance(farms[player], dict)
        or not isinstance(farms[1 - player], dict)
    ):
        return None
    return player, step, day, hour, farms


def _wool_opponent_sheep(farm):
    tiles = farm.get("tiles") if isinstance(farm, dict) else None
    if not isinstance(tiles, list) or not tiles:
        return None
    count = 0
    for row in tiles:
        if not isinstance(row, list):
            return None
        for tile in row:
            if isinstance(tile, dict):
                kind = tile.get("kind")
                animal = tile.get("animal")
                if kind == "PASTURE" and animal == "SHEEP":
                    count += 1
                elif kind == "PASTURE" and animal is not None and not isinstance(animal, str):
                    return None
            elif tile is not None and tile != "LOCKED":
                return None
    return count


def _wool_market_state(obs):
    market = _wool_plain_dict(obs.get("market"))
    prices = _wool_plain_dict(market.get("prices")) if market is not None else None
    inventory = _wool_plain_dict(market.get("inventory")) if market is not None else None
    if prices is None or inventory is None or "WOOL" not in prices or "WOOL" not in inventory:
        return None
    price = _wool_number(prices["WOOL"])
    quantity = _wool_number(inventory["WOOL"])
    if price is None or quantity is None:
        return None
    return price, quantity


def _wool_capacity(config):
    if config is None:
        return 100, 10
    if not hasattr(config, "get"):
        return None
    shed_capacity = config.get("shedCapacity", 100)
    order_capacity = config.get("maxMarketOrdersPerTurn", 10)
    shed_capacity = _wool_exact_int(shed_capacity, 1)
    order_capacity = _wool_exact_int(order_capacity, 1)
    if shed_capacity is None or order_capacity != 10:
        return None
    return shed_capacity, order_capacity


def _wool_episode_steps(config):
    if config is None:
        return 720
    if not hasattr(config, "get"):
        return None
    return _wool_exact_int(config.get("episodeSteps", 720), 2)


def _wool_project_official(action, obs, config):
    """Project the official farmer-then-hands unit phase without touching input."""
    private = _wool_plain_dict(obs.get("private"))
    raw_shed = _wool_plain_dict(private.get("shed")) if private is not None else None
    raw_inventories = private.get("inventories") if private is not None else None
    farm = _current_farm(obs)
    raw_tiles = farm.get("tiles") if isinstance(farm, dict) else None
    capacities = _wool_capacity(config)
    if (
        raw_shed is None
        or not isinstance(raw_inventories, list)
        or capacities is None
        or not isinstance(raw_tiles, list)
        or not raw_tiles
        or any(
            not isinstance(row, list) or len(row) != len(raw_tiles)
            for row in raw_tiles
        )
    ):
        return None
    shed_capacity, _ = capacities
    tiles = deepcopy(raw_tiles)
    board_size = len(tiles)
    if config is not None:
        configured_size = config.get("boardSize", board_size)
        if _wool_exact_int(configured_size, 1) != board_size:
            return None
    shed = deepcopy(raw_shed)
    inventories = deepcopy(raw_inventories)
    truncation = 0
    units = [action.get("farmer"), *action.get("hands", [])]
    positions = [farm.get("farmer"), *(farm.get("hands", []) or [])]
    if len(units) != len(inventories) or len(positions) != len(inventories):
        return None
    adjacent = {
        (board_size // 2 - 1, board_size // 2 - 1),
        (board_size // 2, board_size // 2 - 1),
        (board_size // 2 - 1, board_size // 2),
        (board_size // 2, board_size // 2),
    }
    for unit_action, position, inventory in zip(units, positions, inventories):
        if (
            not isinstance(unit_action, list)
            or not unit_action
            or not isinstance(position, (list, tuple))
            or len(position) < 2
            or type(position[0]) is not int
            or type(position[1]) is not int
            or not isinstance(inventory, dict)
        ):
            return None
        x, y = position[0], position[1]
        if not (0 <= x < board_size and 0 <= y < board_size):
            return None
        tile = tiles[y][x]
        on_shed = (x, y) in adjacent and tiles[y][x] != "LOCKED"
        op = unit_action[0]
        if op == "DROP" and on_shed:
            for item, amount in list(inventory.items()):
                room = max(0, shed_capacity - sum(shed.values()))
                deposited = min(amount, room)
                if deposited:
                    shed[item] = shed.get(item, 0) + deposited
                truncation += amount - deposited
                del inventory[item]
        elif op == "PICKUP" and on_shed:
            if len(unit_action) not in (2, 3) or not isinstance(unit_action[1], str):
                return None
            amount = unit_action[2] if len(unit_action) == 3 else 1
            amount = _wool_exact_int(amount, 1)
            if amount is None:
                return None
            item = unit_action[1]
            taken = min(amount, shed.get(item, 0))
            if taken:
                shed[item] -= taken
                inventory[item] = inventory.get(item, 0) + taken
        elif op == "PLACE":
            if len(unit_action) not in (2, 3) or not isinstance(unit_action[1], str):
                return None
            item = unit_action[1]
            animal_structure = {"GOOSE": "COOP", "COW": "PASTURE", "SHEEP": "PASTURE"}
            if (
                item in animal_structure
                and isinstance(tile, dict)
                and tile.get("kind") == animal_structure[item]
                and "animal" not in tile
            ):
                if inventory.get(item, 0) > 0:
                    inventory[item] -= 1
                    if inventory[item] == 0:
                        del inventory[item]
                    tiles[y][x] = {
                        "kind": animal_structure[item],
                        "animal": item,
                        "placed_day": obs["day"],
                        "yield_units": 0,
                        "consecutive_unfed": 0,
                        "fed_today": False,
                        "cared_today": False,
                        "fertilizer_available": False,
                        "pending_care_bonus": 0,
                    }
            elif on_shed:
                amount = unit_action[2] if len(unit_action) == 3 else 1
                amount = _wool_exact_int(amount, 1)
                if amount is None:
                    return None
                deposited = min(amount, inventory.get(item, 0))
                room = max(0, shed_capacity - sum(shed.values()))
                deposited = min(deposited, room)
                if deposited:
                    inventory[item] -= deposited
                    if inventory[item] == 0:
                        del inventory[item]
                    shed[item] = shed.get(item, 0) + deposited
        elif op == "HARVEST" and isinstance(tile, dict):
            units = tile.get("yield_units")
            if _wool_exact_int(units, 1) is None:
                continue
            if tile.get("kind") == "PLANT":
                crop = tile.get("crop")
                crop_data = {
                    "WHEAT": (2, False),
                    "CARROT": (2, False),
                    "TOMATO": (8, True),
                    "STRAWBERRY": (10, True),
                    "MELON": (10, False),
                }.get(crop)
                planted_day = _wool_exact_int(tile.get("planted_day"))
                if crop_data is None or planted_day is None:
                    return None
                if obs["day"] - planted_day < crop_data[0]:
                    continue
                tile["yield_units"] = 0
                inventory[crop] = inventory.get(crop, 0) + units
                if not crop_data[1]:
                    tiles[y][x] = None
            elif "animal" in tile:
                product = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}.get(
                    tile.get("animal")
                )
                if product is None:
                    return None
                tile["yield_units"] = 0
                inventory[product] = inventory.get(product, 0) + units
        elif op == "FERTILIZE" and isinstance(tile, dict) and tile.get("kind") == "PLANT":
            if inventory.get("FERTILIZER", 0) > 0:
                inventory["FERTILIZER"] -= 1
                if inventory["FERTILIZER"] == 0:
                    del inventory["FERTILIZER"]
                tile["fertilized_until_day"] = max(
                    tile.get("fertilized_until_day", -1), obs["day"] + 2
                )
        elif op == "FEED" and isinstance(tile, dict) and "animal" in tile:
            if tile.get("fed_today") is False and inventory.get("WHEAT", 0) > 0:
                inventory["WHEAT"] -= 1
                if inventory["WHEAT"] == 0:
                    del inventory["WHEAT"]
                tile["fed_today"] = True
        elif op == "COLLECT_FERTILIZER" and isinstance(tile, dict) and "animal" in tile:
            if tile.get("fertilizer_available") is True:
                tile["fertilizer_available"] = False
                inventory["FERTILIZER"] = inventory.get("FERTILIZER", 0) + 1
    return {
        "shed": shed,
        "inventories": inventories,
        "total": sum(shed.values()),
        "wool": shed.get("WOOL", 0),
        "truncation": truncation,
        "tiles": tiles,
    }


def _wool_validate_private_and_action(action, obs, config):
    if not isinstance(action, dict):
        return None
    farmer = action.get("farmer")
    hands = action.get("hands")
    market = action.get("market")
    if (
        not isinstance(farmer, list)
        or not farmer
        or not isinstance(hands, list)
        or not all(isinstance(item, list) and item for item in hands)
        or not isinstance(market, list)
        or len(market) > 10
    ):
        return None
    for order in market:
        if not isinstance(order, list) or not order or not isinstance(order[0], str):
            return None
        if order[0] == "SELL":
            if len(order) != 3 or not isinstance(order[1], str):
                return None
            if _wool_exact_int(order[2], 1) is None:
                return None

    private = _wool_plain_dict(obs.get("private"))
    raw_shed = _wool_plain_dict(private.get("shed")) if private is not None else None
    inventories = private.get("inventories") if private is not None else None
    if raw_shed is None or not isinstance(inventories, list) or len(inventories) != len(hands) + 1:
        return None
    if any(not isinstance(item, str) or _wool_exact_int(quantity) is None for item, quantity in raw_shed.items()):
        return None
    for inventory in inventories:
        if not isinstance(inventory, dict):
            return None
        if any(
            not isinstance(item, str) or _wool_exact_int(quantity) is None
            for item, quantity in inventory.items()
        ):
            return None

    projected = _wool_project_official(action, obs, config)
    if (
        not isinstance(projected, dict)
        or any(
            _wool_exact_int(value) is None
            for value in projected.get("shed", {}).values()
        )
        or projected.get("total", _wool_capacity(config)[0] + 1)
        > _wool_capacity(config)[0]
    ):
        return None
    return projected, market


def _wool_sell_info(market):
    wool = []
    for index, order in enumerate(market):
        if order[0] == "SELL" and order[1] == "WOOL":
            quantity = order[2] if len(order) == 3 else 1
            wool.append((index, quantity))
        elif order[0] in ("BUY_PRODUCT", "BUY_ANIMAL") and len(order) >= 2 and order[1] == "WOOL":
            return None
    if len(wool) > 1:
        return None
    return wool[0] if wool else (None, 0)


def _wool_replace_sole_order(market, index, quantity):
    rewritten = deepcopy(market)
    if index is None:
        if quantity <= 0:
            return rewritten
        if len(rewritten) >= 10:
            return None
        rewritten.append(["SELL", "WOOL", quantity])
    elif quantity <= 0:
        del rewritten[index]
    else:
        rewritten[index] = ["SELL", "WOOL", quantity]
    return rewritten


def _wool_fallback(original):
    _WOOL_METRICS["fallback_count"] += 1
    return deepcopy(original)


def _wool_state_for(player, step):
    state = _WOOL_STATE.get(player)
    if (
        state is None
        or step == 0
        or type(state.get("last_step")) is not int
        or step != state["last_step"] + 1
    ):
        state = {"last_step": step, "pending_confirmed": 0, "inflight": None}
        _WOOL_STATE[player] = state
    return state


def _wool_reconcile(state, current_wool):
    inflight = state.get("inflight")
    if not isinstance(inflight, dict):
        return
    units = inflight["units"]
    if current_wool == inflight["expected_wool"]:
        if inflight["kind"] == "create":
            state["pending_confirmed"] += units
            _WOOL_METRICS["create_observed_units"] += units
        else:
            completed = min(units, state["pending_confirmed"])
            state["pending_confirmed"] -= completed
            _WOOL_METRICS["release_observed_units"] += completed
            _WOOL_METRICS["causal_completed_reserve_release_units"] += completed
    elif inflight["kind"] == "release":
        _WOOL_METRICS["blocked_release_units"] += units
    else:
        _WOOL_METRICS["false_trigger_count"] += 1
    state["inflight"] = None


def _wool_postmarket_projection(projection, market, hour, capacity):
    shed = deepcopy(projection["shed"])
    impossible = 0
    if hour == 23 and any(order[0] in ("BUY_PRODUCT", "BUY_ANIMAL") for order in market):
        return None
    for order in market:
        if order[0] != "SELL":
            continue
        item = order[1]
        quantity = order[2] if len(order) == 3 else 1
        available = shed.get(item, 0)
        if quantity > available:
            impossible += quantity - available
            return {"impossible": impossible}
        shed[item] = available - quantity
    discarded = 0
    if hour == 23:
        for inventory in projection["inventories"]:
            for item, quantity in inventory.items():
                if item == "SEED":
                    continue
                room = max(0, capacity - sum(shed.values()))
                deposited = min(quantity, room)
                shed[item] = shed.get(item, 0) + deposited
                discarded += quantity - deposited
    return {"shed": shed, "discarded": discarded, "impossible": impossible}


def _wool_record_terminal(state, projection, market, hour, capacity):
    post = _wool_postmarket_projection(projection, market, hour, capacity)
    _WOOL_METRICS["terminal_pending"] = state["pending_confirmed"]
    if post is not None and not post.get("impossible", 0):
        _WOOL_METRICS["terminal_wool_remaining"] = post["shed"].get("WOOL", 0)
    else:
        sell = _wool_sell_info(market)
        intended = sell[1] if sell is not None else 0
        _WOOL_METRICS["terminal_wool_remaining"] = max(
            0, projection["wool"] - intended
        )


def _wool_only_allowed_delta(original, candidate):
    if original.get("farmer") != candidate.get("farmer") or original.get("hands") != candidate.get("hands"):
        return False
    original_market = original.get("market")
    candidate_market = candidate.get("market")
    if not isinstance(original_market, list) or not isinstance(candidate_market, list):
        return False
    original_nonwool = [
        order
        for order in original_market
        if not (order[0] == "SELL" and order[1] == "WOOL")
    ]
    candidate_nonwool = [
        order
        for order in candidate_market
        if not (order[0] == "SELL" and order[1] == "WOOL")
    ]
    return (
        original_nonwool == candidate_nonwool
        and len(candidate_market) <= 10
        and sum(order[0] == "SELL" and order[1] == "WOOL" for order in candidate_market)
        <= 1
    )


def _apply_wool_glut_buffer(g1_action, obs, config=None):
    original = deepcopy(g1_action)
    context = _wool_player_context(obs)
    if context is None:
        return original
    player, step, day, hour, farms = context
    sheep = _wool_opponent_sheep(farms[1 - player])
    shared_market = _wool_market_state(obs)
    validated = _wool_validate_private_and_action(original, obs, config)
    episode_steps = _wool_episode_steps(config)
    if sheep is None or shared_market is None or validated is None or episode_steps is None:
        return original
    price, market_inventory = shared_market
    projected, market = validated
    sell = _wool_sell_info(market)
    if sell is None:
        return original
    wool_index, intended = sell
    available = projected["wool"]
    if intended > available:
        _WOOL_METRICS["impossible_sell_units"] += intended - available
        return _wool_fallback(original)
    state = _wool_state_for(player, step)
    current_wool = obs["private"]["shed"].get("WOOL", 0)
    _wool_reconcile(state, current_wool)
    state["last_step"] = step
    _WOOL_METRICS["pending_start"] = state["pending_confirmed"]
    _WOOL_METRICS["pending_end"] = state["pending_confirmed"]

    if step >= episode_steps - 2:
        _wool_record_terminal(
            state, projected, market, hour, _wool_capacity(config)[0]
        )
        return original

    if sheep < 4:
        return original
    trigger = day < 28 and price < 200 and market_inventory > 10000 and intended > 0
    release = day >= 28 or (day < 28 and (price >= 200 or market_inventory < 10000))
    action = deepcopy(original)
    if trigger:
        remainder = available - intended
        create = min(intended, max(0, 20 - remainder))
        if projected["total"] > 80 or projected["truncation"] > 0 or create <= 0:
            _WOOL_METRICS["false_trigger_count"] += 1
            return original
        _WOOL_METRICS["eligible_trigger_turns"] += 1
        rewritten = _wool_replace_sole_order(market, wool_index, intended - create)
        if rewritten is None:
            return _wool_fallback(original)
        post = _wool_postmarket_projection(
            projected, rewritten, hour, _wool_capacity(config)[0]
        )
        if post is not None and post.get("impossible", 0):
            _WOOL_METRICS["impossible_sell_units"] += post["impossible"]
        if post is None or post.get("impossible", 0) or post.get("discarded", 0):
            return _wool_fallback(original)
        action["market"] = rewritten
        _WOOL_METRICS["sell_suppressed_orders"] += 1
        _WOOL_METRICS["create_requested_units"] += create
        state["inflight"] = {
            "kind": "create",
            "units": create,
            "expected_wool": post["shed"].get("WOOL", 0),
        }
    elif release and state["pending_confirmed"] > 0:
        room = available - intended
        release_cap = (
            state["pending_confirmed"]
            if day >= 28
            else min(4, state["pending_confirmed"])
        )
        released = min(release_cap, max(0, room))
        if released <= 0 or (wool_index is None and len(market) >= 10):
            _WOOL_METRICS["blocked_release_units"] += release_cap
            if day >= 28:
                _wool_record_terminal(
                    state, projected, market, hour, _wool_capacity(config)[0]
                )
            return original
        rewritten = _wool_replace_sole_order(market, wool_index, intended + released)
        if rewritten is None:
            _WOOL_METRICS["blocked_release_units"] += release_cap
            return original
        post = _wool_postmarket_projection(
            projected, rewritten, hour, _wool_capacity(config)[0]
        )
        if post is not None and post.get("impossible", 0):
            _WOOL_METRICS["impossible_sell_units"] += post["impossible"]
        if post is None or post.get("impossible", 0) or post.get("discarded", 0):
            _WOOL_METRICS["blocked_release_units"] += released
            if day >= 28:
                _wool_record_terminal(
                    state, projected, market, hour, _wool_capacity(config)[0]
                )
            return original
        action["market"] = rewritten
        _WOOL_METRICS["release_orders"] += 1
        _WOOL_METRICS["release_requested_units"] += released
        state["inflight"] = {
            "kind": "release",
            "units": released,
            "expected_wool": post["shed"].get("WOOL", 0),
        }
    if day >= 28:
        _wool_record_terminal(
            state, projected, action["market"], hour, _wool_capacity(config)[0]
        )
    _WOOL_METRICS["pending_end"] = state["pending_confirmed"]
    if action != original and not _wool_only_allowed_delta(original, action):
        _WOOL_METRICS["outside_allowed_action_diff"] += 1
        state["inflight"] = None
        return _wool_fallback(original)
    return action


def agent(obs, config=None):
    g1_action = _g1_agent(obs, config)
    return _apply_wool_glut_buffer(g1_action, obs, config)
'''


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def render_source(upstream: bytes) -> bytes:
    actual = sha256(upstream)
    if actual != UPSTREAM_G1_SHA256:
        raise ValueError(
            f"frozen G1 SHA mismatch: expected {UPSTREAM_G1_SHA256}, got {actual}"
        )
    text = upstream.decode("utf-8")
    if "# Upstream license: Apache-2.0" not in text or "def agent(obs, config=None):" not in text:
        raise ValueError("frozen G1 attribution or agent marker missing")
    output = (text + _SUFFIX).encode("utf-8")
    compile(output, "<fa05_wool_glut_buffer>", "exec")
    return output


def build_file(upstream_path: Path, output_path: Path) -> dict[str, object]:
    upstream = upstream_path.read_bytes()
    output = render_source(upstream)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(output)
    return {
        "upstream": upstream_path.as_posix(),
        "upstream_sha256": sha256(upstream),
        "output": output_path.as_posix(),
        "output_sha256": sha256(output),
        "output_bytes": len(output),
    }


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, default=DEFAULT_UPSTREAM)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    print(json.dumps(build_file(args.upstream, args.output), sort_keys=True))


if __name__ == "__main__":
    main()
