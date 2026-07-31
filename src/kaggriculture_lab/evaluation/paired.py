"""Strict paired comparison for two Kaggriculture runner reports.

Candidate and control games are matched by the complete experimental cell:
``(scenario, opponent, seed, seat)``.  Bootstrap resampling uses the seed as the
cluster, so every scenario, opponent, and seat sharing a seed moves together.
"""

from __future__ import annotations

import json
import math
import random
import statistics
from collections.abc import Mapping, Sequence
from fractions import Fraction
from pathlib import Path
from typing import Any

CellKey = tuple[str, str, int, int]

BOOTSTRAP_DRAWS = 10_000
BOOTSTRAP_RANDOM_SEED = 0


def _require_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be an object")
    return value


def _require_games(report: Mapping[str, Any], label: str) -> Sequence[object]:
    games = report.get("games")
    if not isinstance(games, list):
        raise TypeError(f"{label}.games must be a list")
    return games


def _cell_key(row: Mapping[str, Any], label: str) -> CellKey:
    missing = [field for field in ("scenario", "opponent", "seed", "seat") if field not in row]
    if missing:
        raise ValueError(f"{label} is missing cell fields: {missing}")
    scenario = row["scenario"]
    opponent = row["opponent"]
    seed = row["seed"]
    seat = row["seat"]
    if not isinstance(scenario, str) or not scenario:
        raise ValueError(f"{label}.scenario must be a non-empty string")
    if not isinstance(opponent, str) or not opponent:
        raise ValueError(f"{label}.opponent must be a non-empty string")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError(f"{label}.seed must be an integer")
    if isinstance(seat, bool) or not isinstance(seat, int):
        raise TypeError(f"{label}.seat must be an integer")
    if seat not in (0, 1):
        raise ValueError(f"{label}.seat must be 0 or 1")
    return scenario, opponent, seed, seat


def _index_report(report: Mapping[str, Any], label: str) -> dict[CellKey, Mapping[str, Any]]:
    indexed: dict[CellKey, Mapping[str, Any]] = {}
    for index, raw_row in enumerate(_require_games(report, label)):
        row = _require_mapping(raw_row, f"{label}.games[{index}]")
        key = _cell_key(row, f"{label}.games[{index}]")
        if key in indexed:
            raise ValueError(f"duplicate {label} cell: {key}")
        indexed[key] = row
    return indexed


def _configuration_hash(row: Mapping[str, Any], label: str) -> str:
    value = row.get("effective_configuration_sha256")
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} is missing effective_configuration_sha256")
    return value


def _validate_report_configuration_hashes(
    candidate_report: Mapping[str, Any], control_report: Mapping[str, Any]
) -> None:
    field = "effective_scenarios_sha256"
    candidate_hash = candidate_report.get(field)
    control_hash = control_report.get(field)
    if candidate_hash is None and control_hash is None:
        return
    if candidate_hash is None or control_hash is None:
        raise ValueError(f"both reports must provide {field} when either report does")
    if not isinstance(candidate_hash, str) or not isinstance(control_hash, str):
        raise TypeError(f"both {field} values must be strings")
    if candidate_hash != control_hash:
        raise ValueError(
            f"report configuration hash mismatch: candidate={candidate_hash!r}, "
            f"control={control_hash!r}"
        )


def _validate_cell_configuration(
    key: CellKey,
    candidate_row: Mapping[str, Any],
    control_row: Mapping[str, Any],
) -> str:
    candidate_hash = _configuration_hash(candidate_row, f"candidate cell {key}")
    control_hash = _configuration_hash(control_row, f"control cell {key}")
    if candidate_hash != control_hash:
        raise ValueError(
            f"cell configuration hash mismatch for {key}: "
            f"candidate={candidate_hash!r}, control={control_hash!r}"
        )

    candidate_environment = candidate_row.get("environment_configuration_sha256")
    control_environment = control_row.get("environment_configuration_sha256")
    if candidate_environment is not None and control_environment is not None:
        if not isinstance(candidate_environment, str) or not isinstance(control_environment, str):
            raise TypeError(f"environment configuration hashes must be strings at {key}")
        if candidate_environment != control_environment:
            raise ValueError(f"environment configuration hash mismatch for {key}")
    elif candidate_environment is not None or control_environment is not None:
        # Runner exception rows cannot record the realized environment hash.  The
        # requested/effective hash above is still mandatory and comparable; preserve
        # the failed cell so the result can report it instead of hiding the failure.
        if _row_quality(candidate_row) == "valid" and _row_quality(control_row) == "valid":
            raise ValueError(f"environment configuration hash missing for one report at {key}")
    return candidate_hash


