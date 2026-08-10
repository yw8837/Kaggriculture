"""Materialize bounded reused-seed market variants from the exact Tetsu v16 control."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
VARIANTS = HERE / "variants"
CONTROL = ROOT / "research/campaign_3000/06_candidates/snapshots/tetsu_v16.py"
CONTROL_SHA256 = "997E6BFC5234534E246E945BC61C87858EBF997AB85B0A5C9427DD4ED710F1B6"
BASE_HEAD = "d9e2e82e4a1ba09c7b4cdc625e9e84710442a719"
OLD_K03_PATH = "research/campaign_3000/12_next_candidates/kag_03/main.py"
OLD_K03_SHA256 = "9034026D6872109C9AF6BD5582F65446312F0D109654BE388A17D8F8A186FE36"


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _replace_once(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise ValueError(f"expected one replacement target, found {source.count(old)}: {old!r}")
    return source.replace(old, new, 1)


_METRICS = '''
_SCREEN_COUNTERS = {"calls": 0, "trigger": 0}


def rescue_metrics():
    return dict(_SCREEN_COUNTERS)


def reset_rescue_metrics():
    for name in _SCREEN_COUNTERS:
        _SCREEN_COUNTERS[name] = 0
    return dict(_SCREEN_COUNTERS)
'''.strip()


def _instrument_preempt(source: str) -> str:
    source = _replace_once(
        source,
        "_PREMIUM = (\"STRAWBERRY\", \"MELON\", \"MILK\", \"WOOL\")\n",
        "_PREMIUM = (\"STRAWBERRY\", \"MELON\", \"MILK\", \"WOOL\")\n\n"
        + _METRICS
        + "\n",
    )
    source = _replace_once(
        source,
        "        if shifted:\n            action[\"market\"] = trial_market[:10]",
        "        if shifted:\n            _SCREEN_COUNTERS[\"trigger\"] += 1\n"
        "            action[\"market\"] = trial_market[:10]",
    )
    source = _replace_once(
        source,
        "def agent(obs):\n    try:",
        "def agent(obs):\n    _SCREEN_COUNTERS[\"calls\"] += 1\n    try:",
    )
    return source


def _git_blob() -> bytes:
    result = subprocess.run(
        ["git", "show", f"{BASE_HEAD}:{OLD_K03_PATH}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    if _sha(result.stdout) != OLD_K03_SHA256:
        raise ValueError("old Kag_03 Git blob hash mismatch")
    return result.stdout


def _write(name: str, source: str, action_delta: str, trigger_metric: str) -> dict[str, Any]:
    payload = source.encode("utf-8")
    compile(source, f"<{name}>", "exec")
    path = VARIANTS / name / "main.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {
        "name": name,
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": _sha(payload),
        "bytes": len(payload),
        "action_delta": action_delta,
        "trigger_metric": trigger_metric,
    }


def main() -> int:
    control_bytes = CONTROL.read_bytes()
    if _sha(control_bytes) != CONTROL_SHA256:
        raise ValueError("exact Tetsu v16 control hash mismatch")
    control = control_bytes.decode("utf-8")
    old = _git_blob().decode("utf-8")
    old_key = "ranked = sorted(rows, key=lambda row: (-row[0], -row[1], row[2], row[3]))"

    records = [
        _write(
            "old_inventory_desc",
            old,
            "After exact Tetsu, permute existing unique legal SELL slots by public inventory descending, then quantity descending.",
            "reordered",
        ),
        _write(
            "sell_quantity_desc",
            _replace_once(
                old,
                old_key,
                "ranked = sorted(rows, key=lambda row: (-row[1], -row[0], row[2], row[3]))",
            ),
            "Same guarded SELL-slot permutation, changing only the ranking key to requested quantity descending, then inventory descending.",
            "reordered",
        ),
        _write(
            "sell_inventory_asc",
            _replace_once(
                old,
                old_key,
                "ranked = sorted(rows, key=lambda row: (row[0], -row[1], row[2], row[3]))",
            ),
            "Same guarded SELL-slot permutation, changing only the ranking key to public inventory ascending, then quantity descending.",
            "reordered",
        ),
        _write(
            "sell_price_value_desc",
            _replace_once(
                old,
                old_key,
                "ranked = sorted(rows, key=lambda row: (-int(obs[\"market\"].get(\"prices\", {}).get(row[2], 0)) * row[1], -row[0], row[2], row[3]))",
            ),
            "Same guarded SELL-slot permutation, changing only the ranking key to observable quote times requested quantity descending.",
            "reordered",
        ),
    ]

    preempt_specs = [
        (
            "preempt_horizon_123",
            "for horizon in (3, 2, 1):",
            "for horizon in (1, 2, 3):",
            "Change only premium preemption horizon preference from 3,2,1 to 1,2,3; counters are action-neutral instrumentation.",
        ),
        (
            "preempt_fraction_1",
            "_PREEMPT_FRACTION = 2.0",
            "_PREEMPT_FRACTION = 1.0",
            "Change only premium preemption fraction from 2.0 to 1.0; counters are action-neutral instrumentation.",
        ),
        (
            "preempt_batch_15",
            "_PREEMPT_MAX_BATCH = 30",
            "_PREEMPT_MAX_BATCH = 15",
            "Change only premium preemption maximum batch from 30 to 15; counters are action-neutral instrumentation.",
        ),
        (
            "preempt_horizon_4321",
            "for horizon in (3, 2, 1):",
            "for horizon in (4, 3, 2, 1):",
            "Change only premium preemption horizon preference from 3,2,1 to 4,3,2,1; counters are action-neutral instrumentation.",
        ),
        (
            "preempt_horizon_54321",
            "for horizon in (3, 2, 1):",
            "for horizon in (5, 4, 3, 2, 1):",
            "Change only premium preemption horizon preference from 3,2,1 to 5,4,3,2,1; counters are action-neutral instrumentation.",
        ),
        (
            "preempt_seat0_horizon_4321",
            "for horizon in (3, 2, 1):",
            "for horizon in ((4, 3, 2, 1) if _seat(obs) == 0 else (3, 2, 1)):",
            "Use horizon preference 4,3,2,1 only when the candidate occupies observable seat 0; seat 1 keeps exact 3,2,1 control semantics; counters are action-neutral instrumentation.",
        ),
    ]
    for name, old_text, new_text, delta in preempt_specs:
        modified = _replace_once(control, old_text, new_text)
        records.append(_write(name, _instrument_preempt(modified), delta, "trigger"))

    manifest = {
        "schema_version": 1,
        "purpose": "historical_reused_seed_screen_only_no_promotion_authority",
        "base_head": BASE_HEAD,
        "control": {
            "path": CONTROL.relative_to(ROOT).as_posix(),
            "sha256": CONTROL_SHA256,
            "bytes": len(control_bytes),
        },
        "historical_seeds": [50000, 50015],
        "seats": [0, 1],
        "opponent": "exact_same_tetsu_v16",
        "variants": records,
    }
    (HERE / "variant_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
