"""Materialize Kag_03's sole premium-preemption horizon delta over Tetsu v16."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

CONTROL_SHA256 = "997E6BFC5234534E246E945BC61C87858EBF997AB85B0A5C9427DD4ED710F1B6"
CONTROL_SOURCE_RELATIVE_PATH = Path(
    "research/campaign_3000/06_candidates/snapshots/tetsu_v16.py"
)
CONTROL_HORIZON = "    for horizon in (3, 2, 1):"
CANDIDATE_HORIZON = "    for horizon in (4, 3, 2, 1):"
METRICS_ANCHOR = '_PREMIUM = ("STRAWBERRY", "MELON", "MILK", "WOOL")\n'
PREEMPT_SUCCESS_ANCHOR = "        if shifted:\n"
AGENT_ANCHOR = "def agent(obs):\n"

METRICS_BLOCK = '''_KAG03_COUNTERS = {
    "calls": 0,
    "preemptions": 0,
    "horizon4_preemptions": 0,
}


def kag03_metrics():
    """Return action-neutral instrumentation only."""
    return dict(_KAG03_COUNTERS)


def get_metrics():
    """Generic evaluator hook."""
    return kag03_metrics()


def rescue_metrics():
    """Runner-discoverable evaluator hook."""
    return kag03_metrics()


def reset_rescue_metrics():
    """Reset instrumentation only; it cannot alter future actions."""
    for name in _KAG03_COUNTERS:
        _KAG03_COUNTERS[name] = 0
    return kag03_metrics()
'''
PREEMPT_METRICS = '''            _KAG03_COUNTERS["preemptions"] += 1
            if horizon == 4:
                _KAG03_COUNTERS["horizon4_preemptions"] += 1
'''
CALL_METRICS = '    _KAG03_COUNTERS["calls"] += 1\n'


def sha256_bytes(content: bytes) -> str:
    """Return the uppercase campaign SHA-256."""
    return hashlib.sha256(content).hexdigest().upper()


def sha256_text(source: str) -> str:
    """Return the uppercase SHA-256 of exact UTF-8 source text."""
    return sha256_bytes(source.encode("utf-8"))


def _replace_once(source: str, old: str, new: str, label: str) -> str:
    if source.count(old) != 1:
        raise ValueError(f"Kag_03 expected exactly one {label}")
    return source.replace(old, new, 1)


def build_source(control_source: str) -> str:
    """Return exact control plus one horizon semantic change and counters."""
    if sha256_text(control_source) != CONTROL_SHA256:
        raise ValueError("Kag_03 requires the exact pinned Kag_01/Tetsu v16 source")
    candidate = _replace_once(
        control_source, CONTROL_HORIZON, CANDIDATE_HORIZON, "control horizon tuple"
    )
    candidate = _replace_once(
        candidate,
        METRICS_ANCHOR,
        f"{METRICS_ANCHOR}\n{METRICS_BLOCK}",
        "metrics anchor",
    )
    candidate = _replace_once(
        candidate,
        PREEMPT_SUCCESS_ANCHOR,
        f"{PREEMPT_SUCCESS_ANCHOR}{PREEMPT_METRICS}",
        "preemption success branch",
    )
    candidate = _replace_once(
        candidate,
        AGENT_ANCHOR,
        f"{AGENT_ANCHOR}{CALL_METRICS}",
        "agent entrypoint",
    )
    compile(candidate, "<kag03_preempt_horizon>", "exec")
    return candidate


def build_file(control_path: Path, output_path: Path) -> dict[str, Any]:
    """Materialize the policy and record exact source provenance."""
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
    """Write the policy and a compile/metric-hook receipt."""
    build = build_file(control_path, output_path)
    namespace: dict[str, Any] = {}
    exec(  # noqa: S102 - compile evidence for self-contained submission source.
        compile(output_path.read_bytes(), "<kag03_preempt_horizon_freeze>", "exec"),
        namespace,
    )
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
        "schema": "kag03_preempt_horizon_freeze.v1",
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
        "semantic_replacement": {
            "from": CONTROL_HORIZON.strip(),
            "to": CANDIDATE_HORIZON.strip(),
        },
        "compile": {"filename": "<kag03_preempt_horizon_freeze>", "ok": True},
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
