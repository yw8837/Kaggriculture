from __future__ import annotations

import ast
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

from kaggriculture_lab.evaluation.paired import (
    compare_report_files,
    compare_reports,
    require_gate_eligible,
)


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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _json_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def _contract_fixture(tmp_path: Path) -> tuple[dict, dict, dict]:
    candidate, control = _known_reports()
    root_config = tmp_path / "root.json"
    scenario_config = tmp_path / "scenarios.json"
    root_config.write_text('{"boundary":"frozen"}\n', encoding="utf-8")
    scenario_config.write_text('{"scenarios":{"base":{},"stress":{}}}\n', encoding="utf-8")
    opponent_hashes = {"alpha": "A" * 64, "beta": "B" * 64}
    effective_scenarios = {
        "base": {"episodeSteps": 720, "startingMoney": 100},
        "stress": {"episodeSteps": 720, "startingMoney": 50},
    }
    effective_scenarios_hash = _json_sha256(effective_scenarios)

    for report, source_hash in (
        (candidate, "C" * 64),
        (control, "D" * 64),
    ):
        report["effective_scenarios"] = copy.deepcopy(effective_scenarios)
        report["effective_scenarios_sha256"] = effective_scenarios_hash
        report["candidate_sha256"] = source_hash
        report["candidate_sha256_at_start"] = source_hash
        report["candidate_sha256_at_end"] = source_hash
        report["sources_unchanged_during_run"] = True
        report["opponent_sha256_at_start"] = dict(opponent_hashes)
        report["opponent_sha256_at_end"] = dict(opponent_hashes)
        for row in report["games"]:
            effective_configuration = {
                **effective_scenarios[row["scenario"]],
                "seed": row["seed"],
            }
            row["effective_configuration"] = copy.deepcopy(effective_configuration)
            row["effective_configuration_sha256"] = _json_sha256(effective_configuration)
            row["environment_configuration"] = copy.deepcopy(effective_configuration)
            row["environment_configuration_sha256"] = _json_sha256(effective_configuration)
            row["resolved_environment_seed"] = row["seed"]

    keys = [
        [row["scenario"], row["opponent"], row["seed"], row["seat"]] for row in candidate["games"]
    ]
    contract = {
        "candidate_source_sha256": "C" * 64,
        "control_source_sha256": "D" * 64,
        "root_config": {"path": str(root_config), "sha256": _sha256(root_config)},
        "scenario_config": {
            "path": str(scenario_config),
            "sha256": _sha256(scenario_config),
        },
        "effective_scenarios_sha256": effective_scenarios_hash,
        "opponent_source_sha256": opponent_hashes,
        "cell_keys": keys,
        "cell_count": len(keys),
    }
    return candidate, control, contract


def test_known_overall_scenario_paired_and_cluster_metrics_are_exact() -> None:
    candidate, control = _known_reports()

    result = compare_reports(candidate, control)

    assert result["gate_eligible"] is False
    assert result["contract"]["enforced"] is False
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


def test_metrics_without_expected_contract_cannot_be_used_for_a_gate() -> None:
    candidate, control = _known_reports()
    result = compare_reports(candidate, control)

    with pytest.raises(ValueError, match="not gate-eligible"):
        require_gate_eligible(result)


def test_complete_expected_contract_makes_result_gate_eligible(tmp_path: Path) -> None:
    candidate, control, contract = _contract_fixture(tmp_path)

    result = compare_reports(candidate, control, expected_contract=contract)

    require_gate_eligible(result)
    assert result["gate_eligible"] is True
    assert result["contract"] == {
        "enforced": True,
        "gate_eligible": True,
        "candidate_source_sha256": "C" * 64,
        "control_source_sha256": "D" * 64,
        "root_config": {
            "path": Path(contract["root_config"]["path"]).as_posix(),
            "sha256": contract["root_config"]["sha256"],
        },
        "scenario_config": {
            "path": Path(contract["scenario_config"]["path"]).as_posix(),
            "sha256": contract["scenario_config"]["sha256"],
        },
        "effective_scenarios_sha256": contract["effective_scenarios_sha256"],
        "expected_cell_count": 8,
        "resolved_environment_seed_matches_requested": True,
        "opponent_source_hashes_enforced": True,
    }


def test_expected_contract_rejects_symmetric_cell_omission(tmp_path: Path) -> None:
    candidate, control, contract = _contract_fixture(tmp_path)
    candidate["games"].pop()
    control["games"].pop()

    with pytest.raises(ValueError, match="cells violate expected contract"):
        compare_reports(candidate, control, expected_contract=contract)


def test_expected_contract_requires_opponent_source_hashes(tmp_path: Path) -> None:
    candidate, control, contract = _contract_fixture(tmp_path)
    del contract["opponent_source_sha256"]

    with pytest.raises(ValueError, match="opponent_source_sha256"):
        compare_reports(candidate, control, expected_contract=contract)


