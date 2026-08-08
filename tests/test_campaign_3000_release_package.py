from __future__ import annotations

import ast
import base64
import hashlib
import importlib.util
import json
import tarfile
from pathlib import Path
from types import ModuleType

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = PROJECT_ROOT / "research" / "campaign_3000" / "07_release"
BUILDER_PATH = RELEASE_ROOT / "build_release.py"
EXPECTED_ARTIFACTS = (
    "Kag_01 - Tetsu v16 Exact.tar.gz",
    "Kag_02 - Kaito v22 Price Impact.tar.gz",
)
EXPECTED_SOURCE_HASHES = (
    "997E6BFC5234534E246E945BC61C87858EBF997AB85B0A5C9427DD4ED710F1B6",
    "62FB5A5F66F0011092A2B51E3192879BA583D5D815D761F176091C615657147A",
)
EXPECTED_ATTRIBUTION_HASHES = (
    "3685283A43DF0B5352041EA24BC1E531CE706D0F722C22BB1D07DC71F362101F",
    "A13EDD083A33082DD781B7A1EDD75306C868C743E12082CF4623F5B4BF970BD9",
)
LICENSE_SHA256 = "1EB85FC97224598DAD1852B5D6483BBCF0AA8608790DCC657A5A2A761AE9C8C6"
TETSU_VERDICT_SHA256 = (
    "DA8764985D0EFCFC63867DB673E242D82B9D72CFE7495BFCB932A2DD6F0DF721"
)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def load_builder() -> ModuleType:
    spec = importlib.util.spec_from_file_location("campaign_3000_release", BUILDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def builder() -> ModuleType:
    return load_builder()


def file_map(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def write_spec(builder: ModuleType, path: Path, spec: dict) -> None:
    path.write_bytes(builder.canonical_json(spec))


def wrapper_payload(notebook_path: Path) -> tuple[str, bytes]:
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "".join(notebook["cells"][1]["source"])
    tree = ast.parse(source)
    payload_assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "PAYLOAD_B64" for target in node.targets)
    )
    encoded = ast.literal_eval(payload_assignment.value)
    return source, base64.b64decode(encoded)


def test_two_build_roots_are_byte_identical(builder: ModuleType, tmp_path: Path) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first = builder.build_all(PROJECT_ROOT, first_root)
    second = builder.build_all(PROJECT_ROOT, second_root)

    assert file_map(first_root) == file_map(second_root)
    assert first["candidates"] == second["candidates"]
    assert first["release_manifest"]["sha256"] == second["release_manifest"]["sha256"]
    assert tuple(item["artifact"]["path"].split("/")[-1] for item in first["candidates"]) == (
        EXPECTED_ARTIFACTS
    )
    assert first["candidates"][0]["artifact"]["sha256"] != first["candidates"][1][
        "artifact"
    ]["sha256"]


def test_archives_are_exact_licensed_and_attributed(
    builder: ModuleType, tmp_path: Path
) -> None:
    output_root = tmp_path / "build"
    result = builder.build_all(PROJECT_ROOT, output_root)

    for candidate, expected_source_hash in zip(
        result["candidates"], EXPECTED_SOURCE_HASHES, strict=True
    ):
        artifact_path = output_root / candidate["artifact"]["path"]
        assert sha256(artifact_path.read_bytes()) == candidate["artifact"]["sha256"]
        assert artifact_path.name in EXPECTED_ARTIFACTS
        with tarfile.open(artifact_path, mode="r:gz") as archive:
            members = archive.getmembers()
            assert [member.name for member in members] == [
                "main.py",
                "LICENSE",
                "ATTRIBUTION.md",
            ]
            for member in members:
                assert (member.mode, member.mtime, member.uid, member.gid) == (0o644, 0, 0, 0)
                assert (member.uname, member.gname) == ("", "")
            main = archive.extractfile("main.py")
            license_file = archive.extractfile("LICENSE")
            attribution_file = archive.extractfile("ATTRIBUTION.md")
            assert main is not None and sha256(main.read()) == expected_source_hash
            assert license_file is not None and sha256(license_file.read()) == LICENSE_SHA256
            assert attribution_file is not None
            attribution = attribution_file.read().decode("utf-8")
            assert "Apache License 2.0" in attribution
            assert expected_source_hash in attribution


