from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import random
import re
import statistics
import subprocess
import sys
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
PLAN_PATH = HERE / "candidate_plan.json"
GATE_PATH = HERE / "gate_config.json"
SEED_SCAN_PATH = HERE / "seed_collision_scan.json"
SELECTION_PATH = HERE / "selection_evidence.json"
MANIFEST_PATH = HERE / "manifest.json"
BINDING_PATH = HERE / "execution_binding.json"
LIFECYCLE_PATH = HERE / "lifecycle.json"
AUDITOR_TASK_ID = "019fb8b8-7758-7860-9304-39eb4f06c65c"
AUTHORITY_RECEIPT_RELATIVE = (
    "dist/campaign_3000/authority/auditor_development_open.json"
)
AUDITOR_OPEN_DELIVERY_RELATIVE = (
    "dist/campaign_3000/authority/auditor_development_open.delivery.json"
)
AUDITOR_O_REVIEW_RELATIVE = (
    "dist/campaign_3000/authority/auditor_authority_o_review.delivery.json"
)
EXPECTED_SEED_RANGES = {
    "Kag_01": {
        "development": (50000, 50015),
        "confirmation": (51000, 51063),
        "robustness": (52000, 52031),
    },
    "Kag_02": {
        "development": (53000, 53015),
        "confirmation": (54000, 54063),
        "robustness": (55000, 55031),
    },
}

TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".py", ".toml", ".txt", ".xml", ".yaml", ".yml"}
SCAN_EXCLUDES = {
    "tests/test_campaign_3000_candidate_freeze.py",
}
SCAN_EXCLUDED_PREFIXES = (
    "research/campaign_3000/06_candidates/",
    "research/campaign_3000/07_release/",
    "research/campaign_3000/08_public_release/",
    "research/campaign_3000/09_audit/",
)
PHASES = ("development", "confirmation", "robustness")


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _json_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def _candidate(plan: Mapping[str, Any], slot: str) -> Mapping[str, Any]:
    matches = [item for item in plan["candidates"] if item["slot"] == slot]
    if len(matches) != 1:
        raise ValueError(f"expected one candidate for {slot}, got {len(matches)}")
    return matches[0]


def _seeds(candidate: Mapping[str, Any], phase: str) -> list[int]:
    pool = candidate["seed_pools"][phase]
    return list(range(pool["start"], pool["end_inclusive"] + 1))


def _scenario_names(plan: Mapping[str, Any], phase: str) -> list[str]:
    return list(plan["scenario_source"][phase])


def expected_grid(plan: Mapping[str, Any], slot: str, phase: str) -> list[dict[str, Any]]:
    candidate = _candidate(plan, slot)
    rows = [
        {
            "slot": slot,
            "candidate": candidate["candidate_alias"],
            "phase": phase,
            "scenario": scenario,
            "opponent": opponent,
            "seed": seed,
            "seat": seat,
            "seed_status": "CLOSED",
        }
        for scenario in _scenario_names(plan, phase)
        for opponent in candidate["opponents"]
        for seed in _seeds(candidate, phase)
        for seat in plan["execution"]["seats"]
    ]
    return rows


def _expand_range(start: int, end: int) -> Iterable[int]:
    if 0 <= start <= end and end - start <= 100_000:
        return range(start, end + 1)
    return ()


def _direct_seed_values(value: Any) -> set[int]:
    found: set[int] = set()
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        found.add(value)
    elif isinstance(value, list):
        for item in value:
            found.update(_direct_seed_values(item))
    elif isinstance(value, str):
        match = re.fullmatch(r"\s*(\d+)\s*-\s*(\d+)\s*", value)
        if match:
            found.update(_expand_range(int(match.group(1)), int(match.group(2))))
    return found


def _json_seed_values(value: Any, active: bool = False) -> set[int]:
    found: set[int] = set()
    if isinstance(value, dict):
        if active:
            start = value.get("start")
            end = value.get("end_inclusive", value.get("end"))
            if isinstance(start, int) and isinstance(end, int):
                found.update(_expand_range(start, end))
        for key, item in value.items():
            lowered = str(key).lower()
            seed_key = "seed" in lowered
            if seed_key:
                found.update(_direct_seed_values(item))
            found.update(_json_seed_values(item, active or seed_key))
    elif isinstance(value, list):
        for item in value:
            found.update(_json_seed_values(item, active))
    return found


def _text_seed_values(text: str) -> set[int]:
    found: set[int] = set()
    for line in text.splitlines():
        if not re.search(r"(?i)\bseed(?:s|ed|ing)?\b", line):
            continue
        for match in re.finditer(r"\b(\d+)\s*-\s*(\d+)\b", line):
            found.update(_expand_range(int(match.group(1)), int(match.group(2))))
        for match in re.finditer(r"range\(\s*(\d+)\s*,\s*(\d+)\s*\)", line):
            start, stop = int(match.group(1)), int(match.group(2))
            found.update(_expand_range(start, stop - 1))
        for match in re.finditer(r"(?<![A-Za-z0-9])\d+(?![A-Za-z0-9])", line):
            found.add(int(match.group()))
    return found


def _compressed_ranges(values: Sequence[int]) -> list[list[int]]:
    ranges: list[list[int]] = []
    for value in values:
        if not ranges or value > ranges[-1][1] + 1:
            ranges.append([value, value])
        else:
            ranges[-1][1] = value
    return ranges


def scan_observed_seeds(project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    root = project_root.resolve()
    completed = subprocess.run(
        ["rg", "--files"],
        cwd=root,
        check=True,
        capture_output=True,
        encoding="utf-8",
    )
    paths = sorted(Path(line) for line in completed.stdout.splitlines() if line)
    observed: set[int] = set()
    evidence_files: dict[str, str] = {}
    scanned = 0
    for relative_path in paths:
        portable = relative_path.as_posix()
        if (
            relative_path.suffix.lower() not in TEXT_SUFFIXES
            or portable in SCAN_EXCLUDES
            or portable.startswith(SCAN_EXCLUDED_PREFIXES)
        ):
            continue
        path = root / relative_path
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        scanned += 1
        values: set[int] = set()
        if relative_path.suffix.lower() == ".json":
            try:
                values = _json_seed_values(
                    json.loads(text), active="seed" in relative_path.name.lower()
                )
            except json.JSONDecodeError:
                values = _text_seed_values(text)
        elif relative_path.suffix.lower() == ".jsonl":
            try:
                for line in text.splitlines():
                    if line.strip():
                        values.update(
                            _json_seed_values(
                                json.loads(line), active="seed" in relative_path.name.lower()
                            )
                        )
            except json.JSONDecodeError:
                values = _text_seed_values(text)
        else:
            values = _text_seed_values(text)
        if values:
            observed.update(values)
            evidence_files[portable] = _sha256(path)
    sorted_values = sorted(observed)
    return {
        "excluded_exact_paths": sorted(SCAN_EXCLUDES),
        "excluded_prefixes": list(SCAN_EXCLUDED_PREFIXES),
        "enumerated_rg_files": len(paths),
        "scanned_text_files": scanned,
        "seed_bearing_files": len(evidence_files),
        "seed_evidence_files_sha256": _json_sha256(evidence_files),
        "observed_seed_count": len(sorted_values),
        "observed_seed_min": min(sorted_values) if sorted_values else None,
        "observed_seed_max": max(sorted_values) if sorted_values else None,
        "observed_seed_values_sha256": _json_sha256(sorted_values),
        "observed_seed_ranges": _compressed_ranges(sorted_values),
        "observed_seed_values": sorted_values,
    }


def _inventory_row(ref: str) -> dict[str, Any]:
    path = PROJECT_ROOT / "research/campaign_3000/02_public_meta/code_inventory.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    matches = [row for row in rows if row.get("ref") == ref]
    if len(matches) != 1:
        raise ValueError(f"expected one inventory row for {ref}, got {len(matches)}")
    return matches[0]


def _environment_snapshot() -> dict[str, str]:
    distribution = importlib.metadata.distribution("kaggle-environments")
    path = Path(
        distribution.locate_file(
            "kaggle_environments/envs/kaggriculture/kaggriculture.py"
        )
    )
    return {
        "version": distribution.version,
        "kaggriculture_py_sha256": _sha256(path),
    }


def _repo_path(project_root: Path, portable_path: str) -> Path:
    if (
        not portable_path
        or "\\" in portable_path
        or Path(portable_path).is_absolute()
        or any(part in {"", ".", ".."} for part in portable_path.split("/"))
    ):
        raise ValueError(f"invalid repository-relative path: {portable_path!r}")
    root = project_root.resolve()
    path = (root / portable_path).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"path escapes repository: {portable_path}")
    return path