@pytest.mark.parametrize("report_name", ["candidate", "control"])
def test_expected_contract_rejects_wrong_policy_source_hash(
    tmp_path: Path, report_name: str
) -> None:
    candidate, control, contract = _contract_fixture(tmp_path)
    report = candidate if report_name == "candidate" else control
    report["candidate_sha256"] = "F" * 64

    with pytest.raises(ValueError, match=f"{report_name}_report source hash mismatch"):
        compare_reports(candidate, control, expected_contract=contract)


@pytest.mark.parametrize("config_name", ["root_config", "scenario_config"])
def test_expected_contract_rejects_changed_config_file(tmp_path: Path, config_name: str) -> None:
    candidate, control, contract = _contract_fixture(tmp_path)
    Path(contract[config_name]["path"]).write_text("changed\n", encoding="utf-8")

    with pytest.raises(ValueError, match=f"{config_name} hash mismatch"):
        compare_reports(candidate, control, expected_contract=contract)


def test_expected_contract_rejects_same_wrong_effective_scenario_hash(tmp_path: Path) -> None:
    candidate, control, contract = _contract_fixture(tmp_path)
    candidate["effective_scenarios_sha256"] = "F" * 64
    control["effective_scenarios_sha256"] = "F" * 64
    contract["effective_scenarios_sha256"] = "F" * 64

    with pytest.raises(ValueError, match="effective scenarios hash does not match mapping"):
        compare_reports(candidate, control, expected_contract=contract)


def test_expected_contract_requires_report_effective_scenarios_mapping(tmp_path: Path) -> None:
    candidate, control, contract = _contract_fixture(tmp_path)
    del candidate["effective_scenarios"]
    del control["effective_scenarios"]

    with pytest.raises(TypeError, match="effective_scenarios must be an object"):
        compare_reports(candidate, control, expected_contract=contract)


def test_expected_contract_rejects_same_wrong_valid_cell_hash(tmp_path: Path) -> None:
    candidate, control, contract = _contract_fixture(tmp_path)
    candidate["games"][0]["effective_configuration_sha256"] = "F" * 64
    control["games"][0]["effective_configuration_sha256"] = "F" * 64

    with pytest.raises(ValueError, match="effective configuration hash does not match mapping"):
        compare_reports(candidate, control, expected_contract=contract)


def test_expected_contract_requires_cell_effective_configuration_mapping(tmp_path: Path) -> None:
    candidate, control, contract = _contract_fixture(tmp_path)
    del candidate["games"][0]["effective_configuration"]
    del control["games"][0]["effective_configuration"]

    with pytest.raises(TypeError, match="effective_configuration must be an object"):
        compare_reports(candidate, control, expected_contract=contract)


def test_expected_contract_rejects_self_consistent_mutated_cell_mapping(tmp_path: Path) -> None:
    candidate, control, contract = _contract_fixture(tmp_path)
    for report in (candidate, control):
        configuration = report["games"][0]["effective_configuration"]
        configuration["startingMoney"] = 999
        report["games"][0]["effective_configuration_sha256"] = _json_sha256(configuration)

    with pytest.raises(ValueError, match="requested seed injected"):
        compare_reports(candidate, control, expected_contract=contract)


def test_expected_contract_rejects_same_wrong_environment_hash(tmp_path: Path) -> None:
    candidate, control, contract = _contract_fixture(tmp_path)
    candidate["games"][0]["environment_configuration_sha256"] = "F" * 64
    control["games"][0]["environment_configuration_sha256"] = "F" * 64

    with pytest.raises(ValueError, match="environment configuration hash does not match mapping"):
        compare_reports(candidate, control, expected_contract=contract)


def test_expected_contract_requires_environment_mapping_and_hash_for_every_cell(
    tmp_path: Path,
) -> None:
    candidate, control, contract = _contract_fixture(tmp_path)
    for report in (candidate, control):
        del report["games"][0]["environment_configuration"]
        del report["games"][0]["environment_configuration_sha256"]

    with pytest.raises(ValueError, match="must provide environment_configuration and its hash"):
        compare_reports(candidate, control, expected_contract=contract)


def test_expected_contract_rejects_different_realized_environment_mappings(
    tmp_path: Path,
) -> None:
    candidate, control, contract = _contract_fixture(tmp_path)
    candidate_environment = candidate["games"][0]["environment_configuration"]
    candidate_environment["runtimeOnly"] = 1
    candidate["games"][0]["environment_configuration_sha256"] = _json_sha256(candidate_environment)

    with pytest.raises(ValueError, match="environment configuration mismatch"):
        compare_reports(candidate, control, expected_contract=contract)


