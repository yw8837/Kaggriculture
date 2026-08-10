"""Build Kag_03: an exact Tetsu v16 control plus a SELL-slot-only delta.

The generated agent first calls the pinned Kag_01/Tetsu v16 control.  It can
only permute already-existing, legal, unique ``SELL`` orders in the market
list.  The farmer, hands, order count, non-SELL slots, and every SELL payload
are preserved.  Any uncertainty returns the untouched control action.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

CONTROL_SHA256 = "997E6BFC5234534E246E945BC61C87858EBF997AB85B0A5C9427DD4ED710F1B6"
CONTROL_SOURCE_RELATIVE_PATH = Path(
    "research/campaign_3000/06_candidates/snapshots/tetsu_v16.py"
)
RUNTIME_MARKER = "# KAG_03_TERMINAL_MARKET_DELTA"


_RUNTIME = r'''
# KAG_03_TERMINAL_MARKET_DELTA
# This delta deliberately has no horizon, seat, episode, or opponent trigger.
_KAG03_MAX_MARKET_ORDERS = 10
_KAG03_COUNTERS = {
    "calls": 0,
    "reordered": 0,
    "no_op": 0,
    "rejected_malformed": 0,
    "rejected_ambiguous": 0,
    "rejected_illegal": 0,
    "rejected_resize": 0,
    "exception_fallback": 0,
}


def kag03_metrics():
    """Return delta-only counters; no counter influences an action."""
    return dict(_KAG03_COUNTERS)


def get_metrics():
    """Optional generic post-episode metrics hook for an external evaluator."""
    return kag03_metrics()


def rescue_metrics():
    """Runner-compatible alias for the immutable metrics snapshot."""
    return kag03_metrics()


def reset_rescue_metrics():
    """Reset counters only; the action path has no dependency on these values."""
    for name in _KAG03_COUNTERS:
        _KAG03_COUNTERS[name] = 0
    return kag03_metrics()


def _kag03_is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _kag03_valid_non_sell(order):
    if not isinstance(order, list) or not order:
        return False
    op = order[0]
    if op in ("HIRE", "BUY_LAND"):
        return len(order) == 1
    if op in ("BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL"):
        return (
            len(order) == 3
            and isinstance(order[1], str)
            and bool(order[1])
            and _kag03_is_int(order[2])
            and order[2] > 0
        )
    return False


def _kag03_validate_market(obs, control_action):
    """Return sortable SELL rows, or a conservative fallback reason."""
    if not isinstance(obs, dict) or not isinstance(control_action, dict):
        return "rejected_malformed", None
    if not isinstance(control_action.get("farmer"), list):
        return "rejected_malformed", None
    if not isinstance(control_action.get("hands"), list):
        return "rejected_malformed", None
    market = control_action.get("market")
    if not isinstance(market, list):
        return "rejected_malformed", None
    if len(market) > _KAG03_MAX_MARKET_ORDERS:
        return "rejected_resize", None

    private = obs.get("private")
    visible_market = obs.get("market")
    if not isinstance(private, dict) or not isinstance(visible_market, dict):
        return "rejected_malformed", None
    shed = private.get("shed")
    inventory = visible_market.get("inventory")
    if not isinstance(shed, dict) or not isinstance(inventory, dict):
        return "rejected_malformed", None

    rows = []
    seen_items = set()
    for index, order in enumerate(market):
        if not isinstance(order, list) or not order:
            return "rejected_malformed", None
        if order[0] != "SELL":
            if not _kag03_valid_non_sell(order):
                return "rejected_malformed", None
            continue
        if (
            len(order) != 3
            or not isinstance(order[1], str)
            or not order[1]
            or not _kag03_is_int(order[2])
            or order[2] <= 0
        ):
            return "rejected_malformed", None
        item = order[1]
        quantity = order[2]
        available = shed.get(item)
        current_inventory = inventory.get(item)
        if (
            item not in _MARKET_PARAMS
            or item not in inventory
            or not _kag03_is_int(available)
            or available < quantity
            or not _kag03_is_int(current_inventory)
            or current_inventory < 0
        ):
            return "rejected_illegal", None
        if item in seen_items:
            return "rejected_ambiguous", None
        seen_items.add(item)
        rows.append((current_inventory, quantity, item, index, order))
    return None, rows


def _kag03_only_sell_permutation(original, candidate):
    if len(original) != len(candidate):
        return False
    original_sells = []
    candidate_sells = []
    for old, new in zip(original, candidate):
        if old[0] != "SELL" and new != old:
            return False
        if old[0] == "SELL":
            original_sells.append(tuple(old))
        if new[0] == "SELL":
            candidate_sells.append(tuple(new))
    return sorted(original_sells) == sorted(candidate_sells)


def _kag03_control_market_delta(obs, control_action):
    """Return control unchanged unless a checked SELL-slot permutation exists."""
    _KAG03_COUNTERS["calls"] += 1
    try:
        reason, rows = _kag03_validate_market(obs, control_action)
        if reason is not None:
            _KAG03_COUNTERS[reason] += 1
            return control_action
        if len(rows) < 2:
            _KAG03_COUNTERS["no_op"] += 1
            return control_action

        market = control_action["market"]
        ranked = sorted(rows, key=lambda row: (-row[0], -row[1], row[2], row[3]))
        ranked_orders = iter(row[4] for row in ranked)
        candidate_market = [
            next(ranked_orders) if order[0] == "SELL" else order for order in market
        ]
        if candidate_market == market:
            _KAG03_COUNTERS["no_op"] += 1
            return control_action
        if not _kag03_only_sell_permutation(market, candidate_market):
            _KAG03_COUNTERS["rejected_resize"] += 1
            return control_action

        candidate_action = copy.deepcopy(control_action)
        candidate_action["market"] = candidate_market
        if (
            candidate_action.get("farmer") != control_action.get("farmer")
            or candidate_action.get("hands") != control_action.get("hands")
        ):
            _KAG03_COUNTERS["exception_fallback"] += 1
            return control_action
        _KAG03_COUNTERS["reordered"] += 1
        return candidate_action
    except Exception:
        _KAG03_COUNTERS["exception_fallback"] += 1
        return control_action


def agent(obs):
    control_action = _kag03_control_agent(obs)
    return _kag03_control_market_delta(obs, control_action)
'''.strip()


def sha256_text(source: str) -> str:
    """Return the uppercase UTF-8 SHA-256 used by campaign manifests."""
    return hashlib.sha256(source.encode("utf-8")).hexdigest().upper()


def sha256_bytes(content: bytes) -> str:
    """Return the uppercase SHA-256 of an exact file payload."""
    return hashlib.sha256(content).hexdigest().upper()


def build_source(control_source: str) -> str:
    """Wrap the exact Kag_01 source with the conservative Kag_03 delta."""
    if sha256_text(control_source) != CONTROL_SHA256:
        raise ValueError("Kag_03 requires the exact pinned Kag_01/Tetsu v16 source")
    if RUNTIME_MARKER in control_source:
        raise ValueError("Kag_03 delta is already present")

    marker = "\ndef agent(obs):"
    if control_source.count(marker) != 1:
        raise ValueError("Kag_03 expected exactly one control agent entrypoint")
    renamed = control_source.replace(marker, "\ndef _kag03_control_agent(obs):", 1)
    candidate = f"{renamed}\n\n{_RUNTIME}\n"
    compile(candidate, "<kag03_terminal_market>", "exec")
    return candidate


def build_file(control_path: Path, output_path: Path) -> dict[str, Any]:
    """Build a self-contained candidate and return a compact provenance receipt."""
    control_bytes = control_path.read_bytes()
    if sha256_bytes(control_bytes) != CONTROL_SHA256:
        raise ValueError("Kag_03 requires the exact pinned Kag_01/Tetsu v16 source")
    control_source = control_bytes.decode("utf-8")
    candidate = build_source(control_source)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(candidate, encoding="utf-8", newline="")
    return {
        "control_path": str(control_path),
        "control_sha256": sha256_bytes(control_bytes),
        "control_bytes": len(control_bytes),
        "candidate_path": str(output_path),
        "candidate_sha256": sha256_text(candidate),
        "candidate_bytes": len(candidate.encode("utf-8")),
    }


def materialize_freeze(
    control_path: Path, output_path: Path, receipt_path: Path
) -> dict[str, Any]:
    """Write the self-contained candidate and a deterministic local freeze receipt."""
    build = build_file(control_path, output_path)
    candidate_bytes = output_path.read_bytes()
    candidate_source = candidate_bytes.decode("utf-8")
    if sha256_bytes(candidate_bytes) != build["candidate_sha256"]:
        raise ValueError("Kag_03 materialized candidate hash mismatch")

    namespace: dict[str, Any] = {}
    exec(compile(candidate_source, "<kag03_freeze>", "exec"), namespace)  # noqa: S102
    hook_names = (
        "kag03_metrics",
        "get_metrics",
        "rescue_metrics",
        "reset_rescue_metrics",
    )
    if not all(callable(namespace.get(name)) for name in hook_names):
        raise ValueError("Kag_03 metrics hooks are incomplete")
    initial_metrics = namespace["rescue_metrics"]()
    reset_metrics = namespace["reset_rescue_metrics"]()
    generic_metrics = namespace["get_metrics"]()
    if initial_metrics != reset_metrics or reset_metrics != generic_metrics:
        raise ValueError("Kag_03 metrics hooks disagree")

    receipt = {
        "schema": "kag03_terminal_market_freeze.v1",
        "control": {
            "path": CONTROL_SOURCE_RELATIVE_PATH.as_posix(),
            "sha256": build["control_sha256"],
            "bytes": build["control_bytes"],
        },
        "candidate": {
            "path": output_path.as_posix(),
            "sha256": build["candidate_sha256"],
            "bytes": build["candidate_bytes"],
        },
        "compile": {"filename": "<kag03_freeze>", "ok": True},
        "metrics_hooks": list(hook_names),
        "metrics_initial": initial_metrics,
        "metrics_after_reset": reset_metrics,
        "metrics_generic": generic_metrics,
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="",
    )
    return receipt