def _binding_inputs(
    project_root: Path, binding_path: Path
) -> tuple[dict[str, Any], str, bytes, list[dict[str, Any]]]:
    root = project_root.resolve()
    binding_path = binding_path.resolve()
    try:
        binding_relative = binding_path.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError("execution binding is outside the repository") from exc
    binding = _load(binding_path)
    if binding.get("schema_version") != 1:
        raise ValueError("unsupported execution binding schema")
    if binding.get("binding_protocol") != "clean_two_stage_S_to_E_v1":
        raise ValueError("execution binding protocol mismatch")
    if binding.get("binding_path") != binding_relative:
        raise ValueError("execution binding path mismatch")
    if binding.get("binding_excluded_from_input_manifest") is not True:
        raise ValueError("binding exclusion declaration is required")
    lifecycle_relative = binding.get("lifecycle_path")
    if not isinstance(lifecycle_relative, str):
        raise TypeError("lifecycle path must be a string")
    _repo_path(root, lifecycle_relative)
    if binding.get("lifecycle_excluded_from_input_manifest") is not True:
        raise ValueError("lifecycle exclusion declaration is required")
    candidate_plan_relative = binding.get("candidate_plan_path")
    if not isinstance(candidate_plan_relative, str):
        raise TypeError("candidate plan path must be a string")
    _repo_path(root, candidate_plan_relative)

    manifest_pin = binding.get("input_manifest")
    if not isinstance(manifest_pin, dict):
        raise TypeError("missing input manifest pin")
    manifest_relative = manifest_pin.get("path")
    if not isinstance(manifest_relative, str):
        raise TypeError("input manifest path must be a string")
    manifest_path = _repo_path(root, manifest_relative)
    if not manifest_path.is_file():
        raise ValueError("input manifest is missing")
    manifest_bytes = manifest_path.read_bytes()
    if len(manifest_bytes) != manifest_pin.get("bytes"):
        raise ValueError("current manifest byte count mismatch")
    if _sha256_bytes(manifest_bytes) != manifest_pin.get("sha256"):
        raise ValueError("current manifest SHA mismatch")
    try:
        manifest = json.loads(manifest_bytes)
    except json.JSONDecodeError as exc:
        raise ValueError("input manifest is not valid JSON") from exc
    records = manifest.get("files")
    if not isinstance(records, list) or not records:
        raise ValueError("input manifest has no files")

    by_path: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            raise TypeError("invalid input manifest record")
        relative = record["path"]
        _repo_path(root, relative)
        if relative in by_path:
            raise ValueError(f"duplicate input manifest path: {relative}")
        if relative == binding_relative:
            raise ValueError("execution binding must be excluded from input manifest")
        if relative == lifecycle_relative:
            raise ValueError("lifecycle must be excluded from input manifest")
        if (
            not isinstance(record.get("bytes"), int)
            or record["bytes"] < 0
            or not isinstance(record.get("sha256"), str)
            or re.fullmatch(r"[0-9A-F]{64}", record["sha256"]) is None
        ):
            raise ValueError(f"invalid input identity: {relative}")
        by_path[relative] = record

    tracked_inputs = binding.get("tracked_execution_inputs")
    if (
        not isinstance(tracked_inputs, list)
        or not tracked_inputs
        or not all(isinstance(item, str) for item in tracked_inputs)
        or len(set(tracked_inputs)) != len(tracked_inputs)
    ):
        raise ValueError("tracked execution inputs must be a unique nonempty list")
    missing = sorted(set(tracked_inputs) - set(by_path))
    if missing:
        raise ValueError(f"tracked execution input absent from manifest: {missing}")
    if candidate_plan_relative not in by_path:
        raise ValueError("candidate plan must be a tracked manifest input")
    return binding, manifest_relative, manifest_bytes, list(by_path.values())


def _closed_lifecycle(plan: Mapping[str, Any]) -> dict[str, Any]:
    slots = [candidate["slot"] for candidate in plan["candidates"]]
    if slots != ["Kag_01", "Kag_02"]:
        raise ValueError("lifecycle requires exact Kag_01/Kag_02 slots")
    return {
        "schema_version": 1,
        "lifecycle_protocol": "auditor_exact_development_open_v1",
        "state": "CLOSED",
        "execution_commit": "PENDING",
        "authority_receipt": {
            "path": AUTHORITY_RECEIPT_RELATIVE,
            "bytes": 0,
            "sha256": "PENDING",
        },
        "auditor_open_delivery": {
            "path": AUDITOR_OPEN_DELIVERY_RELATIVE,
            "bytes": 0,
            "sha256": "PENDING",
        },
        "phases": {
            slot: {
                "development": "CLOSED",
                "confirmation": "HOLD",
                "robustness": "HOLD",
            }
            for slot in slots
        },
        "external_actions": "HOLD",
        "fresh_games_executed": 0,
    }


def _load_bound_plan(project_root: Path, binding: Mapping[str, Any]) -> dict[str, Any]:
    return _load(_repo_path(project_root, binding["candidate_plan_path"]))


def _require_closed_lifecycle(payload: bytes, plan: Mapping[str, Any], label: str) -> None:
    try:
        lifecycle = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} is not valid JSON") from exc
    if lifecycle != _closed_lifecycle(plan):
        raise ValueError(f"{label} is not the exact CLOSED lifecycle")


def _validate_current_inputs(project_root: Path, records: Sequence[Mapping[str, Any]]) -> None:
    for record in records:
        relative = record["path"]
        path = _repo_path(project_root, relative)
        if not path.is_file():
            raise ValueError(f"current manifest input is missing: {relative}")
        payload = path.read_bytes()
        if len(payload) != record["bytes"]:
            raise ValueError(f"current input byte count mismatch: {relative}")
        if _sha256_bytes(payload) != record["sha256"]:
            raise ValueError(f"current input SHA mismatch: {relative}")


def _git_result(project_root: Path, *arguments: str) -> bytes:
    result = subprocess.run(
        ["git", *arguments],
        cwd=project_root,
        check=False,
        capture_output=True,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"git {' '.join(arguments)} failed: {detail}")
    return result.stdout


def _git_text(project_root: Path, *arguments: str) -> str:
    return _git_result(project_root, *arguments).decode("utf-8", errors="strict").strip()


def _git_blob(project_root: Path, commit: str, relative: str) -> bytes:
    return _git_result(project_root, "show", f"{commit}:{relative}")


def validate_execution_binding(
    mode: str,
    project_root: Path = PROJECT_ROOT,
    binding_path: Path | None = None,
    execution_ref: str = "HEAD",
) -> dict[str, Any]:
    """Validate the pre-commit S placeholder or the committed S -> E execution binding."""
    root = project_root.resolve()
    selected_binding = (binding_path or (root / BINDING_PATH.relative_to(PROJECT_ROOT))).resolve()
    binding, manifest_relative, manifest_bytes, records = _binding_inputs(
        root, selected_binding
    )
    implementation_commit = binding.get("implementation_commit")
    plan = _load_bound_plan(root, binding)
    lifecycle_relative = binding["lifecycle_path"]

    if mode == "implementation-freeze":
        if implementation_commit != "PENDING":
            raise ValueError("implementation-freeze mode requires explicit PENDING")
        _validate_current_inputs(root, records)
        lifecycle_path = _repo_path(root, lifecycle_relative)
        if not lifecycle_path.is_file():
            raise ValueError("CLOSED lifecycle is missing")
        _require_closed_lifecycle(
            lifecycle_path.read_bytes(), plan, "implementation-freeze lifecycle"
        )
        return {
            "status": "VALID_IMPLEMENTATION_FREEZE_PENDING",
            "implementation_commit": "PENDING",
            "manifest_sha256": _sha256_bytes(manifest_bytes),
            "manifest_bytes": len(manifest_bytes),
            "tracked_input_count": len(binding["tracked_execution_inputs"]),
        }
    if mode != "execution":
        raise ValueError(f"unknown execution binding mode: {mode}")
    if not isinstance(implementation_commit, str) or re.fullmatch(
        r"[0-9a-f]{40}", implementation_commit
    ) is None:
        raise ValueError("execution mode requires a full lowercase implementation commit")

    resolved_execution = _git_text(
        root, "rev-parse", "--verify", f"{execution_ref}^{{commit}}"
    )
    head_line = _git_text(
        root, "rev-list", "--parents", "-n", "1", resolved_execution
    ).split()
    if len(head_line) != 2:
        raise ValueError("execution commit E must have exactly one parent S")
    execution_commit, parent_commit = head_line
    if implementation_commit != parent_commit:
        raise ValueError("implementation_commit is not exactly E parent S")

    binding_relative = selected_binding.relative_to(root).as_posix()
    changed = _git_text(
        root,
        "diff-tree",
        "--no-commit-id",
        "--name-only",
        "-r",
        parent_commit,
        execution_commit,
    ).splitlines()
    if changed != [binding_relative]:
        raise ValueError("S to E must change only execution_binding.json")

    s_binding_bytes = _git_blob(root, parent_commit, binding_relative)
    try:
        s_binding = json.loads(s_binding_bytes)
    except json.JSONDecodeError as exc:
        raise ValueError("S execution binding is not valid JSON") from exc
    if s_binding.get("implementation_commit") != "PENDING":
        raise ValueError("S execution binding lacks the explicit PENDING placeholder")
    current_binding_bytes = selected_binding.read_bytes()
    if current_binding_bytes != _git_blob(root, execution_commit, binding_relative):
        raise ValueError("current execution binding bytes differ from E blob")
    bound_line = f'"implementation_commit": "{parent_commit}"'.encode()
    if current_binding_bytes.count(bound_line) != 1:
        raise ValueError("E binding must contain exactly one implementation_commit line")
    if current_binding_bytes.replace(
        bound_line, b'"implementation_commit": "PENDING"', 1
    ) != s_binding_bytes:
        raise ValueError("E may change only the implementation_commit value from S")

    tracked_status = _git_text(root, "status", "--porcelain=v1", "--untracked-files=no")
    if tracked_status:
        raise ValueError(f"tracked tree is dirty: {tracked_status}")

    _require_closed_lifecycle(
        _git_blob(root, execution_commit, lifecycle_relative),
        plan,
        "E lifecycle blob",
    )

    s_manifest_bytes = _git_blob(root, parent_commit, manifest_relative)
    if s_manifest_bytes != manifest_bytes:
        raise ValueError("S manifest blob does not equal current manifest bytes")
    if _sha256_bytes(s_manifest_bytes) != binding["input_manifest"]["sha256"]:
        raise ValueError("S manifest blob SHA does not equal bound manifest SHA")
    if len(s_manifest_bytes) != binding["input_manifest"]["bytes"]:
        raise ValueError("S manifest blob byte count does not equal bound manifest bytes")

    _validate_current_inputs(root, records)
    for record in records:
        relative = record["path"]
        _git_result(root, "ls-files", "--error-unmatch", "--", relative)
        if _git_blob(root, parent_commit, relative) != _repo_path(root, relative).read_bytes():
            raise ValueError(f"current input bytes differ from S blob: {relative}")
    return {
        "status": "VALID_CLEAN_EXECUTION_BINDING",
        "implementation_commit": parent_commit,
        "execution_commit": execution_commit,
        "manifest_sha256": _sha256_bytes(manifest_bytes),
        "manifest_bytes": len(manifest_bytes),
        "tracked_input_count": len(binding["tracked_execution_inputs"]),
    }