def test_private_wrapper_is_payload_only(builder: ModuleType, tmp_path: Path) -> None:
    output_root = tmp_path / "build"
    result = builder.build_all(PROJECT_ROOT, output_root)

    for candidate in result["candidates"]:
        artifact_path = output_root / candidate["artifact"]["path"]
        notebook_path = output_root / candidate["notebook"]["path"]
        metadata_path = output_root / candidate["metadata"]["path"]
        prepush_path = output_root / candidate["prepush"]["path"]

        source, embedded_payload = wrapper_payload(notebook_path)
        assert embedded_payload == artifact_path.read_bytes()
        assert builder._wrapper_imports(source) == builder.ALLOWED_WRAPPER_IMPORTS
        assert all(
            token not in source
            for token in ("requests", "urllib", "socket", "subprocess", "kernels.push", "submit(")
        )
        assert "assert " not in source
        assert "raise RuntimeError" in source

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert metadata["is_private"] is True
        assert metadata["enable_internet"] is False
        assert metadata["competition_sources"] == ["kaggriculture"]

        prepush = json.loads(prepush_path.read_text(encoding="utf-8"))
        assert prepush["external_action_performed"] is False
        assert prepush["kaggle_push"] == "NOT_RUN_NOT_AUTHORIZED"
        assert prepush["competition_submission"] == "NOT_RUN_NOT_AUTHORIZED"
        assert prepush["publication"] == "NOT_RUN_NOT_AUTHORIZED"
        assert prepush["external_action_gate"]["status"] == "HOLD"
        assert prepush["status"] == "LOCAL_PACKAGE_BUILT_EXTERNAL_ACTIONS_HOLD"
        assert prepush["checks"]["source_snapshot_commit_contained"] == (
            "PENDING_FINAL_GIT_FREEZE"
        )
        assert prepush["worktree_binding"]["binding"] == "WORKTREE_PINNED"
        assert prepush["worktree_binding"]["status"] == "PENDING_FINAL_GIT_FREEZE"

    assert result["external_action_gate"]["status"] == "HOLD"
    assert result["status"] == "LOCAL_PACKAGE_BUILT_EXTERNAL_ACTIONS_HOLD"
    assert result["worktree_binding"]["status"] == "PENDING_FINAL_GIT_FREEZE"


def test_worktree_inputs_and_receipts_are_pinned() -> None:
    spec = json.loads((RELEASE_ROOT / "release_spec.json").read_text(encoding="utf-8"))
    assert sha256((RELEASE_ROOT / "LICENSE").read_bytes()) == LICENSE_SHA256
    assert sha256((RELEASE_ROOT / "TETSU_IP_VERDICT.md").read_bytes()) == (
        TETSU_VERDICT_SHA256
    )

    for candidate, expected_hash, expected_attribution_hash in zip(
        spec["candidates"],
        EXPECTED_SOURCE_HASHES,
        EXPECTED_ATTRIBUTION_HASHES,
        strict=True,
    ):
        snapshot = PROJECT_ROOT / candidate["source_path"]
        assert snapshot.is_file()
        assert sha256(snapshot.read_bytes()) == expected_hash
        attribution = PROJECT_ROOT / candidate["attribution_path"]
        assert candidate["attribution_sha256"] == expected_attribution_hash
        assert sha256(attribution.read_bytes()) == expected_attribution_hash

    for receipt_key in ("evidence_receipt", "source_snapshot_receipt"):
        receipt = spec[receipt_key]
        assert sha256((PROJECT_ROOT / receipt["path"]).read_bytes()) == receipt["sha256"]