def _finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _row_quality(row: Mapping[str, Any]) -> str:
    error = row.get("error")
    candidate_status = row.get("candidate_status")
    opponent_status = row.get("opponent_status")
    if error is not None or candidate_status != "DONE" or opponent_status != "DONE":
        return "failure"
    if not _finite_number(row.get("candidate_money")) or not _finite_number(
        row.get("opponent_money")
    ):
        return "invalid"
    return "valid"


def _outcome(row: Mapping[str, Any]) -> float:
    candidate_money = float(row["candidate_money"])
    opponent_money = float(row["opponent_money"])
    if candidate_money > opponent_money:
        return 1.0
    if candidate_money < opponent_money:
        return 0.0
    return 0.5


def _policy_summary(cells: list[dict[str, Any]], policy: str) -> dict[str, Any]:
    outcomes: list[float] = []
    money: list[float] = []
    per_scenario_values: dict[str, list[tuple[float, float, float]]] = {}
    per_opponent_values: dict[str, list[tuple[float, float, float]]] = {}
    quality = {"valid": 0, "failures": 0, "invalid": 0}
    for cell in cells:
        record = cell[policy]
        state = record["quality"]
        quality[{"valid": "valid", "failure": "failures", "invalid": "invalid"}[state]] += 1
        if state != "valid":
            continue
        outcome = float(record["outcome"])
        cash = float(record["money"])
        margin = cash - float(record["opponent_money"])
        outcomes.append(outcome)
        money.append(cash)
        value = (outcome, cash, margin)
        per_scenario_values.setdefault(cell["scenario"], []).append(value)
        per_opponent_values.setdefault(cell["opponent"], []).append(value)

    per_scenario = {}
    scenarios = sorted({str(cell["scenario"]) for cell in cells})
    for scenario in scenarios:
        values = per_scenario_values.get(scenario, [])
        raw_cells = sum(cell["scenario"] == scenario for cell in cells)
        per_scenario[scenario] = {
            "raw_cells": raw_cells,
            "valid_cells": len(values),
            "match_score": statistics.fmean(value[0] for value in values) if values else None,
            "money_mean": statistics.fmean(value[1] for value in values) if values else None,
        }
    per_opponent = {}
    opponents = sorted({str(cell["opponent"]) for cell in cells})
    for opponent in opponents:
        values = per_opponent_values.get(opponent, [])
        raw_cells = sum(cell["opponent"] == opponent for cell in cells)
        per_opponent[opponent] = {
            "raw_cells": raw_cells,
            "valid_cells": len(values),
            "match_score": statistics.fmean(value[0] for value in values) if values else None,
            "money_mean": statistics.fmean(value[1] for value in values) if values else None,
            "margin_mean": statistics.fmean(value[2] for value in values) if values else None,
        }
    return {
        "raw_cells": len(cells),
        "valid_cells": quality["valid"],
        "failures": quality["failures"],
        "invalid": quality["invalid"],
        "match_score": statistics.fmean(outcomes) if outcomes else None,
        "money_mean": statistics.fmean(money) if money else None,
        "per_scenario": per_scenario,
        "per_opponent": per_opponent,
    }


