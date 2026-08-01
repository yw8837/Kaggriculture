from __future__ import annotations

import hashlib
import inspect
import json
from copy import deepcopy
from pathlib import Path

import pytest

from kaggriculture_lab.evaluation import fa05_trace_gate as gate

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY = ROOT / "configs" / "fa05_r145_trace_boundary.json"
REGISTRY = ROOT / "configs" / "fa_ab_seed_registry.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_fa05_candidate_is_deterministic_attributed_and_compiles() -> None:
    boundary = _load(BOUNDARY)
    candidate = boundary["candidate"]
    source = ROOT / candidate["path"]
    assert _sha256(source) == candidate["sha256"]
    assert source.stat().st_size == candidate["bytes"]
    text = source.read_text(encoding="utf-8")
    assert "PRVSIYAN" in text
    assert "Apache-2.0" in text
    assert "Source episode: 89268002" in text
    assert "Source player: 1" in text
    compile(text, str(source), "exec")


def test_fa05_pools_are_exact_disjoint_and_closed() -> None:
    boundary = _load(BOUNDARY)
    registry = _load(REGISTRY)["next_boundary_reservations"]
    expected = {
        "development": ("Fa05_R145_trace_guard_development", 43000, 43015, 16),
        "confirmation": ("Fa05_R145_trace_guard_confirmation", 44000, 44063, 64),
        "robustness": ("Fa05_R145_trace_guard_robustness", 45000, 45031, 32),
    }
    all_values: set[int] = set()
    for lane, (key, start, end, count) in expected.items():
        pool = boundary["pools"][lane]
        registered = registry[key]
        assert pool == {
            "registry_key": key,
            "start": start,
            "end_inclusive": end,
            "count": count,
            "status": "CLOSED",
        }
        assert registered["status"] == "CLOSED"
        assert registered["opened"] is False
        assert registered["consumed"] is False
        assert registered["evaluated_games"] == 0
        values = set(range(start, end + 1))
        assert not (values & all_values)
        all_values |= values


def test_fa05_exact_opponents_and_claim_boundary() -> None:
    boundary = _load(BOUNDARY)
    identities = {entry["identity"] for entry in boundary["opponents"]}
    assert identities == {
        "C135_chocolat",
        "R140_radiant",
        "R150_radiant",
        "R155_radiant",
        "formal_final_day_labor",
        "Fa04_G1_sell_guard",
    }
    assert "R145_radiant" not in identities
    assert "complementary" in boundary["claim_limit"].lower()
    assert "cannot guarantee" in boundary["claim_limit"].lower()
    gate._validate_opponent_contract(boundary["opponents"], boundary["control"])
    swapped = deepcopy(boundary["opponents"])
    swapped[0]["identity"], swapped[-1]["identity"] = (
        swapped[-1]["identity"],
        swapped[0]["identity"],
    )
    with pytest.raises(ValueError, match="identity/path/hash"):
        gate._validate_opponent_contract(swapped, boundary["control"])