def test_raw_notebook_cells_extract_to_exact_main(builder: ModuleType) -> None:
    spec = json.loads((RELEASE_ROOT / "release_spec.json").read_text(encoding="utf-8"))
    archive = spec["raw_source_archive"]
    receipt_path = PROJECT_ROOT / archive["path"]
    assert sha256(receipt_path.read_bytes()) == archive["sha256"]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["status"] == "PASS_EXACT_CURRENT_VERSION_SOURCE_ARCHIVED"
    assert receipt["version_binding"]["status"] == (
        "PASS_CURRENT_VERSION_AND_SOURCE_IN_SAME_OFFICIAL_API_RESPONSE"
    )

    records = {record["ref"]: record for record in receipt["notebooks"]}
    for candidate in spec["candidates"]:
        record = records[candidate["notebook_ref"]]
        raw_path = PROJECT_ROOT / record["path"]
        raw_payload = raw_path.read_bytes()
        assert len(raw_payload) == record["bytes"]
        assert sha256(raw_payload) == candidate["notebook_source_sha256"]
        assert record["current_version_number"] == candidate["notebook_version"]
        response_record = record["getkernel_response"]
        response_payload = (PROJECT_ROOT / response_record["path"]).read_bytes()
        assert len(response_payload) == response_record["bytes"]
        assert sha256(response_payload) == response_record["sha256"]
        response = json.loads(response_payload)
        assert response["metadata"] | {
            "ref": candidate["notebook_ref"],
            "id": candidate["notebook_id"],
            "currentVersionNumber": candidate["notebook_version"],
            "isPrivate": False,
            "competitionDataSources": ["kaggriculture"],
        } == response["metadata"]
        assert response["blob"]["source"].encode("utf-8") == raw_payload
        notebook = json.loads(raw_payload)
        extracted = builder._extract_raw_main(
            notebook,
            candidate["sequence"],
            record["extraction"]["cell_index_zero_based"],
        )
        assert extracted == (PROJECT_ROOT / candidate["source_path"]).read_bytes()


def test_tracked_candidate_pages_bind_license_and_score_boundaries() -> None:
    spec = json.loads((RELEASE_ROOT / "release_spec.json").read_text(encoding="utf-8"))
    receipt_record = spec["evidence_receipt"]
    receipt_payload = (PROJECT_ROOT / receipt_record["path"]).read_bytes()
    assert sha256(receipt_payload) == receipt_record["sha256"]
    pages = {
        page["ref"]: page
        for page in json.loads(receipt_payload)["pages"]
        if "tracked_live_capture" in page
    }

    for candidate in spec["candidates"]:
        page = pages[candidate["notebook_ref"]]
        assert page["body_archive_status"] == (
            "TIMESTAMPED_CAPTURE_ATTESTATION_BODY_NOT_ARCHIVED"
        )
        capture = page["tracked_live_capture"]
        payload = (PROJECT_ROOT / capture["path"]).read_bytes()
        assert len(payload) == capture["bytes"]
        assert sha256(payload) == capture["sha256"]
        text = payload.decode("utf-8")
        assert candidate["notebook_url"] in text
        assert "Apache 2.0" in text

    tetsu = pages[spec["candidates"][0]["notebook_ref"]]
    assert tetsu["live_remote_score_evidence"] == {
        "status": "LIVE_REMOTE_PAGE_SCORE_V16_NOT_LOCAL_REPRODUCTION",
        "score": 3097.4,
        "version": 16,
        "script_version_id": 341040786,
        "claim_gate": "PENDING_INDEPENDENT_AUDITOR_CONFIRMATION",
    }


