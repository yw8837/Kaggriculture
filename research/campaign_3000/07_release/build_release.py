from __future__ import annotations

import argparse
import ast
import base64
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import warnings
import zlib
from pathlib import Path
from typing import Any

ARCHIVE_MEMBERS = ("main.py", "LICENSE", "ATTRIBUTION.md")
ALLOWED_WRAPPER_IMPORTS = {
    "base64",
    "hashlib",
    "io",
    "json",
    "pathlib",
    "tarfile",
}
FINAL_FREEZE_PENDING = "PENDING_FINAL_GIT_FREEZE"
FINAL_FREEZE_PASS = "PASS_FINAL_GIT_FREEZE"
FULL_SHA256 = re.compile(r"[0-9A-F]{64}")
FULL_GIT_COMMIT = re.compile(r"[0-9a-f]{40}")
FORBIDDEN_PRIVATE_PAYLOAD_MARKERS = (
    b"c:\\users\\",
    b"c:\\\\users\\\\",
    b"c:/users/",
    "최용우".encode(),
    b"\\ucd5c\\uc6a9\\uc6b0",
    b"\\\\ucd5c\\\\uc6a9\\\\uc6b0",
    b"kaggle_key",
    b"kaggle_username",
    b"api_token",
    b".kaggle/",
    b".kaggle\\",
)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def canonical_json(payload: Any) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _reject_private_payload_markers(payload: bytes, label: str) -> None:
    lowered = payload.lower()
    matches = [
        marker.decode("utf-8", errors="replace")
        for marker in FORBIDDEN_PRIVATE_PAYLOAD_MARKERS
        if marker.lower() in lowered
    ]
    if matches:
        raise ValueError(f"private path, username, or credential marker in {label}: {matches}")


def load_spec(spec_path: Path) -> dict[str, Any]:
    return json.loads(spec_path.read_text(encoding="utf-8"))


def _read_pinned(path: Path, expected_sha256: str, label: str) -> bytes:
    payload = path.read_bytes()
    actual = sha256(payload)
    if actual != expected_sha256:
        raise ValueError(f"{label} SHA-256 mismatch: {actual} != {expected_sha256}")
    return payload


def _tar_info(name: str, size: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size = size
    info.mode = 0o644
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    return info


def deterministic_archive(members: dict[str, bytes]) -> bytes:
    if tuple(members) != ARCHIVE_MEMBERS:
        raise ValueError(f"archive members must be ordered as {ARCHIVE_MEMBERS}")
    compressed = io.BytesIO()
    with (
        gzip.GzipFile(filename="", mode="wb", fileobj=compressed, mtime=0) as gzip_file,
        tarfile.open(fileobj=gzip_file, mode="w", format=tarfile.USTAR_FORMAT) as archive,
    ):
        for name, payload in members.items():
            archive.addfile(_tar_info(name, len(payload)), io.BytesIO(payload))
    return compressed.getvalue()


def inspect_archive(payload: bytes, expected: dict[str, bytes]) -> dict[str, str]:
    member_hashes: dict[str, str] = {}
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        members = archive.getmembers()
        if tuple(member.name for member in members) != ARCHIVE_MEMBERS:
            raise ValueError("archive membership or ordering changed")
        for member in members:
            if (
                member.mode != 0o644
                or member.mtime != 0
                or member.uid != 0
                or member.gid != 0
                or member.uname != ""
                or member.gname != ""
            ):
                raise ValueError(f"non-deterministic metadata for {member.name}")
            extracted = archive.extractfile(member)
            if extracted is None:
                raise ValueError(f"unable to extract {member.name}")
            content = extracted.read()
            if content != expected[member.name]:
                raise ValueError(f"archive payload mismatch for {member.name}")
            _reject_private_payload_markers(content, f"archive member {member.name}")
            member_hashes[member.name] = sha256(content)
    return member_hashes


def _attribution_markers(candidate: dict[str, Any]) -> tuple[str, ...]:
    common = (
        candidate["notebook_ref"],
        candidate["notebook_url"],
        candidate["notebook_source_sha256"],
        candidate["source_sha256"],
        "Apache License 2.0",
    )
    if candidate["sequence"] == "Kag_01":
        return common + (
            "boatlee/84-84-base-public-holdout-v14-clone-preemption",
            "flexonafft/kaggriculture-adaptive-replay-agent",
            "A7F827B9438885B34B7FD5BF8165458A72F8BB83031A288DD4640F21ADE3294B",
            "3C41010DE37114C082D481E4A4C3E42CA5148E826A140E2AA02964ACA8636DD8",
            "EDC3163ED477B6F9EF70FA8F7A212A4F8179C4FA281008D400EDF6EE488906C2",
            "Kakuteki",
            "mrgrishninsb",
            "V23",
            "2703.1 V15",
            "No public score is claimed for this v16 artifact",
        )
    return common + (
        "roma",
        "55299523",
        "90473746",
        "CD4380D55C4A13C2ED4FD0C9463268C5764599F7E3F58B91E960B49D7DFD5D77",
        "2957.6 V2",
        "captured remote public score",
    )


def _wrapper_source(
    artifact_name: str,
    artifact_sha256: str,
    artifact_payload: bytes,
    member_hashes: dict[str, str],
) -> str:
    encoded = base64.b64encode(artifact_payload).decode("ascii")
    chunks = "\n".join(
        f"    {encoded[index:index + 96]!r}"
        for index in range(0, len(encoded), 96)
    )
    hashes = json.dumps(member_hashes, sort_keys=True)
    return f'''# Local-only wrapper: emit the prebuilt archive byte-for-byte.
import base64
import hashlib
import io
import json
import tarfile
from pathlib import Path

ARTIFACT_NAME = {artifact_name!r}
EXPECTED_ARCHIVE_SHA256 = {artifact_sha256!r}
EXPECTED_MEMBER_SHA256 = {hashes}
PAYLOAD_B64 = (
{chunks}
)

payload = base64.b64decode(PAYLOAD_B64)
actual_archive_sha256 = hashlib.sha256(payload).hexdigest().upper()
if actual_archive_sha256 != EXPECTED_ARCHIVE_SHA256:
    raise RuntimeError("archive SHA-256 mismatch")

with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
    names = archive.getnames()
    if names != ["main.py", "LICENSE", "ATTRIBUTION.md"]:
        raise RuntimeError("archive membership or ordering mismatch")
    actual_members = {{
        name: hashlib.sha256(archive.extractfile(name).read()).hexdigest().upper()
        for name in names
    }}
if actual_members != EXPECTED_MEMBER_SHA256:
    raise RuntimeError("archive member SHA-256 mismatch")

working_dir = Path("/kaggle/working")
if not working_dir.exists():
    working_dir = Path.cwd()
output_path = working_dir / ARTIFACT_NAME
output_path.write_bytes(payload)

print(json.dumps({{
    "artifact": ARTIFACT_NAME,
    "archive_sha256": actual_archive_sha256,
    "bytes": len(payload),
    "members": names,
    "member_sha256": actual_members,
}}, sort_keys=True))
'''


def _wrapper_imports(source: str) -> set[str]:
    import ast

    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".", 1)[0])
    return names


