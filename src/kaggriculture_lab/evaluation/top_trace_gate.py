from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _outcome(row: dict[str, Any]) -> float:
    candidate = float(row["candidate_money"])
    opponent = float(row["opponent_money"])
    return 1.0 if candidate > opponent else 0.0 if candidate < opponent else 0.5


def _validate_report(
    report: dict[str, Any],
    *,
    expected_agent: dict[str, Any],
    opponents: list[dict[str, Any]],
    seeds: list[int],
    scenario_sha256: str,
) -> dict[tuple[str, str, int, int], dict[str, Any]]:
    opponent_paths = [entry["path"] for entry in opponents]
    expected_keys = {
        ("default", opponent, seed, seat)
        for opponent in opponent_paths
        for seed in seeds
        for seat in (0, 1)
    }
    assert report["candidate"] == expected_agent["path"]
    assert report["candidate_sha256_at_start"] == expected_agent["sha256"]
    assert report["candidate_sha256_at_end"] == expected_agent["sha256"]
    assert report["sources_unchanged_during_run"] is True
    assert report["opponents"] == opponent_paths
    assert report["seeds"] == seeds
    assert report["effective_scenarios_sha256"] == scenario_sha256
    expected_hashes = {entry["path"]: entry["sha256"] for entry in opponents}
    assert report["opponent_sha256_at_start"] == expected_hashes
    assert report["opponent_sha256_at_end"] == expected_hashes
    receipt = Path(report["start_receipt"])
    assert receipt.is_file()
    assert _sha256(receipt) == report["start_receipt_sha256"]

    rows: dict[tuple[str, str, int, int], dict[str, Any]] = {}
    for row in report["games"]:
        key = (row["scenario"], row["opponent"], int(row["seed"]), int(row["seat"]))
        assert key not in rows
        assert row["error"] is None
        assert row["candidate_status"] == row["opponent_status"] == "DONE"
        assert row["candidate_money"] is not None and row["opponent_money"] is not None
        rows[key] = row
    assert set(rows) == expected_keys
    return rows


def analyze(
    candidate_report_path: Path,
    control_report_path: Path,
    runtime_report_path: Path,
    boundary_path: Path,
) -> dict[str, Any]:
    boundary = _load(boundary_path)
    assert boundary["status"] == "DEVELOPMENT_OPEN_AUTHORIZED"
    candidate_report = _load(candidate_report_path)
    control_report = _load(control_report_path)
    runtime = _load(runtime_report_path)
    seeds = list(
        range(
            boundary["pools"]["development"]["start"],
            boundary["pools"]["development"]["end_inclusive"] + 1,
        )
    )
    opponents = boundary["opponents"]
    candidate_rows = _validate_report(
        candidate_report,
        expected_agent=boundary["candidate"],
        opponents=opponents,
        seeds=seeds,
        scenario_sha256=boundary["expected_effective_scenarios_sha256"],
    )
    control_rows = _validate_report(
        control_report,
        expected_agent=boundary["control"],
        opponents=opponents,
        seeds=seeds,
        scenario_sha256=boundary["expected_effective_scenarios_sha256"],
    )
    assert set(candidate_rows) == set(control_rows)

    formal_path = next(
        entry["path"] for entry in opponents if entry["identity"] == "formal_final_day_labor"
    )
    per_opponent: dict[str, dict[str, float | int]] = {}
    for opponent in (entry["path"] for entry in opponents):
        rows = [row for key, row in candidate_rows.items() if key[1] == opponent]
        per_opponent[opponent] = {
            "games": len(rows),
            "match_score": statistics.mean(_outcome(row) for row in rows),
            "margin_mean": statistics.mean(
                float(row["candidate_money"] - row["opponent_money"]) for row in rows
            ),
        }
    top_rows = [row for key, row in candidate_rows.items() if key[1] != formal_path]
    paired_match = [
        _outcome(candidate_rows[key]) - _outcome(control_rows[key]) for key in candidate_rows
    ]
    paired_money = [
        float(candidate_rows[key]["candidate_money"] - control_rows[key]["candidate_money"])
        for key in candidate_rows
    ]
    actions_changed = sum(
        int((row.get("candidate_metrics") or {}).get("actions_changed", 0))
        for row in candidate_rows.values()
    )
    gates = boundary["development_gates"]
    checks = {
        "candidate_failures": candidate_report["summary"]["failed_raw_games"]
        == gates["candidate_failures"],
        "control_failures": control_report["summary"]["failed_raw_games"]
        == gates["control_failures"],
        "top_trace_match": statistics.mean(_outcome(row) for row in top_rows)
        >= gates["minimum_candidate_top_trace_match_score"],
        "each_top_trace_match": all(
            values["match_score"] >= gates["minimum_each_top_trace_match_score"]
            for opponent, values in per_opponent.items()
            if opponent != formal_path
        ),
        "formal_match": per_opponent[formal_path]["match_score"]
        >= gates["minimum_formal_match_score"],
        "each_margin": all(
            values["margin_mean"] >= gates["minimum_each_opponent_mean_margin"]
            for values in per_opponent.values()
        ),
        "paired_match_noninferior": statistics.mean(paired_match)
        >= gates["minimum_paired_match_delta_vs_control"],
        "paired_money_noninferior": statistics.mean(paired_money)
        >= gates["minimum_paired_money_delta_vs_control"],
        "guard_activated": actions_changed >= gates["minimum_actions_changed"],
        "runtime_calls": runtime["calls"] == 720,
        "runtime_invalid": runtime["invalid_outputs"] == gates["invalid_outputs"],
        "runtime_p95": runtime["p95_ms"] <= gates["runtime_p95_ms_max"],
        "runtime_p99": runtime["p99_ms"] <= gates["runtime_p99_ms_max"],
        "runtime_max": runtime["max_ms"] <= gates["runtime_absolute_ms_max"],
        "runtime_source": runtime["source_sha256"] == boundary["candidate"]["sha256"],
        "runtime_replay": runtime["replay_sha256"] == boundary["attribution"]["replay_sha256"],
    }
    return {
        "schema_version": 1,
        "boundary": boundary_path.as_posix(),
        "boundary_sha256": _sha256(boundary_path),
        "candidate_report": candidate_report_path.as_posix(),
        "candidate_report_sha256": _sha256(candidate_report_path),
        "control_report": control_report_path.as_posix(),
        "control_report_sha256": _sha256(control_report_path),
        "runtime_report": runtime_report_path.as_posix(),
        "runtime_report_sha256": _sha256(runtime_report_path),
        "cells": len(candidate_rows),
        "top_trace_match_score": statistics.mean(_outcome(row) for row in top_rows),
        "formal_match_score": per_opponent[formal_path]["match_score"],
        "per_opponent": per_opponent,
        "paired_match_delta": statistics.mean(paired_match),
        "paired_money_delta": statistics.mean(paired_money),
        "actions_changed": actions_changed,
        "runtime": runtime,
        "checks": checks,
        "development_pass": all(checks.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze frozen Fa04 top-trace development")
    parser.add_argument("--candidate-report", type=Path, required=True)
    parser.add_argument("--control-report", type=Path, required=True)
    parser.add_argument("--runtime-report", type=Path, required=True)
    parser.add_argument("--boundary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(
        args.candidate_report,
        args.control_report,
        args.runtime_report,
        args.boundary,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"development_pass": result["development_pass"], **result["checks"]}))
    if not result["development_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
