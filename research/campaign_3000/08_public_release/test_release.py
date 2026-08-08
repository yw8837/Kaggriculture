from __future__ import annotations

import json
import runpy
import tarfile
from pathlib import Path

import build_release as release


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_public_source_is_exact_audited_g1_and_compiles() -> None:
    canonical = release.read_expected(
        release.CANONICAL_SOURCE,
        release.EXPECTED_SOURCE_SHA256,
    )
    public = release.read_expected(release.PUBLIC_SOURCE, release.EXPECTED_SOURCE_SHA256)
    assert public == canonical
    compile(public, "main.py", "exec")


def test_archive_is_deterministic_root_main_only_and_exact() -> None:
    source = release.PUBLIC_SOURCE.read_bytes()
    assert release.deterministic_archive(source) == release.deterministic_archive(source)
    assert release.ARCHIVE_PATH.read_bytes() == release.deterministic_archive(source)
    with tarfile.open(release.ARCHIVE_PATH, "r:gz") as archive:
        assert archive.getnames() == ["main.py"]
        member = archive.getmember("main.py")
        assert member.mtime == 0
        assert member.mode == 0o644
        assert member.uid == member.gid == 0
        assert member.uname == member.gname == ""
        extracted = archive.extractfile(member)
        assert extracted is not None
        assert extracted.read() == source