def validate_plan(check_seed_snapshot: bool = True) -> dict[str, Any]:
    plan = _load(PLAN_PATH)
    gate = _load(GATE_PATH)
    selection = _load(SELECTION_PATH)
    errors: list[str] = []
    if plan["status"] != "CLOSED" or gate["status"] != "FROZEN_CLOSED":
        errors.append("plan and gate must remain CLOSED")
    if set(plan["authority"].values()) & {"ALLOWED", "AUTHORIZED", "OPEN"}:
        errors.append("authority unexpectedly permits an action")

    catalog = plan["opponent_catalog"]
    for alias, record in catalog.items():
        path = PROJECT_ROOT / record["path"]
        if not path.is_file():
            errors.append(f"missing source: {alias}")
            continue
        if path.stat().st_size != record["bytes"] or _sha256(path) != record["sha256"]:
            errors.append(f"source identity mismatch: {alias}")
        try:
            compile(path.read_bytes(), record["path"], "exec")
        except SyntaxError:
            errors.append(f"source does not compile: {alias}")

    runner = plan["runner"]
    if _sha256(PROJECT_ROOT / runner["path"]) != runner["sha256"]:
        errors.append("runner SHA mismatch")
    scenario_source = plan["scenario_source"]
    if _sha256(PROJECT_ROOT / scenario_source["path"]) != scenario_source["sha256"]:
        errors.append("scenario config SHA mismatch")
    scenarios = _load(PROJECT_ROOT / scenario_source["path"])["scenarios"]
    named_scenarios = {
        name for phase in PHASES for name in _scenario_names(plan, phase)
    }
    if not named_scenarios <= scenarios.keys():
        errors.append("unknown scenario name")

    reservations: list[tuple[int, int, str]] = []
    for candidate in plan["candidates"]:
        alias = candidate["candidate_alias"]
        if candidate["status"] != "CLOSED":
            errors.append(f"candidate is not CLOSED: {candidate['slot']}")
        if candidate["candidate_sha256"] != catalog[alias]["sha256"]:
            errors.append(f"candidate/catalog mismatch: {candidate['slot']}")
        opponent_hashes = {catalog[name]["sha256"] for name in candidate["opponents"]}
        if alias in candidate["opponents"] or candidate["candidate_sha256"] in opponent_hashes:
            errors.append(f"self-lane contamination: {candidate['slot']}")
        for phase in PHASES:
            pool = candidate["seed_pools"][phase]
            seeds = _seeds(candidate, phase)
            if (
                pool["status"] != "CLOSED"
                or pool["opened"] is not False
                or pool["consumed"] is not False
                or pool["evaluated_games"] != 0
                or len(seeds) != pool["count"]
            ):
                errors.append(f"seed pool is not pristine CLOSED: {candidate['slot']} {phase}")
            reservations.append((seeds[0], seeds[-1], f"{candidate['slot']}:{phase}"))
            if len(expected_grid(plan, candidate["slot"], phase)) != candidate[
                "expected_cells"
            ][phase]:
                errors.append(f"cell count mismatch: {candidate['slot']} {phase}")

    for index, (start, end, label) in enumerate(reservations):
        for other_start, other_end, other_label in reservations[index + 1 :]:
            if max(start, other_start) <= min(end, other_end):
                errors.append(f"reservation overlap: {label} and {other_label}")

    if check_seed_snapshot:
        frozen = _load(SEED_SCAN_PATH)
        current = scan_observed_seeds()
        for key in (
            "observed_seed_count",
            "observed_seed_values_sha256",
        ):
            if frozen["scan"][key] != current[key]:
                errors.append(f"seed scan snapshot mismatch: {key}")
        observed = set(current["observed_seed_values"])
        collisions = [
            seed
            for start, end, _ in reservations
            for seed in range(start, end + 1)
            if seed in observed
        ]
        if collisions:
            errors.append(f"reserved seed collision: {sorted(set(collisions))}")

    environment = _environment_snapshot()
    if environment != {
        "version": plan["engine"]["version"],
        "kaggriculture_py_sha256": plan["engine"]["kaggriculture_py_sha256"],
    }:
        errors.append("installed environment identity mismatch")

    kaito = _candidate(plan, "Kag_02")["license_gate"]
    row = _inventory_row(kaito["notebook_ref"])
    if (
        _json_sha256(row) != kaito["inventory_row_canonical_sha256"]
        or row["license_name"] != "Apache 2.0"
        or row["version"] != kaito["notebook_version"]
    ):
        errors.append("Kaito license/source inventory mapping mismatch")
    for record in selection["evidence"].values():
        if _sha256(PROJECT_ROOT / record["path"]) != record["sha256"]:
            errors.append(f"selection evidence SHA mismatch: {record['path']}")

    if errors:
        raise ValueError("; ".join(errors))
    return {
        "status": "VALID_CLOSED_PLAN",
        "plan_sha256": _sha256(PLAN_PATH),
        "gate_sha256": _sha256(GATE_PATH),
        "candidate_slots": [item["slot"] for item in plan["candidates"]],
        "planned_cells": sum(
            sum(item["expected_cells"].values()) for item in plan["candidates"]
        ),
        "fresh_games_executed": 0,
    }