@pytest.mark.parametrize(
    ("missing_key", "expected_error"),
    (
        ("candidate_gate", "missing candidate prerequisite: candidate_gate"),
        ("development_result", "missing candidate prerequisite: development_result"),
        (
            "independent_auditor_exact_private_saverun_release",
            "missing candidate prerequisite: independent_auditor_exact_private_saverun_release",
        ),
    ),
)
def test_required_candidate_gate_and_audit_omission_are_rejected(
    builder: ModuleType,
    tmp_path: Path,
    missing_key: str,
    expected_error: str,
) -> None:
    spec = json.loads((RELEASE_ROOT / "release_spec.json").read_text(encoding="utf-8"))
    spec["candidate_evaluation_prerequisites"].pop(missing_key)
    spec_path = tmp_path / f"missing-{missing_key}.json"
    write_spec(builder, spec_path, spec)
    output_root = tmp_path / "existing"
    builder.build_all(PROJECT_ROOT, output_root)
    (output_root / "old.bin").write_bytes(b"prior output\x00")
    before = file_map(output_root)

    with pytest.raises((TypeError, ValueError), match=expected_error):
        builder.build_all(PROJECT_ROOT, output_root, spec_path)

    assert file_map(output_root) == before


def test_attribution_hash_mismatch_is_rejected(
    builder: ModuleType,
    tmp_path: Path,
) -> None:
    spec = json.loads((RELEASE_ROOT / "release_spec.json").read_text(encoding="utf-8"))
    spec["candidates"][0]["attribution_sha256"] = "0" * 64
    spec_path = tmp_path / "bad-attribution.json"
    write_spec(builder, spec_path, spec)

    with pytest.raises(ValueError, match="candidate attribution SHA-256 mismatch"):
        builder.build_all(PROJECT_ROOT, tmp_path / "output", spec_path)


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    (
        ("archive_name", "candidate plan archive name mismatch: Kag_01"),
        ("tetsu_verdict", "candidate plan Tetsu verdict mismatch"),
        ("kaito_notebook_ref", "candidate plan Kaito notebook_ref mismatch"),
    ),
)
def test_candidate_plan_semantic_bindings_are_enforced(
    builder: ModuleType,
    tmp_path: Path,
    mutation: str,
    expected_error: str,
) -> None:
    spec = json.loads((RELEASE_ROOT / "release_spec.json").read_text(encoding="utf-8"))
    if mutation == "archive_name":
        spec["candidates"][0]["artifact_name"] = "renamed.tar.gz"
    elif mutation == "tetsu_verdict":
        spec["tetsu_ip_verdict"]["verdict"] = "UNBOUND"
    elif mutation == "kaito_notebook_ref":
        spec["candidates"][1]["notebook_ref"] = "unbound/notebook"
    else:
        raise RuntimeError(f"unsupported test mutation: {mutation}")
    spec_path = tmp_path / f"semantic-{mutation}.json"
    write_spec(builder, spec_path, spec)

    with pytest.raises(ValueError, match=expected_error):
        builder.build_all(PROJECT_ROOT, tmp_path / "output", spec_path)


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    (
        ("slot_status", "candidate plan slot is not CLOSED: Kag_01"),
        (
            "archive_members",
            "candidate plan required archive members mismatch: Kag_01",
        ),
    ),
)
def test_candidate_plan_slot_and_archive_member_gates_are_enforced(
    builder: ModuleType,
    tmp_path: Path,
    mutation: str,
    expected_error: str,
) -> None:
    spec = json.loads((RELEASE_ROOT / "release_spec.json").read_text(encoding="utf-8"))
    prerequisites = spec["candidate_evaluation_prerequisites"]
    plan = json.loads((PROJECT_ROOT / prerequisites["candidate_plan"]["path"]).read_text())
    if mutation == "slot_status":
        plan["candidates"][0]["status"] = "OPEN"
    elif mutation == "archive_members":
        plan["candidates"][0]["license_gate"]["required_archive_members"] = [
            "main.py",
            "LICENSE",
        ]
    else:
        raise RuntimeError(f"unsupported test mutation: {mutation}")
    plan_path = tmp_path / f"plan-{mutation}.json"
    write_spec(builder, plan_path, plan)
    plan_sha = sha256(plan_path.read_bytes())
    prerequisites["candidate_plan"] = {
        "path": plan_path.as_posix(),
        "sha256": plan_sha,
    }

    manifest = json.loads(
        (PROJECT_ROOT / prerequisites["candidate_manifest"]["path"]).read_text()
    )
    manifest["plan_sha256"] = plan_sha
    manifest_path = tmp_path / f"manifest-{mutation}.json"
    write_spec(builder, manifest_path, manifest)
    prerequisites["candidate_manifest"] = {
        "path": manifest_path.as_posix(),
        "sha256": sha256(manifest_path.read_bytes()),
    }
    spec_path = tmp_path / f"spec-{mutation}.json"
    write_spec(builder, spec_path, spec)

    with pytest.raises(ValueError, match=expected_error):
        builder.build_all(PROJECT_ROOT, tmp_path / "output", spec_path)


