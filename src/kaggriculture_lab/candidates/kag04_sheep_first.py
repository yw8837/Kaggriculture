"""Build the narrowly scoped Kag_04 opening-sheep Tetsu v16 derivative."""

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
# KAG04_TETSU_V16_OPENING_SHEEP_DELTA
# The only treatment is COW 2 -> 1 and SHEEP 2 -> 3 in one already-planned
# opening market action. All other base behavior remains untouched.
_KAG04_METRICS = {
    "calls": 0,
    "applied": 0,
    "fallback_malformed": 0,
    "fallback_ambiguous": 0,
    "fallback_owned_animals": 0,
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


def _kag04_own_animal_count(obs):
    if not isinstance(obs, dict):
        return None
    player = obs.get("player")
    farms = obs.get("farms")
    private = obs.get("private")
    if (
        not isinstance(player, int)
        or isinstance(player, bool)
        or not isinstance(farms, list)
        or player < 0
        or player >= len(farms)
        or not isinstance(farms[player], dict)
        or not isinstance(private, dict)
    ):
        return None
    tiles = farms[player].get("tiles")
    shed = private.get("shed")
    if not isinstance(tiles, list) or not isinstance(shed, dict):
        return None
    count = 0
    for row in tiles:
        if not isinstance(row, list):
            return None
        for tile in row:
            if tile is None or tile == "LOCKED":
                continue
            if not isinstance(tile, dict):
                return None
            animal = tile.get("animal")
            if animal is None:
                continue
            if not isinstance(animal, str) or not animal:
                return None
            count += 1
    for animal in ("COW", "SHEEP", "GOOSE"):
        quantity = shed.get(animal, 0)
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 0:
            return None
        count += quantity
    return count


def _kag04_rewrite_market(base_action):
    if not isinstance(base_action, dict):
        return "malformed", None
    market = base_action.get("market")
    if not isinstance(market, list):
        return "malformed", None
    cow_index = None
    sheep_index = None
    for index, order in enumerate(market):
        if not isinstance(order, list) or not order or not isinstance(order[0], str):
            return "malformed", None
        if order[0] != "BUY_ANIMAL":
            continue
        if (
            len(order) != 3
            or not isinstance(order[1], str)
            or not isinstance(order[2], int)
            or isinstance(order[2], bool)
        ):
            return "malformed", None
        if order == ["BUY_ANIMAL", "COW", 2]:
            if cow_index is not None:
                return "ambiguous", None
            cow_index = index
        elif order == ["BUY_ANIMAL", "SHEEP", 2]:
            if sheep_index is not None:
                return "ambiguous", None
            sheep_index = index
        else:
            return "ambiguous", None
    if cow_index is None or sheep_index is None:
        return "ambiguous", None
    rewritten_market = list(market)
    rewritten_market[cow_index] = ["BUY_ANIMAL", "COW", 1]
    rewritten_market[sheep_index] = ["BUY_ANIMAL", "SHEEP", 3]
    candidate = dict(base_action)
    candidate["market"] = rewritten_market
    return "applied", candidate


def _kag04_overlay(obs, base_action):
    _KAG04_METRICS["calls"] += 1
    owned_animals = _kag04_own_animal_count(obs)
    if owned_animals is None:
        _KAG04_METRICS["fallback_malformed"] += 1
        return base_action
    if owned_animals != 0:
        _KAG04_METRICS["fallback_owned_animals"] += 1
        return base_action
    result, candidate = _kag04_rewrite_market(base_action)
    if result == "malformed":
        _KAG04_METRICS["fallback_malformed"] += 1
        return base_action
    if result == "ambiguous":
        _KAG04_METRICS["fallback_ambiguous"] += 1
        return base_action
    _KAG04_METRICS["applied"] += 1
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
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "agent"
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
    """Return a deterministic derivative only for the exact pinned Tetsu v16 bytes."""
    if _sha256(base_bytes) != TETSU_V16_SHA256:
        raise ValueError("base bytes do not match pinned Tetsu v16 SHA-256")
    base_source = base_bytes.decode("utf-8")
    built = _rename_top_level_agent(base_source).rstrip() + "\n\n" + _RUNTIME.lstrip()
    built = built.rstrip() + "\n"
    compile(built, "<kag04_tetsu_v16_opening_sheep>", "exec")
    return built


def materialize_file(base_path: Path, output_path: Path, receipt_path: Path) -> dict[str, Any]:
    """Materialize the derivative and bind its Apache-2.0 attribution contract."""
    base_bytes = base_path.read_bytes()
    source = build_source(base_bytes)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(source, encoding="utf-8", newline="\n")
    output_bytes = output_path.read_bytes()
    receipt = {
        "schema_version": 1,
        "artifact_kind": "kag_04_tetsu_v16_opening_sheep_materialization",
        "status": "MATERIALIZED_NOT_EVALUATED",
        "base_sha256": _sha256(base_bytes),
        "output_sha256": _sha256(output_bytes),
        "output_bytes": len(output_bytes),
        "license": "Apache-2.0 page-level mapping inference; preserve the Tetsu lineage attribution",
        "delta": "COW 2 -> 1 and SHEEP 2 -> 3 only when the guarded opening shape is exact",
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize the Kag_04 Tetsu v16 opening-sheep derivative")
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(materialize_file(args.base, args.output, args.receipt), sort_keys=True))


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()
