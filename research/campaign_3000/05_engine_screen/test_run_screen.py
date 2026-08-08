from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]


def _load(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_cell_registry_is_exact_and_uses_only_consumed_screen_seeds() -> None:
    registry = _load("cell_registry.json")
    cells = registry["cells"]

    assert registry["seed_status"] == "CONSUMED_SCREEN"
    assert registry["promotion_eligible"] is False
    assert len(cells) == 260
    assert len({cell["exact_cell_key"] for cell in cells}) == 260
    assert {cell["seed_status"] for cell in cells} == {"CONSUMED_SCREEN"}
    assert {cell["seed"] for cell in cells} == set(range(23000, 23008))
    assert {cell["candidate_seat"] for cell in cells} == {0, 1}


def test_frozen_agent_bytes_still_match_screen_config() -> None:
    config = _load("screen_config.json")
    records = [config["fa04_g1"], *config["public_agents"]]

    for record in records:
        path = PROJECT_ROOT / record["path"]
        assert path.stat().st_size == record["bytes"]
        assert _sha256(path) == record["sha256"]


def test_completed_screen_has_all_cells_and_integrity_receipts() -> None:
    summary = _load("summary.json")
    comparison = _load("engine_comparison.json")
    raw = _load("raw_games.json")

    assert summary["verdict"] == "SCREEN_EXECUTED_NON_PROMOTION"
    assert summary["executed_cells"] == {
        "engine_1.32.6": 240,
        "engine_1.32.6_fa04_g1": 80,
        "engine_1.32.6_public_round_robin": 160,
        "engine_1.32.2_comparison": 20,
        "engine_specific_total": 260,
    }
    assert len(raw["records"]) == 260
    assert comparison["summary"]["paired_logical_cells"] == 20

    for engine_version in ("1.32.6", "1.32.2"):
        receipt = _load(f"receipts/engine_{engine_version}.completed.json")
        assert receipt["sources_unchanged_during_phase"] is True
        assert receipt["environment_unchanged_during_phase"] is True
        assert receipt["config_unchanged_during_phase"] is True
        assert receipt["cell_registry_unchanged_during_phase"] is True
