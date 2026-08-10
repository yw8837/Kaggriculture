"""Build the guarded Kag_04 Tetsu-v16 late-inventory liquidation derivative."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any

TETSU_V16_SHA256 = "997E6BFC5234534E246E945BC61C87858EBF997AB85B0A5C9427DD4ED710F1B6"
TETSU_V16_BASE_PATH = Path("research/campaign_3000/06_candidates/snapshots/tetsu_v16.py")

_RUNTIME = r'''
# KAG04_TETSU_V16_LATE_INVENTORY_LIQUIDATION
# The overlay has one treatment: in the observable final four hours only, append
# stock-safe SELLs for unreserved FERTILIZER and WHEAT. It never changes an
# existing base order, farmer action, or hand action.
_KAG04_MAX_MARKET_ORDERS = 10
_KAG04_LIQUIDATABLE = ("FERTILIZER", "WHEAT")
_KAG04_PRODUCTS = {
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"
}
_KAG04_METRICS = {
    "calls": 0,
    "terminal_window": 0,
    "applied": 0,
    "added_orders": 0,
    "added_fertilizer_units": 0,
    "added_wheat_units": 0,
    "fallback_not_terminal": 0,
    "fallback_malformed": 0,
    "fallback_conflict": 0,
    "fallback_order_limit": 0,
    "fallback_no_inventory": 0,
}


def kag04_metrics():
    return dict(_KAG04_METRICS)


def reset_kag04_metrics():
    for key in _KAG04_METRICS:
        _KAG04_METRICS[key] = 0


def get_metrics():
    return kag04_metrics()


def rescue_metrics():
    return kag04_metrics()


def reset_rescue_metrics():
    reset_kag04_metrics()
    return kag04_metrics()


def _kag04_late_shed(obs):
    if not isinstance(obs, dict):
        return "malformed", None
    day = obs.get("day")
    hour = obs.get("hour")
    private = obs.get("private")
    if (
        not isinstance(day, int)
        or isinstance(day, bool)
        or not isinstance(hour, int)
        or isinstance(hour, bool)
        or not isinstance(private, dict)
    ):
        return "malformed", None
    shed = private.get("shed")
    if not isinstance(shed, dict):
        return "malformed", None
    if day != 29 or hour < 20 or hour >= 24:
        return "not_terminal", None
    quantities = {}
    for item in _KAG04_LIQUIDATABLE:
        quantity = shed.get(item, 0)
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 0:
            return "malformed", None
        quantities[item] = quantity
    return "terminal", quantities


def _kag04_valid_base_market(base_action, shed):
    if not isinstance(base_action, dict):
        return "malformed", None
    market = base_action.get("market")
    if not isinstance(market, list) or len(market) > _KAG04_MAX_MARKET_ORDERS:
        return "malformed", None
    reserved = {item: 0 for item in _KAG04_LIQUIDATABLE}
    for order in market:
        if not isinstance(order, list) or not order or not isinstance(order[0], str):
            return "malformed", None
        op = order[0]
        if op in ("HIRE", "BUY_LAND"):
            if len(order) != 1:
                return "malformed", None
            continue
        if op not in ("SELL", "BUY_PRODUCT", "BUY_SEED", "BUY_ANIMAL"):
            return "malformed", None
        if (
            len(order) != 3
            or not isinstance(order[1], str)
            or not isinstance(order[2], int)
            or isinstance(order[2], bool)
            or order[2] <= 0
        ):
            return "malformed", None
        item = order[1]
        if op == "SELL":
            if item not in _KAG04_PRODUCTS:
                return "malformed", None
            if item in reserved:
                reserved[item] += order[2]
        elif op == "BUY_PRODUCT":
            if item not in _KAG04_LIQUIDATABLE:
                return "malformed", None
            return "conflict", None
        elif op == "BUY_SEED":
            if item not in {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"}:
                return "malformed", None
        elif item not in {"GOOSE", "COW", "SHEEP"}:
            return "malformed", None
    if any(reserved[item] > shed[item] for item in _KAG04_LIQUIDATABLE):
        return "conflict", None
    return "valid", (market, reserved)


def _kag04_overlay(obs, base_action):
    _KAG04_METRICS["calls"] += 1
    window, shed = _kag04_late_shed(obs)
    if window == "malformed":
        _KAG04_METRICS["fallback_malformed"] += 1
        return base_action
    if window == "not_terminal":
        _KAG04_METRICS["fallback_not_terminal"] += 1
        return base_action
    _KAG04_METRICS["terminal_window"] += 1
    market_state, payload = _kag04_valid_base_market(base_action, shed)
    if market_state == "malformed":
        _KAG04_METRICS["fallback_malformed"] += 1
        return base_action
    if market_state == "conflict":
        _KAG04_METRICS["fallback_conflict"] += 1
        return base_action
    market, reserved = payload
    additions = [
        ["SELL", item, shed[item] - reserved[item]]
        for item in _KAG04_LIQUIDATABLE
        if shed[item] - reserved[item] > 0
    ]
    if not additions:
        _KAG04_METRICS["fallback_no_inventory"] += 1
        return base_action
    if len(market) + len(additions) > _KAG04_MAX_MARKET_ORDERS:
        _KAG04_METRICS["fallback_order_limit"] += 1
        return base_action
    candidate = dict(base_action)
    candidate["market"] = [*market, *additions]
    _KAG04_METRICS["applied"] += 1
    _KAG04_METRICS["added_orders"] += len(additions)
    for order in additions:
        if order[1] == "FERTILIZER":
            _KAG04_METRICS["added_fertilizer_units"] += order[2]
        else:
            _KAG04_METRICS["added_wheat_units"] += order[2]
    return candidate


def agent(obs):
    base_action = _kag04_base_agent(obs)
    return _kag04_overlay(obs, base_action)
'''


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _rename_top_level_agent(base_source: str) -> str:
    tree = ast.parse(base_source)
    agents = [
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "agent"
    ]
    if len(agents) != 1:
        raise ValueError("pinned base must define exactly one top-level def agent(...)")
    agent_node = agents[0]
    lines = base_source.splitlines(keepends=True)
    line_index = agent_node.lineno - 1
    line = lines[line_index]
    start = agent_node.col_offset
    marker = "def agent("
    if not line[start:].startswith(marker):
        raise ValueError("pinned base must use a plain def agent(...)")
    lines[line_index] = line[:start] + "def _kag04_base_agent(" + line[start + len(marker) :]
    return "".join(lines)


def build_source(base_bytes: bytes) -> str:
    """Return the deterministic derivative for only the pinned Tetsu v16 bytes."""
    if _sha256(base_bytes) != TETSU_V16_SHA256:
        raise ValueError("base bytes do not match pinned Tetsu v16 SHA-256")
    built = _rename_top_level_agent(base_bytes.decode("utf-8")).rstrip() + "\n\n" + _RUNTIME.lstrip()
    built = built.rstrip() + "\n"
    compile(built, "<kag04_tetsu_v16_late_inventory_liquidation>", "exec")
    return built


def materialize_file(base_path: Path, output_path: Path, receipt_path: Path) -> dict[str, Any]:
    """Materialize the derivative and bind its exact-base provenance."""
    base_bytes = base_path.read_bytes()
    source = build_source(base_bytes)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(source, encoding="utf-8", newline="\n")
    output_bytes = output_path.read_bytes()
    receipt = {
        "schema_version": 2,
        "artifact_kind": "kag_04_tetsu_v16_late_inventory_liquidation_materialization",
        "status": "MATERIALIZED_NOT_EVALUATED",
        "base_sha256": _sha256(base_bytes),
        "output_sha256": _sha256(output_bytes),
        "output_bytes": len(output_bytes),
        "license": "Apache-2.0 page-level mapping inference; preserve the Tetsu lineage attribution",
        "delta": "late day-29 hour-20..23 append-only stock-safe FERTILIZER/WHEAT SELL orders",
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize the Kag_04 Tetsu v16 liquidation derivative")
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(materialize_file(args.base, args.output, args.receipt), sort_keys=True))


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()
