"""Materialize Kag_03 as one actor-local WEED-repair delta over exact Tetsu v16.

The generated policy calls the pinned Kag_01 control first.  The only permitted
candidate change is replacing one own actor's otherwise-idle or failed placement
action with ``["DIG"]`` when that actor is visibly standing on an own-farm WEED.
Every malformed, ambiguous, illegal, or exceptional path returns the original
control action object unchanged.
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
RUNTIME_MARKER = "# KAG_03_ACTOR_LOCAL_WEED_DELTA"


_RUNTIME = r'''
# KAG_03_ACTOR_LOCAL_WEED_DELTA
# The player field only selects the agent's own visible farm. It is never used
# as a threshold, branch identity, or persistent key. No time/seed/opponent
# field is read by this delta.
_KAG03_COUNTERS = {
    "calls": 0,
    "obstructions_observed": 0,
    "repairs_applied": 0,
    "farmer_repairs": 0,
    "hand_repairs": 0,
    "no_op": 0,
    "rejected_malformed": 0,
    "rejected_ambiguous": 0,
    "rejected_illegal": 0,
    "exception_fallback": 0,
}


def kag03_metrics():
    """Return counters only; no counter affects an action."""
    return dict(_KAG03_COUNTERS)


def get_metrics():
    """Generic evaluator hook."""
    return kag03_metrics()


def rescue_metrics():
    """Runner-compatible evaluator hook."""
    return kag03_metrics()


def reset_rescue_metrics():
    """Reset metrics only; action selection remains history-free."""
    for name in _KAG03_COUNTERS:
        _KAG03_COUNTERS[name] = 0
    return kag03_metrics()


def _kag03_is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


class _Kag03Ambiguous(ValueError):
    pass


def _kag03_action_shape_is_safe(control_action, hand_count):
    if not isinstance(control_action, dict):
        return False
    farmer = control_action.get("farmer")
    hands = control_action.get("hands")
    market = control_action.get("market")
    if (
        not isinstance(farmer, list)
        or not farmer
        or not isinstance(farmer[0], str)
        or not isinstance(hands, list)
        or len(hands) != hand_count
        or not isinstance(market, list)
    ):
        return False
    return all(
        isinstance(action, list) and action and isinstance(action[0], str)
        for action in hands
    )


def _kag03_position(position, tiles):
    if (
        not isinstance(position, (list, tuple))
        or len(position) != 2
        or not _kag03_is_int(position[0])
        or not _kag03_is_int(position[1])
    ):
        raise ValueError("position")
    x, y = position
    if y < 0 or y >= len(tiles) or not isinstance(tiles[y], list):
        raise ValueError("position")
    if x < 0 or x >= len(tiles[y]):
        raise ValueError("position")
    return x, y


def _kag03_own_actor_rows(obs, control_action):
    """Return own actors in deterministic farmer-then-hand order, or raise."""
    if not isinstance(obs, dict):
        raise TypeError("observation")
    player = obs.get("player")
    farms = obs.get("farms")
    if not _kag03_is_int(player) or player not in (0, 1):
        raise ValueError("player")
    if not isinstance(farms, list) or len(farms) != 2:
        raise ValueError("farms")
    farm = farms[player]
    if not isinstance(farm, dict):
        raise ValueError("farm")
    hands = farm.get("hands")
    tiles = farm.get("tiles")
    farmer = farm.get("farmer")
    if not isinstance(hands, list) or not isinstance(tiles, list):
        raise ValueError("farm")
    if not _kag03_action_shape_is_safe(control_action, len(hands)):
        raise ValueError("action")
    rows = [("farmer", _kag03_position(farmer, tiles), control_action["farmer"])]
    for index, (position, action) in enumerate(zip(hands, control_action["hands"])):
        rows.append((index, _kag03_position(position, tiles), action))
    return tiles, rows


def _kag03_is_obstructed(tile, action):
    if not isinstance(tile, dict) or tile.get("kind") != "WEED":
        return False
    # PASS leaves the obstruction in place; PLANT and BUILD_PASTURE fail while
    # the tile is occupied. DIG is legal for a WEED and consumes no inventory.
    return action[0] in ("PASS", "PLANT", "BUILD_PASTURE")


def _kag03_exact_one_actor_delta(control_action, candidate_action, actor):
    if not isinstance(candidate_action, dict):
        return False
    if candidate_action.get("market") != control_action.get("market"):
        return False
    if actor == "farmer":
        return (
            candidate_action.get("farmer") == ["DIG"]
            and candidate_action.get("hands") == control_action.get("hands")
        )
    index = int(actor)
    candidate_hands = candidate_action.get("hands")
    control_hands = control_action.get("hands")
    return (
        candidate_action.get("farmer") == control_action.get("farmer")
        and isinstance(candidate_hands, list)
        and candidate_hands[index] == ["DIG"]
        and all(
            candidate_hands[row] == control_hands[row]
            for row in range(len(control_hands))
            if row != index
        )
    )


def _kag03_actor_local_weed_delta(obs, control_action):
    """Use one legal local DIG or return the exact control object."""
    _KAG03_COUNTERS["calls"] += 1
    try:
        tiles, rows = _kag03_own_actor_rows(obs, control_action)
        eligible = []
        for actor, (x, y), action in rows:
            if not _kag03_is_obstructed(tiles[y][x], action):
                continue
            eligible.append((actor, action))
        _KAG03_COUNTERS["obstructions_observed"] += len(eligible)
        if not eligible:
            _KAG03_COUNTERS["no_op"] += 1
            return control_action
        if len(eligible) != 1:
            raise _Kag03Ambiguous("multiple eligible WEED repairs")
        actor, _action = eligible[0]
        candidate_action = copy.deepcopy(control_action)
        if actor == "farmer":
            candidate_action["farmer"] = ["DIG"]
        else:
            candidate_action["hands"][actor] = ["DIG"]
        if not _kag03_exact_one_actor_delta(control_action, candidate_action, actor):
            _KAG03_COUNTERS["rejected_illegal"] += 1
            return control_action
        _KAG03_COUNTERS["repairs_applied"] += 1
        if actor == "farmer":
            _KAG03_COUNTERS["farmer_repairs"] += 1
        else:
            _KAG03_COUNTERS["hand_repairs"] += 1
        return candidate_action
    except _Kag03Ambiguous:
        _KAG03_COUNTERS["rejected_ambiguous"] += 1
        return control_action
    except (TypeError, ValueError, IndexError, KeyError):
        _KAG03_COUNTERS["rejected_malformed"] += 1
        return control_action
    except Exception:
        _KAG03_COUNTERS["exception_fallback"] += 1
        return control_action


def agent(obs):
    control_action = _kag03_control_agent(obs)
    return _kag03_actor_local_weed_delta(obs, control_action)
'''.strip()


def sha256_bytes(content: bytes) -> str:
    """Return the uppercase SHA-256 used by campaign receipts."""
    return hashlib.sha256(content).hexdigest().upper()


def sha256_text(source: str) -> str:
    """Return the uppercase UTF-8 SHA-256 used by campaign receipts."""
    return sha256_bytes(source.encode("utf-8"))


def build_source(control_source: str) -> str:
    """Return exact Tetsu prefix plus the single bounded Kag_03 delta."""
    if sha256_text(control_source) != CONTROL_SHA256:
        raise ValueError("Kag_03 requires the exact pinned Kag_01/Tetsu v16 source")
    if RUNTIME_MARKER in control_source:
        raise ValueError("Kag_03 delta is already present")
    marker = "\ndef agent(obs):"
    if control_source.count(marker) != 1:
        raise ValueError("Kag_03 expected exactly one control agent entrypoint")
    prefix = control_source.replace(marker, "\ndef _kag03_control_agent(obs):", 1)
    candidate = f"{prefix}\n\n{_RUNTIME}\n"
    compile(candidate, "<kag03_actor_local_weed>", "exec")
    return candidate


def build_file(control_path: Path, output_path: Path) -> dict[str, Any]:
    """Materialize a self-contained policy and return its provenance."""
    control_bytes = control_path.read_bytes()
    if sha256_bytes(control_bytes) != CONTROL_SHA256:
        raise ValueError("Kag_03 requires the exact pinned Kag_01/Tetsu v16 source")
    candidate = build_source(control_bytes.decode("utf-8"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(candidate, encoding="utf-8", newline="")
    candidate_bytes = output_path.read_bytes()
    return {
        "control_path": str(control_path),
        "control_sha256": sha256_bytes(control_bytes),
        "control_bytes": len(control_bytes),
        "candidate_path": str(output_path),
        "candidate_sha256": sha256_bytes(candidate_bytes),
        "candidate_bytes": len(candidate_bytes),
    }


def materialize_freeze(
    control_path: Path, output_path: Path, receipt_path: Path
) -> dict[str, Any]:
    """Write the policy and a deterministic compile/metrics receipt."""
    build = build_file(control_path, output_path)
    candidate_bytes = output_path.read_bytes()
    namespace: dict[str, Any] = {}
    exec(compile(candidate_bytes, "<kag03_freeze>", "exec"), namespace)  # noqa: S102
    hook_names = (
        "kag03_metrics",
        "get_metrics",
        "rescue_metrics",
        "reset_rescue_metrics",
    )
    if not all(callable(namespace.get(name)) for name in hook_names):
        raise ValueError("Kag_03 metrics hooks are incomplete")
    initial = namespace["rescue_metrics"]()
    after_reset = namespace["reset_rescue_metrics"]()
    generic = namespace["get_metrics"]()
    if initial != after_reset or after_reset != generic:
        raise ValueError("Kag_03 metrics hooks disagree")
    receipt = {
        "schema": "kag03_actor_local_weed_freeze.v2",
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
        "metrics_initial": initial,
        "metrics_after_reset": after_reset,
        "metrics_generic": generic,
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="",
    )
    return receipt