def test_project_root_and_ancestor_outputs_are_rejected_before_write(
    builder: ModuleType,
) -> None:
    sentinel_path = RELEASE_ROOT / "release_spec.json"
    sentinel = sentinel_path.read_bytes()

    for dangerous_root in (PROJECT_ROOT, PROJECT_ROOT.parent):
        with pytest.raises(
            ValueError,
            match="output root cannot be the project root or its ancestor",
        ):
            builder.build_all(PROJECT_ROOT, dangerous_root)
    assert sentinel_path.read_bytes() == sentinel


@pytest.mark.parametrize(
    ("dangerous_root", "sentinel_path"),
    (
        (
            PROJECT_ROOT / "src",
            PROJECT_ROOT / "src" / "kaggriculture_lab" / "evaluation" / "runner.py",
        ),
        (PROJECT_ROOT / "tests", Path(__file__).resolve()),
        (PROJECT_ROOT / ".git", PROJECT_ROOT / ".git"),
    ),
)
def test_nonowned_project_and_git_outputs_are_rejected_before_write(
    builder: ModuleType,
    dangerous_root: Path,
    sentinel_path: Path,
) -> None:
    sentinel = sentinel_path.read_bytes()

    with pytest.raises(ValueError, match="inside project|Git metadata"):
        builder.build_all(PROJECT_ROOT, dangerous_root)

    assert sentinel_path.read_bytes() == sentinel


@pytest.mark.parametrize(
    "dangerous_root",
    (
        RELEASE_ROOT,
        RELEASE_ROOT / "source",
        RELEASE_ROOT / "evidence" / "raw",
    ),
)
def test_output_roots_containing_frozen_inputs_are_rejected_before_write(
    builder: ModuleType,
    dangerous_root: Path,
) -> None:
    sentinel_path = RELEASE_ROOT / "release_spec.json"
    sentinel = sentinel_path.read_bytes()

    with pytest.raises(ValueError, match="output root contains frozen release input"):
        builder.build_all(PROJECT_ROOT, dangerous_root)

    assert sentinel_path.read_bytes() == sentinel


def test_safe_nested_local_build_roots_do_not_overlap_inputs(builder: ModuleType) -> None:
    spec_path = RELEASE_ROOT / "release_spec.json"
    builder._validate_output_root(PROJECT_ROOT, RELEASE_ROOT / "local_build", spec_path)
    builder._validate_output_root(
        PROJECT_ROOT,
        RELEASE_ROOT / "local_build" / "nested",
        spec_path,
    )


