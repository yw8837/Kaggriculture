"""Summarize exact direct-Tetsu reused-seed reports for the variant screen."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
EXPECTED = {(seed, seat) for seed in range(50000, 50016) for seat in (0, 1)}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _summarize(record: dict[str, Any]) -> dict[str, Any]:
    path = HERE.parents[4] / record["report_path"]
    report = json.loads(path.read_text(encoding="utf-8"))
    rows = report.get("games")
    if not isinstance(rows, list):
        raise TypeError(f"games missing in {path}")
    cells: set[tuple[int, int]] = set()
    margins: list[float] = []
    wins = ties = losses = 0
    trigger = 0
    failures: list[str] = []
    for row in rows:
        seed, seat = row.get("seed"), row.get("seat")
        if type(seed) is not int or type(seat) is not int:
            failures.append("invalid seed/seat type")
            continue
        cells.add((seed, seat))
        candidate = row.get("candidate_money")
        opponent = row.get("opponent_money")
        if (
            Path(str(row.get("opponent"))).stem != "tetsu_v16"
            or row.get("scenario") != "default"
            or row.get("error") is not None
            or row.get("candidate_status") != "DONE"
            or row.get("opponent_status") != "DONE"
            or isinstance(candidate, bool)
            or not isinstance(candidate, (int, float))
            or isinstance(opponent, bool)
            or not isinstance(opponent, (int, float))
            or not math.isfinite(float(candidate))
            or not math.isfinite(float(opponent))
        ):
            failures.append(f"invalid game {(seed, seat)}")
            continue
        margin = float(candidate) - float(opponent)
        margins.append(margin)
        if margin > 0:
            wins += 1
        elif margin < 0:
            losses += 1
        else:
            ties += 1
        metrics = row.get("candidate_metrics") or {}
        value = metrics.get(record["trigger_metric"], 0)
        if type(value) is not int or value < 0:
            failures.append(f"invalid trigger metric {(seed, seat)}")
        else:
            trigger += value
    if cells != EXPECTED:
        failures.append("cell set mismatch")
    score = (wins + 0.5 * ties) / len(margins) if margins else None
    mean_margin = statistics.fmean(margins) if margins else None
    return {
        **record,
        "report_sha256": _sha(path),
        "games": len(margins),
        "wins": wins,
        "ties": ties,
        "losses": losses,
        "match_score": score,
        "mean_margin": mean_margin,
        "median_margin": statistics.median(margins) if margins else None,
        "trigger_count": trigger,
        "pass": not failures and len(margins) == 32 and score > 0.5 and mean_margin > 0,
        "failures": failures,
    }


def main() -> int:
    manifest = json.loads((HERE / "variant_manifest.json").read_text(encoding="utf-8"))
    reports = json.loads((HERE / "report_index.json").read_text(encoding="utf-8"))
    by_name = {item["name"]: item for item in reports["reports"]}
    results = []
    for variant in manifest["variants"]:
        merged = {**variant, **by_name[variant["name"]]}
        results.append(_summarize(merged))
    winners = sorted(
        (row for row in results if row["pass"]),
        key=lambda row: (row["match_score"], row["mean_margin"]),
        reverse=True,
    )[:2]
    summary = {
        "schema_version": 1,
        "promotion_evidence": False,
        "historical_reused_seeds": [50000, 50015],
        "exact_cells_per_variant": 32,
        "results": results,
        "top_passing_max_two": [row["name"] for row in winners],
    }
    output = HERE / "screen_summary.json"
    output.write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
