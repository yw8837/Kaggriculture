"""Build the single-delta Kag_04 seat-0 horizon-four Tetsu derivative."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any

TETSU_V16_SHA256 = "997E6BFC5234534E246E945BC61C87858EBF997AB85B0A5C9427DD4ED710F1B6"
TETSU_V16_BASE_PATH = Path("research/campaign_3000/06_candidates/snapshots/tetsu_v16.py")
_HORIZON_LOOP = "for horizon in (3, 2, 1):"
_SEAT0_HORIZON_LOOP = "for horizon in ((4, 3, 2, 1) if _seat(obs) == 0 else (3, 2, 1)):"
_SHIFT_MARKER = "        if shifted:\n"

_RUNTIME = r'''
# KAG04_TETSU_V16_SEAT0_HORIZON4_METRICS
_KAG04_METRICS = {
    "calls": 0,
    "preemptions": 0,
    "horizon4_preemptions": 0,
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


def _kag04_record_preemption(horizon):
    _KAG04_METRICS["preemptions"] += 1
    if horizon == 4:
        _KAG04_METRICS["horizon4_preemptions"] += 1


def agent(obs):
    _KAG04_METRICS["calls"] += 1
    return _kag04_base_agent(obs)
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
    """Return the only permitted decision mutation plus causal metrics hooks."""
    if _sha256(base_bytes) != TETSU_V16_SHA256:
        raise ValueError("base bytes do not match pinned Tetsu v16 SHA-256")
    base_source = base_bytes.decode("utf-8")
    if base_source.count(_HORIZON_LOOP) != 1:
        raise ValueError("pinned base must contain exactly one three-horizon loop")
    if base_source.count(_SHIFT_MARKER) != 1:
        raise ValueError("pinned base must contain exactly one shifted branch")
    altered = base_source.replace(_HORIZON_LOOP, _SEAT0_HORIZON_LOOP, 1)
    altered = altered.replace(
        _SHIFT_MARKER,
        _SHIFT_MARKER + "            _kag04_record_preemption(horizon)\n",
        1,
    )
    built = _rename_top_level_agent(altered).rstrip() + "\n\n" + _RUNTIME.lstrip()
    built = built.rstrip() + "\n"
    compile(built, "<kag04_tetsu_v16_seat0_horizon4>", "exec")
    return built


def materialize_file(base_path: Path, output_path: Path, receipt_path: Path) -> dict[str, Any]:
    """Materialize the exact-base derivative with its provenance receipt."""
    base_bytes = base_path.read_bytes()
    source = build_source(base_bytes)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(source, encoding="utf-8", newline="\n")
    output_bytes = output_path.read_bytes()
    receipt = {
        "schema_version": 3,
        "artifact_kind": "kag_04_tetsu_v16_seat0_horizon4_materialization",
        "status": "MATERIALIZED_SCREEN_POSITIVE_NOT_PROMOTED",
        "base_sha256": _sha256(base_bytes),
        "output_sha256": _sha256(output_bytes),
        "output_bytes": len(output_bytes),
        "license": "Apache-2.0 page-level mapping inference; preserve the Tetsu lineage attribution",
        "decision_delta": "seat 0 horizon loop (3,2,1) to (4,3,2,1); seat 1 unchanged",
        "instrumentation": "calls, preemptions, horizon4_preemptions only",
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materialize the Kag_04 Tetsu v16 seat-0 horizon-four derivative"
    )
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(materialize_file(args.base, args.output, args.receipt), sort_keys=True))


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()