def test_notebook_is_output_free_readable_and_byte_exact(monkeypatch, tmp_path: Path) -> None:
    notebook = load_json(release.NOTEBOOK_PATH)
    metadata = load_json(release.METADATA_PATH)
    expected_ids = [
        "overview",
        "plan-plus-guardrail",
        "agent-anatomy",
        "provenance-and-license",
        "engine-version-lesson",
        "audited-agent-source",
        "compile-and-guard-probe",
        "evaluation-blueprint",
        "next-experiments",
        "deterministic-package",
        "claims-and-limitations",
        "license-and-notice",
    ]
    assert [cell["id"] for cell in notebook["cells"]] == expected_ids
    assert all(not cell.get("outputs") for cell in notebook["cells"])
    source_cell = notebook["cells"][5]
    rendered = "".join(source_cell["source"])
    assert rendered.startswith("%%writefile main.py\n")
    assert rendered.removeprefix("%%writefile main.py\n").encode() == release.PUBLIC_SOURCE.read_bytes()
    assert notebook["cells"][6]["cell_type"] == "code"
    assert "compile(payload, \"main.py\", \"exec\")" in "".join(notebook["cells"][6]["source"])
    notebook_text = "\n".join("".join(cell["source"]) for cell in notebook["cells"])
    assert "kaggle-environments==1.32.6" in notebook_text
    assert "lost all 32 local games" in notebook_text
    assert "lost 32/32" in notebook_text
    assert "Expected Kaggle rating | **unknown; no claim made**" in notebook_text
    assert release.EXISTING_BASELINE_URL in notebook_text
    assert metadata["is_private"] is False
    assert metadata["enable_internet"] is False
    assert metadata["competition_sources"] == ["kaggriculture"]
    archive_hash = release.sha256(release.ARCHIVE_PATH.read_bytes())
    rebuilt = release.build_notebook(
        release.PUBLIC_SOURCE.read_bytes(),
        archive_hash,
        release.PUBLIC_LICENSE.read_text(encoding="utf-8"),
        (release.RELEASE_ROOT / "NOTICE.md").read_text(encoding="utf-8"),
    )
    assert release.json_bytes(rebuilt) == release.NOTEBOOK_PATH.read_bytes()
    assert release.PUBLIC_LICENSE.read_text(encoding="utf-8").strip() in notebook_text
    assert "The upstream trajectory is not presented as independently authored strategy" in notebook_text
    (tmp_path / "main.py").write_bytes(release.PUBLIC_SOURCE.read_bytes())
    smoke_path = tmp_path / "notebook_smoke.py"
    smoke_path.write_text("".join(notebook["cells"][6]["source"]), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    runpy.run_path(smoke_path)


def test_default_build_is_self_contained(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(release, "CANONICAL_SOURCE", tmp_path / "missing-source.py")
    monkeypatch.setattr(release, "CANONICAL_LICENSE", tmp_path / "missing-license")
    monkeypatch.setattr(release, "CANONICAL_ENGINE_SUMMARY", tmp_path / "missing-summary.json")
    monkeypatch.setattr(
        release,
        "CANONICAL_ENGINE_COMPARISON",
        tmp_path / "missing-comparison.json",
    )
    monkeypatch.setattr(release, "CANONICAL_ENGINE_CONFIG", tmp_path / "missing-config.json")
    monkeypatch.setattr(
        release,
        "CANONICAL_PRIVATE_RELEASE_MANIFEST",
        tmp_path / "missing-private-release.json",
    )
    monkeypatch.setattr(
        release,
        "CANONICAL_PRIVATE_RELEASE_SPEC",
        tmp_path / "missing-private-spec.json",
    )
    manifest = release.build()
    assert manifest["public_source"]["sha256"] == release.EXPECTED_SOURCE_SHA256
    assert manifest["status"] == "LOCAL_PUBLIC_RELEASE_DRAFT_NO_EXTERNAL_ACTION"


def test_manifest_binds_exact_private_separation_without_score_claim() -> None:
    manifest = load_json(release.MANIFEST_PATH)
    separation = manifest["strength_separation"]
    assert separation["status"] == "PASS_EXACT_LOCAL_HEAD_TO_HEAD_NON_PROMOTION"
    assert separation["Kag_01"]["designated_source_sha256"] == release.KAG_01_SOURCE_SHA256
    assert separation["Kag_02"]["designated_source_sha256"] == release.KAG_02_SOURCE_SHA256
    assert separation["Kag_01"]["public_losses"] == 16
    assert separation["Kag_02"]["public_losses"] == 16
    assert separation["Kag_01"]["local_archive_sha256"] == release.KAG_01_ARCHIVE_SHA256
    assert separation["Kag_02"]["local_archive_sha256"] == release.KAG_02_ARCHIVE_SHA256
    assert separation["Kag_01"]["local_notebook_sha256"] == release.KAG_01_NOTEBOOK_SHA256
    assert separation["Kag_02"]["local_notebook_sha256"] == release.KAG_02_NOTEBOOK_SHA256
    assert separation["Kag_01"]["local_prepush_sha256"] == release.KAG_01_PREPUSH_SHA256
    assert separation["Kag_02"]["local_prepush_sha256"] == release.KAG_02_PREPUSH_SHA256
    assert separation["five_public_agent_screen"]["public_source_losses"] == 80
    claims = manifest["score_claim_contract"]
    assert claims["score_claim_for_exact_public_source"] is None
    assert claims["expected_public_rating"] == "UNKNOWN"
    assert claims["historical_remote_evidence"]["may_be_claimed_for_this_release"] is False
    assert claims["historical_remote_evidence"]["upload_byte_identity"].startswith("UNVERIFIED")
    assert manifest["code_exclusion"]["allowlisted_agent_source_sha256"] == [
        release.EXPECTED_SOURCE_SHA256
    ]


def test_strength_claims_match_original_engine_evidence() -> None:
    summary_path = release.LOCAL_ENGINE_SUMMARY
    comparison_path = release.LOCAL_ENGINE_COMPARISON
    assert release.sha256(summary_path.read_bytes()) == release.ENGINE_SUMMARY_SHA256
    assert release.sha256(comparison_path.read_bytes()) == release.ENGINE_COMPARISON_SHA256
    assert release.sha256(release.LOCAL_ENGINE_CONFIG.read_bytes()) == release.ENGINE_CONFIG_SHA256
    assert (
        release.sha256(release.LOCAL_PRIVATE_RELEASE_MANIFEST.read_bytes())
        == release.PRIVATE_RELEASE_MANIFEST_SHA256
    )
    assert (
        release.sha256(release.LOCAL_PRIVATE_RELEASE_SPEC.read_bytes())
        == release.PRIVATE_RELEASE_SPEC_SHA256
    )
    private_release = load_json(release.LOCAL_PRIVATE_RELEASE_MANIFEST)
    private_candidates = {item["sequence"]: item for item in private_release["candidates"]}
    assert private_candidates["Kag_01"]["artifact"]["sha256"] == release.KAG_01_ARCHIVE_SHA256
    assert private_candidates["Kag_02"]["artifact"]["sha256"] == release.KAG_02_ARCHIVE_SHA256
    assert private_candidates["Kag_01"]["notebook"]["sha256"] == release.KAG_01_NOTEBOOK_SHA256
    assert private_candidates["Kag_02"]["notebook"]["sha256"] == release.KAG_02_NOTEBOOK_SHA256
    assert private_candidates["Kag_01"]["prepush"]["sha256"] == release.KAG_01_PREPUSH_SHA256
    assert private_candidates["Kag_02"]["prepush"]["sha256"] == release.KAG_02_PREPUSH_SHA256
    assert private_release["external_action_performed"] is False
    summary = load_json(summary_path)
    lanes = summary["engine_1.32.6_fa04_g1"]["by_public_agent"]
    assert lanes["tetsu_adaptive"]["wins"] == 16
    assert lanes["tetsu_adaptive"]["losses"] == 0
    assert lanes["kaito_v22_price_impact"]["wins"] == 16
    assert lanes["kaito_v22_price_impact"]["losses"] == 0
    overall = summary["engine_1.32.6_fa04_g1"]["overall"]
    assert (overall["wins"], overall["ties"], overall["losses"]) == (80, 0, 0)
    comparison = load_json(comparison_path)
    assert comparison["summary"]["paired_logical_cells"] == 20
    assert comparison["summary"]["result_changed_excluding_runtime"] == 20
    assert comparison["summary"]["outcome_changed"] == 16


def test_public_copy_has_no_remote_score_private_names_secrets_or_submit_command() -> None:
    public_paths = [
        release.NOTEBOOK_PATH,
        release.METADATA_PATH,
        release.RELEASE_ROOT / "discussion_draft.md",
        release.RELEASE_ROOT / "titles.json",
        release.RELEASE_ROOT / "NOTICE.md",
    ]
    public_text = "\n".join(path.read_text(encoding="utf-8") for path in public_paths)
    for forbidden in (
        "1317.1",
        "Kag_01",
        "Kag_02",
        "KAGGLE_API_TOKEN",
        "KAGGLE_USERNAME",
        "BEGIN PRIVATE KEY",
        "kaggle competitions submit",
    ):
        assert forbidden not in public_text


def test_external_payload_is_disabled_and_forbids_competition_submission() -> None:
    payload = load_json(release.EXTERNAL_PAYLOAD_PATH)
    assert payload["status"] == "DRAFT_ONLY_NOT_EXECUTED"
    assert payload["execution_authorized"] is False
    assert payload["external_calls_performed"] == []
    assert all(action["enabled"] is False for action in payload["actions"])
    discussion_action, code_action = payload["actions"]
    assert discussion_action["sequence"] == 1
    assert discussion_action["kind"] == "kaggle_discussion_create"
    assert discussion_action["new_code_url"].endswith(
        "/yw8837/kaggriculture-fixed-trace-safety-baseline"
    )
    assert discussion_action["link_state_at_publication"] == (
        "EXPECTED_SLUG_PUBLISHED_IN_SEQUENCE_2"
    )
    assert code_action["sequence"] == 2
    assert code_action["kind"] == "kaggle_code_push"
    assert code_action["competition_submission"] is False
    assert code_action["visibility"] == "public"
    assert code_action["command_argv"][:3] == ["kaggle", "kernels", "push"]
    assert code_action["notebook"]["sha256"] == release.sha256(release.NOTEBOOK_PATH.read_bytes())
    assert code_action["metadata"]["sha256"] == release.sha256(release.METADATA_PATH.read_bytes())
    gate = payload["strength_gate"]
    assert gate["Kag_01_local_archive_sha256"] == release.KAG_01_ARCHIVE_SHA256
    assert gate["Kag_02_local_archive_sha256"] == release.KAG_02_ARCHIVE_SHA256
    assert gate["Kag_01_local_notebook_sha256"] == release.KAG_01_NOTEBOOK_SHA256
    assert gate["Kag_02_local_notebook_sha256"] == release.KAG_02_NOTEBOOK_SHA256
    assert gate["Kag_01_prepush_sha256"] == release.KAG_01_PREPUSH_SHA256
    assert gate["Kag_02_prepush_sha256"] == release.KAG_02_PREPUSH_SHA256
    assert "kaggle competitions submit" in payload["forbidden_actions"]
    manifest = load_json(release.MANIFEST_PATH)
    assert manifest["authority"]["publication_order"] == ["discussion", "kaggle_code"]


def test_titles_are_exact_front_loaded_and_score_free() -> None:
    titles = load_json(release.RELEASE_ROOT / "titles.json")
    assert titles["selected"]["kaggle_code"] == release.CODE_TITLE
    assert titles["selected"]["discussion"] == release.DISCUSSION_TITLE
    all_candidates = titles["kaggle_code_shortlist"] + titles["discussion_shortlist"]
    assert all(item["title"].startswith("Kaggriculture") for item in all_candidates)
    assert all(item["score_claim"] is False for item in all_candidates)
    assert sum(item["selected"] for item in titles["kaggle_code_shortlist"]) == 1
    assert sum(item["selected"] for item in titles["discussion_shortlist"]) == 1


def test_sha256sums_covers_and_matches_release_files() -> None:
    records = {}
    for line in release.HASHES_PATH.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        records[relative] = digest
    expected = {
        path.relative_to(release.RELEASE_ROOT).as_posix()
        for path in release.RELEASE_ROOT.rglob("*")
        if path.is_file()
        and path != release.HASHES_PATH
        and "__pycache__" not in path.parts
        and ".pytest_cache" not in path.parts
    }
    assert set(records) == expected
    for relative, expected_hash in records.items():
        assert release.sha256((release.RELEASE_ROOT / relative).read_bytes()) == expected_hash
