from __future__ import annotations

import hashlib
import inspect
from pathlib import Path

from kaggle_environments.envs.kaggriculture import kaggriculture as engine

PINNED_NORMALIZED_SHA256 = "FB9215C5E21A25243E2D13E75B3D70A79CF7D78FFF150A90F1BB5EACF9BA2BCF"


def _normalized_sha256(path: Path) -> str:
    normalized = path.read_text(encoding="utf-8").replace("\r\n", "\n").encode()
    return hashlib.sha256(normalized).hexdigest().upper()


def test_installed_engine_matches_pinned_source_after_line_ending_normalization() -> None:
    installed = Path(inspect.getsourcefile(engine) or "")
    pinned = Path(
        "references/ke1326/kaggle_environments/envs/"
        "kaggriculture/kaggriculture.py"
    )
    assert _normalized_sha256(installed) == PINNED_NORMALIZED_SHA256
    assert _normalized_sha256(pinned) == PINNED_NORMALIZED_SHA256


def test_fed_and_cared_animal_banks_one_bonus_unit() -> None:
    tile = engine._new_animal("COW", 0)
    tile["fed_today"] = True
    tile["cared_today"] = True
    farm = {"tiles": [[tile]]}

    engine._daily_refresh_animals(farm, 0)

    assert tile["pending_care_bonus"] == 1
    assert tile["yield_units"] == 0


def test_care_bonus_is_consumed_on_fed_production_then_rebanked() -> None:
    tile = engine._new_animal("COW", -7)
    tile["pending_care_bonus"] = 1
    tile["fed_today"] = True
    tile["cared_today"] = True
    farm = {"tiles": [[tile]]}

    engine._daily_refresh_animals(farm, 0)

    assert tile["yield_units"] == 2
    assert tile["pending_care_bonus"] == 1


def test_market_price_floor_is_one() -> None:
    assert engine.market_price("MELON", 10**9) == 1


def test_end_of_day_shed_overflow_is_discarded() -> None:
    private = {
        "shed": {"WHEAT": 99},
        "inventories": [{"CARROT": 5}],
    }

    engine._drop_inventories_to_shed(private, 100)

    assert private["shed"] == {"WHEAT": 99, "CARROT": 1}
    assert private["inventories"] == [{}]
