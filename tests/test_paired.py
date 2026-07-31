from __future__ import annotations

import ast
import copy
import json
import sys
from pathlib import Path

import pytest

from kaggriculture_lab.evaluation.paired import compare_report_files, compare_reports


def test_paired_module_imports_only_python_standard_library() -> None:
    source = Path("src/kaggriculture_lab/evaluation/paired.py").read_text(encoding="utf-8")
    modules = {
        alias.name.split(".")[0]
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
    }
    assert modules <= set(sys.stdlib_module_names) | {"__future__"}


def _row(
    scenario: str,
    opponent: str,
    seed: int,
    seat: int,
    money: float | None,
    opponent_money: float | None,
    *,
    config_hash: str = "CELL-CONFIG",
    environment_hash: str | None = "ENV-CONFIG",
    candidate_status: str = "DONE",
    opponent_status: str = "DONE",
    error: str | None = None,
) -> dict[str, object]:
    row: dict[str, object] = {
        "scenario": scenario,
        "opponent": opponent,
        "seed": seed,
        "seat": seat,
        "candidate_money": money,
        "opponent_money": opponent_money,
        "candidate_status": candidate_status,
        "opponent_status": opponent_status,
        "error": error,
        "effective_configuration_sha256": config_hash,
    }
    if environment_hash is not None:
        row["environment_configuration_sha256"] = environment_hash
    return row


def _report(games: list[dict[str, object]], config_hash: str = "REPORT-CONFIG") -> dict:
    return {
        "schema_version": 1,
        "effective_scenarios_sha256": config_hash,
        "games": games,
    }


def test_all_scenarios_opponents_and_seats_for_one_seed_form_one_cluster() -> None:
    candidate = []
    control = []
    for scenario in ("base", "stress"):
        for opponent in ("alpha", "beta"):
            for seat in (0, 1):
                candidate.append(_row(scenario, opponent, 101, seat, 200, 100))
                control.append(_row(scenario, opponent, 101, seat, 90, 100))

    result = compare_reports(_report(candidate), _report(control))

    assert result["raw_cells"] == 8
    assert result["paired"]["seed_cluster_count"] == 1
    assert result["paired"]["seed_clusters"] == [
        {
            "seed": 101,
            "paired_valid_cells": 8,
            "match_score_delta_mean": 1.0,
            "money_delta_mean": 110.0,
        }
    ]
    assert result["paired"]["match_score_delta_seed_cluster_bootstrap_95"] == [
        1.0,
        1.0,
    ]
    assert result["paired"]["money_delta_seed_cluster_bootstrap_95"] == [110.0, 110.0]


def _known_reports() -> tuple[dict, dict]:
    keys = [
        ("base", "alpha", 1, 0),
        ("base", "alpha", 1, 1),
        ("stress", "beta", 1, 0),
        ("stress", "beta", 1, 1),
        ("base", "alpha", 2, 0),
        ("base", "alpha", 2, 1),
        ("stress", "beta", 2, 0),
        ("stress", "beta", 2, 1),
    ]
    candidate_values = [
        (100, 90),
        (90, 90),
        (70, 75),
        (110, 100),
        (50, 60),
        (120, 100),
        (80, 80),
        (60, 70),
    ]
    control_values = [
        (80, 90),
        (85, 85),
        (60, 55),
        (100, 110),
        (40, 50),
        (100, 100),
        (70, 80),
        (90, 80),
    ]
    candidate = [
        _row(*key, money, opponent_money)
        for key, (money, opponent_money) in zip(keys, candidate_values, strict=True)
    ]
    control = [
        _row(*key, money, opponent_money)
        for key, (money, opponent_money) in zip(keys, control_values, strict=True)
    ]
    return _report(candidate), _report(control)