def build_notebook(candidate: dict[str, Any], wrapper_source: str) -> dict[str, Any]:
    imports = _wrapper_imports(wrapper_source)
    if imports != ALLOWED_WRAPPER_IMPORTS:
        raise ValueError(f"unexpected wrapper imports: {sorted(imports)}")
    forbidden = ("requests", "urllib", "socket", "subprocess", "kernels.push", "submit(")
    if any(token in wrapper_source for token in forbidden):
        raise ValueError("wrapper contains network, push, or submission code")
    return {
        "cells": [
            {
                "cell_type": "markdown",
                "id": "private-release-boundary",
                "metadata": {},
                "source": [
                    f"# {candidate['title']}\n",
                    "\n",
                    "Private Save & Run wrapper. It emits a hash-pinned archive containing ",
                    "the exact public agent bytes, full Apache-2.0 license, and attribution. ",
                    "It performs no upload, submission, publication, or network request.\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "emit-exact-private-payload",
                "metadata": {},
                "outputs": [],
                "source": wrapper_source.splitlines(keepends=True),
            },
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def build_metadata(candidate: dict[str, Any], notebook_name: str, competition: str) -> dict[str, Any]:
    return {
        "code_file": notebook_name,
        "competition_sources": [competition],
        "dataset_sources": [],
        "enable_gpu": False,
        "enable_internet": False,
        "enable_tpu": False,
        "id": candidate["kernel_id"],
        "is_private": True,
        "kernel_sources": [],
        "kernel_type": "notebook",
        "language": "python",
        "machine_shape": "",
        "model_sources": [],
        "title": candidate["title"],
    }


def _load_pinned_json(
    project_root: Path,
    pin: dict[str, Any],
    label: str,
) -> dict[str, Any]:
    payload = _read_pinned(project_root / pin["path"], pin["sha256"], label)
    parsed = json.loads(payload)
    if not isinstance(parsed, dict):
        raise TypeError(f"{label} must contain a JSON object")
    return parsed


def _validate_release_tooling(
    project_root: Path,
    spec: dict[str, Any],
) -> dict[str, Any]:
    tooling = spec.get("release_tooling")
    if not isinstance(tooling, dict):
        raise TypeError("missing release_tooling")
    expected_paths = {
        "builder": "research/campaign_3000/07_release/build_release.py",
        "tests": "tests/test_campaign_3000_release_package.py",
        "postrun_validator": "research/campaign_3000/06_candidates/orchestrator.py",
    }
    validated: dict[str, Any] = {}
    for key, expected_path in expected_paths.items():
        pin = tooling.get(key)
        if not isinstance(pin, dict):
            raise TypeError(f"missing release tooling pin: {key}")
        if pin.get("path") != expected_path:
            raise ValueError(f"release tooling path mismatch: {key}")
        expected_sha = pin.get("sha256")
        if not isinstance(expected_sha, str) or not FULL_SHA256.fullmatch(expected_sha):
            raise ValueError(f"release tooling SHA-256 is invalid: {key}")
        payload = _read_pinned(project_root / expected_path, expected_sha, f"release {key}")
        if pin.get("bytes") != len(payload):
            raise ValueError(f"release tooling byte count mismatch: {key}")
        validated[key] = dict(pin)
    return validated


def _require_prerequisite(
    prerequisites: dict[str, Any],
    key: str,
    expected: dict[str, Any],
) -> dict[str, Any]:
    value = prerequisites.get(key)
    if not isinstance(value, dict):
        raise TypeError(f"missing candidate prerequisite: {key}")
    for field, required in expected.items():
        if value.get(field) != required:
            raise ValueError(f"invalid candidate prerequisite {key}.{field}")
    return value


def _load_development_evidence_manifest(
    project_root: Path,
    pin: dict[str, Any],
    slot: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = _load_pinned_json(project_root, pin, f"{slot} development evidence manifest")
    expected_header = {
        "schema_version": 1,
        "artifact_kind": "campaign_3000_tracked_development_evidence_v1",
        "slot": slot,
        "phase": "development",
    }
    for field, expected in expected_header.items():
        if manifest.get(field) != expected:
            raise ValueError(f"{slot} development evidence manifest {field} mismatch")
    records = manifest.get("files")
    if not isinstance(records, list):
        raise TypeError(f"{slot} development evidence file records are absent")
    expected_roles = (
        "authorized_run",
        "runner_started",
        "raw_report",
        "outer_started",
        "outer_completed",
        "gate",
    )
    if tuple(record.get("role") for record in records if isinstance(record, dict)) != (
        expected_roles
    ):
        raise ValueError(f"{slot} development evidence roles changed")
    payloads: dict[str, bytes] = {}
    for record in records:
        if not isinstance(record, dict):
            raise TypeError(f"{slot} development evidence record is invalid")
        role = record["role"]
        expected_sha = record.get("sha256")
        if not isinstance(expected_sha, str) or not FULL_SHA256.fullmatch(expected_sha):
            raise ValueError(f"{slot} development evidence SHA-256 is invalid: {role}")
        payload = _read_pinned(
            project_root / record["path"],
            expected_sha,
            f"{slot} development {role}",
        )
        if len(payload) != record.get("bytes"):
            raise ValueError(f"{slot} development evidence byte count mismatch: {role}")
        payloads[role] = payload
    stderr_capture = manifest.get("stderr_capture")
    if not isinstance(stderr_capture, dict) or stderr_capture.get("captured") is not False:
        raise ValueError(f"{slot} stderr evidence boundary changed")
    gate = json.loads(payloads["gate"])
    if not isinstance(gate, dict) or gate.get("integrity") != "PASS":
        raise ValueError(f"{slot} development gate integrity is not PASS")
    return manifest, gate


def _validate_development_results(
    project_root: Path,
    prerequisites: dict[str, Any],
    postrun_validator: dict[str, Any],
) -> dict[str, Any]:
    development = prerequisites.get("development_results")
    if not isinstance(development, dict):
        raise TypeError("missing candidate prerequisite: development_results")
    lifecycle_pin = development.get("lifecycle")
    if not isinstance(lifecycle_pin, dict):
        raise TypeError("development lifecycle pin is absent")
    lifecycle = _load_pinned_json(project_root, lifecycle_pin, "development lifecycle")
    if (
        lifecycle.get("schema_version") != 2
        or lifecycle.get("lifecycle_protocol") != "auditor_exact_development_close_v1"
        or lifecycle.get("state") != "DEVELOPMENT_CLOSED"
        or lifecycle.get("fresh_games_executed") != 256
        or lifecycle.get("external_actions") != "HOLD"
    ):
        raise ValueError("development lifecycle close contract mismatch")
    lifecycle_slots = lifecycle.get("slots")
    if not isinstance(lifecycle_slots, dict):
        raise TypeError("development lifecycle slots are absent")
    slots = development.get("slots")
    if not isinstance(slots, dict) or set(slots) != {"Kag_01", "Kag_02"}:
        raise ValueError("development result slots must be exactly Kag_01 and Kag_02")
    validated_slots: dict[str, Any] = {}
    gate_hashes: dict[str, str] = {}
    for slot in ("Kag_01", "Kag_02"):
        record = slots[slot]
        if not isinstance(record, dict):
            raise TypeError(f"development result record is invalid: {slot}")
        pin = record.get("evidence_manifest")
        if not isinstance(pin, dict):
            raise TypeError(f"development evidence manifest pin is absent: {slot}")
        manifest, gate = _load_development_evidence_manifest(project_root, pin, slot)
        gate_record = next(record for record in manifest["files"] if record["role"] == "gate")
        gate_hashes[slot] = gate_record["sha256"]
        required_strict = "PASS" if slot == "Kag_01" else "NO_GO"
        strict = gate.get("strict")
        if not isinstance(strict, dict) or strict.get("verdict") != required_strict:
            raise ValueError(f"{slot} strict development verdict mismatch")
        if record.get("required_strict_verdict") != required_strict:
            raise ValueError(f"{slot} required strict verdict policy mismatch")
        if slot == "Kag_01":
            required_readiness = "STRICT_DEVELOPMENT_PASS"
        else:
            required_readiness = (
                "EXPLORATORY_PACKAGE_GATE_PASS_NON_PROMOTION_AUDITOR_RELEASE_PENDING"
            )
            exploratory = gate.get("exploratory")
            if not isinstance(exploratory, dict):
                raise TypeError("Kag_02 exploratory development gate is absent")
            checks = exploratory.get("checks")
            if not isinstance(checks, dict):
                raise TypeError("Kag_02 exploratory checks are absent")
            evidence_checks = {
                key: value
                for key, value in checks.items()
                if key not in {"package_gate", "package_and_final_audit", "independent_auditor_release"}
            }
            if not evidence_checks or any(value is not True for value in evidence_checks.values()):
                raise ValueError("Kag_02 exploratory evidence checks are not all PASS")
            if exploratory.get("strict_promotion_claim") is not False:
                raise ValueError("Kag_02 exploratory result permits a promotion claim")
        if record.get("package_readiness") != required_readiness:
            raise ValueError(f"{slot} package readiness policy mismatch")
        if slot == "Kag_02" and record.get("required_future_release_label") != (
            "EXPLORATORY_PRIVATE_SAVERUN_READY_NON_PROMOTION"
        ):
            raise ValueError("Kag_02 future auditor-release label policy mismatch")
        lifecycle_slot = lifecycle_slots.get(slot)
        if not isinstance(lifecycle_slot, dict):
            raise TypeError(f"development lifecycle slot is absent: {slot}")
        lifecycle_development = lifecycle_slot.get("development")
        if not isinstance(lifecycle_development, dict):
            raise TypeError(f"development lifecycle phase is absent: {slot}")
        expected_lifecycle = (
            {
                "seed_start": 50000,
                "seed_end_inclusive": 50015,
                "evaluated_games": 128,
                "status": "CONSUMED_PASS",
                "strict_verdict": "PASS",
            }
            if slot == "Kag_01"
            else {
                "seed_start": 53000,
                "seed_end_inclusive": 53015,
                "evaluated_games": 128,
                "status": "CONSUMED_NO_GO",
                "strict_verdict": "NO_GO",
            }
        )
        for field, expected in expected_lifecycle.items():
            if lifecycle_development.get(field) != expected:
                raise ValueError(f"{slot} development lifecycle {field} mismatch")
        if (
            lifecycle_development.get("evidence_manifest_path") != pin.get("path")
            or lifecycle_development.get("evidence_manifest_sha256") != pin.get("sha256")
        ):
            raise ValueError(f"{slot} lifecycle evidence-manifest binding mismatch")
        expected_later = (
            {"authorization": "HOLD", "status": "CLOSED"}
            if slot == "Kag_01"
            else {"authorization": "HOLD", "status": "RETIRED_UNUSED"}
        )
        for phase in ("confirmation", "robustness"):
            if lifecycle_slot.get(phase) != expected_later:
                raise ValueError(f"{slot} {phase} lifecycle HOLD mismatch")
        for field in ("execution_authority_commit", "execution_commit", "open_lifecycle_sha256"):
            if manifest.get(field) != lifecycle.get(field):
                raise ValueError(f"{slot} evidence/lifecycle {field} mismatch")
        validated_slots[slot] = {
            **record,
            "execution_authority_commit": manifest.get("execution_authority_commit"),
            "execution_commit": manifest.get("execution_commit"),
            "gate_integrity": gate["integrity"],
            "observed_strict_verdict": strict["verdict"],
        }
    completed = subprocess.run(
        [
            sys.executable,
            str(project_root / postrun_validator["path"]),
            "results",
        ],
        cwd=project_root,
        check=True,
        capture_output=True,
        encoding="utf-8",
        text=True,
    )
    try:
        production_validation = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("postrun production validator output is not exact JSON") from exc
    expected_production_header = {
        "status": "DEVELOPMENT_CLOSED_VALIDATED",
        "execution_authority_commit": lifecycle["execution_authority_commit"],
        "execution_commit": lifecycle["execution_commit"],
        "lifecycle_sha256": lifecycle_pin["sha256"],
        "fresh_games_executed": 256,
        "external_actions": "HOLD",
    }
    for field, expected in expected_production_header.items():
        if production_validation.get(field) != expected:
            raise ValueError(f"postrun production validator {field} mismatch")
    production_results = production_validation.get("results")
    if not isinstance(production_results, list) or [
        result.get("slot") for result in production_results if isinstance(result, dict)
    ] != ["Kag_01", "Kag_02"]:
        raise ValueError("postrun production validator slot set mismatch")
    for result in production_results:
        slot = result["slot"]
        expected_result = {
            "slot": slot,
            "evidence_manifest_sha256": slots[slot]["evidence_manifest"]["sha256"],
            "valid_games": 128,
            "strict_verdict": "PASS" if slot == "Kag_01" else "NO_GO",
            "strict_gate_sha256": gate_hashes[slot],
            "stderr_captured": False,
        }
        if result != expected_result:
            raise ValueError(f"postrun production validator result mismatch: {slot}")
    return {
        **development,
        "production_validator_result": production_validation,
        "slots": validated_slots,
    }


def _validate_candidate_prerequisites(
    project_root: Path,
    spec: dict[str, Any],
) -> dict[str, Any]:
    prerequisites = spec.get("candidate_evaluation_prerequisites")
    if not isinstance(prerequisites, dict):
        raise TypeError("missing candidate_evaluation_prerequisites")
    _require_prerequisite(
        prerequisites,
        "independent_auditor_exact_private_saverun_release",
        {
            "required": True,
            "scope": "EACH_EXACT_SLOT_PRIVATE_SAVERUN_RELEASE",
            "required_verdict": "PASS",
            "auditor_task_id": "019fb8b8-7758-7860-9304-39eb4f06c65c",
            "slots": {"Kag_01": "PENDING", "Kag_02": "PENDING"},
        },
    )

    pinned: dict[str, dict[str, Any]] = {}
    for key, label in (
        ("candidate_plan", "candidate plan"),
        ("candidate_gate", "candidate gate"),
        ("candidate_manifest", "candidate manifest"),
    ):
        pin = prerequisites.get(key)
        if not isinstance(pin, dict) or not isinstance(pin.get("path"), str) or not isinstance(
            pin.get("sha256"), str
        ):
            raise TypeError(f"missing candidate prerequisite: {key}")
        pinned[key] = _load_pinned_json(project_root, pin, label)

    plan_pin = prerequisites["candidate_plan"]
    gate_pin = prerequisites["candidate_gate"]
    manifest = pinned["candidate_manifest"]
    if manifest.get("plan_sha256") != plan_pin["sha256"]:
        raise ValueError("candidate manifest plan SHA-256 binding mismatch")
    if manifest.get("gate_sha256") != gate_pin["sha256"]:
        raise ValueError("candidate manifest gate SHA-256 binding mismatch")
    if pinned["candidate_plan"].get("status") != "CLOSED":
        raise ValueError("candidate plan is not CLOSED")
    if pinned["candidate_gate"].get("status") != "FROZEN_CLOSED":
        raise ValueError("candidate gate is not FROZEN_CLOSED")

    planned_candidates = {
        candidate.get("slot"): candidate
        for candidate in pinned["candidate_plan"].get("candidates", [])
        if isinstance(candidate, dict)
    }
    for candidate in spec["candidates"]:
        planned = planned_candidates.get(candidate["sequence"])
        if planned is None:
            raise ValueError(f"candidate absent from exact plan: {candidate['sequence']}")
        if planned.get("status") != "CLOSED":
            raise ValueError(f"candidate plan slot is not CLOSED: {candidate['sequence']}")
        if planned.get("candidate_sha256") != candidate["source_sha256"]:
            raise ValueError(f"candidate plan source mismatch: {candidate['sequence']}")
        if planned.get("archive_name") != candidate["artifact_name"]:
            raise ValueError(f"candidate plan archive name mismatch: {candidate['sequence']}")

        license_gate = planned.get("license_gate")
        if not isinstance(license_gate, dict):
            raise TypeError(f"candidate plan license gate absent: {candidate['sequence']}")
        if license_gate.get("required_archive_members") != list(ARCHIVE_MEMBERS):
            raise ValueError(
                f"candidate plan required archive members mismatch: {candidate['sequence']}"
            )

        if candidate["sequence"] == "Kag_01":
            verdict = spec.get("tetsu_ip_verdict")
            if not isinstance(verdict, dict):
                raise TypeError("missing tetsu_ip_verdict")
            expected_tetsu_gate = {
                "verdict": verdict.get("verdict"),
                "evidence_path": verdict.get("path"),
                "evidence_sha256": verdict.get("sha256"),
                "auditor_task": prerequisites[
                    "independent_auditor_exact_private_saverun_release"
                ]["auditor_task_id"],
            }
            for field, expected in expected_tetsu_gate.items():
                if license_gate.get(field) != expected:
                    raise ValueError(f"candidate plan Tetsu {field} mismatch")
        elif candidate["sequence"] == "Kag_02":
            for field in (
                "notebook_ref",
                "notebook_version",
                "notebook_source_sha256",
            ):
                if license_gate.get(field) != candidate.get(field):
                    raise ValueError(f"candidate plan Kaito {field} mismatch")
        else:
            raise ValueError(f"unsupported candidate sequence: {candidate['sequence']}")

    release_tooling = _validate_release_tooling(project_root, spec)
    return {
        **prerequisites,
        "development_results": _validate_development_results(
            project_root,
            prerequisites,
            release_tooling["postrun_validator"],
        ),
        "release_tooling": release_tooling,
    }


def _cell_source(notebook: dict[str, Any], index: int) -> str:
    cells = notebook.get("cells")
    if not isinstance(cells, list):
        raise TypeError("raw notebook cells must be a list")
    if not isinstance(index, int) or not 0 <= index < len(cells):
        raise ValueError(f"raw notebook extraction cell is absent: {index}")
    cell = cells[index]
    if not isinstance(cell, dict):
        raise TypeError(f"raw notebook extraction cell is invalid: {index}")
    source = cell.get("source")
    if isinstance(source, str):
        return source
    if isinstance(source, list) and all(isinstance(line, str) for line in source):
        return "".join(source)
    raise ValueError(f"raw notebook extraction cell source is invalid: {index}")


def _extract_raw_main(notebook: dict[str, Any], sequence: str, index: int) -> bytes:
    source = _cell_source(notebook, index)
    if sequence == "Kag_01":
        first_line, separator, main_source = source.partition("\n")
        if first_line != "%%writefile main.py" or not separator:
            raise ValueError("Tetsu raw notebook extraction cell changed")
        return main_source.encode("utf-8")
    if sequence != "Kag_02":
        raise ValueError(f"unsupported raw notebook extraction sequence: {sequence}")

    tree = ast.parse(source)
    assignment = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "_AGENT_B85_PARTS"
                for target in node.targets
            )
        ),
        None,
    )
    if assignment is None:
        raise ValueError("Kaito raw notebook payload assignment is absent")
    parts = ast.literal_eval(assignment.value)
    if not isinstance(parts, list) or not all(isinstance(part, str) for part in parts):
        raise ValueError("Kaito raw notebook payload parts are invalid")
    try:
        return zlib.decompress(base64.b85decode("".join(parts).encode("ascii")))
    except (ValueError, zlib.error) as exc:
        raise ValueError("Kaito raw notebook payload cannot be decoded") from exc


def _validate_raw_source_archive(
    project_root: Path,
    spec: dict[str, Any],
) -> dict[str, Any]:
    archive = spec.get("raw_source_archive")
    if not isinstance(archive, dict):
        raise TypeError("missing raw_source_archive")
    if archive.get("status") != "PASS_EXACT_CURRENT_VERSION_SOURCE_ARCHIVED":
        raise ValueError("raw source archive is not exact-version PASS")
    receipt = _load_pinned_json(project_root, archive, "raw source archive receipt")
    if receipt.get("status") != archive["status"]:
        raise ValueError("raw source archive status mismatch")
    version_binding = receipt.get("version_binding")
    if not isinstance(version_binding, dict) or version_binding.get("status") != (
        "PASS_CURRENT_VERSION_AND_SOURCE_IN_SAME_OFFICIAL_API_RESPONSE"
    ):
        raise ValueError("raw source archive version binding is not PASS")

    records = receipt.get("notebooks")
    if not isinstance(records, list):
        raise TypeError("raw source archive notebook records are absent")
    by_ref = {
        record.get("ref"): record
        for record in records
        if isinstance(record, dict) and isinstance(record.get("ref"), str)
    }
    if len(by_ref) != len(spec["candidates"]):
        raise ValueError("raw source archive notebook set changed")

    for candidate in spec["candidates"]:
        record = by_ref.get(candidate["notebook_ref"])
        if record is None:
            raise ValueError(f"raw notebook record absent: {candidate['sequence']}")
        if record.get("kernel_id") != candidate["notebook_id"]:
            raise ValueError(f"raw notebook kernel id mismatch: {candidate['sequence']}")
        if record.get("current_version_number") != candidate["notebook_version"]:
            raise ValueError(f"raw notebook version mismatch: {candidate['sequence']}")
        if record.get("sha256") != candidate["notebook_source_sha256"]:
            raise ValueError(f"raw notebook source SHA mismatch: {candidate['sequence']}")
        raw_notebook = _read_pinned(
            project_root / record["path"],
            record["sha256"],
            f"raw notebook {candidate['sequence']}",
        )
        if len(raw_notebook) != record.get("bytes"):
            raise ValueError(f"raw notebook byte count mismatch: {candidate['sequence']}")
        response_record = record.get("getkernel_response")
        if not isinstance(response_record, dict):
            raise TypeError(f"GetKernel response receipt absent: {candidate['sequence']}")
        response_payload = _read_pinned(
            project_root / response_record["path"],
            response_record["sha256"],
            f"GetKernel response {candidate['sequence']}",
        )
        if len(response_payload) != response_record.get("bytes"):
            raise ValueError(f"GetKernel response byte count mismatch: {candidate['sequence']}")
        response = json.loads(response_payload)
        metadata = response.get("metadata")
        blob = response.get("blob")
        if not isinstance(metadata, dict) or not isinstance(blob, dict):
            raise TypeError(f"GetKernel response envelope invalid: {candidate['sequence']}")
        expected_metadata = {
            "ref": candidate["notebook_ref"],
            "id": candidate["notebook_id"],
            "currentVersionNumber": candidate["notebook_version"],
            "isPrivate": False,
            "competitionDataSources": [spec["competition"]],
        }
        for field, expected in expected_metadata.items():
            if metadata.get(field) != expected:
                raise ValueError(
                    f"GetKernel response metadata {field} mismatch: {candidate['sequence']}"
                )
        if blob.get("kernelType") != "notebook" or blob.get("language") != "python":
            raise ValueError(f"GetKernel response blob type mismatch: {candidate['sequence']}")
        source = blob.get("source")
        if not isinstance(source, str) or source.encode("utf-8") != raw_notebook:
            raise ValueError(
                f"GetKernel response source differs from raw notebook: {candidate['sequence']}"
            )
        notebook = json.loads(raw_notebook)
        extraction = record.get("extraction")
        if not isinstance(extraction, dict):
            raise TypeError(f"raw notebook extraction receipt absent: {candidate['sequence']}")
        if extraction.get("main_path") != candidate["source_path"]:
            raise ValueError(f"raw notebook main path mismatch: {candidate['sequence']}")
        extracted = _extract_raw_main(
            notebook,
            candidate["sequence"],
            extraction.get("cell_index_zero_based"),
        )
        if len(extracted) != extraction.get("main_bytes"):
            raise ValueError(f"raw notebook extracted byte count mismatch: {candidate['sequence']}")
        if sha256(extracted) != extraction.get("main_sha256"):
            raise ValueError(f"raw notebook extracted SHA mismatch: {candidate['sequence']}")
        if extracted != (project_root / candidate["source_path"]).read_bytes():
            raise ValueError(f"raw notebook extraction differs from main: {candidate['sequence']}")
    return archive


def _validate_official_capture_receipt(
    project_root: Path,
    spec: dict[str, Any],
) -> dict[str, Any]:
    receipt_spec = spec.get("evidence_receipt")
    if not isinstance(receipt_spec, dict):
        raise TypeError("missing evidence_receipt")
    receipt = _load_pinned_json(project_root, receipt_spec, "official capture receipt")
    pages = receipt.get("pages")
    if not isinstance(pages, list):
        raise TypeError("official capture page records are absent")
    by_ref = {
        page.get("ref"): page
        for page in pages
        if isinstance(page, dict) and isinstance(page.get("ref"), str)
    }
    for candidate in spec["candidates"]:
        page = by_ref.get(candidate["notebook_ref"])
        if page is None:
            raise ValueError(f"candidate page record absent: {candidate['sequence']}")
        if (
            page.get("bytes") != candidate["page_capture_bytes"]
            or page.get("sha256") != candidate["page_capture_sha256"]
        ):
            raise ValueError(f"cutoff page receipt mismatch: {candidate['sequence']}")
        if page.get("body_archive_status") != (
            "TIMESTAMPED_CAPTURE_ATTESTATION_BODY_NOT_ARCHIVED"
        ):
            raise ValueError(f"cutoff page archive boundary mismatch: {candidate['sequence']}")
        capture = page.get("tracked_live_capture")
        if not isinstance(capture, dict):
            raise TypeError(f"tracked live page capture absent: {candidate['sequence']}")
        capture_payload = _read_pinned(
            project_root / capture["path"],
            capture["sha256"],
            f"tracked live page capture {candidate['sequence']}",
        )
        if len(capture_payload) != capture.get("bytes"):
            raise ValueError(f"tracked page byte count mismatch: {candidate['sequence']}")
        capture_text = capture_payload.decode("utf-8")
        required_markers = (
            candidate["notebook_url"],
            "Apache 2.0",
            "http://www.apache.org/licenses/LICENSE-2.0",
        )
        if any(marker not in capture_text for marker in required_markers):
            raise ValueError(f"tracked page license evidence mismatch: {candidate['sequence']}")

        if candidate["sequence"] == "Kag_01":
            score_evidence = page.get("live_remote_score_evidence")
            expected_score_evidence = {
                "status": "LIVE_REMOTE_PAGE_SCORE_V16_NOT_LOCAL_REPRODUCTION",
                "score": 3097.4,
                "version": 16,
                "script_version_id": 341040786,
                "claim_gate": "PENDING_INDEPENDENT_AUDITOR_CONFIRMATION",
            }
            if score_evidence != expected_score_evidence:
                raise ValueError("Tetsu live remote score evidence mismatch")
            if "3097.4 V16" not in capture_text or (
                "scriptVersionId=341040786" not in capture_text
            ):
                raise ValueError("Tetsu live remote score markers mismatch")
        elif "2957.6 V2" not in capture_text:
            raise ValueError("Kaito live remote score marker mismatch")
    return receipt_spec


def _relative_or_absolute(path: Path, project_root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _git(
    project_root: Path,
    *arguments: str,
    text: bool = True,
) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        ["git", "-C", str(project_root), *arguments],
        check=True,
        capture_output=True,
        encoding="utf-8" if text else None,
        text=text,
    )


def _final_freeze_input_records(
    project_root: Path,
    spec_path: Path,
    commit: str,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in _release_input_paths(project_root, spec_path):
        try:
            relative = path.resolve().relative_to(project_root.resolve()).as_posix()
        except ValueError as exc:
            raise ValueError(f"final freeze input is outside the repository: {path}") from exc
        payload = path.read_bytes()
        try:
            blob = _git(project_root, "show", f"{commit}:{relative}", text=False).stdout
        except subprocess.CalledProcessError as exc:
            raise ValueError(f"final freeze input is absent from commit: {relative}") from exc
        if blob != payload:
            raise ValueError(f"final freeze input differs from commit: {relative}")
        records.append(
            {
                "bytes": len(payload),
                "path": relative,
                "sha256": sha256(payload),
            }
        )
    return records


def _worktree_binding(
    project_root: Path,
    spec_path: Path,
    final_freeze_commit: str | None = None,
) -> dict[str, Any]:
    builder_path = Path(__file__).resolve()
    if final_freeze_commit is not None:
        if not FULL_GIT_COMMIT.fullmatch(final_freeze_commit):
            raise ValueError("final freeze commit must be exact lowercase 40-hex")
        head = _git(project_root, "rev-parse", "HEAD").stdout.strip()
        if head != final_freeze_commit:
            raise ValueError(f"final freeze commit is stale: {final_freeze_commit} != {head}")
        tracked_status = _git(
            project_root,
            "status",
            "--short",
            "--untracked-files=no",
        ).stdout
        if tracked_status:
            raise ValueError("tracked worktree must be clean for final freeze")
        inputs = _final_freeze_input_records(project_root, spec_path, final_freeze_commit)
        return {
            "binding": "FINAL_GIT_FREEZE_PINNED",
            "status": FINAL_FREEZE_PASS,
            "git_head": {
                "commit": final_freeze_commit,
                "claim": "ALL_TRACKED_RELEASE_INPUTS_BYTE_EXACT_AT_COMMIT",
            },
            "tracked_status": "CLEAN",
            "inputs": inputs,
            "builder": {
                "path": _relative_or_absolute(builder_path, project_root),
                "sha256": sha256(builder_path.read_bytes()),
            },
            "spec": {
                "path": _relative_or_absolute(spec_path, project_root),
                "sha256": sha256(spec_path.read_bytes()),
            },
        }
    return {
        "binding": "WORKTREE_PINNED",
        "status": FINAL_FREEZE_PENDING,
        "git_head": {
            "commit": FINAL_FREEZE_PENDING,
            "claim": "NO_COMMIT_CONTAINMENT_CLAIM_LOCAL_BUILD_ONLY",
        },
        "builder": {
            "path": _relative_or_absolute(builder_path, project_root),
            "sha256": sha256(builder_path.read_bytes()),
        },
        "spec": {
            "path": _relative_or_absolute(spec_path, project_root),
            "sha256": sha256(spec_path.read_bytes()),
        },
    }


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _release_input_paths(project_root: Path, spec_path: Path) -> tuple[Path, ...]:
    spec = load_spec(spec_path)
    paths = {Path(__file__).resolve(), spec_path.resolve()}

    def add_project_path(relative: Any) -> None:
        if isinstance(relative, str):
            paths.add((project_root / relative).resolve())

    for key in (
        "license",
        "tetsu_ip_verdict",
        "evidence_receipt",
        "source_snapshot_receipt",
        "raw_source_archive",
    ):
        pin = spec.get(key)
        if isinstance(pin, dict):
            add_project_path(pin.get("source_path") or pin.get("path"))

    prerequisites = spec.get("candidate_evaluation_prerequisites")
    if isinstance(prerequisites, dict):
        for key in ("candidate_plan", "candidate_gate", "candidate_manifest"):
            pin = prerequisites.get(key)
            if isinstance(pin, dict):
                add_project_path(pin.get("path"))
        development = prerequisites.get("development_results")
        if isinstance(development, dict):
            lifecycle_pin = development.get("lifecycle")
            if isinstance(lifecycle_pin, dict):
                add_project_path(lifecycle_pin.get("path"))
            slots = development.get("slots")
            if isinstance(slots, dict):
                for slot in slots.values():
                    if not isinstance(slot, dict):
                        continue
                    manifest_pin = slot.get("evidence_manifest")
                    if not isinstance(manifest_pin, dict):
                        continue
                    add_project_path(manifest_pin.get("path"))
                    manifest = _load_pinned_json(
                        project_root,
                        manifest_pin,
                        "development evidence manifest",
                    )
                    files = manifest.get("files")
                    if isinstance(files, list):
                        for record in files:
                            if isinstance(record, dict):
                                add_project_path(record.get("path"))

    release_tooling = spec.get("release_tooling")
    if isinstance(release_tooling, dict):
        for key in ("builder", "tests", "postrun_validator"):
            pin = release_tooling.get(key)
            if isinstance(pin, dict):
                add_project_path(pin.get("path"))

    candidates = spec.get("candidates")
    if isinstance(candidates, list):
        for candidate in candidates:
            if isinstance(candidate, dict):
                add_project_path(candidate.get("source_path"))
                add_project_path(candidate.get("attribution_path"))

    fallback = spec.get("fallback")
    if isinstance(fallback, dict):
        add_project_path(fallback.get("source_path"))

    raw_archive = spec.get("raw_source_archive")
    if isinstance(raw_archive, dict):
        receipt = _load_pinned_json(project_root, raw_archive, "raw source archive receipt")
        records = receipt.get("notebooks")
        if isinstance(records, list):
            for record in records:
                if isinstance(record, dict):
                    add_project_path(record.get("path"))
                    response_record = record.get("getkernel_response")
                    if isinstance(response_record, dict):
                        add_project_path(response_record.get("path"))

    evidence = spec.get("evidence_receipt")
    if isinstance(evidence, dict):
        receipt = _load_pinned_json(project_root, evidence, "official capture receipt")
        pages = receipt.get("pages")
        if isinstance(pages, list):
            for page in pages:
                if isinstance(page, dict):
                    capture = page.get("tracked_live_capture")
                    if isinstance(capture, dict):
                        add_project_path(capture.get("path"))
    return tuple(sorted(paths, key=lambda path: path.as_posix()))


def _git_metadata_paths(project_root: Path) -> tuple[Path, ...]:
    paths = {(project_root / ".git").resolve()}
    for argument in ("--git-dir", "--git-common-dir"):
        completed = subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", argument],
            check=True,
            capture_output=True,
            encoding="utf-8",
            text=True,
        )
        raw_path = Path(completed.stdout.strip())
        if not raw_path.is_absolute():
            raw_path = project_root / raw_path
        paths.add(raw_path.resolve())
    return tuple(sorted(paths, key=lambda path: path.as_posix()))


def _validate_output_root(project_root: Path, output_root: Path, spec_path: Path) -> None:
    if output_root == project_root or _path_is_within(project_root, output_root):
        raise ValueError("output root cannot be the project root or its ancestor")
    for git_path in _git_metadata_paths(project_root):
        if (
            output_root == git_path
            or _path_is_within(output_root, git_path)
            or _path_is_within(git_path, output_root)
        ):
            raise ValueError("output root overlaps Git metadata")
    for input_path in _release_input_paths(project_root, spec_path):
        if output_root == input_path or _path_is_within(input_path, output_root):
            raise ValueError(f"output root contains frozen release input: {input_path}")
    if _path_is_within(output_root, project_root):
        owned_local_build = Path(__file__).resolve().with_name("local_build")
        if output_root != owned_local_build and not _path_is_within(
            output_root, owned_local_build
        ):
            raise ValueError(
                "output root inside project must be the owned 07_release/local_build subtree"
            )
    if output_root.exists() and not output_root.is_dir():
        raise ValueError("output root must be a directory")


def _validate_existing_output_ownership(
    output_root: Path,
    spec: dict[str, Any],
    final_freeze_commit: str | None,
) -> None:
    if not output_root.exists():
        return
    if not output_root.is_dir():
        raise ValueError("output root must be a directory")
    if next(output_root.iterdir(), None) is None:
        return

    manifest_path = output_root / "release_manifest.json"
    if not manifest_path.is_file():
        raise ValueError("nonempty output root is not an owned release build")
    try:
        payload = manifest_path.read_bytes()
        manifest = json.loads(payload)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("existing release ownership manifest is invalid") from exc
    if not isinstance(manifest, dict) or canonical_json(manifest) != payload:
        raise ValueError("existing release ownership manifest is not canonical")
    if (
        manifest.get("schema_version") != 1
        or manifest.get("authorization") != "LOCAL_BUILD_ONLY_EXTERNAL_ACTIONS_HOLD"
        or manifest.get("status") != "LOCAL_PACKAGE_BUILT_EXTERNAL_ACTIONS_HOLD"
        or manifest.get("external_action_performed") is not False
    ):
        raise ValueError("existing release ownership manifest marker mismatch")
    candidates = manifest.get("candidates")
    expected = [
        (candidate["sequence"], candidate["artifact_name"])
        for candidate in spec["candidates"]
    ]
    if not isinstance(candidates, list) or [
        (
            candidate.get("sequence"),
            Path(candidate.get("artifact", {}).get("path", "")).name
            if isinstance(candidate, dict)
            and isinstance(candidate.get("artifact"), dict)
            else None,
        )
        for candidate in candidates
    ] != expected:
        raise ValueError("existing release ownership candidate set mismatch")
    binding = manifest.get("worktree_binding")
    if isinstance(binding, dict) and binding.get("status") == FINAL_FREEZE_PASS:
        existing_commit = binding.get("git_head", {}).get("commit")
        if final_freeze_commit is None:
            raise ValueError("cannot overwrite a final-freeze release with a pending build")
        if existing_commit != final_freeze_commit:
            raise ValueError("existing final-freeze release belongs to a different commit")


def build_candidate(
    project_root: Path,
    output_root: Path,
    candidate: dict[str, Any],
    competition: str,
    license_payload: bytes,
    candidate_prerequisites: dict[str, Any],
    raw_source_archive: dict[str, Any],
    worktree_binding: dict[str, Any],
) -> dict[str, Any]:
    source_path = project_root / candidate["source_path"]
    source = _read_pinned(source_path, candidate["source_sha256"], "candidate source")
    compile(source, "main.py", "exec")

    attribution_path = project_root / candidate["attribution_path"]
    attribution = _read_pinned(
        attribution_path,
        candidate["attribution_sha256"],
        "candidate attribution",
    )
    attribution_text = attribution.decode("utf-8")
    missing = [marker for marker in _attribution_markers(candidate) if marker not in attribution_text]
    if missing:
        raise ValueError(f"missing attribution markers for {candidate['sequence']}: {missing}")
    _reject_private_payload_markers(source, f"{candidate['sequence']} main.py")
    _reject_private_payload_markers(license_payload, f"{candidate['sequence']} LICENSE")
    _reject_private_payload_markers(attribution, f"{candidate['sequence']} ATTRIBUTION")

    members = {
        "main.py": source,
        "LICENSE": license_payload,
        "ATTRIBUTION.md": attribution,
    }
    first = deterministic_archive(members)
    second = deterministic_archive(members)
    if first != second:
        raise ValueError("archive rebuild is not deterministic")
    member_hashes = inspect_archive(first, members)

    release_name = candidate["artifact_name"].removesuffix(".tar.gz")
    release_dir = output_root / release_name
    release_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = release_dir / candidate["artifact_name"]
    artifact_path.write_bytes(first)

    artifact_sha256 = sha256(first)
    wrapper = _wrapper_source(
        candidate["artifact_name"], artifact_sha256, first, member_hashes
    )
    compile(wrapper, "save_run_wrapper.py", "exec")
    notebook = build_notebook(candidate, wrapper)
    notebook_name = f"{release_name}.ipynb"
    notebook_path = release_dir / notebook_name
    notebook_payload = canonical_json(notebook)
    notebook_path.write_bytes(notebook_payload)

    metadata = build_metadata(candidate, notebook_name, competition)
    metadata_path = release_dir / "kernel-metadata.json"
    metadata_payload = canonical_json(metadata)
    metadata_path.write_bytes(metadata_payload)

    slot_result = candidate_prerequisites["development_results"]["slots"][
        candidate["sequence"]
    ]
    package_readiness = slot_result["package_readiness"]

    final_freeze_pass = worktree_binding["status"] == FINAL_FREEZE_PASS
    checks = {
        "archive_deterministic_two_builds": "PASS",
        "archive_members_exact": "PASS",
        "attribution_markers": "PASS",
        "full_apache_license": "PASS",
        "main_compile": "PASS",
        "main_exact_source_hash": "PASS",
        "metadata_enable_internet_false": "PASS",
        "metadata_is_private_true": "PASS",
        "notebook_no_network_push_submit_code": "PASS",
        "notebook_payload_matches_archive": "PASS",
        "raw_notebook_extraction_matches_main": "PASS",
        "source_snapshot_commit_contained": (
            "PASS" if final_freeze_pass else FINAL_FREEZE_PENDING
        ),
        "source_snapshot_worktree_hash_pinned": "PASS",
        "targeted_private_material_scan": "PASS",
    }
    prepush = {
        "artifact": {
            "bytes": len(first),
            "member_sha256": member_hashes,
            "members": list(ARCHIVE_MEMBERS),
            "name": candidate["artifact_name"],
            "sha256": artifact_sha256,
        },
        "authorization": "LOCAL_BUILD_ONLY_EXTERNAL_ACTIONS_HOLD",
        "candidate": candidate,
        "candidate_evaluation_prerequisites": candidate_prerequisites,
        "development_result": {
            "evidence_manifest": slot_result["evidence_manifest"],
            "observed_strict_verdict": slot_result["observed_strict_verdict"],
            "package_readiness": package_readiness,
        },
        "checks": checks,
        "competition_submission": "NOT_RUN_NOT_AUTHORIZED",
        "external_action_gate": {
            "status": "HOLD",
            "blocking_prerequisites": [
                "independent_auditor_exact_private_saverun_release",
                *([] if final_freeze_pass else ["final_git_freeze"]),
            ],
        },
        "external_action_performed": False,
        "kaggle_push": "NOT_RUN_NOT_AUTHORIZED",
        "metadata": {
            "path": metadata_path.name,
            "sha256": sha256(metadata_payload),
        },
        "notebook": {
            "path": notebook_path.name,
            "sha256": sha256(notebook_payload),
        },
        "package_readiness": package_readiness,
        "pending_external_checks": [
            "obtain independent-auditor exact per-slot private SaveRun release PASS",
            *(
                []
                if final_freeze_pass
                else [
                    "freeze final Git commit and rebuild this prepush receipt against that exact HEAD"
                ]
            ),
            "confirm kernel slug is still unused immediately before any authorized push",
            "after an authorized private Save & Run, download and compare the output archive hash",
        ],
        "publication": "NOT_RUN_NOT_AUTHORIZED",
        "raw_source_archive": raw_source_archive,
        "schema_version": 1,
        "status": "LOCAL_PACKAGE_BUILT_EXTERNAL_ACTIONS_HOLD",
        "worktree_binding": worktree_binding,
    }
    if candidate["sequence"] == "Kag_02":
        prepush["non_promotion_boundary"] = {
            "label": (
                "EXPLORATORY_PACKAGE_GATE_PASS_NON_PROMOTION_AUDITOR_RELEASE_PENDING"
            ),
            "observed_exploratory_verdict": "NOT_READY",
            "required_future_release_label": (
                "EXPLORATORY_PRIVATE_SAVERUN_READY_NON_PROMOTION"
            ),
            "strict_development_verdict": "NO_GO",
            "prohibited_claims": slot_result["prohibited_claims"],
        }
    prepush_path = release_dir / "prepush.json"
    prepush_payload = canonical_json(prepush)
    for label, payload in (
        ("archive", first),
        ("notebook", notebook_payload),
        ("metadata", metadata_payload),
        ("prepush", prepush_payload),
    ):
        _reject_private_payload_markers(payload, f"{candidate['sequence']} {label}")
    prepush_path.write_bytes(prepush_payload)

    return {
        "artifact": {
            "bytes": len(first),
            "path": artifact_path.relative_to(output_root).as_posix(),
            "sha256": artifact_sha256,
        },
        "attribution": {
            "path": attribution_path.relative_to(project_root).as_posix(),
            "sha256": sha256(attribution),
        },
        "kernel_id": candidate["kernel_id"],
        "license_status": candidate["license_status"],
        "member_sha256": member_hashes,
        "metadata": {
            "path": metadata_path.relative_to(output_root).as_posix(),
            "sha256": sha256(metadata_payload),
        },
        "notebook": {
            "path": notebook_path.relative_to(output_root).as_posix(),
            "sha256": sha256(notebook_payload),
        },
        "prepush": {
            "path": prepush_path.relative_to(output_root).as_posix(),
            "sha256": sha256(prepush_payload),
        },
        "sequence": candidate["sequence"],
        "source_sha256": candidate["source_sha256"],
        "package_readiness": package_readiness,
        "status": "LOCAL_PACKAGE_BUILT_EXTERNAL_ACTIONS_HOLD",
    }


def _build_all_into(
    project_root: Path,
    output_root: Path,
    spec_path: Path,
    final_freeze_commit: str | None = None,
) -> dict[str, Any]:
    spec = load_spec(spec_path)
    candidate_prerequisites = _validate_candidate_prerequisites(project_root, spec)
    raw_source_archive = _validate_raw_source_archive(project_root, spec)
    evidence_receipt = _validate_official_capture_receipt(project_root, spec)
    worktree_binding = _worktree_binding(project_root, spec_path, final_freeze_commit)
    license_spec = spec["license"]
    license_payload = _read_pinned(
        project_root / license_spec["source_path"],
        license_spec["source_sha256"],
        "Apache license",
    )
    _read_pinned(
        project_root / spec["tetsu_ip_verdict"]["path"],
        spec["tetsu_ip_verdict"]["sha256"],
        "Tetsu IP verdict",
    )
    _read_pinned(
        project_root / spec["source_snapshot_receipt"]["path"],
        spec["source_snapshot_receipt"]["sha256"],
        "source snapshot receipt",
    )
    results = [
        build_candidate(
            project_root,
            output_root,
            candidate,
            spec["competition"],
            license_payload,
            candidate_prerequisites,
            raw_source_archive,
            worktree_binding,
        )
        for candidate in spec["candidates"]
    ]
    if [result["sequence"] for result in results] != ["Kag_01", "Kag_02"]:
        raise ValueError("release candidates must be exactly Kag_01 then Kag_02")
    if results[0]["artifact"]["sha256"] == results[1]["artifact"]["sha256"]:
        raise ValueError("Kag_01 and Kag_02 archives unexpectedly collide")
    manifest = {
        "authorization": "LOCAL_BUILD_ONLY_EXTERNAL_ACTIONS_HOLD",
        "candidate_evaluation_prerequisites": candidate_prerequisites,
        "candidates": results,
        "competition_submission": "NOT_RUN_NOT_AUTHORIZED",
        "evidence_cutoff_utc": spec["evidence_cutoff_utc"],
        "external_action_gate": {
            "status": "HOLD",
            "blocking_prerequisites": [
                "independent_auditor_exact_private_saverun_release",
                *(
                    []
                    if worktree_binding["status"] == FINAL_FREEZE_PASS
                    else ["final_git_freeze"]
                ),
            ],
        },
        "external_action_performed": False,
        "evidence_receipt": evidence_receipt,
        "fallback": spec["fallback"],
        "license": license_spec,
        "publication": "NOT_RUN_NOT_AUTHORIZED",
        "raw_source_archive": raw_source_archive,
        "schema_version": 1,
        "source_snapshot_receipt": spec["source_snapshot_receipt"],
        "status": "LOCAL_PACKAGE_BUILT_EXTERNAL_ACTIONS_HOLD",
        "tetsu_ip_verdict": spec["tetsu_ip_verdict"],
        "worktree_binding": worktree_binding,
    }
    manifest_path = output_root / "release_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_payload = canonical_json(manifest)
    _reject_private_payload_markers(manifest_payload, "release manifest")
    manifest_path.write_bytes(manifest_payload)
    result = {
        **manifest,
        "release_manifest": {
            "path": manifest_path.relative_to(output_root).as_posix(),
            "sha256": sha256(manifest_payload),
        },
    }
    _validate_staged_output(output_root, result)
    return result


def _validate_staged_output(output_root: Path, result: dict[str, Any]) -> None:
    expected_paths = {"release_manifest.json"}
    for candidate in result["candidates"]:
        for key in ("artifact", "notebook", "metadata", "prepush"):
            record = candidate[key]
            relative = record["path"]
            expected_paths.add(relative)
            path = output_root / relative
            if not path.is_file():
                raise ValueError(f"staged release file is missing: {relative}")
            if sha256(path.read_bytes()) != record["sha256"]:
                raise ValueError(f"staged release SHA-256 mismatch: {relative}")

    actual_paths = {
        path.relative_to(output_root).as_posix()
        for path in output_root.rglob("*")
        if path.is_file()
    }
    if actual_paths != expected_paths:
        raise ValueError("staged release contains missing or unexpected files")

    manifest_record = result["release_manifest"]
    manifest_path = output_root / manifest_record["path"]
    manifest_payload = manifest_path.read_bytes()
    if sha256(manifest_payload) != manifest_record["sha256"]:
        raise ValueError("staged release manifest SHA-256 mismatch")
    expected_manifest = {key: value for key, value in result.items() if key != "release_manifest"}
    if manifest_payload != canonical_json(expected_manifest):
        raise ValueError("staged release manifest payload mismatch")


def _transaction_directory(output_root: Path, role: str) -> Path:
    return Path(
        tempfile.mkdtemp(
            prefix=f".{output_root.name}.{role}-",
            dir=output_root.parent,
        )
    )


def _validate_transaction_path(path: Path, output_root: Path) -> None:
    if path.parent.resolve() != output_root.parent.resolve():
        raise ValueError("transaction path escaped the output parent")
    if not path.name.startswith(f".{output_root.name}."):
        raise ValueError("transaction path does not match the output root")


def _remove_transaction_path(path: Path, output_root: Path) -> None:
    _validate_transaction_path(path, output_root)
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def _publish_staged_output(staging_root: Path, output_root: Path) -> None:
    _validate_transaction_path(staging_root, output_root)
    backup_root: Path | None = None
    prior_moved = False
    if output_root.exists() or output_root.is_symlink():
        backup_root = _transaction_directory(output_root, "backup")
        backup_root.rmdir()
        os.replace(output_root, backup_root)
        prior_moved = True
    try:
        os.replace(staging_root, output_root)
    except BaseException:
        if prior_moved and backup_root is not None and backup_root.exists():
            if output_root.exists() or output_root.is_symlink():
                raise RuntimeError("publish failed and output root was concurrently recreated")
            os.replace(backup_root, output_root)
        raise
    if backup_root is not None and backup_root.exists():
        try:
            _remove_transaction_path(backup_root, output_root)
        except OSError as exc:
            warnings.warn(
                f"published release but could not remove retained backup {backup_root}: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )


def build_all(
    project_root: Path,
    output_root: Path,
    spec_path: Path | None = None,
    final_freeze_commit: str | None = None,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    requested_output_root = Path(os.path.abspath(output_root))
    if requested_output_root.is_symlink():
        raise ValueError("output root cannot be a symbolic link")
    output_root = requested_output_root.resolve()
    spec_path = (spec_path or Path(__file__).with_name("release_spec.json")).resolve()
    if not output_root.name:
        raise ValueError("output root must have a directory name")
    _validate_output_root(project_root, output_root, spec_path)
    _validate_existing_output_ownership(
        output_root,
        load_spec(spec_path),
        final_freeze_commit,
    )
    output_root.parent.mkdir(parents=True, exist_ok=True)
    staging_root = _transaction_directory(output_root, "staging")
    try:
        result = _build_all_into(
            project_root,
            staging_root,
            spec_path,
            final_freeze_commit,
        )
        _publish_staged_output(staging_root, output_root)
    except BaseException:
        if staging_root.exists() or staging_root.is_symlink():
            _remove_transaction_path(staging_root, output_root)
        raise
    return result


def verify_release_build(
    project_root: Path,
    output_root: Path,
    final_freeze_commit: str,
    spec_path: Path | None = None,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    output_root = output_root.resolve()
    spec_path = (spec_path or Path(__file__).with_name("release_spec.json")).resolve()
    manifest_path = output_root / "release_manifest.json"
    manifest_payload = manifest_path.read_bytes()
    manifest = json.loads(manifest_payload)
    if canonical_json(manifest) != manifest_payload:
        raise ValueError("release manifest is not canonical")
    expected_binding = _worktree_binding(project_root, spec_path, final_freeze_commit)
    if manifest.get("worktree_binding") != expected_binding:
        raise ValueError("release manifest final freeze binding is stale")
    result = {
        **manifest,
        "release_manifest": {
            "path": "release_manifest.json",
            "sha256": sha256(manifest_payload),
        },
    }
    _validate_staged_output(output_root, result)
    for candidate in manifest["candidates"]:
        prepush_path = output_root / candidate["prepush"]["path"]
        prepush = json.loads(prepush_path.read_bytes())
        if prepush.get("worktree_binding") != expected_binding:
            raise ValueError(
                f"candidate prepush final freeze binding is stale: {candidate['sequence']}"
            )
    with tempfile.TemporaryDirectory(
        prefix=".campaign-3000-release-verify-",
        dir=output_root.parent,
    ) as temporary:
        rebuilt_root = Path(temporary)
        rebuilt_result = _build_all_into(
            project_root,
            rebuilt_root,
            spec_path,
            final_freeze_commit,
        )
        _validate_staged_output(rebuilt_root, rebuilt_result)
        actual_files = {
            path.relative_to(output_root).as_posix(): path.read_bytes()
            for path in sorted(output_root.rglob("*"))
            if path.is_file()
        }
        rebuilt_files = {
            path.relative_to(rebuilt_root).as_posix(): path.read_bytes()
            for path in sorted(rebuilt_root.rglob("*"))
            if path.is_file()
        }
        if actual_files != rebuilt_files:
            raise ValueError("release build differs from deterministic rebuild")
    return result


def main() -> None:
    project_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Build local-only Kag_01/Kag_02 payloads")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(__file__).with_name("local_build"),
    )
    parser.add_argument(
        "--spec",
        type=Path,
        default=Path(__file__).with_name("release_spec.json"),
    )
    parser.add_argument("--final-freeze-commit")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    output_root = args.output_root.resolve()
    if args.verify_only:
        if args.final_freeze_commit is None:
            parser.error("--verify-only requires --final-freeze-commit")
        result = verify_release_build(
            project_root,
            output_root,
            args.final_freeze_commit,
            args.spec.resolve(),
        )
    else:
        result = build_all(
            project_root,
            output_root,
            args.spec.resolve(),
            args.final_freeze_commit,
        )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
