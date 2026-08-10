"""Evaluate reused-seed diagnostic reports; never authorize promotion."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
EXPECTED_SEEDS = set(range(50000, 50016))
EXPECTED_CELLS = {(seed, seat) for seed in EXPECTED_SEEDS for seat in (0, 1)}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    return value


def _evaluate_slot(path: Path) -> dict[str, Any]:
    report = _load(path)
    rows = report.get("games")
    if not isinstance(rows, list):
        raise TypeError(f"games must be a list: {path}")
    indexed: dict[tuple[int, int], dict[str, Any]] = {}
    failures: list[str] = []
    outcomes: list[float] = []
    margins: list[float] = []
    for raw in rows:
        if not isinstance(raw, dict):
            failures.append("non-object row")
            continue
        seed, seat = raw.get("seed"), raw.get("seat")
        if type(seed) is not int or type(seat) is not int or seat not in (0, 1):
            failures.append("invalid seed/seat type")
            continue
        key = (seed, seat)
        if key in indexed:
            failures.append(f"duplicate cell {key}")
            continue
        indexed[key] = raw
        candidate = raw.get("candidate_money")
        opponent = raw.get("opponent_money")
        elapsed = raw.get("elapsed_seconds")
        if (
            raw.get("opponent") != "tetsu_v16"
            or raw.get("scenario") != "default"
            or raw.get("error") is not None
            or raw.get("candidate_status") != "DONE"
            or raw.get("opponent_status") != "DONE"
            or isinstance(candidate, bool)
            or not isinstance(candidate, (int, float))
            or isinstance(opponent, bool)
            or not isinstance(opponent, (int, float))
            or isinstance(elapsed, bool)
            or not isinstance(elapsed, (int, float))
            or not all(math.isfinite(float(v)) for v in (candidate, opponent, elapsed))
            or float(elapsed) < 0
        ):
            failures.append(f"invalid game {key}")
            continue
        margin = float(candidate) - float(opponent)
        margins.append(margin)
        outcomes.append(1.0 if margin > 0 else 0.0 if margin < 0 else 0.5)
    if set(indexed) != EXPECTED_CELLS:
        failures.append("cells do not equal exact 16-seed both-seat diagnostic")
    match_score = statistics.fmean(outcomes) if outcomes else None
    mean_margin = statistics.fmean(margins) if margins else None
    passed = (
        not failures
        and len(outcomes) == 32
        and match_score is not None
        and mean_margin is not None
        and match_score > 0.5
        and mean_margin > 0.0
    )
    return {
        "pass": passed,
        "games": len(outcomes),
        "match_score": match_score,
        "mean_margin": mean_margin,
        "median_margin": statistics.median(margins) if margins else None,
        "failures": failures,
    }


def evaluate(kag03: Path, kag04: Path) -> dict[str, Any]:
    slots = {"Kag_03": _evaluate_slot(kag03), "Kag_04": _evaluate_slot(kag04)}
    scores = [item["match_score"] for item in slots.values()]
    return {
        "schema_version": 1,
        "pass": all(item["pass"] for item in slots.values()),
        "score": statistics.fmean(scores) if all(score is not None for score in scores) else None,
        "promotion_evidence": False,
        "historical_reused_seeds": [50000, 50015],
        "slots": slots,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kag03", type=Path, required=True)
    parser.add_argument("--kag04", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(args.kag03, args.kag04)
    payload = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(payload, end="")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