def _percentile(values: list[float], probability: float) -> float | None:
    """R-7/NumPy-linear empirical percentile without a third-party dependency."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * Fraction(str(probability))
    lower = position.numerator // position.denominator
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    interpolated = (
        Fraction(str(ordered[lower])) * (1 - weight) + Fraction(str(ordered[upper])) * weight
    )
    return float(interpolated)


def _cluster_bootstrap_ci(
    cluster_values: list[float], draws: int, random_seed: int
) -> list[float] | None:
    if not cluster_values:
        return None
    if draws <= 0:
        raise ValueError("bootstrap_draws must be positive")
    rng = random.Random(random_seed)
    sample_size = len(cluster_values)
    estimates = sorted(
        statistics.fmean(rng.choice(cluster_values) for _ in range(sample_size))
        for _ in range(draws)
    )
    lower = max(0, math.ceil(0.025 * draws) - 1)
    upper = max(0, math.ceil(0.975 * draws) - 1)
    return [estimates[lower], estimates[upper]]


def _paired_summary(
    cells: list[dict[str, Any]], bootstrap_draws: int, bootstrap_random_seed: int
) -> dict[str, Any]:
    valid = [cell for cell in cells if cell["paired_valid"]]
    match_deltas = [float(cell["match_score_delta"]) for cell in valid]
    money_deltas = [float(cell["money_delta"]) for cell in valid]

    by_seed: dict[int, dict[str, list[float]]] = {}
    for cell in valid:
        cluster = by_seed.setdefault(int(cell["seed"]), {"match": [], "money": []})
        cluster["match"].append(float(cell["match_score_delta"]))
        cluster["money"].append(float(cell["money_delta"]))
    seed_clusters = [
        {
            "seed": seed,
            "paired_valid_cells": len(values["match"]),
            "match_score_delta_mean": statistics.fmean(values["match"]),
            "money_delta_mean": statistics.fmean(values["money"]),
        }
        for seed, values in sorted(by_seed.items())
    ]
    cluster_match = [float(cluster["match_score_delta_mean"]) for cluster in seed_clusters]
    cluster_money = [float(cluster["money_delta_mean"]) for cluster in seed_clusters]
    money_p10 = _percentile(money_deltas, 0.10)
    per_opponent = {}
    for opponent in sorted({str(cell["opponent"]) for cell in cells}):
        opponent_cells = [cell for cell in valid if cell["opponent"] == opponent]
        opponent_match = [float(cell["match_score_delta"]) for cell in opponent_cells]
        opponent_money = [float(cell["money_delta"]) for cell in opponent_cells]
        opponent_by_seed: dict[int, dict[str, list[float]]] = {}
        for cell in opponent_cells:
            cluster = opponent_by_seed.setdefault(int(cell["seed"]), {"match": [], "money": []})
            cluster["match"].append(float(cell["match_score_delta"]))
            cluster["money"].append(float(cell["money_delta"]))
        opponent_cluster_match = [
            statistics.fmean(values["match"]) for _, values in sorted(opponent_by_seed.items())
        ]
        opponent_cluster_money = [
            statistics.fmean(values["money"]) for _, values in sorted(opponent_by_seed.items())
        ]
        per_opponent[opponent] = {
            "raw_cells": sum(cell["opponent"] == opponent for cell in cells),
            "valid_cells": len(opponent_cells),
            "match_score_delta_mean": (
                statistics.fmean(opponent_match) if opponent_match else None
            ),
            "money_delta_mean": statistics.fmean(opponent_money) if opponent_money else None,
            "seed_cluster_count": len(opponent_by_seed),
            "match_score_delta_seed_cluster_bootstrap_95": _cluster_bootstrap_ci(
                opponent_cluster_match, bootstrap_draws, bootstrap_random_seed
            ),
            "money_delta_seed_cluster_bootstrap_95": _cluster_bootstrap_ci(
                opponent_cluster_money, bootstrap_draws, bootstrap_random_seed
            ),
        }
    return {
        "valid_cells": len(valid),
        "match_score_delta_mean": statistics.fmean(match_deltas) if match_deltas else None,
        "money_delta_mean": statistics.fmean(money_deltas) if money_deltas else None,
        "money_delta_p10": money_p10,
        "money_delta_p10_method": "R-7 linear interpolation",
        "seed_cluster_count": len(seed_clusters),
        "bootstrap_cluster_unit": "seed",
        "bootstrap_draws": bootstrap_draws,
        "bootstrap_random_seed": bootstrap_random_seed,
        "match_score_delta_seed_cluster_bootstrap_95": _cluster_bootstrap_ci(
            cluster_match, bootstrap_draws, bootstrap_random_seed
        ),
        "money_delta_seed_cluster_bootstrap_95": _cluster_bootstrap_ci(
            cluster_money, bootstrap_draws, bootstrap_random_seed
        ),
        "seed_clusters": seed_clusters,
        "per_opponent": per_opponent,
    }


def compare_reports(
    candidate_report: Mapping[str, Any],
    control_report: Mapping[str, Any],
    *,
    bootstrap_draws: int = BOOTSTRAP_DRAWS,
    bootstrap_random_seed: int = BOOTSTRAP_RANDOM_SEED,
) -> dict[str, Any]:
    """Strictly match and compare two in-memory runner reports."""
    candidate_report = _require_mapping(candidate_report, "candidate_report")
    control_report = _require_mapping(control_report, "control_report")
    _validate_report_configuration_hashes(candidate_report, control_report)
    candidate_rows = _index_report(candidate_report, "candidate")
    control_rows = _index_report(control_report, "control")
    candidate_keys = set(candidate_rows)
    control_keys = set(control_rows)
    if candidate_keys != control_keys:
        candidate_only = sorted(candidate_keys - control_keys)
        control_only = sorted(control_keys - candidate_keys)
        raise ValueError(
            f"paired cell mismatch: candidate_only={candidate_only}, control_only={control_only}"
        )
    if not candidate_keys:
        raise ValueError("paired reports contain no cells")

    cells: list[dict[str, Any]] = []
    for key in sorted(candidate_keys):
        candidate_row = candidate_rows[key]
        control_row = control_rows[key]
        configuration_hash = _validate_cell_configuration(key, candidate_row, control_row)
        candidate_quality = _row_quality(candidate_row)
        control_quality = _row_quality(control_row)
        candidate_outcome = _outcome(candidate_row) if candidate_quality == "valid" else None
        control_outcome = _outcome(control_row) if control_quality == "valid" else None
        paired_valid = candidate_quality == control_quality == "valid"
        cells.append(
            {
                "scenario": key[0],
                "opponent": key[1],
                "seed": key[2],
                "seat": key[3],
                "effective_configuration_sha256": configuration_hash,
                "candidate": {
                    "quality": candidate_quality,
                    "status": candidate_row.get("candidate_status"),
                    "opponent_status": candidate_row.get("opponent_status"),
                    "error": candidate_row.get("error"),
                    "money": (
                        float(candidate_row["candidate_money"])
                        if candidate_quality == "valid"
                        else None
                    ),
                    "opponent_money": (
                        float(candidate_row["opponent_money"])
                        if candidate_quality == "valid"
                        else None
                    ),
                    "outcome": candidate_outcome,
                },
                "control": {
                    "quality": control_quality,
                    "status": control_row.get("candidate_status"),
                    "opponent_status": control_row.get("opponent_status"),
                    "error": control_row.get("error"),
                    "money": (
                        float(control_row["candidate_money"])
                        if control_quality == "valid"
                        else None
                    ),
                    "opponent_money": (
                        float(control_row["opponent_money"]) if control_quality == "valid" else None
                    ),
                    "outcome": control_outcome,
                },
                "paired_valid": paired_valid,
                "match_score_delta": (
                    float(candidate_outcome - control_outcome) if paired_valid else None
                ),
                "money_delta": (
                    float(candidate_row["candidate_money"] - control_row["candidate_money"])
                    if paired_valid
                    else None
                ),
            }
        )

    candidate_summary = _policy_summary(cells, "candidate")
    control_summary = _policy_summary(cells, "control")
    paired = _paired_summary(cells, bootstrap_draws, bootstrap_random_seed)
    failures = {
        "candidate": candidate_summary["failures"],
        "control": control_summary["failures"],
        "either_policy_cells": sum(
            cell["candidate"]["quality"] == "failure" or cell["control"]["quality"] == "failure"
            for cell in cells
        ),
    }
    invalid = {
        "candidate": candidate_summary["invalid"],
        "control": control_summary["invalid"],
        "either_policy_cells": sum(
            cell["candidate"]["quality"] == "invalid" or cell["control"]["quality"] == "invalid"
            for cell in cells
        ),
    }
    return {
        "schema_version": 1,
        "cell_key": ["scenario", "opponent", "seed", "seat"],
        "raw_cells": len(cells),
        "candidate": candidate_summary,
        "control": control_summary,
        "paired": paired,
        "failures": failures,
        "invalid": invalid,
        "cells": cells,
    }


def compare_report_files(
    candidate_path: str | Path,
    control_path: str | Path,
    *,
    bootstrap_draws: int = BOOTSTRAP_DRAWS,
    bootstrap_random_seed: int = BOOTSTRAP_RANDOM_SEED,
) -> dict[str, Any]:
    """Load two JSON runner reports and return :func:`compare_reports`."""
    candidate = json.loads(Path(candidate_path).read_text(encoding="utf-8"))
    control = json.loads(Path(control_path).read_text(encoding="utf-8"))
    return compare_reports(
        candidate,
        control,
        bootstrap_draws=bootstrap_draws,
        bootstrap_random_seed=bootstrap_random_seed,
    )


analyze_paired_reports = compare_reports
