"""Reconstruct Kaggriculture market execution from raw replay transitions.

The official engine processes the two seats together: one market-order slot at a
time and, within a quantity order, one unit from each seat at a time.  This
module mirrors that ordering and records *accepted* quantities; raw requested
quantities alone can substantially overstate actual trading.

Only :func:`main` writes output.  The analysis functions are read-only and
return JSON-serialisable dictionaries.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from kaggle_environments.envs.kaggriculture import kaggriculture as official

JsonObject = dict[str, Any]


def _configuration_value(configuration: Mapping[str, Any], key: str, default: Any) -> Any:
    value = configuration.get(key, default)
    return default if value is None else value


def _declared_quantity(order: Any) -> int | None:
    if not isinstance(order, list) or not order:
        return None
    if order[0] in ("HIRE", "BUY_LAND"):
        return 1
    if len(order) < 3:
        return None
    try:
        return int(order[2])
    except (TypeError, ValueError):
        return None


def _new_order_record(seat: int, slot: int, order: Any, max_orders: int) -> JsonObject:
    parsed = official._parse_order(order)
    record: JsonObject = {
        "seat": seat,
        "slot": slot,
        "raw_order": copy.deepcopy(order),
        "type": parsed["type"] if parsed else None,
        "item": parsed.get("item") if parsed else None,
        "requested_quantity": _declared_quantity(order),
        "accepted_quantity": 0,
        "rejected_quantity": None,
        "cash_delta": 0,
        "market_inventory_delta": {},
        "dropped_by_order_cap": slot >= max_orders,
        "status": "pending",
        "failure_reason": None,
        "unit_price_counts": [],
        "_prices": Counter(),
    }
    if slot >= max_orders:
        record["status"] = "dropped"
        record["failure_reason"] = "order_cap"
    elif parsed is None:
        record["status"] = "failed"
        record["failure_reason"] = "invalid"
    return record


def _finalize_order(record: JsonObject) -> None:
    prices: Counter[int] = record.pop("_prices")
    record["unit_price_counts"] = [
        {"price": price, "accepted_quantity": count} for price, count in sorted(prices.items())
    ]
    requested = record["requested_quantity"]
    accepted = record["accepted_quantity"]
    if isinstance(requested, int) and requested >= 0 and isinstance(accepted, int):
        record["rejected_quantity"] = max(0, requested - accepted)
    if record["status"] != "pending":
        return
    if accepted == requested:
        record["status"] = "accepted"
    elif accepted:
        record["status"] = "partial"
    else:
        record["status"] = "failed"


def _apply_unit_actions(
    farms: list[JsonObject],
    privates: list[JsonObject],
    actions: Sequence[Any],
    configuration: Mapping[str, Any],
) -> None:
    """Advance only the unit-action phase that precedes the market phase."""

    board_size = int(_configuration_value(configuration, "boardSize", 10))
    turns_per_day = max(1, int(_configuration_value(configuration, "turnsPerDay", 24)))
    shed_capacity = int(_configuration_value(configuration, "shedCapacity", 100))
    step = 0
    if farms:
        # Day is passed separately below; this local merely documents that unit
        # actions never advance the replay clock.
        step = 0
    del step

    for seat in range(min(2, len(farms), len(privates), len(actions))):
        action = actions[seat] if isinstance(actions[seat], dict) else {}
        farmer_action = action.get("farmer", ["PASS"])
        hands_actions = action.get("hands", [])
        if not isinstance(hands_actions, list):
            hands_actions = []
        unit_actions = [farmer_action, *hands_actions]
        plant_demand: Counter[str] = Counter()
        for unit_action in unit_actions:
            if (
                isinstance(unit_action, list)
                and len(unit_action) >= 2
                and unit_action[0] == "PLANT"
            ):
                plant_demand[str(unit_action[1])] += 1
        seeds = privates[seat].get("seeds", {})
        blocked = {crop for crop, count in plant_demand.items() if count > seeds.get(crop, 0)}

        day = int(configuration.get("_observation_day", 0))

        def allowed(unit_action: Any, blocked_crops: set[str] = blocked) -> Any:
            if (
                isinstance(unit_action, list)
                and len(unit_action) >= 2
                and unit_action[0] == "PLANT"
                and unit_action[1] in blocked_crops
            ):
                return ["PASS"]
            return unit_action

        official._apply_unit_action(
            farms[seat],
            privates[seat],
            0,
            allowed(farmer_action),
            board_size,
            day,
            turns_per_day,
            shed_capacity,
        )
        for hand_index, hand_action in enumerate(hands_actions):
            official._apply_unit_action(
                farms[seat],
                privates[seat],
                hand_index + 1,
                allowed(hand_action),
                board_size,
                day,
                turns_per_day,
                shed_capacity,
            )


def _failure_reason(op: str, item: str, farm: JsonObject, private: JsonObject) -> str:
    if op == "SELL":
        return "inventory" if private["shed"].get(item, 0) <= 0 else "invalid"
    if op in ("BUY_PRODUCT", "BUY_SEED", "BUY_ANIMAL"):
        return "cash"
    return "invalid"


def _record_commit(
    record: JsonObject,
    item: str,
    price: int,
    money_before: float,
    inventory_before: int | None,
    farm: JsonObject,
    market: JsonObject,
) -> None:
    record["accepted_quantity"] += 1
    record["cash_delta"] += farm["money"] - money_before
    if inventory_before is not None:
        inventory_delta = market["inventory"][item] - inventory_before
        if inventory_delta:
            current = record["market_inventory_delta"].get(item, 0)
            record["market_inventory_delta"][item] = current + inventory_delta
    record["_prices"][int(price)] += 1


def _process_known_market(
    farms: list[JsonObject],
    privates: list[JsonObject],
    market: JsonObject,
    actions: Sequence[Any],
    records: list[JsonObject],
    configuration: Mapping[str, Any],
) -> None:
    max_orders = max(1, int(_configuration_value(configuration, "maxMarketOrdersPerTurn", 10)))
    board_size = int(_configuration_value(configuration, "boardSize", 10))
    hire_mult = int(_configuration_value(configuration, "farmHandCostMult", 1))
    records_by_key = {(row["seat"], row["slot"]): row for row in records}
    queues: list[list[Any]] = []
    for seat in range(2):
        action = actions[seat] if isinstance(actions[seat], dict) else {}
        raw_market = action.get("market", [])
        queue = list(raw_market) if isinstance(raw_market, list) else []
        queues.append(queue[:max_orders])

    max_len = max((len(queue) for queue in queues), default=0)
    for slot in range(max_len):
        order_states: list[JsonObject | None] = []
        for seat, queue in enumerate(queues):
            parsed = official._parse_order(queue[slot]) if slot < len(queue) else None
            if parsed is not None:
                parsed = {**parsed, "record": records_by_key[(seat, slot)]}
            order_states.append(parsed)

        # The official engine handles atomic orders once, in seat order, before
        # either seat's unit-priced order in the same slot.
        for seat, order_state in enumerate(order_states):
            if order_state is None:
                continue
            op = order_state["type"]
            record = order_state["record"]
            if op == "HIRE":
                money_before = farms[seat]["money"]
                hands_before = len(farms[seat]["hands"])
                cost = official._hire_cost(farms[seat]["hires_today"], hire_mult)
                official._do_hire(farms[seat], privates[seat], board_size, hire_mult)
                accepted = int(len(farms[seat]["hands"]) > hands_before)
                record["accepted_quantity"] = accepted
                record["cash_delta"] = farms[seat]["money"] - money_before
                if not accepted:
                    record["failure_reason"] = "cash" if money_before < cost else "invalid"
                order_states[seat] = None
            elif op == "BUY_LAND":
                money_before = farms[seat]["money"]
                land_before = len(farms[seat]["unlocked_quadrants"])
                extra_before = land_before - 1
                exhausted = extra_before >= len(official.LAND_ORDER)
                cost = None if exhausted else official.LAND_PRICES[extra_before]
                official._do_buy_land(farms[seat], board_size)
                accepted = int(len(farms[seat]["unlocked_quadrants"]) > land_before)
                record["accepted_quantity"] = accepted
                record["cash_delta"] = farms[seat]["money"] - money_before
                if not accepted:
                    record["failure_reason"] = (
                        "land_exhausted"
                        if exhausted
                        else "cash"
                        if cost is not None and money_before < cost
                        else "invalid"
                    )
                order_states[seat] = None

        # Quote both seats from the same pre-commit market state, then commit in
        # seat order.  This is the subtle interaction that a seat-by-seat parser
        # would get wrong.
        iterations = 0
        while True:
            iterations += 1
            if iterations >= 100_000:
                for order_state in order_states:
                    if order_state is not None and order_state.get("remaining", 0) > 0:
                        order_state["record"]["failure_reason"] = "engine_iteration_cap"
                break
            quoted: list[tuple[str, str, int, JsonObject] | None] = [None, None]
            for seat, order_state in enumerate(order_states):
                if order_state is None or order_state.get("remaining", 0) <= 0:
                    continue
                op = order_state["type"]
                item = order_state["item"]
                if op == "SELL" and item in official.PRODUCTS:
                    price = official.market_price(
                        item, market["inventory"][item], market.get("params")
                    )
                    quoted[seat] = (op, item, price, order_state)
                elif op == "BUY_PRODUCT" and item in ("WHEAT", "FERTILIZER"):
                    price = official.market_price(
                        item, market["inventory"][item] - 1, market.get("params")
                    )
                    quoted[seat] = (op, item, price, order_state)
                elif op == "BUY_SEED" and item in official.CROPS:
                    quoted[seat] = (op, item, official.CROPS[item]["seed"], order_state)
                elif op == "BUY_ANIMAL" and item in official.ANIMALS:
                    quoted[seat] = (op, item, official.ANIMALS[item]["cost"], order_state)
                else:
                    order_state["record"]["failure_reason"] = "invalid"
                    order_states[seat] = None

            if all(quote is None for quote in quoted):
                break

            committed_any = False
            for seat, quote in enumerate(quoted):
                if quote is None:
                    continue
                op, item, price, order_state = quote
                money_before = farms[seat]["money"]
                inventory_before = market["inventory"].get(item)
                accepted = official._commit_unit(
                    op, item, price, farms[seat], privates[seat], market
                )
                if accepted:
                    order_state["remaining"] -= 1
                    _record_commit(
                        order_state["record"],
                        item,
                        price,
                        money_before,
                        inventory_before,
                        farms[seat],
                        market,
                    )
                    committed_any = True
                else:
                    order_state["record"]["failure_reason"] = _failure_reason(
                        op, item, farms[seat], privates[seat]
                    )
                    order_states[seat] = None
            if not committed_any:
                break

        official._refresh_prices(market)


def _market_orders(actions: Sequence[Any], max_orders: int) -> list[JsonObject]:
    records: list[JsonObject] = []
    for seat, action in enumerate(actions[:2]):
        if not isinstance(action, dict):
            continue
        orders = action.get("market", [])
        if not isinstance(orders, list):
            continue
        records.extend(
            _new_order_record(seat, slot, order, max_orders) for slot, order in enumerate(orders)
        )
    return sorted(records, key=lambda row: (row["slot"], row["seat"]))


def _mapping_delta(before: Mapping[str, Any], after: Mapping[str, Any]) -> JsonObject:
    result: JsonObject = {}
    for key in sorted(set(before) | set(after)):
        delta = after.get(key, 0) - before.get(key, 0)
        if delta:
            result[key] = delta
    return result


def _mapping_mismatches(
    field: str, expected: Mapping[str, Any], observed: Mapping[str, Any]
) -> list[JsonObject]:
    mismatches = []
    for key in sorted(set(expected) | set(observed)):
        if expected.get(key) != observed.get(key):
            mismatches.append(
                {
                    "field": f"{field}.{key}",
                    "expected": expected.get(key),
                    "observed": observed.get(key),
                }
            )
    return mismatches


def _expected_market_after_town(
    market_after_orders: JsonObject,
    town: Mapping[str, Any],
    step: int,
    configuration: Mapping[str, Any],
) -> JsonObject:
    market = copy.deepcopy(market_after_orders)
    shop_interval = max(1, int(_configuration_value(configuration, "townShopSellInterval", 4)))
    center_interval = max(1, int(_configuration_value(configuration, "townCenterSellInterval", 12)))
    turns_per_day = max(1, int(_configuration_value(configuration, "turnsPerDay", 24)))
    day = step // turns_per_day
    if step % shop_interval == 0:
        for shop_name in town.get("unlocked_shops", []):
            products = official.SHOPS[shop_name]
            multiplier = 2 if len(products) == 1 else 1
            for item in products:
                market["inventory"][item] -= multiplier
    if step % center_interval == 0:
        center_multiplier = next(
            multiplier
            for threshold, multiplier in official.TOWN_CENTER_DEMAND_SCHEDULE
            if day >= threshold
        )
        for item in official.TOWN_CENTER_PRODUCTS:
            market["inventory"][item] -= center_multiplier
    official._refresh_prices(market)
    return market


def _compare_raw_after(
    farms: list[JsonObject],
    privates: list[JsonObject],
    market: JsonObject,
    raw_after: Sequence[Mapping[str, Any]],
    pre_public: Mapping[str, Any],
    configuration: Mapping[str, Any],
) -> JsonObject:
    if not raw_after:
        return {"available": False, "mismatches": [], "matches": None}
    step = int(pre_public.get("step", 0))
    expected_market = _expected_market_after_town(
        market, pre_public.get("town", {}), step, configuration
    )
    observed_public = raw_after[0]
    observed_market = observed_public.get("market", {})
    mismatches = _mapping_mismatches(
        "market.inventory",
        expected_market.get("inventory", {}),
        observed_market.get("inventory", {}),
    )
    mismatches.extend(
        _mapping_mismatches(
            "market.prices",
            expected_market.get("prices", {}),
            observed_market.get("prices", {}),
        )
    )
    observed_farms = observed_public.get("farms", [])
    for seat in range(min(2, len(farms), len(observed_farms))):
        if farms[seat].get("money") != observed_farms[seat].get("money"):
            mismatches.append(
                {
                    "field": f"farms.{seat}.money",
                    "expected": farms[seat].get("money"),
                    "observed": observed_farms[seat].get("money"),
                }
            )

    turns_per_day = max(1, int(_configuration_value(configuration, "turnsPerDay", 24)))
    end_of_day = (step + 1) % turns_per_day == 0
    skipped = []
    if end_of_day:
        skipped.append("private state: official end-of-day inventory drop/reset follows market")
    else:
        for seat in range(min(2, len(privates), len(raw_after))):
            observed_private = raw_after[seat].get("private", {})
            for key in ("shed", "seeds"):
                mismatches.extend(
                    _mapping_mismatches(
                        f"private.{seat}.{key}",
                        privates[seat].get(key, {}),
                        observed_private.get(key, {}),
                    )
                )
            if privates[seat].get("inventories") != observed_private.get("inventories"):
                mismatches.append(
                    {
                        "field": f"private.{seat}.inventories",
                        "expected": privates[seat].get("inventories"),
                        "observed": observed_private.get("inventories"),
                    }
                )
    return {
        "available": True,
        "matches": not mismatches,
        "mismatches": mismatches,
        "skipped": skipped,
    }


def reconstruct_market_turn(
    pre_observations: Sequence[Mapping[str, Any]],
    actions: Sequence[Any],
    configuration: Mapping[str, Any] | None = None,
    *,
    raw_after: Sequence[Mapping[str, Any]] | None = None,
    apply_unit_actions: bool = True,
) -> JsonObject:
    """Reconstruct one transition's market phase for both seats.

    ``pre_observations`` are the observations at step ``t`` and ``actions`` are
    the actions stored in replay step ``t + 1``.  Supplying both seats is
    required for exact price/cash reconstruction.  A missing opposing seat is
    reported as ``unknown_opponent_interleave`` instead of guessed.
    """

    if not pre_observations:
        raise ValueError("at least one pre-action observation is required")
    config: JsonObject = dict(configuration or {})
    pre_public = pre_observations[0]
    config["_observation_day"] = int(pre_public.get("day", 0))
    farms = copy.deepcopy(pre_public.get("farms", []))
    market = copy.deepcopy(pre_public.get("market", {}))
    privates = [
        copy.deepcopy(pre_observations[seat].get("private", {}))
        for seat in range(min(2, len(pre_observations)))
    ]
    max_orders = max(1, int(_configuration_value(config, "maxMarketOrdersPerTurn", 10)))
    records = _market_orders(actions, max_orders)
    exact = len(farms) >= 2 and len(privates) >= 2 and len(actions) >= 2

    if exact:
        if apply_unit_actions:
            _apply_unit_actions(farms, privates, actions, config)
        money_before_market = [farms[seat].get("money", 0) for seat in range(2)]
        inventory_before_market = copy.deepcopy(market.get("inventory", {}))
        _process_known_market(farms, privates, market, actions, records, config)
    else:
        money_before_market = None
        inventory_before_market = copy.deepcopy(market.get("inventory", {}))
        for record in records:
            if record["status"] == "pending":
                record["status"] = "unknown"
                record["accepted_quantity"] = None
                record["cash_delta"] = None
                record["market_inventory_delta"] = None
                record["failure_reason"] = "unknown_opponent_interleave"

    for record in records:
        _finalize_order(record)

    comparison = (
        _compare_raw_after(farms, privates, market, raw_after, pre_public, config)
        if exact and raw_after is not None
        else {"available": False, "matches": None, "mismatches": []}
    )
    return {
        "step": int(pre_public.get("step", 0)),
        "day": int(pre_public.get("day", 0)),
        "hour": int(pre_public.get("hour", 0)),
        "exact": exact,
        "orders": records,
        "cash_before_market": money_before_market,
        "cash_after_market": (
            [farms[seat].get("money", 0) for seat in range(2)] if exact else None
        ),
        "cash_delta_by_seat": (
            [farms[seat].get("money", 0) - money_before_market[seat] for seat in range(2)]
            if exact and money_before_market is not None
            else None
        ),
        "market_inventory_before": inventory_before_market,
        "market_inventory_after": copy.deepcopy(market.get("inventory", {})),
        "market_inventory_delta": (
            _mapping_delta(inventory_before_market, market.get("inventory", {})) if exact else None
        ),
        "raw_after_comparison": comparison,
    }


def _summarize_turns(turns: Sequence[JsonObject]) -> JsonObject:
    by_seat: list[JsonObject] = []
    for seat in range(2):
        requested: Counter[str] = Counter()
        accepted: Counter[str] = Counter()
        failures: Counter[str] = Counter()
        cash_delta = 0
        cap_drops = 0
        for turn in turns:
            for order in turn["orders"]:
                if order["seat"] != seat:
                    continue
                key = order["type"] or "INVALID"
                quantity = order["requested_quantity"]
                if isinstance(quantity, int) and quantity > 0:
                    requested[key] += quantity
                accepted_quantity = order["accepted_quantity"]
                if isinstance(accepted_quantity, int):
                    accepted[key] += accepted_quantity
                if isinstance(order["cash_delta"], (int, float)):
                    cash_delta += order["cash_delta"]
                if order["failure_reason"]:
                    failures[order["failure_reason"]] += 1
                cap_drops += int(order["dropped_by_order_cap"])
        by_seat.append(
            {
                "seat": seat,
                "requested_quantity_by_type": dict(requested),
                "accepted_quantity_by_type": dict(accepted),
                "cash_delta": cash_delta,
                "failed_or_partial_orders_by_reason": dict(failures),
                "orders_dropped_by_cap": cap_drops,
            }
        )
    comparisons = [turn["raw_after_comparison"] for turn in turns]
    return {
        "market_turns": len(turns),
        "orders": sum(len(turn["orders"]) for turn in turns),
        "exact_turns": sum(bool(turn["exact"]) for turn in turns),
        "raw_comparisons": sum(bool(row["available"]) for row in comparisons),
        "raw_comparison_mismatches": sum(len(row.get("mismatches", [])) for row in comparisons),
        "by_seat": by_seat,
    }


def analyze_replay(replay: Mapping[str, Any]) -> JsonObject:
    """Analyze all market-bearing transitions in one decoded raw replay."""

    steps = replay.get("steps", [])
    configuration = replay.get("configuration", {})
    turns = []
    for state_index in range(1, len(steps)):
        previous_state = steps[state_index - 1]
        current_state = steps[state_index]
        pre_observations = [agent.get("observation", {}) for agent in previous_state[:2]]
        actions = [agent.get("action") for agent in current_state[:2]]
        has_market = any(
            isinstance(action, dict) and bool(action.get("market")) for action in actions
        )
        if not has_market:
            continue
        raw_after = [agent.get("observation", {}) for agent in current_state[:2]]
        turn = reconstruct_market_turn(
            pre_observations,
            actions,
            configuration,
            raw_after=raw_after,
        )
        turn["state_index"] = state_index
        turns.append(turn)
    info = replay.get("info", {})
    return {
        "schema_version": 1,
        "episode_id": info.get("EpisodeId", replay.get("id")),
        "teams": info.get("TeamNames"),
        "engine_module_version": replay.get("module_version"),
        "summary": _summarize_turns(turns),
        "turns": turns,
    }


def run(replay_path: Path) -> JsonObject:
    """Read and analyze one replay without writing any files."""

    raw = replay_path.read_bytes()
    report = analyze_replay(json.loads(raw))
    report["source"] = replay_path.as_posix()
    report["source_sha256"] = hashlib.sha256(raw).hexdigest().upper()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reconstruct requested and accepted Kaggriculture market orders"
    )
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.replay)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "episode_id": report["episode_id"],
                "market_turns": report["summary"]["market_turns"],
                "orders": report["summary"]["orders"],
                "raw_comparison_mismatches": report["summary"]["raw_comparison_mismatches"],
                "output": str(args.output),
            }
        )
    )


if __name__ == "__main__":
    main()
