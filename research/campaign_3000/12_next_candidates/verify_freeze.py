"""Read-only verifier for the CLOSED Kag_03/Kag_04 S/E freeze."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
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


def _load_module(relative: str, name: str) -> ModuleType:
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        encoding="utf-8",
        timeout=30,
    )
    return completed.stdout.strip()


def _verify_manifest_inputs(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    inputs = manifest.get("inputs")
    if not isinstance(inputs, list) or manifest.get("input_count") != len(inputs):
        raise ValueError("freeze manifest input count mismatch")
    paths = [item.get("path") for item in inputs if isinstance(item, dict)]
    if len(paths) != len(inputs) or len(paths) != len(set(paths)):
        raise ValueError("freeze manifest paths are missing or duplicated")
    forbidden = {
        MANIFEST_PATH.relative_to(ROOT).as_posix(),
        BINDING_PATH.relative_to(ROOT).as_posix(),
    }
    if forbidden.intersection(paths):
        raise ValueError("manifest cannot self-pin or pin the S/E binding")
    for item in inputs:
        path = ROOT / item["path"]
        data = path.read_bytes()
        if len(data) != item.get("bytes") or _sha256(data) != item.get("sha256"):
            raise ValueError(f"freeze input drift: {item['path']}")
    return inputs


def _verify_artifact_manifest() -> None:
    artifact = _strict_json(HERE / "kag_04" / "artifact_hashes.json")
    for item in artifact["files"] + artifact["pinned_inputs"]:
        data = (ROOT / item["path"]).read_bytes()
        if len(data) != item.get("bytes") or _sha256(data) != item.get("sha256"):
            raise ValueError(f"Kag_04 artifact manifest drift: {item['path']}")


def _verify_candidate_reconstruction() -> None:
    control = ROOT / "research/campaign_3000/06_candidates/snapshots/tetsu_v16.py"
    control_bytes = control.read_bytes()
    kag03 = _load_module(
        "src/kaggriculture_lab/research/kag03_preempt_horizon.py", "frozen_kag03_builder"
    )
    kag04 = _load_module(
        "src/kaggriculture_lab/research/kag04_seat0_horizon4.py", "frozen_kag04_builder"
    )
    expected03 = kag03.build_source(control_bytes.decode("utf-8")).encode("utf-8")
    expected04 = kag04.build_source(control_bytes).encode("utf-8")
    actual03 = (HERE / "kag_03" / "main.py").read_bytes()
    actual04 = (HERE / "kag_04" / "main.py").read_bytes()
    if expected03 != actual03:
        raise ValueError("Kag_03 builder output does not equal frozen main.py")
    if expected04 != actual04:
        raise ValueError("Kag_04 builder output does not equal frozen main.py")

    receipt03 = _strict_json(HERE / "kag_03" / "freeze_receipt.json")
    if (
        receipt03.get("schema") != "kag03_preempt_horizon_freeze.v1"
        or receipt03.get("candidate", {}).get("sha256") != _sha256(actual03)
        or receipt03.get("candidate", {}).get("bytes") != len(actual03)
        or receipt03.get("compile") != {
            "filename": "<kag03_preempt_horizon_freeze>",
            "ok": True,
        }
    ):
        raise ValueError("Kag_03 materialization receipt mismatch")
    receipt04 = _strict_json(HERE / "kag_04" / "materialized_receipt.json")
    if (
        receipt04.get("output_sha256") != _sha256(actual04)
        or receipt04.get("output_bytes") != len(actual04)
    ):
        raise ValueError("Kag_04 materialization receipt mismatch")


def _verify_current_runtime(plan: dict[str, Any]) -> str:
    """Bind the CLOSED freeze to the engine actually imported by the runner."""
    runner = _load_module(
        "src/kaggriculture_lab/evaluation/runner.py", "frozen_runtime_runner"
    )
    snapshot = runner._runtime_environment_snapshot()
    engine = plan["engine"]
    if (
        snapshot.get("schema_version") != 1
        or snapshot.get("distribution_name") != engine.get("package")
        or snapshot.get("distribution_version") != engine.get("version")
        or snapshot.get("distribution_error") is not None
        or snapshot.get("make_callable_error") is not None
        or snapshot.get("make_callable_contract_matches_expected") is not True
        or snapshot.get("make_callable_contract")
        != engine.get("runtime_make_callable_contract")
    ):
        raise ValueError("actual runner runtime does not match the frozen engine contract")

    root = snapshot.get("distribution_root")
    dependencies = snapshot.get("runtime_dependency_files")
    expected_dependencies = engine.get("runtime_dependency_manifest")
    imported = snapshot.get("imported_module_paths")
    if (
        not isinstance(root, str)
        or not root
        or not isinstance(dependencies, dict)
        or not isinstance(expected_dependencies, dict)
        or set(dependencies) != set(expected_dependencies)
        or not isinstance(imported, dict)
    ):
        raise ValueError("actual runner runtime snapshot has an invalid shape")
    normalized_root = root.replace("\\", "/").rstrip("/") + "/"
    for label, expected in expected_dependencies.items():
        actual = dependencies[label]
        relative = expected["relative_path"]
        actual_path = actual.get("path")
        if (
            actual.get("exists") is not True
            or actual.get("read_error") is not None
            or actual.get("bytes") != expected.get("bytes")
            or actual.get("sha256") != expected.get("sha256")
            or not isinstance(actual_path, str)
            or actual_path.replace("\\", "/")
            != normalized_root + relative
        ):
            raise ValueError(f"actual runner dependency drift: {label}")
        if label != "kaggriculture_json":
            imported_item = imported.get(label)
            if (
                not isinstance(imported_item, dict)
                or imported_item.get("error") is not None
                or imported_item.get("path") != actual_path
            ):
                raise ValueError(f"actual imported module path drift: {label}")
    return _sha256(
        json.dumps(
            snapshot, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    )


def _verify_binding(manifest: dict[str, Any], inputs: list[dict[str, Any]]) -> str:
    binding = _strict_json(BINDING_PATH)
    if binding.get("schema_version") != 2 or binding.get("artifact_kind") != (
        "kag_03_kag_04_execution_freeze_binding"
    ):
        raise ValueError("execution binding identity is invalid")
    manifest_bytes = MANIFEST_PATH.read_bytes()
    pin = binding.get("implementation_manifest")
    if not isinstance(pin, dict):
        raise TypeError("execution binding manifest pin is missing")
    if (
        pin.get("path") != MANIFEST_PATH.relative_to(ROOT).as_posix()
        or pin.get("bytes") != len(manifest_bytes)
        or pin.get("sha256") != _sha256(manifest_bytes)
        or pin.get("input_count") != len(inputs)
    ):
        raise ValueError("execution binding does not match the freeze manifest")
    if binding.get("lifecycle") != {
        "all_six_pools": "CLOSED",
        "opened": False,
        "consumed": False,
        "fresh_games_executed": 0,
    }:
        raise ValueError("execution binding lifecycle is not pristine CLOSED")
    expected_candidates = {
        slot: {
            "sha256": details["sha256"],
            "development_pool": details["development_pool"],
        }
        for slot, details in manifest["candidates"].items()
    }
    if binding.get("candidates") != expected_candidates:
        raise ValueError("execution binding candidate pins do not match the manifest")
    if binding.get("expected_execution_freeze") != {
        "parent": "IMPLEMENTATION_COMMIT",
        "allowed_diff": [BINDING_PATH.relative_to(ROOT).as_posix()],
    }:
        raise ValueError("execution binding S to E contract is invalid")
    if binding.get("auditor_authority") != {
        "status": "PENDING_INDEPENDENT_AUDITOR_EXACT_OPEN",
        "development_seed_execution": "FORBIDDEN",
    }:
        raise ValueError("execution binding auditor authority is not CLOSED")
    if binding.get("external_actions") != {
        "save_run": False,
        "upload": False,
        "competition_submission": False,
        "publication": False,
    }:
        raise ValueError("execution binding external actions are not all disabled")

    status = binding.get("status")
    implementation = binding.get("implementation_commit")
    if status == "PENDING_S_E_BINDING" and implementation == "PENDING_S_COMMIT":
        return "PENDING_S_E_BINDING"
    if status != "CLOSED_EXECUTION_FREEZE" or not isinstance(implementation, str):
        raise ValueError("execution binding status is invalid")
    if re.fullmatch(r"[0-9a-f]{40}", implementation) is None:
        raise ValueError("implementation commit is not exact lowercase SHA-1")
    head = _git("rev-parse", "HEAD")
    parents = _git("rev-list", "--parents", "-n", "1", head).split()
    if len(parents) != 2 or parents[1] != implementation:
        raise ValueError("execution HEAD must have implementation commit as its sole parent")
    changed = _git("diff", "--name-only", implementation, head).splitlines()
    if changed != [BINDING_PATH.relative_to(ROOT).as_posix()]:
        raise ValueError("S to E diff must contain only execution_binding.json")
    if _git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("final execution freeze worktree is not clean")
    return "VALID_CLEAN_S_E_FREEZE"


def verify() -> dict[str, Any]:
    manifest = _strict_json(MANIFEST_PATH)
    inputs = _verify_manifest_inputs(manifest)
    _verify_artifact_manifest()
    _verify_candidate_reconstruction()

    for relative in (
        "research/campaign_3000/12_next_candidates/development_gate.py",
        "research/campaign_3000/12_next_candidates/build_freeze_manifest.py",
        "research/campaign_3000/12_next_candidates/verify_freeze.py",
        "src/kaggriculture_lab/evaluation/runner.py",
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
    if (HERE / "results").exists() and any((HERE / "results").rglob("*")):
        raise ValueError("unexpected fresh development result artifact exists")

    seed_module = _load_module(
        "research/campaign_3000/12_next_candidates/seed_reservation.py",
        "frozen_seed_reservation",
    )
    seed_result = seed_module.validate()
    scan_pin = _strict_json(HERE / "seed_collision_scan.json")["reservation_state"][
        "current_adapter_revalidation"
    ]
    for key in (
        "observed_seed_count",
        "observed_seed_values_sha256",
        "seed_evidence_files_sha256",
        "scanned_text_files",
        "seed_bearing_files",
        "enumerated_rg_files",
    ):
        if seed_result["observed"].get(key) != scan_pin.get(key):
            raise ValueError(f"seed collision receipt drift: {key}")

    gate = _load_module(
        "research/campaign_3000/12_next_candidates/development_gate.py", "frozen_gate"
    )
    plan_result = gate.validate_plan()
    plan = _strict_json(HERE / "evaluation_plan.json")
    runtime_environment_sha256 = _verify_current_runtime(plan)
    binding_status = _verify_binding(manifest, inputs)
    return {
        "status": binding_status,
        "manifest_sha256": _sha256(MANIFEST_PATH.read_bytes()),
        "input_count": len(inputs),
        "plan": plan_result,
        "runtime_environment_sha256": runtime_environment_sha256,
        "fresh_games_executed": 0,
        "external_actions": 0,
    }


def main() -> int:
    print(json.dumps(verify(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