def _exact_phase_records(
    plan: Mapping[str, Any], phases: Sequence[str], verdict: str
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    candidates = {candidate["slot"]: candidate for candidate in plan["candidates"]}
    if set(candidates) != set(EXPECTED_SEED_RANGES):
        raise ValueError("authority plan must contain exactly Kag_01 and Kag_02")
    for slot, expected_phases in EXPECTED_SEED_RANGES.items():
        candidate = candidates[slot]
        for phase in phases:
            pool = candidate["seed_pools"][phase]
            start, end = expected_phases[phase]
            if (
                pool["start"] != start
                or pool["end_inclusive"] != end
                or pool["count"] != end - start + 1
            ):
                raise ValueError(f"authority range mismatch in plan: {slot} {phase}")
            records.append(
                {
                    "slot": slot,
                    "candidate_sha256": candidate["candidate_sha256"],
                    "phase": phase,
                    "seed_start": start,
                    "seed_end_inclusive": end,
                    "seed_count": end - start + 1,
                    "seats": [0, 1],
                    "expected_cells": candidate["expected_cells"][phase],
                    "verdict": verdict,
                }
            )
    return records


def _validate_authority_receipt(
    receipt: Mapping[str, Any],
    plan: Mapping[str, Any],
    binding: Mapping[str, Any],
    execution_commit: str,
    implementation_commit: str,
    project_root: Path,
    delivery_pin: Mapping[str, Any],
) -> None:
    required_keys = {
        "schema_version",
        "receipt_type",
        "issued_at_utc",
        "auditor_attestation",
        "subject",
        "authorizations",
        "holds",
        "prohibitions",
        "prior_execution",
        "auditor_delivery",
    }
    if set(receipt) != required_keys:
        raise ValueError("authority receipt fields are not exact")
    if receipt["schema_version"] != 1 or receipt["receipt_type"] != (
        "INDEPENDENT_AUDITOR_EXACT_DEVELOPMENT_OPEN"
    ):
        raise ValueError("authority receipt type mismatch")
    issued_at = receipt["issued_at_utc"]
    try:
        parsed_time = datetime.fromisoformat(issued_at)
    except (AttributeError, ValueError) as exc:
        raise ValueError("authority receipt issued_at_utc is invalid") from exc
    if not issued_at.endswith("Z") or parsed_time.tzinfo is None:
        raise ValueError("authority receipt issued_at_utc must be UTC")

    attestation = receipt["auditor_attestation"]
    if not isinstance(attestation, dict) or set(attestation) != {
        "task_id",
        "role",
        "verdict",
        "scope",
    }:
        raise ValueError("structured auditor attestation is required")
    expected_attestation = {
        "task_id": AUDITOR_TASK_ID,
        "role": "independent-auditor",
        "verdict": "OPEN",
        "scope": "EXACT_LOCAL_DEVELOPMENT_RANGES_ONLY",
    }
    for key, expected in expected_attestation.items():
        if attestation.get(key) != expected:
            raise ValueError(f"auditor attestation mismatch: {key}")
    if receipt["auditor_delivery"] != delivery_pin:
        raise ValueError("authority receipt does not pin exact raw auditor delivery")

    expected_subject = {
        "execution_commit": execution_commit,
        "implementation_commit": implementation_commit,
        "input_manifest_sha256": binding["input_manifest"]["sha256"],
        "candidate_plan_sha256": _sha256(
            _repo_path(project_root, binding["candidate_plan_path"])
        ),
        "engine": plan["engine"],
    }
    if receipt["subject"] != expected_subject:
        raise ValueError("authority receipt subject mismatch")
    if receipt["authorizations"] != _exact_phase_records(
        plan, ("development",), "OPEN"
    ):
        raise ValueError("authority receipt slot/range/OPEN mismatch")
    if receipt["holds"] != _exact_phase_records(
        plan, ("confirmation", "robustness"), "HOLD"
    ):
        raise ValueError("authority receipt confirmation/robustness HOLD mismatch")
    if receipt["prohibitions"] != {
        "kaggle_save_run": "HOLD",
        "upload": "HOLD",
        "competition_submission": "HOLD",
        "publication": "HOLD",
    }:
        raise ValueError("authority receipt external-action HOLD mismatch")
    if receipt["prior_execution"] != {
        "fresh_games_executed": 0,
        "opened_seed_ranges": [],
    }:
        raise ValueError("authority receipt must attest zero prior fresh games")


def _validate_raw_task_delivery(
    path: Path, expected_decision: Mapping[str, Any]
) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"raw auditor task delivery is missing: {path}")
    payload = path.read_bytes()
    try:
        export = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("raw auditor task delivery is not valid JSON") from exc
    if not isinstance(export, dict) or set(export) != {
        "schemaVersion",
        "thread",
        "page",
        "turns",
    }:
        raise ValueError("file is not an unmodified codex_app__read_thread result")
    thread = export["thread"]
    required_thread_fields = {"id", "kind", "hostId", "title", "status"}
    if not isinstance(thread, dict) or not required_thread_fields <= set(thread):
        raise ValueError("read_thread thread metadata is incomplete")
    if (
        thread["id"] != AUDITOR_TASK_ID
        or thread["kind"] != "codex"
        or thread["hostId"] != "local"
        or not isinstance(thread["status"], dict)
        or thread["status"].get("type") != "idle"
    ):
        raise ValueError("read_thread task identity/status mismatch")
    if (
        not isinstance(export["page"], dict)
        or export["page"].get("order") != "newest_first"
        or not isinstance(export["turns"], list)
        or len(export["turns"]) != 1
    ):
        raise ValueError("read_thread page/turns are invalid")
    turn = export["turns"][0]
    if (
        not isinstance(turn, dict)
        or not isinstance(turn.get("id"), str)
        or turn.get("status") != "completed"
        or turn.get("error") is not None
        or not isinstance(turn.get("items"), list)
    ):
        raise ValueError("read_thread latest turn is not a clean completed turn")
    final_items = [
        item
        for item in turn["items"]
        if isinstance(item, dict)
        and item.get("type") == "agentMessage"
        and item.get("phase") == "final_answer"
    ]
    if len(final_items) != 1:
        raise ValueError("read_thread needs exactly one final_answer agentMessage")
    final_item = final_items[0]
    if not isinstance(final_item.get("id"), str) or not isinstance(
        final_item.get("text"), str
    ):
        raise TypeError("read_thread final agentMessage is invalid")
    turn_id = turn["id"]
    raw_message = final_item["text"]
    try:
        decision = json.loads(raw_message)
    except json.JSONDecodeError as exc:
        raise ValueError("raw auditor message is not structured JSON") from exc
    if decision != expected_decision:
        raise ValueError("raw auditor decision does not match exact expected verdict")
    return {
        "bytes": len(payload),
        "sha256": _sha256_bytes(payload),
        "thread_id": thread["id"],
        "host_id": thread["hostId"],
        "turn_id": turn_id,
        "item_id": final_item["id"],
        "raw_message_sha256": _sha256_bytes(raw_message.encode()),
    }


def _open_lifecycle(
    plan: Mapping[str, Any],
    execution_commit: str,
    receipt_bytes: bytes,
    delivery_bytes: bytes,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "lifecycle_protocol": "auditor_exact_development_open_v1",
        "state": "DEVELOPMENT_OPEN",
        "execution_commit": execution_commit,
        "authority_receipt": {
            "path": AUTHORITY_RECEIPT_RELATIVE,
            "bytes": len(receipt_bytes),
            "sha256": _sha256_bytes(receipt_bytes),
        },
        "auditor_open_delivery": {
            "path": AUDITOR_OPEN_DELIVERY_RELATIVE,
            "bytes": len(delivery_bytes),
            "sha256": _sha256_bytes(delivery_bytes),
        },
        "phases": {
            candidate["slot"]: {
                "development": "OPEN",
                "confirmation": "HOLD",
                "robustness": "HOLD",
            }
            for candidate in plan["candidates"]
        },
        "external_actions": "HOLD",
        "fresh_games_executed": 0,
    }


