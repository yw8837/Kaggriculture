from __future__ import annotations

import ast
import runpy
from pathlib import Path

from kaggriculture_lab.candidates.build import run

BASE = Path("artifacts/opponents/public_kaggle/hamburger_base.py")


def test_second_generation_candidates_encode_isolated_hypotheses(tmp_path: Path) -> None:
    manifest = run(BASE, tmp_path)
    names = {record["name"] for record in manifest["candidates"]}
    assert {
        "staged_herd",
        "final_day_labor",
        "final_day_labor_12",
        "final_day_labor_13",
        "overflow_drop",
        "carrier_drop",
        "staged_herd_final",
        "public_expansion_baseline",
        "horizon_crop_rotation",
        "horizon_crop_rotation_cap1",
        "horizon_crop_rotation_cap2",
        "horizon_crop_rotation_cap4",
        "horizon_crop_rotation_cap8",
        "terminal_carry_24",
        "terminal_carry_36",
        "terminal_carry_48",
    } <= names

    staged = (tmp_path / "staged_herd" / "main.py").read_text(encoding="utf-8")
    final_day = (tmp_path / "final_day_labor" / "main.py").read_text(encoding="utf-8")
    combined = (tmp_path / "staged_herd_final" / "main.py").read_text(encoding="utf-8")
    final_day_12 = (tmp_path / "final_day_labor_12" / "main.py").read_text(encoding="utf-8")
    final_day_13 = (tmp_path / "final_day_labor_13" / "main.py").read_text(encoding="utf-8")
    overflow = (tmp_path / "overflow_drop" / "main.py").read_text(encoding="utf-8")
    carrier = (tmp_path / "carrier_drop" / "main.py").read_text(encoding="utf-8")
    assert 'else {"COW": 4, "SHEEP": 2}' in staged
    assert "return (hire_orders + orders)[:10]" not in staged
    assert 'else {"COW": 4, "SHEEP": 2}' not in final_day
    assert "return (hire_orders + orders)[:10]" in final_day
    assert 'else {"COW": 4, "SHEEP": 2}' in combined
    assert "return (hire_orders + orders)[:10]" in combined
    assert 'missing = max(0, 12 - len(farm.get("hands", []) or []))' in final_day_12
    assert 'missing = max(0, 13 - len(farm.get("hands", []) or []))' in final_day_13
    assert "shed_load + carried_load >= 90" in overflow
    assert "shed_load + carried_load >= 90" not in carrier
    assert ">= 6" in carrier

    labor_rush = (tmp_path / "labor_rush" / "main.py").read_text(encoding="utf-8")
    public = (tmp_path / "public_expansion_baseline" / "main.py").read_text(
        encoding="utf-8"
    )
    assert "This is a reproducible public baseline" in public
    assert "Late-horizon adaptation and inventory routing are intentionally simple" in public
    assert ast.dump(ast.parse(public), include_attributes=False) == ast.dump(
        ast.parse(labor_rush), include_attributes=False
    )

    horizon_path = tmp_path / "horizon_crop_rotation" / "main.py"
    namespace = runpy.run_path(str(horizon_path))
    plan = {(0, 0): "STRAWBERRY", (1, 0): "CARROT"}
    empty_tiles = [[None, None], [None, None]]
    farms = [{"tiles": empty_tiles}]
    day17 = {
        "day": 17, "player": 0, "farms": farms,
        "market": {"prices": {"WHEAT": 25, "CARROT": 35}},
    }
    day25 = {
        "day": 25, "player": 0, "farms": farms,
        "market": {"prices": {"WHEAT": 100, "CARROT": 1}},
    }
    day26 = {"day": 26, "market": {"prices": {"WHEAT": 100, "CARROT": 100}}}
    assert namespace["_apply_horizon_crop_rotation"](day17, plan) == {
        (0, 0): "WHEAT",
        (1, 0): "CARROT",
    }
    assert namespace["_apply_horizon_crop_rotation"](day25, plan) == {
        (0, 0): "CARROT",
        (1, 0): "CARROT",
    }
    assert namespace["_apply_horizon_crop_rotation"](day26, plan) is plan

    terminal24 = (tmp_path / "terminal_carry_24" / "main.py").read_text(
        encoding="utf-8"
    )
    terminal36 = (tmp_path / "terminal_carry_36" / "main.py").read_text(
        encoding="utf-8"
    )
    terminal48 = (tmp_path / "terminal_carry_48" / "main.py").read_text(
        encoding="utf-8"
    )
    assert "endgame_turn >= 696" in terminal24
    assert "endgame_turn >= 684" in terminal36
    assert "endgame_turn >= 672" in terminal48
    assert "Carried inventory has zero terminal value" in terminal24
