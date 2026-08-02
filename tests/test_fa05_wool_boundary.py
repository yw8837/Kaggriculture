from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_wool_seed_pools_are_exact_closed_and_unused() -> None:
    boundary = json.loads((ROOT / "configs/fa05_wool_glut_boundary.json").read_text())
    registry = json.loads((ROOT / "configs/fa_ab_seed_registry.json").read_text())
    expected = {
        "development": ("Fa05_wool_glut_buffer_development", 46000, 46015, 16),
        "confirmation": ("Fa05_wool_glut_buffer_confirmation", 47000, 47063, 64),
        "robustness": ("Fa05_wool_glut_buffer_robustness", 48000, 48031, 32),
    }
    assert boundary["status"] == "CLOSED_PENDING_INDEPENDENT_AUDIT"
    for lane, (key, start, end, count) in expected.items():
        pool = boundary["pools"][lane]
        saved = registry["next_boundary_reservations"][key]
        assert (pool["start"], pool["end_inclusive"], pool["count"]) == (start, end, count)
        assert pool["status"] == saved["status"] == "CLOSED"
        assert saved["opened"] is saved["consumed"] is False
        assert saved["evaluated_games"] == 0


def test_grid_and_release_policy_are_exact() -> None:
    boundary = json.loads((ROOT / "configs/fa05_wool_glut_boundary.json").read_text())
    design = boundary["development_design"]
    assert design["exact_cells_per_lane"] == 6 * 16 * 2 == 192
    assert "R145_radiant" in design["opponent_identities"]
    assert "Fa04_G1_sell_guard" not in design["opponent_identities"]
    assert boundary["release_policy"].startswith(
        "Development PASS permits only a separate private SaveRun audit request."
    )