def _git_path_is_ignored(project_root: Path, relative: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "-q", "--", relative],
        cwd=project_root,
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def _git_path_is_tracked(project_root: Path, relative: str) -> bool:
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative],
        cwd=project_root,
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def validate_development_authority(
    project_root: Path = PROJECT_ROOT,
    binding_path: Path | None = None,
    lifecycle_path: Path | None = None,
    receipt_path: Path | None = None,
    auditor_delivery_path: Path | None = None,
    o_review_delivery_path: Path | None = None,
) -> dict[str, Any]:
    root = project_root.resolve()
    selected_binding = (binding_path or (root / BINDING_PATH.relative_to(PROJECT_ROOT))).resolve()
    binding, _, _, _ = _binding_inputs(root, selected_binding)
    plan = _load_bound_plan(root, binding)
    selected_lifecycle = (
        lifecycle_path or _repo_path(root, binding["lifecycle_path"])
    ).resolve()
    expected_lifecycle_path = _repo_path(root, binding["lifecycle_path"])
    if selected_lifecycle != expected_lifecycle_path:
        raise ValueError("lifecycle path differs from frozen binding")
    if not selected_lifecycle.is_file():
        raise ValueError("lifecycle file is missing")
    lifecycle_bytes = selected_lifecycle.read_bytes()
    try:
        lifecycle = json.loads(lifecycle_bytes)
    except json.JSONDecodeError as exc:
        raise ValueError("lifecycle is not valid JSON") from exc
    if lifecycle.get("state") == "CLOSED":
        _require_closed_lifecycle(lifecycle_bytes, plan, "current lifecycle")
        return {
            "status": "CLOSED",
            "development": "CLOSED",
            "confirmation": "HOLD",
            "robustness": "HOLD",
            "fresh_games_executed": 0,
        }
    if lifecycle.get("state") != "DEVELOPMENT_OPEN":
        raise ValueError("unknown lifecycle state")

    o_line = _git_text(root, "rev-list", "--parents", "-n", "1", "HEAD").split()
    if len(o_line) != 2:
        raise ValueError("authority commit O must have exactly one parent E")
    authority_commit, execution_commit = o_line
    if lifecycle.get("execution_commit") != execution_commit:
        raise ValueError("lifecycle execution_commit is not exactly O parent E")
    lifecycle_relative = selected_lifecycle.relative_to(root).as_posix()
    changed = _git_text(
        root,
        "diff-tree",
        "--no-commit-id",
        "--name-only",
        "-r",
        execution_commit,
        authority_commit,
    ).splitlines()
    if changed != [lifecycle_relative]:
        raise ValueError("E to O must change only lifecycle.json")
    binding_result = validate_execution_binding(
        "execution", root, selected_binding, execution_ref=execution_commit
    )

    expected_receipt_path = _repo_path(root, AUTHORITY_RECEIPT_RELATIVE)
    selected_receipt = (receipt_path or expected_receipt_path).resolve()
    if selected_receipt != expected_receipt_path:
        raise ValueError("authority receipt path is not exact")
    if not _git_path_is_ignored(root, AUTHORITY_RECEIPT_RELATIVE):
        raise ValueError("authority receipt must be ignored by Git")
    if _git_path_is_tracked(root, AUTHORITY_RECEIPT_RELATIVE):
        raise ValueError("authority receipt must remain untracked")
    if not selected_receipt.is_file():
        raise ValueError("exact authority receipt is missing")
    receipt_bytes = selected_receipt.read_bytes()
    receipt_pin = lifecycle.get("authority_receipt")
    if receipt_pin != {
        "path": AUTHORITY_RECEIPT_RELATIVE,
        "bytes": len(receipt_bytes),
        "sha256": _sha256_bytes(receipt_bytes),
    }:
        raise ValueError("authority receipt SHA/bytes do not match lifecycle")
    try:
        receipt = json.loads(receipt_bytes)
    except json.JSONDecodeError as exc:
        raise ValueError("authority receipt is not valid JSON") from exc

    expected_delivery_path = _repo_path(root, AUDITOR_OPEN_DELIVERY_RELATIVE)
    selected_delivery = (auditor_delivery_path or expected_delivery_path).resolve()
    if selected_delivery != expected_delivery_path:
        raise ValueError("raw auditor OPEN delivery path is not exact")
    if not _git_path_is_ignored(root, AUDITOR_OPEN_DELIVERY_RELATIVE) or (
        _git_path_is_tracked(root, AUDITOR_OPEN_DELIVERY_RELATIVE)
    ):
        raise ValueError("raw auditor OPEN delivery must be ignored and untracked")
    initial_decision = {
        "verdict": "OPEN",
        "auditor_attestation": receipt.get("auditor_attestation"),
        "subject": receipt.get("subject"),
        "authorizations": receipt.get("authorizations"),
        "holds": receipt.get("holds"),
        "prohibitions": receipt.get("prohibitions"),
        "prior_execution": receipt.get("prior_execution"),
    }
    delivery_identity = _validate_raw_task_delivery(
        selected_delivery, initial_decision
    )
    delivery_bytes = selected_delivery.read_bytes()
    delivery_pin = {
        "path": AUDITOR_OPEN_DELIVERY_RELATIVE,
        **delivery_identity,
    }
    if lifecycle.get("auditor_open_delivery") != {
        "path": AUDITOR_OPEN_DELIVERY_RELATIVE,
        "bytes": len(delivery_bytes),
        "sha256": _sha256_bytes(delivery_bytes),
    }:
        raise ValueError("raw auditor OPEN delivery SHA/bytes do not match lifecycle")
    _validate_authority_receipt(
        receipt,
        plan,
        binding,
        execution_commit,
        binding_result["implementation_commit"],
        root,
        delivery_pin,
    )
    if lifecycle != _open_lifecycle(
        plan, execution_commit, receipt_bytes, delivery_bytes
    ):
        raise ValueError("lifecycle OPEN document is not exact")

    expected_review_path = _repo_path(root, AUDITOR_O_REVIEW_RELATIVE)
    selected_review = (o_review_delivery_path or expected_review_path).resolve()
    if selected_review != expected_review_path:
        raise ValueError("post-O auditor review delivery path is not exact")
    if not _git_path_is_ignored(root, AUDITOR_O_REVIEW_RELATIVE) or _git_path_is_tracked(
        root, AUDITOR_O_REVIEW_RELATIVE
    ):
        raise ValueError("post-O auditor review delivery must be ignored and untracked")
    review_decision = {
        "verdict": "OPEN",
        "authority_commit": authority_commit,
        "execution_commit": execution_commit,
        "lifecycle_sha256": _sha256_bytes(lifecycle_bytes),
        "authority_receipt_sha256": _sha256_bytes(receipt_bytes),
        "auditor_open_delivery_sha256": _sha256_bytes(delivery_bytes),
        "confirmation": "HOLD",
        "robustness": "HOLD",
        "external_actions": "HOLD",
        "fresh_games_executed": 0,
    }
    review_identity = _validate_raw_task_delivery(selected_review, review_decision)
    return {
        "status": "AUTHORIZED_DEVELOPMENT_OPEN",
        "authority_commit": authority_commit,
        "execution_commit": execution_commit,
        "auditor_task_id": AUDITOR_TASK_ID,
        "auditor_open_delivery_sha256": _sha256_bytes(delivery_bytes),
        "o_review_delivery_sha256": review_identity["sha256"],
        "authorized_slots": ["Kag_01", "Kag_02"],
        "authorized_ranges": {
            slot: list(phases["development"])
            for slot, phases in EXPECTED_SEED_RANGES.items()
        },
        "confirmation": "HOLD",
        "robustness": "HOLD",
        "external_actions": "HOLD",
        "fresh_games_executed": 0,
    }


def require_open_authority(
    slot: str | None = None,
    phase: str | None = None,
    project_root: Path = PROJECT_ROOT,
    binding_path: Path | None = None,
    lifecycle_path: Path | None = None,
    receipt_path: Path | None = None,
    auditor_delivery_path: Path | None = None,
    o_review_delivery_path: Path | None = None,
) -> dict[str, Any]:
    if slot is None or phase is None:
        raise PermissionError("CLOSED: exact slot, phase, and auditor receipt are required")
    authority = validate_development_authority(
        project_root,
        binding_path,
        lifecycle_path,
        receipt_path,
        auditor_delivery_path,
        o_review_delivery_path,
    )
    if authority["status"] != "AUTHORIZED_DEVELOPMENT_OPEN":
        raise PermissionError("CLOSED: no exact independent-auditor OPEN receipt")
    if phase != "development":
        raise PermissionError(f"{phase} remains HOLD")
    if slot not in authority["authorized_slots"]:
        raise PermissionError(f"slot is not authorized: {slot}")
    plan = _load_bound_plan(project_root.resolve(), _load(binding_path or BINDING_PATH))
    candidate = _candidate(plan, slot)
    seeds = _seeds(candidate, phase)
    if [seeds[0], seeds[-1]] != authority["authorized_ranges"][slot]:
        raise PermissionError("authorized range does not equal frozen development pool")
    return {
        "status": "AUTHORIZED_LOCAL_DEVELOPMENT_EXECUTION",
        "slot": slot,
        "phase": phase,
        "seeds": seeds,
        "seats": [0, 1],
        "expected_cells": candidate["expected_cells"][phase],
        "candidate_sha256": candidate["candidate_sha256"],
        "execution_commit": authority["execution_commit"],
        "authority_commit": authority["authority_commit"],
        "auditor_task_id": AUDITOR_TASK_ID,
        "auditor_open_delivery_sha256": authority["auditor_open_delivery_sha256"],
        "o_review_delivery_sha256": authority["o_review_delivery_sha256"],
        "external_actions": "HOLD",
    }


def _authorized_run_paths(project_root: Path, slot: str) -> dict[str, str]:
    relative_dir = f"dist/campaign_3000/runs/{slot.lower()}_development"
    return {
        "authorized_run_receipt": f"{relative_dir}/authorized_run.json",
        "raw_report": f"{relative_dir}/raw_report.json",
        "runner_started": f"{relative_dir}/raw_report.started.json",
        "outer_started": f"{relative_dir}/outer.started.json",
        "outer_completed": f"{relative_dir}/outer.completed.json",
    }


def _authorized_runner_argv(project_root: Path, run_receipt_relative: str) -> list[str]:
    runner_script = HERE / "authorized_runner.py"
    return [
        str(Path(sys.executable).resolve()),
        runner_script.relative_to(project_root).as_posix(),
        "--run-receipt",
        run_receipt_relative,
    ]


def create_authorized_run_receipt(slot: str, phase: str = "development") -> Path:
    authority = require_open_authority(
        slot,
        phase,
        receipt_path=_repo_path(PROJECT_ROOT, AUTHORITY_RECEIPT_RELATIVE),
        auditor_delivery_path=_repo_path(PROJECT_ROOT, AUDITOR_OPEN_DELIVERY_RELATIVE),
        o_review_delivery_path=_repo_path(PROJECT_ROOT, AUDITOR_O_REVIEW_RELATIVE),
    )
    plan = _load(PLAN_PATH)
    contract = run_contract(plan, slot, phase)
    paths = _authorized_run_paths(PROJECT_ROOT, slot)
    run_path = _repo_path(PROJECT_ROOT, paths["authorized_run_receipt"])
    if not _git_path_is_ignored(PROJECT_ROOT, paths["authorized_run_receipt"]):
        raise ValueError("authorized run outputs must be ignored by Git")
    for relative in paths.values():
        if _repo_path(PROJECT_ROOT, relative).exists():
            raise FileExistsError(f"refusing to overwrite run evidence: {relative}")
    payload = {
        "schema_version": 1,
        "artifact_kind": "campaign_3000_authorized_development_run_v1",
        "created_at_utc": datetime.now().astimezone().isoformat(),
        "status": "AUTHORIZED_NOT_STARTED",
        "slot": slot,
        "phase": phase,
        "plan_sha256": _sha256(PLAN_PATH),
        "gate_sha256": _sha256(GATE_PATH),
        "selection_sha256": _sha256(SELECTION_PATH),
        "runner_sha256": plan["runner"]["sha256"],
        "engine": plan["engine"],
        "authority": {
            key: authority[key]
            for key in (
                "authority_commit",
                "execution_commit",
                "auditor_task_id",
                "auditor_open_delivery_sha256",
                "o_review_delivery_sha256",
            )
        },
        "authority_receipt_sha256": _sha256(
            _repo_path(PROJECT_ROOT, AUTHORITY_RECEIPT_RELATIVE)
        ),
        "lifecycle_sha256": _sha256(LIFECYCLE_PATH),
        "contract": contract,
        "outputs": paths,
        "runner_argv": _authorized_runner_argv(
            PROJECT_ROOT, paths["authorized_run_receipt"]
        ),
        "fresh_games_executed_before_start": 0,
        "external_actions": "HOLD",
    }
    run_path.parent.mkdir(parents=True, exist_ok=True)
    run_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return run_path


