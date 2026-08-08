from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]


def _load(path: str) -> dict:
    return json.loads((HERE / path).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_exact_candidate_and_consumed_cell_registry() -> None:
    config = _load("screen_config.json")
    candidate = config["candidate"]
    candidate_path = PROJECT_ROOT / candidate["path"]
    cells = _load("cell_registry.json")["cells"]

    assert candidate_path.stat().st_size == 26545
    assert _sha256(candidate_path) == candidate["sha256"]
    assert len(cells) == 64
    assert len({cell["exact_cell_key"] for cell in cells}) == 64
    assert {cell["seed"] for cell in cells} == set(range(23000, 23008))
    assert {cell["candidate_seat"] for cell in cells} == {0, 1}
    assert {cell["seed_status"] for cell in cells} == {"CONSUMED_SCREEN"}


def test_addendum_outputs_and_integrity() -> None:
    summary = _load("summary.json")
    raw = _load("raw_games.json")
    receipt = _load("receipts/engine_1.32.6.completed.json")

    assert summary["verdict"] == "ADDENDUM_SCREEN_EXECUTED_NON_PROMOTION"
    assert summary["executed_cells"] == 64
    assert len(raw["records"]) == 64
    assert receipt["executed_cells"] == 64
    assert receipt["sources_unchanged_during_phase"] is True
    assert receipt["environment_unchanged_during_phase"] is True
    assert receipt["cell_registry_unchanged_during_phase"] is True