def test_fa05_gate_and_threshold_hashes_are_bound() -> None:
    boundary = _load(BOUNDARY)
    gate_path = ROOT / boundary["tooling"]["gate_evaluator"]
    assert _sha256(gate_path) == boundary["tooling"]["gate_evaluator_sha256"]
    assert _sha256(gate_path) == boundary["tooling"]["runtime_generator_sha256"]
    raw = json.dumps(
        boundary["development_gates"],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    assert hashlib.sha256(raw).hexdigest().upper() == boundary["execution_freeze"][
        "development_gates_sha256"
    ]
    source = inspect.getsource(gate.analyze)
    assert "paired.compare_reports" in source
    assert "paired.require_gate_eligible" in source


def test_fa05_runtime_contract_is_player_one_and_exact_length() -> None:
    boundary = _load(BOUNDARY)
    runtime = boundary["execution_freeze"]["runtime_replay"]
    replay = ROOT / runtime["path"]
    assert runtime["player"] == 1
    assert runtime["observations"] == 720
    assert runtime["recorded_actions"] == 719
    assert _sha256(replay) == runtime["sha256"]
    assert replay.stat().st_size == runtime["bytes"]


def test_fa05_every_frozen_input_hash_matches_actual_bytes() -> None:
    boundary = _load(BOUNDARY)
    entries = [
        boundary["scenario_config"],
        boundary["candidate"],
        boundary["control"],
        *boundary["opponents"],
        boundary["execution_freeze"]["third_party_license"],
        boundary["execution_freeze"]["third_party_attribution"],
        boundary["execution_freeze"]["runtime_replay"],
    ]
    tooling = boundary["tooling"]
    for name in (
        "generator",
        "runner",
        "paired_analyzer",
        "runtime_generator",
        "runtime_benchmark",
        "gate_evaluator",
    ):
        entries.append(
            {"path": tooling[name], "sha256": tooling[f"{name}_sha256"]}
        )
    for entry in entries:
        path = ROOT / entry["path"]
        assert _sha256(path) == entry["sha256"]
        if "bytes" in entry:
            assert path.stat().st_size == entry["bytes"]
    assert _sha256(REGISTRY) == boundary["seed_registry_sha256"]


def test_fa05_lifecycle_rejects_non_utc_open_time() -> None:
    boundary = _load(BOUNDARY)
    registry = _load(REGISTRY)
    boundary["status"] = "DEVELOPMENT_OPEN_AUTHORIZED"
    boundary["pools"]["development"]["status"] = "OPEN"
    boundary["development_opened_at_utc"] = "2026-08-02T06:00:00"
    boundary["opening_authority"] = gate.OPENING_AUTHORITY
    registered = registry["next_boundary_reservations"][gate.DEVELOPMENT_KEY]
    registered["status"] = "OPEN"
    registered["opened"] = True
    registered["opened_at_utc"] = boundary["development_opened_at_utc"]
    with pytest.raises(ValueError, match="must be UTC"):
        gate._validate_lifecycle(boundary, registry)


def test_fa05_runtime_rejects_out_of_order_percentiles() -> None:
    plan = {
        "execution_head": "A" * 40,
        "candidate": {"path": "candidate.py", "sha256": "B" * 64},
        "runtime_replay": {"path": "replay.json", "sha256": "C" * 64},
    }
    receipt = {
        "command": ["python", "-m", "gate"],
        "generator": {"path": "gate.py", "sha256": "D" * 64},
        "tracked_provenance": {"implementation_commit": "A" * 40},
    }
    runtime = {
        "schema_version": 2,
        "created_at_utc": "2026-08-02T00:01:00+00:00",
        "python": "test",
        "platform": "test",
        "calls": 720,
        "invalid_outputs": 0,
        "p50_ms": 3.0,
        "p95_ms": 5.0,
        "p99_ms": 4.0,
        "max_ms": 6.0,
        "git_head": plan["execution_head"],
        "tracked_tree_clean": True,
        "source": plan["candidate"]["path"],
        "source_sha256": plan["candidate"]["sha256"],
        "replay": plan["runtime_replay"]["path"],
        "replay_sha256": plan["runtime_replay"]["sha256"],
        "player": 1,
        "observations": 720,
        "recorded_actions": 719,
        "command": deepcopy(receipt["command"]),
        "generator": deepcopy(receipt["generator"]),
        "tracked_provenance": deepcopy(receipt["tracked_provenance"]),
        "generation_receipt": {"path": "runtime.started.json", "sha256": "E" * 64},
    }
    with pytest.raises(ValueError, match="percentiles are not ordered"):
        gate._validate_runtime_report(runtime, receipt, plan)

    runtime["p99_ms"] = 5.5
    runtime["p50_ms"] = float("nan")
    with pytest.raises(ValueError, match="finite nonnegative"):
        gate._validate_runtime_report(runtime, receipt, plan)


def test_fa05_rejects_nonfinite_derived_money_delta() -> None:
    with pytest.raises(ValueError, match="must be a finite number"):
        gate._finite_difference(1.7e308, -1.7e308, "derived money")
