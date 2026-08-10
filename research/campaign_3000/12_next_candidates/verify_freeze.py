"""Read-only verifier for the CLOSED Kag_03/Kag_04 implementation freeze."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MANIFEST_PATH = HERE / "freeze_manifest.json"
BINDING_PATH = HERE / "execution_binding.json"


def _strict_json(path: Path) -> dict[str, Any]:
    def object_pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in items:
            if key in value:
                raise ValueError(f"duplicate JSON key {key!r}: {path}")
            value[key] = item
        return value

    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=object_pairs,
        parse_constant=lambda constant: (_ for _ in ()).throw(ValueError(constant)),
    )
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    return value


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _load_gate() -> ModuleType:
    path = HERE / "development_gate.py"
    spec = importlib.util.spec_from_file_location("kag03_kag04_frozen_gate", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the frozen development gate")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify() -> dict[str, Any]:
    manifest = _strict_json(MANIFEST_PATH)
    binding = _strict_json(BINDING_PATH)
    inputs = manifest.get("inputs")
    if not isinstance(inputs, list) or manifest.get("input_count") != len(inputs):
        raise ValueError("freeze manifest input count mismatch")
    paths = [item.get("path") for item in inputs if isinstance(item, dict)]
    if len(paths) != len(inputs) or len(paths) != len(set(paths)):
        raise ValueError("freeze manifest paths are missing or duplicated")
    for item in inputs:
        path = ROOT / item["path"]
        data = path.read_bytes()
        if len(data) != item.get("bytes") or _sha256(data) != item.get("sha256"):
            raise ValueError(f"freeze input drift: {item['path']}")

    manifest_bytes = MANIFEST_PATH.read_bytes()
    manifest_pin = binding.get("implementation_manifest")
    if not isinstance(manifest_pin, dict):
        raise TypeError("execution binding manifest pin is missing")
    if (
        manifest_pin.get("path") != MANIFEST_PATH.relative_to(ROOT).as_posix()
        or manifest_pin.get("bytes") != len(manifest_bytes)
        or manifest_pin.get("sha256") != _sha256(manifest_bytes)
        or manifest_pin.get("input_count") != len(inputs)
    ):
        raise ValueError("execution binding does not match the freeze manifest")

    artifact_manifest = _strict_json(HERE / "kag_04" / "artifact_hashes.json")
    for item in artifact_manifest["files"] + artifact_manifest["pinned_inputs"]:
        data = (ROOT / item["path"]).read_bytes()
        if _sha256(data) != item["sha256"]:
            raise ValueError(f"Kag_04 artifact manifest drift: {item['path']}")

    for relative in (
        "research/campaign_3000/12_next_candidates/kag_03/main.py",
        "research/campaign_3000/12_next_candidates/kag_04/main.py",
        "research/campaign_3000/12_next_candidates/development_gate.py",
        "src/kaggriculture_lab/candidates/kag03_terminal_market.py",
        "src/kaggriculture_lab/candidates/kag04_sheep_first.py",
    ):
        compile((ROOT / relative).read_text(encoding="utf-8"), relative, "exec")

    catalog = _strict_json(HERE / "candidate_catalog.json")
    for slot in catalog["slots"]:
        for phase, pool in slot["seed_pools"].items():
            if (
                pool.get("status") != "CLOSED"
                or pool.get("opened") is not False
                or pool.get("consumed") is not False
                or pool.get("evaluated_games") != 0
            ):
                raise ValueError(f"seed pool is not pristine CLOSED: {slot['slot']}/{phase}")
    if catalog["reservation_check"].get("fresh_games_executed") != 0:
        raise ValueError("fresh development games were already executed")
    if (HERE / "results").exists() and any((HERE / "results").rglob("*")):
        raise ValueError("unexpected development result artifact exists")

    plan_result = _load_gate().validate_plan()
    return {
        "status": "VALID_CLOSED_S_E_FREEZE_INPUTS",
        "manifest_sha256": _sha256(manifest_bytes),
        "input_count": len(inputs),
        "plan": plan_result,
        "fresh_games_executed": 0,
        "external_actions": 0,
    }


def main() -> int:
    print(json.dumps(verify(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
