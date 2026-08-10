"""Validate Kag_03/Kag_04 pools without counting their own reservation record.

The historic Kag_01/Kag_02 scanner correctly excludes its own derived files, but
its exclusions are deliberately frozen to that campaign.  This adapter keeps the
same extraction logic while adding only three exact Kag_03/Kag_04 derived paths.
It must never exclude the whole `12_next_candidates` directory: future evidence
there remains input evidence and must be scanned.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CATALOG_PATH = HERE / "candidate_catalog.json"
DERIVED_EXCLUSIONS = {
    "research/campaign_3000/12_next_candidates/candidate_catalog.json",
    "research/campaign_3000/12_next_candidates/seed_collision_scan.json",
    "research/campaign_3000/12_next_candidates/evaluation_plan.json",
}


def _load_hardened_scanner() -> ModuleType:
    path = ROOT / "research" / "campaign_3000" / "06_candidates" / "orchestrator.py"
    spec = importlib.util.spec_from_file_location("campaign_3000_seed_scan", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the hardened Kag_01/Kag_02 seed scanner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.SCAN_EXCLUDES = set(module.SCAN_EXCLUDES) | DERIVED_EXCLUSIONS
    return module


def _reservations(catalog: dict[str, Any]) -> dict[str, range]:
    result: dict[str, range] = {}
    for slot in catalog["slots"]:
        for phase, pool in slot["seed_pools"].items():
            name = f"{slot['slot']}_{phase}"
            result[name] = range(pool["start"], pool["end_inclusive"] + 1)
    return result


def scan() -> dict[str, Any]:
    """Return the current observed-input scan and per-pool collision lists."""
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    scanner = _load_hardened_scanner()
    observed_scan = scanner.scan_observed_seeds(ROOT)
    observed = set(observed_scan["observed_seed_values"])
    reservations = _reservations(catalog)
    collisions = {name: sorted(observed.intersection(values)) for name, values in reservations.items()}
    return {
        "scan_adapter": "hardened_06_candidates_scanner_with_exact_12_reservation_exclusions",
        "derived_exclusions": sorted(DERIVED_EXCLUSIONS),
        "observed": observed_scan,
        "collisions": collisions,
        "all_pools_collision_free": not any(collisions.values()),
        "fresh_games_executed": 0,
    }


def validate() -> dict[str, Any]:
    """Raise when any planned seed was already observed outside its own record."""
    result = scan()
    if not result["all_pools_collision_free"]:
        raise ValueError(f"Kag_03/Kag_04 seed collision: {result['collisions']}")
    return result


def main() -> None:
    print(json.dumps(validate(), sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
