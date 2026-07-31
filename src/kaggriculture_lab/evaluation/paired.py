"""Strict paired comparison for two Kaggriculture runner reports.

Candidate and control games are matched by the complete experimental cell:
``(scenario, opponent, seed, seat)``.  Bootstrap resampling uses the seed as the
cluster, so every scenario, opponent, and seat sharing a seed moves together.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
import statistics
from collections.abc import Mapping, Sequence
from fractions import Fraction
from pathlib import Path
from typing import Any

CellKey = tuple[str, str, int, int]

BOOTSTRAP_DRAWS = 10_000
BOOTSTRAP_RANDOM_SEED = 0

EXPECTED_CONTRACT_FIELDS = (
    "candidate_source_sha256",
    "control_source_sha256",
    "root_config",
    "scenario_config",
    "effective_scenarios_sha256",
    "opponent_source_sha256",
    "cell_keys",
    "cell_count",
)


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


def _normalized_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9A-Fa-f]{64}", value) is None:
        raise ValueError(f"{label} must be exactly 64 hexadecimal SHA-256 characters")
    return value.upper()


def _canonical_json_bytes(value: object, label: str) -> bytes:
    """Match runner._json_sha256 serialization exactly."""
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{label} must be canonical-JSON serializable") from exc


def _json_sha256(value: object, label: str) -> str:
    return hashlib.sha256(_canonical_json_bytes(value, label)).hexdigest().upper()


def _file_contract(contract: Mapping[str, Any], field: str) -> dict[str, str]:
    entry = _require_mapping(contract.get(field), f"expected_contract.{field}")
    path_value = entry.get("path")
    if not isinstance(path_value, (str, Path)):
        raise TypeError(f"expected_contract.{field}.path must be a path")
    path = Path(path_value)
    if not path.is_file():
        raise FileNotFoundError(f"expected contract file does not exist: {path}")
    expected = _normalized_sha256(entry.get("sha256"), f"expected_contract.{field}.sha256")
    actual = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    if actual != expected:
        raise ValueError(
            f"{field} hash mismatch: expected={expected!r}, actual={actual!r}, path={path}"
        )
    return {"path": path.as_posix(), "sha256": actual}


def _expected_cell_keys(contract: Mapping[str, Any]) -> tuple[set[CellKey], int]:
    raw_keys = contract.get("cell_keys")
    if not isinstance(raw_keys, list):
        raise TypeError("expected_contract.cell_keys must be a list")
    normalized = []
    for index, raw_key in enumerate(raw_keys):
        if not isinstance(raw_key, (list, tuple)) or len(raw_key) != 4:
            raise ValueError(f"expected_contract.cell_keys[{index}] must have four fields")
        normalized.append(
            _cell_key(
                dict(zip(("scenario", "opponent", "seed", "seat"), raw_key, strict=True)),
                f"expected_contract.cell_keys[{index}]",
            )
        )
    expected_keys = set(normalized)
    if len(expected_keys) != len(normalized):
        raise ValueError("expected_contract.cell_keys contains duplicates")
    count = contract.get("cell_count")
    if isinstance(count, bool) or not isinstance(count, int):
        raise TypeError("expected_contract.cell_count must be an integer")
    if count <= 0 or count != len(expected_keys):
        raise ValueError(
            f"expected contract cardinality mismatch: cell_count={count}, "
            f"unique_cell_keys={len(expected_keys)}"
        )
    return expected_keys, count


def _validate_report_source(report: Mapping[str, Any], label: str, expected_hash: str) -> None:
    for field in ("candidate_sha256", "candidate_sha256_at_start", "candidate_sha256_at_end"):
        actual = _normalized_sha256(report.get(field), f"{label}.{field}")
        if actual != expected_hash:
            raise ValueError(
                f"{label} source hash mismatch at {field}: "
                f"expected={expected_hash!r}, actual={actual!r}"
            )
    if report.get("sources_unchanged_during_run") is not True:
        raise ValueError(f"{label}.sources_unchanged_during_run must be true")


def _validate_opponent_sources(
    report: Mapping[str, Any], label: str, expected: Mapping[str, Any]
) -> None:
    normalized_expected = {
        str(name): _normalized_sha256(value, f"expected opponent {name!r}")
        for name, value in expected.items()
    }
    for field in ("opponent_sha256_at_start", "opponent_sha256_at_end"):
        actual = _require_mapping(report.get(field), f"{label}.{field}")
        normalized_actual = {
            str(name): _normalized_sha256(value, f"{label}.{field}[{name!r}]")
            for name, value in actual.items()
        }
        if normalized_actual != normalized_expected:
            raise ValueError(
                f"{label} opponent source hash mismatch at {field}: "
                f"expected={normalized_expected!r}, actual={normalized_actual!r}"
            )


def _validate_report_effective_scenarios(
    report: Mapping[str, Any], label: str, expected_hash: str
) -> Mapping[str, Any]:
    scenarios = _require_mapping(report.get("effective_scenarios"), f"{label}.effective_scenarios")
    recalculated_hash = _json_sha256(scenarios, f"{label}.effective_scenarios")
    reported_hash = _normalized_sha256(
        report.get("effective_scenarios_sha256"),
        f"{label}.effective_scenarios_sha256",
    )
    if reported_hash != recalculated_hash:
        raise ValueError(
            f"{label} effective scenarios hash does not match mapping: "
            f"reported={reported_hash!r}, recalculated={recalculated_hash!r}"
        )
    if recalculated_hash != expected_hash:
        raise ValueError(
            f"{label} effective scenario hash mismatch: "
            f"expected={expected_hash!r}, actual={recalculated_hash!r}"
        )
    for scenario, configuration in scenarios.items():
        if not isinstance(scenario, str) or not scenario:
            raise ValueError(f"{label}.effective_scenarios keys must be non-empty strings")
        _require_mapping(
            configuration,
            f"{label}.effective_scenarios[{scenario!r}]",
        )
    return scenarios


def _validate_row_effective_configuration(
    row: Mapping[str, Any],
    label: str,
    key: CellKey,
    effective_scenarios: Mapping[str, Any],
) -> None:
    if key[0] not in effective_scenarios:
        raise ValueError(f"{label} cell {key} references an unknown effective scenario")
    scenario_configuration = _require_mapping(
        effective_scenarios[key[0]],
        f"{label}.effective_scenarios[{key[0]!r}]",
    )
    expected_configuration = dict(scenario_configuration)
    expected_configuration["seed"] = key[2]
    expected_payload = _canonical_json_bytes(
        expected_configuration,
        f"{label} cell {key} expected effective_configuration",
    )
    expected_hash = hashlib.sha256(expected_payload).hexdigest().upper()

    actual_configuration = _require_mapping(
        row.get("effective_configuration"),
        f"{label} cell {key}.effective_configuration",
    )
    actual_payload = _canonical_json_bytes(
        actual_configuration,
        f"{label} cell {key}.effective_configuration",
    )
    recalculated_hash = hashlib.sha256(actual_payload).hexdigest().upper()
    reported_hash = _normalized_sha256(
        row.get("effective_configuration_sha256"),
        f"{label} cell {key}.effective_configuration_sha256",
    )
    if reported_hash != recalculated_hash:
        raise ValueError(
            f"{label} cell {key} effective configuration hash does not match mapping: "
            f"reported={reported_hash!r}, recalculated={recalculated_hash!r}"
        )
    if actual_payload != expected_payload or reported_hash != expected_hash:
        raise ValueError(
            f"{label} cell {key} effective configuration does not match "
            "the scenario with requested seed injected"
        )


def _validated_environment_configuration(
    row: Mapping[str, Any], label: str, key: CellKey
) -> tuple[bytes, str]:
    mapping_present = (
        "environment_configuration" in row and row["environment_configuration"] is not None
    )
    hash_present = (
        "environment_configuration_sha256" in row
        and row["environment_configuration_sha256"] is not None
    )
    if not mapping_present or not hash_present:
        raise ValueError(f"{label} cell {key} must provide environment_configuration and its hash")
    configuration = _require_mapping(
        row["environment_configuration"],
        f"{label} cell {key}.environment_configuration",
    )
    payload = _canonical_json_bytes(
        configuration,
        f"{label} cell {key}.environment_configuration",
    )
    recalculated_hash = hashlib.sha256(payload).hexdigest().upper()
    reported_hash = _normalized_sha256(
        row["environment_configuration_sha256"],
        f"{label} cell {key}.environment_configuration_sha256",
    )
    if reported_hash != recalculated_hash:
        raise ValueError(
            f"{label} cell {key} environment configuration hash does not match mapping: "
            f"reported={reported_hash!r}, recalculated={recalculated_hash!r}"
        )
    return payload, reported_hash


def _validate_expected_contract(
    candidate_report: Mapping[str, Any],
    control_report: Mapping[str, Any],
    candidate_rows: Mapping[CellKey, Mapping[str, Any]],
    control_rows: Mapping[CellKey, Mapping[str, Any]],
    expected_contract: Mapping[str, Any],
) -> dict[str, Any]:
    missing = [field for field in EXPECTED_CONTRACT_FIELDS if field not in expected_contract]
    if missing:
        raise ValueError(f"expected_contract is missing required fields: {missing}")
    candidate_hash = _normalized_sha256(
        expected_contract["candidate_source_sha256"],
        "expected_contract.candidate_source_sha256",
    )
    control_hash = _normalized_sha256(
        expected_contract["control_source_sha256"],
        "expected_contract.control_source_sha256",
    )
    _validate_report_source(candidate_report, "candidate_report", candidate_hash)
    _validate_report_source(control_report, "control_report", control_hash)
    root_config = _file_contract(expected_contract, "root_config")
    scenario_config = _file_contract(expected_contract, "scenario_config")

    effective_hash = _normalized_sha256(
        expected_contract["effective_scenarios_sha256"],
        "expected_contract.effective_scenarios_sha256",
    )
    candidate_scenarios = _validate_report_effective_scenarios(
        candidate_report, "candidate_report", effective_hash
    )
    control_scenarios = _validate_report_effective_scenarios(
        control_report, "control_report", effective_hash
    )
    if _canonical_json_bytes(
        candidate_scenarios, "candidate_report.effective_scenarios"
    ) != _canonical_json_bytes(control_scenarios, "control_report.effective_scenarios"):
        raise ValueError("candidate/control effective scenario mappings do not match")

    expected_keys, expected_count = _expected_cell_keys(expected_contract)
    for label, actual_keys in (
        ("candidate", set(candidate_rows)),
        ("control", set(control_rows)),
    ):
        if actual_keys != expected_keys:
            raise ValueError(
                f"{label} cells violate expected contract: "
                f"missing={sorted(expected_keys - actual_keys)}, "
                f"unexpected={sorted(actual_keys - expected_keys)}"
            )
        if len(actual_keys) != expected_count:
            raise ValueError(
                f"{label} cell cardinality mismatch: "
                f"expected={expected_count}, actual={len(actual_keys)}"
            )

    for key in sorted(expected_keys):
        _validate_row_effective_configuration(
            candidate_rows[key], "candidate", key, candidate_scenarios
        )
        _validate_row_effective_configuration(control_rows[key], "control", key, control_scenarios)
        candidate_environment = _validated_environment_configuration(
            candidate_rows[key], "candidate", key
        )
        control_environment = _validated_environment_configuration(
            control_rows[key], "control", key
        )
        if candidate_environment != control_environment:
            raise ValueError(f"candidate/control environment configuration mismatch for {key}")
        for label, row in (
            ("candidate", candidate_rows[key]),
            ("control", control_rows[key]),
        ):
            resolved = row.get("resolved_environment_seed")
            if resolved is None:
                raise ValueError(f"{label} cell {key} is missing resolved_environment_seed")
            if isinstance(resolved, bool) or not isinstance(resolved, int):
                raise TypeError(f"{label} cell {key} resolved_environment_seed must be an integer")
            if resolved != key[2]:
                raise ValueError(
                    f"{label} resolved environment seed mismatch for {key}: "
                    f"requested={key[2]}, resolved={resolved}"
                )

    opponent_hashes = _require_mapping(
        expected_contract["opponent_source_sha256"],
        "expected_contract.opponent_source_sha256",
    )
    _validate_opponent_sources(candidate_report, "candidate_report", opponent_hashes)
    _validate_opponent_sources(control_report, "control_report", opponent_hashes)

    return {
        "enforced": True,
        "gate_eligible": True,
        "candidate_source_sha256": candidate_hash,
        "control_source_sha256": control_hash,
        "root_config": root_config,
        "scenario_config": scenario_config,
        "effective_scenarios_sha256": effective_hash,
        "expected_cell_count": expected_count,
        "resolved_environment_seed_matches_requested": True,
        "opponent_source_hashes_enforced": True,
    }


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
    expected_contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Strictly match and compare two in-memory runner reports.

    Historical/diagnostic callers may omit ``expected_contract`` and still obtain
    metrics, but the result is explicitly ineligible for promotion-gate use.  A
    gate-eligible comparison must pin sources, config files, effective scenarios,
    the complete cell grid, and resolved environment seeds.
    """
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
    if expected_contract is None:
        contract_result = {
            "enforced": False,
            "gate_eligible": False,
            "reason": "expected_contract was not supplied; metrics are diagnostic only",
        }
    else:
        contract_result = _validate_expected_contract(
            candidate_report,
            control_report,
            candidate_rows,
            control_rows,
            _require_mapping(expected_contract, "expected_contract"),
        )

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
        "gate_eligible": contract_result["gate_eligible"],
        "contract": contract_result,
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
    expected_contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Load two JSON runner reports and return :func:`compare_reports`."""
    candidate = json.loads(Path(candidate_path).read_text(encoding="utf-8"))
    control = json.loads(Path(control_path).read_text(encoding="utf-8"))
    return compare_reports(
        candidate,
        control,
        bootstrap_draws=bootstrap_draws,
        bootstrap_random_seed=bootstrap_random_seed,
        expected_contract=expected_contract,
    )


def require_gate_eligible(result: Mapping[str, Any]) -> None:
    """Reject a metric result that lacks a successfully enforced contract."""
    result = _require_mapping(result, "paired_result")
    contract = _require_mapping(result.get("contract"), "paired_result.contract")
    if result.get("gate_eligible") is not True or contract.get("gate_eligible") is not True:
        reason = contract.get("reason", "expected contract was not successfully enforced")
        raise ValueError(f"paired result is not gate-eligible: {reason}")


analyze_paired_reports = compare_reports