def validate_authorized_run_receipt(run_receipt_path: Path) -> dict[str, Any]:
    root = PROJECT_ROOT
    run_path = run_receipt_path.resolve()
    try:
        run_relative = run_path.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError("authorized run receipt is outside project root") from exc
    if not run_path.is_file() or not _git_path_is_ignored(root, run_relative):
        raise ValueError("authorized run receipt must exist in the ignored run directory")
    run = _load(run_path)
    if not isinstance(run, dict) or run.get("artifact_kind") != (
        "campaign_3000_authorized_development_run_v1"
    ):
        raise ValueError("not an authorized run receipt")
    slot, phase = run.get("slot"), run.get("phase")
    if slot not in {"Kag_01", "Kag_02"} or phase != "development":
        raise ValueError("authorized run receipt is outside development scope")
    authority = require_open_authority(
        slot,
        phase,
        receipt_path=_repo_path(root, AUTHORITY_RECEIPT_RELATIVE),
        auditor_delivery_path=_repo_path(root, AUDITOR_OPEN_DELIVERY_RELATIVE),
        o_review_delivery_path=_repo_path(root, AUDITOR_O_REVIEW_RELATIVE),
    )
    plan = _load(PLAN_PATH)
    contract = run_contract(plan, slot, phase)
    paths = _authorized_run_paths(root, slot)
    expected = {
        "schema_version": 1,
        "artifact_kind": "campaign_3000_authorized_development_run_v1",
        "status": "AUTHORIZED_NOT_STARTED",
        "slot": slot,
        "phase": phase,
        "plan_sha256": _sha256(PLAN_PATH),
        "gate_sha256": _sha256(GATE_PATH),
        "selection_sha256": _sha256(SELECTION_PATH),
        "runner_sha256": plan["runner"]["sha256"],
        "engine": plan["engine"],
        "authority": {
            key: authority[key]
            for key in (
                "authority_commit",
                "execution_commit",
                "auditor_task_id",
                "auditor_open_delivery_sha256",
                "o_review_delivery_sha256",
            )
        },
        "authority_receipt_sha256": _sha256(
            _repo_path(root, AUTHORITY_RECEIPT_RELATIVE)
        ),
        "lifecycle_sha256": _sha256(LIFECYCLE_PATH),
        "contract": contract,
        "outputs": paths,
        "runner_argv": _authorized_runner_argv(root, paths["authorized_run_receipt"]),
        "fresh_games_executed_before_start": 0,
        "external_actions": "HOLD",
    }
    created_at = run.get("created_at_utc")
    try:
        parsed_created_at = datetime.fromisoformat(created_at)
    except (TypeError, ValueError) as exc:
        raise ValueError("authorized run receipt creation time is invalid") from exc
    if parsed_created_at.tzinfo is None:
        raise ValueError("authorized run receipt creation time needs a timezone")
    comparable = {key: value for key, value in run.items() if key != "created_at_utc"}
    if comparable != expected:
        raise ValueError("authorized run receipt command/grid/authority mismatch")
    if run_relative != paths["authorized_run_receipt"]:
        raise ValueError("authorized run receipt path mismatch")
    if len(expected_grid(plan, slot, phase)) != contract["expected_cells"]:
        raise ValueError("authorized run exact cell count mismatch")
    return run


def execute_authorized_run_receipt(run_receipt_path: Path) -> dict[str, Any]:
    run = validate_authorized_run_receipt(run_receipt_path)
    plan = _load(PLAN_PATH)
    contract = run["contract"]
    paths = run["outputs"]
    outer_started_path = _repo_path(PROJECT_ROOT, paths["outer_started"])
    run_sha256 = _sha256(run_receipt_path)
    outer_started = {
        "slot": run["slot"],
        "phase": run["phase"],
        "authorized_run_receipt_sha256": run_sha256,
        "plan_sha256": run["plan_sha256"],
        "gate_sha256": run["gate_sha256"],
        "selection_sha256": run["selection_sha256"],
        "runner_sha256": run["runner_sha256"],
        "engine": run["engine"],
        "sources_at_start": contract["sources"],
        "grid_sha256": contract["grid_sha256"],
        "authority": run["authority"],
        "runner_argv": run["runner_argv"],
    }
    outer_started_path.write_text(
        json.dumps(outer_started, indent=2) + "\n", encoding="utf-8"
    )

    from kaggriculture_lab.evaluation import runner as runner_module

    original_registry = dict(runner_module.OPPONENT_PATHS)
    try:
        runner_module.OPPONENT_PATHS.update(
            {alias: source["path"] for alias, source in contract["sources"].items()}
        )
        report = runner_module.run_batch(
            contract["candidate_path"],
            contract["opponents"],
            contract["seeds"],
            _repo_path(PROJECT_ROOT, paths["raw_report"]),
            plan["execution"]["workers"],
            PROJECT_ROOT,
            contract["scenarios"],
        )
    finally:
        runner_module.OPPONENT_PATHS.clear()
        runner_module.OPPONENT_PATHS.update(original_registry)

    raw_path = _repo_path(PROJECT_ROOT, paths["raw_report"])
    runner_started_path = _repo_path(PROJECT_ROOT, paths["runner_started"])
    outer_completed = {
        "outer_start_receipt_sha256": _sha256(outer_started_path),
        "runner_start_receipt_sha256": _sha256(runner_started_path),
        "raw_report_sha256": _sha256(raw_path),
        "authorized_run_receipt_sha256": run_sha256,
        "plan_sha256_at_end": _sha256(PLAN_PATH),
        "gate_sha256_at_end": _sha256(GATE_PATH),
        "selection_sha256_at_end": _sha256(SELECTION_PATH),
        "runner_sha256_at_end": plan["runner"]["sha256"],
        "engine_at_end": plan["engine"],
        "sources_at_end": contract["sources"],
        "executed_cells": len(report["games"]),
        "sources_unchanged_during_phase": report["sources_unchanged_during_run"],
        "environment_unchanged_during_phase": True,
        "configs_unchanged_during_phase": True,
    }
    _repo_path(PROJECT_ROOT, paths["outer_completed"]).write_text(
        json.dumps(outer_completed, indent=2) + "\n", encoding="utf-8"
    )
    return {"status": "AUTHORIZED_RUN_COMPLETED", "summary": report["summary"]}


def run_contract(plan: Mapping[str, Any], slot: str, phase: str) -> dict[str, Any]:
    candidate = _candidate(plan, slot)
    catalog = plan["opponent_catalog"]
    scenarios = _load(PROJECT_ROOT / plan["scenario_source"]["path"])["scenarios"]
    selected_scenarios = {
        name: scenarios[name] for name in _scenario_names(plan, phase)
    }
    sources = {
        candidate["candidate_alias"]: {
            "path": candidate["candidate_path"],
            "sha256": candidate["candidate_sha256"],
        },
        **{
            alias: {"path": catalog[alias]["path"], "sha256": catalog[alias]["sha256"]}
            for alias in candidate["opponents"]
        },
    }
    grid = expected_grid(plan, slot, phase)
    return {
        "slot": slot,
        "phase": phase,
        "candidate": candidate["candidate_alias"],
        "candidate_path": candidate["candidate_path"],
        "candidate_sha256": candidate["candidate_sha256"],
        "opponents": candidate["opponents"],
        "opponent_sha256": {
            alias: catalog[alias]["sha256"] for alias in candidate["opponents"]
        },
        "seeds": _seeds(candidate, phase),
        "scenarios": selected_scenarios,
        "sources": sources,
        "grid_sha256": _json_sha256(grid),
        "expected_cells": len(grid),
    }


def _require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise ValueError(f"{label} mismatch")