def test_known_overall_scenario_paired_and_cluster_metrics_are_exact() -> None:
    candidate, control = _known_reports()

    result = compare_reports(candidate, control)

    assert result["candidate"]["match_score"] == 0.5
    assert result["control"]["match_score"] == 0.375
    assert result["candidate"]["per_scenario"]["base"]["match_score"] == 0.625
    assert result["candidate"]["per_scenario"]["stress"]["match_score"] == 0.375
    assert result["control"]["per_scenario"]["base"]["match_score"] == 0.25
    assert result["control"]["per_scenario"]["stress"]["match_score"] == 0.5
    assert result["candidate"]["per_opponent"] == {
        "alpha": {
            "raw_cells": 4,
            "valid_cells": 4,
            "match_score": 0.625,
            "money_mean": 90.0,
            "margin_mean": 5.0,
        },
        "beta": {
            "raw_cells": 4,
            "valid_cells": 4,
            "match_score": 0.375,
            "money_mean": 80.0,
            "margin_mean": -1.25,
        },
    }
    assert result["control"]["per_opponent"] == {
        "alpha": {
            "raw_cells": 4,
            "valid_cells": 4,
            "match_score": 0.25,
            "money_mean": 76.25,
            "margin_mean": -5.0,
        },
        "beta": {
            "raw_cells": 4,
            "valid_cells": 4,
            "match_score": 0.5,
            "money_mean": 80.0,
            "margin_mean": -1.25,
        },
    }
    assert result["paired"]["match_score_delta_mean"] == 0.125
    assert result["paired"]["money_delta_mean"] == 6.875
    assert result["paired"]["money_delta_p10"] == -5.5
    assert result["paired"]["money_delta_p10_method"] == "R-7 linear interpolation"
    assert result["paired"]["seed_cluster_count"] == 2
    assert result["paired"]["match_score_delta_seed_cluster_bootstrap_95"] == [
        0.0,
        0.25,
    ]
    assert result["paired"]["money_delta_seed_cluster_bootstrap_95"] == [2.5, 11.25]
    assert result["paired"]["per_opponent"] == {
        "alpha": {
            "raw_cells": 4,
            "valid_cells": 4,
            "match_score_delta_mean": 0.375,
            "money_delta_mean": 13.75,
            "seed_cluster_count": 2,
            "match_score_delta_seed_cluster_bootstrap_95": [0.25, 0.5],
            "money_delta_seed_cluster_bootstrap_95": [12.5, 15.0],
        },
        "beta": {
            "raw_cells": 4,
            "valid_cells": 4,
            "match_score_delta_mean": -0.125,
            "money_delta_mean": 0.0,
            "seed_cluster_count": 2,
            "match_score_delta_seed_cluster_bootstrap_95": [-0.25, 0.0],
            "money_delta_seed_cluster_bootstrap_95": [-10.0, 10.0],
        },
    }
    assert result["failures"] == {"candidate": 0, "control": 0, "either_policy_cells": 0}
    assert result["invalid"] == {"candidate": 0, "control": 0, "either_policy_cells": 0}


def test_failures_and_invalid_rows_are_explicit_and_excluded_from_paired_metrics() -> None:
    candidate = _report(
        [
            _row(
                "base",
                "alpha",
                1,
                0,
                None,
                None,
                candidate_status="EXCEPTION",
                opponent_status="UNKNOWN",
                error="RuntimeError: boom",
                environment_hash=None,
            ),
            _row("base", "alpha", 1, 1, 20, 10),
        ]
    )
    control = _report(
        [
            _row("base", "alpha", 1, 0, 15, 10),
            _row("base", "alpha", 1, 1, None, 10),
        ]
    )

    result = compare_reports(candidate, control)

    assert result["failures"] == {"candidate": 1, "control": 0, "either_policy_cells": 1}
    assert result["invalid"] == {"candidate": 0, "control": 1, "either_policy_cells": 1}
    assert result["paired"]["valid_cells"] == 0
    assert result["paired"]["match_score_delta_mean"] is None
    assert result["paired"]["seed_cluster_count"] == 0
    assert [cell["paired_valid"] for cell in result["cells"]] == [False, False]
    assert result["candidate"]["per_opponent"]["alpha"] == {
        "raw_cells": 2,
        "valid_cells": 1,
        "match_score": 1.0,
        "money_mean": 20.0,
        "margin_mean": 10.0,
    }
    assert result["control"]["per_opponent"]["alpha"] == {
        "raw_cells": 2,
        "valid_cells": 1,
        "match_score": 1.0,
        "money_mean": 15.0,
        "margin_mean": 5.0,
    }
    assert result["paired"]["per_opponent"]["alpha"] == {
        "raw_cells": 2,
        "valid_cells": 0,
        "match_score_delta_mean": None,
        "money_delta_mean": None,
        "seed_cluster_count": 0,
        "match_score_delta_seed_cluster_bootstrap_95": None,
        "money_delta_seed_cluster_bootstrap_95": None,
    }


def test_missing_cell_is_rejected() -> None:
    candidate, control = _known_reports()
    control["games"].pop()

    with pytest.raises(ValueError, match="paired cell mismatch"):
        compare_reports(candidate, control)


@pytest.mark.parametrize("which", ["candidate", "control"])
def test_duplicate_cell_is_rejected(which: str) -> None:
    candidate, control = _known_reports()
    report = candidate if which == "candidate" else control
    report["games"].append(copy.deepcopy(report["games"][0]))

    with pytest.raises(ValueError, match=f"duplicate {which} cell"):
        compare_reports(candidate, control)


def test_report_configuration_hash_mismatch_is_rejected() -> None:
    candidate, control = _known_reports()
    control["effective_scenarios_sha256"] = "DIFFERENT"

    with pytest.raises(ValueError, match="report configuration hash mismatch"):
        compare_reports(candidate, control)


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("effective_configuration_sha256", "cell configuration hash mismatch"),
        ("environment_configuration_sha256", "environment configuration hash mismatch"),
    ],
)
def test_cell_configuration_hash_mismatch_is_rejected(field: str, message: str) -> None:
    candidate, control = _known_reports()
    control["games"][0][field] = "DIFFERENT"

    with pytest.raises(ValueError, match=message):
        compare_reports(candidate, control)


def test_report_file_loader_is_deterministic(tmp_path: Path) -> None:
    candidate, control = _known_reports()
    candidate_path = tmp_path / "candidate.json"
    control_path = tmp_path / "control.json"
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
    control_path.write_text(json.dumps(control), encoding="utf-8")

    first = compare_report_files(candidate_path, control_path)
    second = compare_report_files(candidate_path, control_path)

    assert first == second
    assert first["paired"]["bootstrap_draws"] == 10_000
