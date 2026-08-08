from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from kaggriculture_lab.evaluation import fa05_wool_gate as gate
from kaggriculture_lab.evaluation import top_trace_gate as core

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY = ROOT / gate.BOUNDARY_RELATIVE


def _zero_metrics() -> dict[str, int]:
    return {name: 0 for name in gate.EXPECTED_METRIC_KEYS}


def _git_blob(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def test_historical_closed_design_is_hash_bound_without_executing_seeds() -> None:
    boundary = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    tracked_entries = [
        boundary["scenario_config"],
        boundary["candidate"],
        boundary["control"],
        *boundary["opponents"],
        boundary["execution_freeze"]["third_party_license"],
        boundary["execution_freeze"]["third_party_attribution"],
    ]
    for name in (
        "generator",
        "runner",
        "paired_analyzer",
        "runtime_generator",
        "runtime_benchmark",
        "gate_evaluator",
    ):
        tracked_entries.append(
            {
                "path": boundary["tooling"][name],
                "sha256": boundary["tooling"][f"{name}_sha256"],
            }
        )
    for entry in tracked_entries:
        payload = _git_blob(boundary["implementation_commit"], entry["path"])
        assert hashlib.sha256(payload).hexdigest().upper() == entry["sha256"]
        if "bytes" in entry:
            assert len(payload) == entry["bytes"]
    assert [entry["identity"] for entry in boundary["opponents"]] == [
        "C135_chocolat", "R140_radiant", "R145_radiant",
        "R150_radiant", "R155_radiant", "formal_final_day_labor",
    ]
    with pytest.raises(ValueError, match="hash mismatch"):
        gate.validate_closed_design(ROOT, BOUNDARY)


def test_closed_boundary_fails_before_any_seed_runner_can_start() -> None:
    with pytest.raises(ValueError, match="seed pools remain CLOSED"):
        gate.run_development_lane(ROOT, BOUNDARY, "candidate")


def test_wrong_candidate_hash_is_rejected() -> None:
    with pytest.raises(ValueError, match="hash mismatch"):
        core._checked_file_entry(
            ROOT,
            {"path": gate.CANDIDATE_ENTRY["path"], "sha256": "0" * 64},
            "candidate",
        )


def test_wrong_cell_partition_is_rejected() -> None:
    cells = {
        identity: [("default", identity, seed, seat) for seed in range(16) for seat in (0, 1)]
        for identity in gate.WEAK_IDENTITIES | gate.PROTECTED_IDENTITIES | {gate.R145_IDENTITY}
    }
    cells[gate.R145_IDENTITY].pop()
    with pytest.raises(ValueError, match="exactly 32 cells"):
        gate._validate_cell_partition(cells)


def test_raw_counter_conservation_and_bool_are_rejected() -> None:
    metrics = _zero_metrics()
    metrics["create_requested_units"] = 4
    metrics["create_observed_units"] = 4
    with pytest.raises(ValueError, match="reserve conservation"):
        gate._validate_metric_mapping(metrics, "cell")
    metrics = _zero_metrics()
    metrics["fallback_count"] = True
    with pytest.raises(ValueError, match="not bool"):
        gate._validate_metric_mapping(metrics, "cell")


def test_blocked_release_is_an_exact_zero_safety_gate() -> None:
    assert gate.EXPECTED_GATES["safety"]["blocked_release_units_eq"] == 0