def test_build_all_preserves_prior_output_when_second_candidate_fails(
    builder: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "release"
    builder.build_all(PROJECT_ROOT, output_root)
    (output_root / "prior" / "nested").mkdir(parents=True)
    (output_root / "prior" / "nested" / "old.bin").write_bytes(b"old\x00release\xff")
    (output_root / "sentinel.txt").write_text("unchanged\n", encoding="utf-8")
    before = file_map(output_root)
    original = builder.build_candidate
    completed: list[str] = []

    def fail_second(
        project_root: Path,
        staging_root: Path,
        candidate: dict,
        competition: str,
        license_payload: bytes,
        candidate_prerequisites: dict,
        raw_source_archive: dict,
        worktree_binding: dict,
    ) -> dict:
        if candidate["sequence"] == "Kag_02":
            assert completed == ["Kag_01"]
            first_artifact = staging_root / "Kag_01 - Tetsu v16 Exact" / EXPECTED_ARTIFACTS[0]
            assert first_artifact.is_file()
            raise RuntimeError("injected second candidate failure")
        result = original(
            project_root,
            staging_root,
            candidate,
            competition,
            license_payload,
            candidate_prerequisites,
            raw_source_archive,
            worktree_binding,
        )
        completed.append(candidate["sequence"])
        return result

    monkeypatch.setattr(builder, "build_candidate", fail_second)
    with pytest.raises(RuntimeError, match="injected second candidate failure"):
        builder.build_all(PROJECT_ROOT, output_root)

    assert file_map(output_root) == before
    assert not list(tmp_path.glob(f".{output_root.name}.staging-*"))
    assert not list(tmp_path.glob(f".{output_root.name}.backup-*"))


def test_publish_swap_failure_restores_prior_output_byte_identically(
    builder: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "release"
    builder.build_all(PROJECT_ROOT, output_root)
    (output_root / "sentinel.bin").write_bytes(b"prior release\x00must survive\xff")
    before = file_map(output_root)
    original_replace = builder.os.replace
    calls: list[tuple[Path, Path]] = []

    def fail_staging_publish(source: Path, destination: Path) -> None:
        calls.append((Path(source), Path(destination)))
        if len(calls) == 2:
            raise OSError("injected staging publish failure")
        original_replace(source, destination)

    monkeypatch.setattr(builder.os, "replace", fail_staging_publish)
    with pytest.raises(OSError, match="injected staging publish failure"):
        builder.build_all(PROJECT_ROOT, output_root)

    assert len(calls) == 3
    assert file_map(output_root) == before
    assert not list(tmp_path.glob(f".{output_root.name}.staging-*"))
    assert not list(tmp_path.glob(f".{output_root.name}.backup-*"))


def test_nonempty_nonowned_and_symlink_outputs_are_rejected_without_changes(
    builder: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    nonowned = tmp_path / "nonowned"
    nonowned.mkdir()
    (nonowned / "sentinel.bin").write_bytes(b"unrelated\x00data")
    before = file_map(nonowned)

    with pytest.raises(ValueError, match="not an owned release build"):
        builder.build_all(PROJECT_ROOT, nonowned)
    assert file_map(nonowned) == before

    target = tmp_path / "symlink-target"
    target.mkdir()
    (target / "sentinel.bin").write_bytes(b"symlink target\x00data")
    link = tmp_path / "symlink-output"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        original_is_symlink = builder.Path.is_symlink
        monkeypatch.setattr(
            builder.Path,
            "is_symlink",
            lambda path: path == link or original_is_symlink(path),
        )
    target_before = file_map(target)
    with pytest.raises(ValueError, match="cannot be a symbolic link"):
        builder.build_all(PROJECT_ROOT, link)
    assert file_map(target) == target_before


def test_successful_build_replaces_existing_output_atomically(
    builder: ModuleType,
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "release"
    builder.build_all(PROJECT_ROOT, output_root)
    (output_root / "stale.txt").write_bytes(b"remove only after validation")

    result = builder.build_all(PROJECT_ROOT, output_root)

    assert not (output_root / "stale.txt").exists()
    assert sha256((output_root / "release_manifest.json").read_bytes()) == (
        result["release_manifest"]["sha256"]
    )
    assert not list(tmp_path.glob(f".{output_root.name}.staging-*"))
    assert not list(tmp_path.glob(f".{output_root.name}.backup-*"))