def test_tracked_fa_ab_reports_are_gate_eligible_under_exact_contract() -> None:
    candidate_report = Path("experiments/evaluations/fa_ab_dev/A1.json")
    control_report = Path("experiments/evaluations/fa_ab_dev/A0.json")
    root_config = Path("configs/fa_ab_development.json")
    scenario_config = Path("configs/fa_ab_scenarios.json")
    candidate_source = Path("experiments/source_snapshots/fa01_market_mpc/A1.py")
    control_source = Path("experiments/source_snapshots/fa01_market_mpc/A0.py")
    opponent_artifacts = {
        "artifacts/candidates/final_day_labor/main.py": Path(
            "artifacts/candidates/final_day_labor/main.py"
        ),
        "hamburger_current": Path("artifacts/opponents/public_kaggle/hamburger_current.py"),
        "scenario_aware": Path("artifacts/opponents/public_kaggle/scenario_aware.py"),
        "niits_pro_tier": Path(
            "references/niits-kaggriculture/src/kaggriculture/agents/"
            "kaggle_builtin/pro_tier_agent.py"
        ),
    }

    preregistered = json.loads(root_config.read_text(encoding="utf-8"))["candidate_A"]
    seed_spec = preregistered["seeds"]
    cell_keys = [
        [scenario, opponent, seed, seat]
        for scenario in preregistered["scenarios"]
        for opponent in preregistered["opponents"]
        for seed in range(seed_spec["start"], seed_spec["end_inclusive"] + 1)
        for seat in (0, 1)
    ]
    contract = {
        "candidate_source_sha256": _sha256(candidate_source),
        "control_source_sha256": _sha256(control_source),
        "root_config": {"path": str(root_config), "sha256": _sha256(root_config)},
        "scenario_config": {
            "path": str(scenario_config),
            "sha256": _sha256(scenario_config),
        },
        "effective_scenarios_sha256": _json_sha256({"default": {"episodeSteps": 720}}),
        "opponent_source_sha256": {
            name: _sha256(path) for name, path in opponent_artifacts.items()
        },
        "cell_keys": cell_keys,
        "cell_count": len(cell_keys),
    }

    result = compare_report_files(
        candidate_report,
        control_report,
        bootstrap_draws=100,
        expected_contract=contract,
    )

    require_gate_eligible(result)
    assert result["gate_eligible"] is True
    assert result["raw_cells"] == 128
    assert result["contract"]["expected_cell_count"] == 128


def test_expected_contract_rejects_declared_cardinality_inconsistent_with_keys(
    tmp_path: Path,
) -> None:
    candidate, control, contract = _contract_fixture(tmp_path)
    contract["cell_count"] += 1

    with pytest.raises(ValueError, match="expected contract cardinality mismatch"):
        compare_reports(candidate, control, expected_contract=contract)


def test_expected_contract_rejects_same_wrong_resolved_environment_seed(
    tmp_path: Path,
) -> None:
    candidate, control, contract = _contract_fixture(tmp_path)
    candidate["games"][0]["resolved_environment_seed"] = 999
    control["games"][0]["resolved_environment_seed"] = 999

    with pytest.raises(ValueError, match="resolved environment seed mismatch"):
        compare_reports(candidate, control, expected_contract=contract)


def test_expected_contract_rejects_same_wrong_opponent_sources(tmp_path: Path) -> None:
    candidate, control, contract = _contract_fixture(tmp_path)
    candidate["opponent_sha256_at_start"]["alpha"] = "E" * 64
    control["opponent_sha256_at_start"]["alpha"] = "E" * 64

    with pytest.raises(ValueError, match="opponent source hash mismatch"):
        compare_reports(candidate, control, expected_contract=contract)


@pytest.mark.parametrize("location", ["contract", "report"])
def test_expected_contract_rejects_malformed_candidate_hash(tmp_path: Path, location: str) -> None:
    candidate, control, contract = _contract_fixture(tmp_path)
    if location == "contract":
        contract["candidate_source_sha256"] = "G" * 64
    else:
        candidate["candidate_sha256"] = "C" * 63

    with pytest.raises(ValueError, match="exactly 64 hexadecimal"):
        compare_reports(candidate, control, expected_contract=contract)


@pytest.mark.parametrize("location", ["contract", "report"])
def test_expected_contract_rejects_malformed_effective_scenario_hash(
    tmp_path: Path, location: str
) -> None:
    candidate, control, contract = _contract_fixture(tmp_path)
    if location == "contract":
        contract["effective_scenarios_sha256"] = "E" * 65
    else:
        candidate["effective_scenarios_sha256"] = "REPORT-CONFIG"
        control["effective_scenarios_sha256"] = "REPORT-CONFIG"

    with pytest.raises(ValueError, match="exactly 64 hexadecimal"):
        compare_reports(candidate, control, expected_contract=contract)


@pytest.mark.parametrize("location", ["contract", "report"])
def test_expected_contract_rejects_malformed_opponent_hash(tmp_path: Path, location: str) -> None:
    candidate, control, contract = _contract_fixture(tmp_path)
    if location == "contract":
        contract["opponent_source_sha256"]["alpha"] = "Z" * 64
    else:
        candidate["opponent_sha256_at_start"]["alpha"] = "A" * 63

    with pytest.raises(ValueError, match="exactly 64 hexadecimal"):
        compare_reports(candidate, control, expected_contract=contract)
