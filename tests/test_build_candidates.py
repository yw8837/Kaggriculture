from __future__ import annotations

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
        "staged_herd_final",
    } <= names

    staged = (tmp_path / "staged_herd" / "main.py").read_text(encoding="utf-8")
    final_day = (tmp_path / "final_day_labor" / "main.py").read_text(encoding="utf-8")
    combined = (tmp_path / "staged_herd_final" / "main.py").read_text(encoding="utf-8")
    final_day_12 = (tmp_path / "final_day_labor_12" / "main.py").read_text(encoding="utf-8")
    final_day_13 = (tmp_path / "final_day_labor_13" / "main.py").read_text(encoding="utf-8")
    assert 'else {"COW": 4, "SHEEP": 2}' in staged
    assert "return (hire_orders + orders)[:10]" not in staged
    assert 'else {"COW": 4, "SHEEP": 2}' not in final_day
    assert "return (hire_orders + orders)[:10]" in final_day
    assert 'else {"COW": 4, "SHEEP": 2}' in combined
    assert "return (hire_orders + orders)[:10]" in combined
    assert 'missing = max(0, 12 - len(farm.get("hands", []) or []))' in final_day_12
    assert 'missing = max(0, 13 - len(farm.get("hands", []) or []))' in final_day_13