def validate_report_files(
    slot: str,
    phase: str,
    raw_report_path: Path,
    runner_started_path: Path,
    outer_started_path: Path,
    outer_completed_path: Path,
    authorized_run_receipt_path: Path | None = None,
) -> list[dict[str, Any]]:
    if authorized_run_receipt_path is None:
        raise PermissionError(
            "OPEN authority and an authorized-run receipt are required before report gating"
        )
    authorized_run = validate_authorized_run_receipt(authorized_run_receipt_path)
    if authorized_run["slot"] != slot or authorized_run["phase"] != phase:
        raise ValueError("authorized run slot/phase mismatch")
    expected_outputs = {
        "raw_report": raw_report_path,
        "runner_started": runner_started_path,
        "outer_started": outer_started_path,
        "outer_completed": outer_completed_path,
    }
    for key, path in expected_outputs.items():
        if path.resolve() != _repo_path(PROJECT_ROOT, authorized_run["outputs"][key]):
            raise ValueError(f"authorized run output path mismatch: {key}")
    for label, path in (
        ("authorized run receipt", authorized_run_receipt_path),
        ("raw report", raw_report_path),
        ("runner started receipt", runner_started_path),
        ("outer started receipt", outer_started_path),
        ("outer completed receipt", outer_completed_path),
    ):
        if not path.is_file():
            raise ValueError(f"missing separate receipt/report: {label}")

    plan = _load(PLAN_PATH)
    contract = run_contract(plan, slot, phase)
    report = _load(raw_report_path)
    runner_started = _load(runner_started_path)
    outer_started = _load(outer_started_path)
    outer_completed = _load(outer_completed_path)
    run_receipt_sha256 = _sha256(authorized_run_receipt_path)

    _require_equal(outer_started.get("slot"), slot, "outer start slot")
    _require_equal(outer_started.get("phase"), phase, "outer start phase")
    _require_equal(outer_started.get("plan_sha256"), _sha256(PLAN_PATH), "start plan SHA")
    _require_equal(outer_started.get("gate_sha256"), _sha256(GATE_PATH), "start gate SHA")
    _require_equal(
        outer_started.get("selection_sha256"), _sha256(SELECTION_PATH), "start selection SHA"
    )
    _require_equal(
        outer_started.get("runner_sha256"), plan["runner"]["sha256"], "start runner SHA"
    )
    _require_equal(outer_started.get("engine"), plan["engine"], "start engine")
    _require_equal(outer_started.get("sources_at_start"), contract["sources"], "start sources")
    _require_equal(outer_started.get("grid_sha256"), contract["grid_sha256"], "start grid")
    _require_equal(
        outer_started.get("authorized_run_receipt_sha256"),
        run_receipt_sha256,
        "start authorized run receipt SHA",
    )
    _require_equal(
        outer_started.get("authority"), authorized_run["authority"], "start authority"
    )
    _require_equal(
        outer_started.get("runner_argv"), authorized_run["runner_argv"], "runner argv"
    )

    _require_equal(
        outer_completed.get("outer_start_receipt_sha256"),
        _sha256(outer_started_path),
        "outer start receipt SHA",
    )
    _require_equal(
        outer_completed.get("runner_start_receipt_sha256"),
        _sha256(runner_started_path),
        "runner start receipt SHA",
    )
    _require_equal(
        outer_completed.get("raw_report_sha256"), _sha256(raw_report_path), "raw report SHA"
    )
    _require_equal(
        outer_completed.get("authorized_run_receipt_sha256"),
        run_receipt_sha256,
        "completed authorized run receipt SHA",
    )
    _require_equal(outer_completed.get("plan_sha256_at_end"), _sha256(PLAN_PATH), "end plan SHA")
    _require_equal(outer_completed.get("gate_sha256_at_end"), _sha256(GATE_PATH), "end gate SHA")
    _require_equal(
        outer_completed.get("selection_sha256_at_end"),
        _sha256(SELECTION_PATH),
        "end selection SHA",
    )
    _require_equal(
        outer_completed.get("runner_sha256_at_end"),
        plan["runner"]["sha256"],
        "end runner SHA",
    )
    _require_equal(outer_completed.get("engine_at_end"), plan["engine"], "end engine")
    _require_equal(outer_completed.get("sources_at_end"), contract["sources"], "end sources")
    _require_equal(
        outer_completed.get("executed_cells"), contract["expected_cells"], "executed cells"
    )
    for flag in (
        "sources_unchanged_during_phase",
        "environment_unchanged_during_phase",
        "configs_unchanged_during_phase",
    ):
        if outer_completed.get(flag) is not True:
            raise ValueError(f"receipt integrity flag failed: {flag}")

    _require_equal(runner_started.get("candidate"), contract["candidate_path"], "runner candidate")
    _require_equal(
        runner_started.get("candidate_sha256_at_start"),
        contract["candidate_sha256"],
        "runner candidate start SHA",
    )
    _require_equal(runner_started.get("opponents"), contract["opponents"], "runner opponents")
    _require_equal(
        runner_started.get("opponent_sha256_at_start"),
        contract["opponent_sha256"],
        "runner opponent start SHA",
    )
    _require_equal(runner_started.get("seeds"), contract["seeds"], "runner seeds")
    _require_equal(
        runner_started.get("scenario_overrides"), contract["scenarios"], "runner scenarios"
    )
    _require_equal(runner_started.get("workers"), plan["execution"]["workers"], "runner workers")
    _require_equal(runner_started.get("seat_policy"), "both seats", "runner seat policy")
    _require_equal(
        runner_started.get("git_head_at_start"),
        authorized_run["authority"]["authority_commit"],
        "runner authority commit",
    )

    _require_equal(report.get("start_receipt_sha256"), _sha256(runner_started_path), "report receipt")
    _require_equal(
        report.get("git_head_at_start"),
        authorized_run["authority"]["authority_commit"],
        "report authority commit",
    )
    _require_equal(report.get("candidate"), contract["candidate_path"], "report candidate")
    for field in ("candidate_sha256", "candidate_sha256_at_start", "candidate_sha256_at_end"):
        _require_equal(report.get(field), contract["candidate_sha256"], f"report {field}")
    _require_equal(report.get("opponents"), contract["opponents"], "report opponents")
    _require_equal(
        report.get("opponent_sha256_at_start"), contract["opponent_sha256"], "report opponent start"
    )
    _require_equal(
        report.get("opponent_sha256_at_end"), contract["opponent_sha256"], "report opponent end"
    )
    _require_equal(report.get("seeds"), contract["seeds"], "report seeds")
    _require_equal(report.get("scenario_overrides"), contract["scenarios"], "report scenarios")
    if report.get("sources_unchanged_during_run") is not True:
        raise ValueError("report source start=end failed")

    games = report.get("games")
    if not isinstance(games, list):
        raise TypeError("raw game rows missing")
    expected_keys = {
        (row["scenario"], row["opponent"], row["seed"], row["seat"])
        for row in expected_grid(plan, slot, phase)
    }
    actual_keys: list[tuple[str, str, int, int]] = []
    for index, row in enumerate(games):
        try:
            key = (
                str(row["scenario"]),
                str(row["opponent"]),
                int(row["seed"]),
                int(row["seat"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"invalid cell key at row {index}") from error
        actual_keys.append(key)
        if row.get("error") is not None:
            raise ValueError(f"runner/framework error at row {index}: {row['error']}")
        if row.get("candidate_status") != "DONE" or row.get("opponent_status") != "DONE":
            raise ValueError(f"non-DONE status at row {index}")
        if row.get("hidden_abnormal_status") not in (None, False):
            raise ValueError(f"hidden abnormal status at row {index}")
        for field in ("candidate_money", "opponent_money", "elapsed_seconds"):
            if not _finite_number(row.get(field)):
                raise ValueError(f"nonfinite {field} at row {index}")
        expected_configuration = {
            "episodeSteps": plan["engine"]["episode_steps"],
            **contract["scenarios"][key[0]],
            "seed": key[2],
        }
        _require_equal(
            row.get("effective_configuration"), expected_configuration, f"row {index} config"
        )
        _require_equal(
            row.get("effective_configuration_sha256"),
            _json_sha256(expected_configuration),
            f"row {index} config SHA",
        )
        _require_equal(row.get("resolved_environment_seed"), key[2], f"row {index} seed")
        env_sha = row.get("environment_configuration_sha256")
        if not isinstance(env_sha, str) or not re.fullmatch(r"[0-9A-F]{64}", env_sha):
            raise ValueError(f"row {index} environment config SHA missing")

    actual_set = set(actual_keys)
    if len(actual_keys) != len(actual_set):
        raise ValueError("duplicate exact cells")
    if actual_set != expected_keys:
        missing = len(expected_keys - actual_set)
        extra = len(actual_set - expected_keys)
        raise ValueError(f"exact cell set mismatch: missing={missing}, extra={extra}")
    summary = report.get("summary")
    if not isinstance(summary, dict):
        raise TypeError("runner summary missing")
    if summary.get("failed_raw_games") != 0:
        raise ValueError("runner summary reports failures")
    if summary.get("hidden_abnormal_status_failures", 0) != 0:
        raise ValueError("runner summary reports hidden abnormal status")
    return games


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _percentile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("percentile requires values")
    position = (len(ordered) - 1) * probability
    low, high = math.floor(position), math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _outcome(row: Mapping[str, Any]) -> float:
    candidate_money = float(row["candidate_money"])
    opponent_money = float(row["opponent_money"])
    return 1.0 if candidate_money > opponent_money else 0.0 if candidate_money < opponent_money else 0.5


def _group_match(rows: Sequence[Mapping[str, Any]], field: str) -> dict[str, float]:
    groups: dict[str, list[float]] = {}
    for row in rows:
        groups.setdefault(str(row[field]), []).append(_outcome(row))
    return {key: statistics.fmean(values) for key, values in sorted(groups.items())}


def _group_margin(rows: Sequence[Mapping[str, Any]], field: str) -> dict[str, float]:
    groups: dict[str, list[float]] = {}
    for row in rows:
        groups.setdefault(str(row[field]), []).append(
            float(row["candidate_money"] - row["opponent_money"])
        )
    return {key: statistics.fmean(values) for key, values in sorted(groups.items())}


def summarize_rows(rows: Sequence[Mapping[str, Any]], bootstrap: Mapping[str, Any]) -> dict[str, Any]:
    for index, row in enumerate(rows):
        for key in ("candidate_money", "opponent_money", "elapsed_seconds"):
            if not _finite_number(row.get(key)):
                raise ValueError(f"nonfinite {key} at row {index}")
    outcomes = [_outcome(row) for row in rows]
    margins = [float(row["candidate_money"] - row["opponent_money"]) for row in rows]
    runtimes = [float(row["elapsed_seconds"]) for row in rows]
    by_seed: dict[int, list[float]] = {}
    for row, outcome in zip(rows, outcomes, strict=True):
        by_seed.setdefault(int(row["seed"]), []).append(outcome)
    seed_clusters = [statistics.fmean(values) for _, values in sorted(by_seed.items())]
    rng = random.Random(int(bootstrap["random_seed"]))
    draws = sorted(
        statistics.fmean(rng.choice(seed_clusters) for _ in seed_clusters)
        for _ in range(int(bootstrap["draws"]))
    )
    tail = (1.0 - float(bootstrap["confidence"])) / 2.0
    summary = {
        "valid_games": len(rows),
        "seed_cluster_count": len(seed_clusters),
        "bootstrap_cluster_unit": "seed",
        "match_score": statistics.fmean(outcomes),
        "match_score_seed_cluster_bootstrap_95": [
            _percentile(draws, tail),
            _percentile(draws, 1.0 - tail),
        ],
        "mean_margin": statistics.fmean(margins),
        "margin_p10": _percentile(margins, 0.10),
        "game_runtime_p99_seconds": _percentile(runtimes, 0.99),
        "game_runtime_max_seconds": max(runtimes),
        "by_opponent_match_score": _group_match(rows, "opponent"),
        "by_opponent_mean_margin": _group_margin(rows, "opponent"),
        "by_scenario_match_score": _group_match(rows, "scenario"),
    }
    if not all(
        _finite_number(value)
        for key, value in summary.items()
        if key not in {
            "bootstrap_cluster_unit",
            "match_score_seed_cluster_bootstrap_95",
            "by_opponent_match_score",
            "by_opponent_mean_margin",
            "by_scenario_match_score",
        }
    ):
        raise ValueError("derived metric is nonfinite")
    return summary


def evaluate_thresholds(summary: Mapping[str, Any], phase: str) -> dict[str, Any]:
    thresholds = _load(GATE_PATH)["strict_performance_promotion_thresholds"][phase]
    checks = {
        "match_score": summary["match_score"] >= thresholds["minimum_match_score"],
        "bootstrap_lower": summary["match_score_seed_cluster_bootstrap_95"][0]
        >= thresholds["minimum_match_score_seed_cluster_bootstrap_95_lower"],
        "mean_margin": summary["mean_margin"] >= thresholds["minimum_mean_margin"],
        "each_opponent": min(summary["by_opponent_match_score"].values())
        >= thresholds["minimum_each_opponent_match_score"],
        "runtime_p99": summary["game_runtime_p99_seconds"]
        <= thresholds["maximum_game_runtime_p99_seconds"],
        "runtime_max": summary["game_runtime_max_seconds"]
        <= thresholds["maximum_game_runtime_seconds"],
    }
    if phase == "robustness":
        checks["margin_p10"] = summary["margin_p10"] >= thresholds["minimum_margin_p10"]
        checks["each_scenario"] = min(summary["by_scenario_match_score"].values()) >= thresholds[
            "minimum_each_scenario_match_score"
        ]
    return {"verdict": "PASS" if all(checks.values()) else "NO_GO", "checks": checks}


def evaluate_exploratory_readiness(
    summary: Mapping[str, Any], hard_integrity_pass: bool, package_gate_pass: bool
) -> dict[str, Any]:
    required = _load(GATE_PATH)["exploratory_private_saverun_readiness"]["required"]
    g1_score = summary["by_opponent_match_score"].get("fa04_g1")
    g1_margin = summary["by_opponent_mean_margin"].get("fa04_g1")
    checks = {
        "hard_integrity": hard_integrity_pass,
        "runtime_p99": summary["game_runtime_p99_seconds"]
        <= required["maximum_game_runtime_p99_seconds"],
        "runtime_max": summary["game_runtime_max_seconds"]
        <= required["maximum_game_runtime_seconds"],
        "fa04_g1_match_score": _finite_number(g1_score)
        and g1_score >= required["fa04_g1_minimum_match_score"],
        "fa04_g1_mean_margin": _finite_number(g1_margin)
        and g1_margin >= required["fa04_g1_minimum_mean_margin"],
        "package_and_final_audit": package_gate_pass,
    }
    return {
        "verdict": (
            "EXPLORATORY_PRIVATE_SAVERUN_READY_NON_PROMOTION"
            if all(checks.values())
            else "NOT_READY"
        ),
        "checks": checks,
        "strict_promotion_claim": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Strict CLOSED Kag_01/Kag_02 candidate freeze")
    parser.add_argument(
        "command",
        choices=("scan", "validate", "binding", "grid", "gate", "open", "run"),
    )
    parser.add_argument(
        "--binding-mode", choices=("implementation-freeze", "execution")
    )
    parser.add_argument("--slot", choices=("Kag_01", "Kag_02"))
    parser.add_argument("--phase", choices=PHASES)
    parser.add_argument("--raw-report", type=Path)
    parser.add_argument("--runner-started", type=Path)
    parser.add_argument("--outer-started", type=Path)
    parser.add_argument("--outer-completed", type=Path)
    parser.add_argument("--authority-receipt", type=Path)
    parser.add_argument("--auditor-delivery", type=Path)
    parser.add_argument("--o-review-delivery", type=Path)
    parser.add_argument("--authorized-run-receipt", type=Path)
    parser.add_argument("--package-gate-pass", action="store_true")
    args = parser.parse_args()
    if args.command == "scan":
        print(json.dumps(scan_observed_seeds(), indent=2))
    elif args.command == "validate":
        print(json.dumps(validate_plan(), indent=2))
    elif args.command == "binding":
        if args.binding_mode is None:
            parser.error("binding requires --binding-mode")
        print(json.dumps(validate_execution_binding(args.binding_mode), indent=2))
    elif args.command == "open":
        if any(
            value is None
            for value in (
                args.slot,
                args.phase,
                args.authority_receipt,
                args.auditor_delivery,
                args.o_review_delivery,
            )
        ):
            parser.error(
                "open requires slot, phase, receipt, raw auditor delivery, and O review"
            )
        print(
            json.dumps(
                require_open_authority(
                    args.slot,
                    args.phase,
                    receipt_path=args.authority_receipt,
                    auditor_delivery_path=args.auditor_delivery,
                    o_review_delivery_path=args.o_review_delivery,
                ),
                indent=2,
            )
        )
    elif args.command == "run":
        if not args.slot or not args.phase:
            parser.error("run requires --slot and --phase")
        run_receipt = create_authorized_run_receipt(args.slot, args.phase)
        argv = _authorized_runner_argv(PROJECT_ROOT, _relative(run_receipt))
        subprocess.run(argv, cwd=PROJECT_ROOT, check=True)
        print(json.dumps({"status": "AUTHORIZED_RUN_COMPLETE", "argv": argv}, indent=2))
    elif args.command == "gate":
        required = (
            args.slot,
            args.phase,
            args.raw_report,
            args.runner_started,
            args.outer_started,
            args.outer_completed,
            args.authorized_run_receipt,
        )
        if any(value is None for value in required):
            parser.error(
                "gate requires slot, phase, raw report, authorized run receipt, and all receipts"
            )
        rows = validate_report_files(
            args.slot,
            args.phase,
            args.raw_report,
            args.runner_started,
            args.outer_started,
            args.outer_completed,
            args.authorized_run_receipt,
        )
        summary = summarize_rows(rows, _load(GATE_PATH)["bootstrap"])
        result = {
            "integrity": "PASS",
            "summary": summary,
            "strict": evaluate_thresholds(summary, args.phase),
        }
        if args.phase == "development":
            result["exploratory"] = evaluate_exploratory_readiness(
                summary, True, args.package_gate_pass
            )
        print(json.dumps(result, indent=2))
    else:
        if not args.slot or not args.phase:
            parser.error("grid requires --slot and --phase")
        plan = _load(PLAN_PATH)
        grid = expected_grid(plan, args.slot, args.phase)
        print(
            json.dumps(
                {
                    "status": "CLOSED_NOT_EXECUTED",
                    "cells": len(grid),
                    "grid_sha256": _json_sha256(grid),
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
