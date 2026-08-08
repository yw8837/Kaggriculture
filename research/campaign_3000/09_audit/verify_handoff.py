"""Verify the Campaign 3000 independent-auditor handoff without external actions."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
HANDOFF_PATH = Path(__file__).with_name("audit_handoff.json")
PENDING = "PENDING_FREEZE"
HEX40 = re.compile(r"[0-9a-fA-F]{40}\Z")
HEX64 = re.compile(r"[0-9a-fA-F]{64}\Z")


class VerificationError(RuntimeError):
    """Raised when a handoff assertion fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def read_jsonl(path: Path) -> list[Any]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise VerificationError(
                        f"invalid JSONL at {path.relative_to(ROOT)}:{line_number}: {exc}"
                    ) from exc
    return rows


def evidence_index(handoff: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries = handoff["evidence_files"]
    index = {entry["path"]: entry for entry in entries}
    require(len(entries) == len(index), "duplicate path in evidence_files")
    return index


def verify_evidence_files(handoff: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index = evidence_index(handoff)
    for relative, entry in index.items():
        path = ROOT / relative
        require(path.is_file(), f"missing evidence file: {relative}")
        require(HEX64.fullmatch(entry["sha256"]) is not None, f"invalid SHA-256: {relative}")
        require(path.stat().st_size == entry["bytes"], f"byte-count mismatch: {relative}")
        require(sha256(path) == entry["sha256"].upper(), f"SHA-256 mismatch: {relative}")
    print(f"PASS evidence_files={len(index)} exact bytes and SHA-256")
    return index


def verify_declared_children(index: dict[str, dict[str, Any]]) -> None:
    manifest_01_path = "research/campaign_3000/01_internal/evidence_manifest.json"
    manifest_01 = load_json(ROOT / manifest_01_path)
    declared_01 = {entry["path"]: entry for entry in manifest_01["files"]}

    manifest_02_path = "research/campaign_3000/02_public_meta/source_manifest.json"
    manifest_02 = load_json(ROOT / manifest_02_path)
    declared_02 = {
        f"research/campaign_3000/02_public_meta/{entry['path']}": entry
        for entry in manifest_02["entries"]
    }

    manifest_03_path = "research/campaign_3000/03_external/manifest.json"
    manifest_03 = load_json(ROOT / manifest_03_path)
    declared_03 = {
        f"research/campaign_3000/03_external/{entry['path']}": entry
        for entry in manifest_03["files"]
    }

    manifest_06_path = "research/campaign_3000/06_candidates/manifest.json"
    manifest_06 = load_json(ROOT / manifest_06_path)
    declared_06 = {entry["path"]: entry for entry in manifest_06["files"]}

    for manifest_path, declared in (
        (manifest_01_path, declared_01),
        (manifest_02_path, declared_02),
        (manifest_03_path, declared_03),
        (manifest_06_path, declared_06),
    ):
        children = [entry for entry in index.values() if entry["declared_by"] == manifest_path]
        require(children, f"no handoff children declared by {manifest_path}")
        for child in children:
            source_entry = declared.get(child["path"])
            require(source_entry is not None, f"manifest omits {child['path']}")
            require(source_entry["bytes"] == child["bytes"], f"manifest bytes drift: {child['path']}")
            require(
                source_entry["sha256"].upper() == child["sha256"].upper(),
                f"manifest SHA-256 drift: {child['path']}",
            )

    declared_total = 0
    for declared in (declared_01, declared_02, declared_03, declared_06):
        for relative, entry in declared.items():
            path = ROOT / relative
            require(path.is_file(), f"source manifest points to missing file: {relative}")
            require(path.stat().st_size == entry["bytes"],
                    f"source manifest byte-count drift: {relative}")
            require(sha256(path) == entry["sha256"].upper(),
                    f"source manifest SHA-256 drift: {relative}")
            declared_total += 1
    print(f"PASS source_manifest_entries={declared_total} exact bytes and SHA-256")

    for directory in (
        "research/campaign_3000/05_engine_screen",
        "research/campaign_3000/05_engine_screen_ray_c45_addendum",
        "research/campaign_3000/06_candidates",
    ):
        sidecar = (ROOT / directory / "manifest.sha256").read_text(encoding="utf-8").split()
        require(len(sidecar) >= 2 and sidecar[1] == "manifest.json", f"invalid sidecar: {directory}")
        manifest_path = f"{directory}/manifest.json"
        require(sidecar[0].upper() == index[manifest_path]["sha256"], f"sidecar drift: {directory}")

    manifest_05 = load_json(ROOT / "research/campaign_3000/05_engine_screen/manifest.json")
    summary_05 = index["research/campaign_3000/05_engine_screen/summary.json"]
    require(manifest_05["artifact_files"]["summary.json"] == {
        "bytes": summary_05["bytes"],
        "sha256": summary_05["sha256"],
    }, "05 summary does not match its manifest")

    addendum_dir = "research/campaign_3000/05_engine_screen_ray_c45_addendum"
    addendum = load_json(ROOT / addendum_dir / "manifest.json")
    addendum_summary = index[f"{addendum_dir}/summary.json"]
    require(addendum["artifact_files"]["summary.json"] == {
        "bytes": addendum_summary["bytes"],
        "sha256": addendum_summary["sha256"],
    }, "05 addendum summary does not match its manifest")

    sums_path = ROOT / "research/campaign_3000/08_public_release/SHA256SUMS"
    sums = {}
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split(maxsplit=1)
        sums[relative.strip()] = digest.upper()
    public_dir = sums_path.parent
    for relative, digest in sums.items():
        path = public_dir / relative
        require(path.is_file(), f"SHA256SUMS points to missing file: {relative}")
        require(sha256(path) == digest, f"SHA256SUMS file drift: {relative}")
    for relative in (
        "release_manifest.json",
        "external_action_payload.json",
        "artifact/kaggriculture_fixed_trace_safety_baseline.tar.gz",
        "public_source/main.py",
        "discussion_draft.md",
        "kaggle_code_draft/kaggriculture-fixed-trace-safety-baseline.ipynb",
    ):
        full = f"research/campaign_3000/08_public_release/{relative}"
        require(sums[relative] == index[full]["sha256"], f"08 SHA256SUMS drift: {relative}")

    print("PASS source manifests, sidecars, and SHA256SUMS agree with handoff")


def population_by_id(handoff: dict[str, Any], population_id: str) -> dict[str, Any]:
    matches = [item for item in handoff["research_populations"] if item["id"] == population_id]
    require(len(matches) == 1, f"missing or duplicate population: {population_id}")
    return matches[0]


def verify_populations(handoff: dict[str, Any]) -> None:
    internal = ROOT / "research/campaign_3000/01_internal"
    submissions = load_json(internal / "our_submissions.json")
    leaderboard = load_json(internal / "leaderboard_top25.json")
    replay_report = load_json(internal / "replay_integrity_report.json")

    ours = population_by_id(handoff, "our_submissions")
    require(submissions["submission_count"] == 22, "our submission_count is not 22")
    require(len(submissions["submissions"]) == 22, "our submissions array is not 22")
    require(ours["submission_rows"] == 22, "handoff our-submission count drift")
    require(
        len(read_jsonl(internal / "our_episode_inventory.jsonl"))
        == ours["episode_metadata_rows"]
        == 1017,
        "our episode-metadata population drift",
    )

    top25 = population_by_id(handoff, "leaderboard_top25")
    require(len(leaderboard["rows"]) == top25["leaderboard_rows"] == 25, "top-25 row drift")
    require(
        len(read_jsonl(internal / "top25_episode_inventory.jsonl"))
        == top25["episode_metadata_rows"]
        == 4166,
        "top-25 episode-metadata population drift",
    )
    require(len(read_jsonl(internal / "replay_inventory.jsonl")) == 89, "replay inventory drift")
    require(replay_report["raw_replays"]["verified"] == 89, "not all 89 replays verified")
    require(replay_report["raw_replays"]["failed"] == 0, "raw replay failure is nonzero")
    unique = replay_report["selection"]["unique_episodes_by_cohort"]
    require(unique == {"leaderboard_top25": 45, "our_submissions": 44}, "cohort replay drift")

    public_dir = ROOT / "research/campaign_3000/02_public_meta"
    public_counts = {
        "public_code": len(read_jsonl(public_dir / "code_inventory.jsonl")),
        "discussion": len(read_jsonl(public_dir / "discussion_inventory.jsonl")),
        "github": len(read_jsonl(public_dir / "github_inventory.jsonl")),
        "models": len(read_jsonl(public_dir / "model_inventory.jsonl")),
    }
    require(public_counts == {
        "public_code": 155,
        "discussion": 57,
        "github": 256,
        "models": 1,
    }, "public inventory counts drift")
    require(population_by_id(handoff, "public_code")["rows"] == 155, "handoff Code count drift")
    require(population_by_id(handoff, "discussion")["rows"] == 57, "handoff topic count drift")
    require(population_by_id(handoff, "github")["rows"] == 256, "handoff GitHub count drift")
    require(population_by_id(handoff, "models")["search_rows"] == 1, "handoff model count drift")
    require(
        population_by_id(handoff, "models")["population_status"]
        == "UNVERIFIED_NOT_ZERO_CLAIM",
        "model population boundary weakened",
    )
    model_population = population_by_id(handoff, "models")
    model_rows = read_jsonl(public_dir / "model_inventory.jsonl")
    require(model_population["analyzed_rows"] == len(model_rows) == 1,
            "model analyzed-row count drift")
    model = model_rows[0]
    analysis = model["analysis"]
    require(model_population["version_number"] == model["current_version"]["version_number"] == 8,
            "model version drift")
    require(model_population["checkpoint_bytes"] == analysis["checkpoint_bytes"] == 6431,
            "model checkpoint byte drift")
    require(
        model_population["checkpoint_sha256"]
        == analysis["checkpoint_sha256"]
        == "9756ADC933DA10D78ADDA449397A83D923995EF4585500B9814A9030CE3E6A3A",
        "model checkpoint hash drift",
    )
    require(
        model_population["static_disposition"]
        == analysis["decision"]
        == "UNUSABLE_WITH_PUBLISHED_INTERFACE_AND_UNVERIFIED_FOR_KAGGRICULTURE",
        "model design-impact disposition drift",
    )
    require(analysis["published_interface_compatible"] is False
            and analysis["used_in_candidate"] is False,
            "model was incorrectly admitted into a candidate")
    disposition = load_json(public_dir / analysis["detail_path"])
    inventory = load_json(public_dir / "model_v8/file_inventory_v8.json")
    require(disposition["decision"] == analysis["decision"],
            "model disposition evidence drift")
    require(len(inventory["files"]) == model_population["published_file_count"] == 4,
            "model file inventory drift")

    external_dir = ROOT / "research/campaign_3000/03_external"
    source_rows = read_jsonl(external_dir / "source_inventory.jsonl")
    query_rows = read_jsonl(external_dir / "query_log.jsonl")
    external = population_by_id(handoff, "external_corpus")
    require(len(source_rows) == external["retained_sources"] == 35, "external source count drift")
    require(len(query_rows) == external["query_events"] == 28, "external query count drift")
    status_counts: dict[str, int] = {}
    for row in source_rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
    require(status_counts == external["source_status_counts"], "external status counts drift")
    print("PASS populations=22 submissions, top25, Code155, Discussion57, external35")


def verify_current_qa_claims(handoff: dict[str, Any]) -> None:
    qa = handoff["current_qa_claims"]
    require(qa["project_pytest"] == "423 passed", "project QA claim drift")
    require(qa["official_environment_pytest"] == "81 passed", "official QA claim drift")
    require(qa["candidate_focused_pytest"] == "91 passed", "candidate QA claim drift")
    require(qa["release_pytest"] == "28 passed", "release QA claim drift")
    require(qa["public_release_pytest"] == "10 passed", "public QA claim drift")
    require(qa["ruff"] == "All checks passed!", "Ruff QA claim drift")
    require("not a self-authenticating attestation" in qa["claim_boundary"],
            "QA claim boundary weakened")
    print("PASS declared QA claims=423 project, 81 official, 91 candidate, 28 release, 10 public")


def verify_tools_and_skills(handoff: dict[str, Any]) -> None:
    statuses = {entry["name"]: entry["status"] for entry in handoff["tool_and_skill_status"]}
    require(
        statuses["oh-my-claudecode:self-improve"] == "NOT_EXECUTED_MANDATORY_TRUST_GATE",
        "self-improve trust-gate status drift",
    )
    require(statuses["agent-reach"] == "EXECUTED_READ_ONLY_WITH_LIMITS", "Agent-Reach drift")
    require(statuses["context7"] == "EXECUTED_READ_ONLY", "Context7 drift")
    require(
        statuses["insane-search"] == "EXECUTED_ONE_BLOCKED_URL_REPRO_FAILED",
        "Insane Search status drift",
    )

    queries = read_jsonl(ROOT / "research/campaign_3000/03_external/query_log.jsonl")
    by_id = {row["query_id"]: row for row in queries}
    require(by_id["Q001"]["status"] == "OK_WITH_LIMITS", "Agent-Reach doctor status drift")
    require(by_id["Q010"]["status"] == "REPRO_FAILED", "Insane Search status drift")
    require(by_id["Q016"]["route"] == "context7", "Context7 evidence missing")
    require(by_id["Q017"]["route"] == "serena", "Serena evidence missing")

    public_queries = load_json(ROOT / "research/campaign_3000/02_public_meta/query_log.json")
    tools = public_queries["tool_evidence"]
    require(any(row.get("tool") == "serena" and row["status"] == "USED" for row in tools),
            "public-meta Serena use missing")
    require(any(row.get("tool") == "insane-search" and row["status"] == "NOT_INVOKED"
                for row in tools), "public-meta Insane Search boundary missing")

    autoresearch = load_json(
        ROOT / "research/campaign_3000/04_synthesis/autoresearch_portfolio_result.json"
    )
    require(autoresearch["skill"] == "oh-my-claudecode:autoresearch", "autoresearch claim drift")
    require(
        autoresearch["claim_boundary"].startswith("Selection readiness only"),
        "autoresearch claim boundary drift",
    )
    tool_report = (
        ROOT / "research/campaign_3000/03_external/tool_and_coverage_evidence.md"
    ).read_text(encoding="utf-8")
    require("self-improve" in tool_report and "실행하지 않았다" in tool_report,
            "source report does not record self-improve non-execution")
    print("PASS named tool and skill statuses, including self-improve trust gate")


def verify_candidates_and_seeds(handoff: dict[str, Any]) -> None:
    candidate_dir = ROOT / "research/campaign_3000/06_candidates"
    plan = load_json(candidate_dir / "candidate_plan.json")
    selection = load_json(candidate_dir / "selection_evidence.json")
    scan = load_json(candidate_dir / "seed_collision_scan.json")
    lifecycle = load_json(candidate_dir / "lifecycle.json")
    require(plan["status"] == "CLOSED", "candidate plan is not CLOSED")
    require(plan["authority"]["fresh_seed_execution"] == "FORBIDDEN",
            "candidate plan permits fresh seed execution")
    require(plan["authority"]["kaggle_save_run_in_this_freeze"] == "FORBIDDEN",
            "candidate plan permits Save & Run")
    require(plan["authority"]["competition_submission"] == "FORBIDDEN",
            "candidate plan permits competition submission")
    require(plan["authority"]["publication"] == "FORBIDDEN",
            "candidate plan permits publication")
    require(lifecycle["state"] == "CLOSED", "candidate lifecycle is not CLOSED")
    require(lifecycle["execution_commit"] == "PENDING", "lifecycle execution commit is open")
    require(lifecycle["fresh_games_executed"] == 0, "lifecycle reports fresh games")
    require(lifecycle["external_actions"] == "HOLD", "lifecycle permits external actions")
    require(
        lifecycle["authority_receipt"]["sha256"] == "PENDING",
        "lifecycle unexpectedly has an authority receipt",
    )
    require(
        lifecycle["auditor_open_delivery"]["sha256"] == "PENDING",
        "lifecycle unexpectedly has an auditor OPEN delivery",
    )
    for slot in ("Kag_01", "Kag_02"):
        phases = lifecycle["phases"][slot]
        require(phases == {
            "development": "CLOSED",
            "confirmation": "HOLD",
            "robustness": "HOLD",
        }, f"lifecycle phase drift: {slot}")
    recorded_lifecycle = handoff["seed_freeze"]["lifecycle"]
    require(recorded_lifecycle["sha256"] == sha256(candidate_dir / "lifecycle.json"),
            "handoff lifecycle SHA-256 drift")
    require(recorded_lifecycle["state"] == lifecycle["state"], "handoff lifecycle state drift")
    require(recorded_lifecycle["execution_commit"] == lifecycle["execution_commit"],
            "handoff lifecycle execution-commit drift")
    require(recorded_lifecycle["authority_receipt_sha256"]
            == lifecycle["authority_receipt"]["sha256"],
            "handoff lifecycle receipt drift")
    require(recorded_lifecycle["authority_receipt_path"]
            == lifecycle["authority_receipt"]["path"],
            "handoff lifecycle receipt path drift")
    require(recorded_lifecycle["auditor_open_delivery_sha256"]
            == lifecycle["auditor_open_delivery"]["sha256"],
            "handoff lifecycle OPEN-delivery drift")
    require(recorded_lifecycle["auditor_open_delivery_path"]
            == lifecycle["auditor_open_delivery"]["path"],
            "handoff lifecycle OPEN-delivery path drift")
    for key in (
        "authority_receipt",
        "auditor_open_delivery",
        "post_o_review_delivery",
    ):
        require(recorded_lifecycle[f"{key}_exists"] is False,
                f"handoff records {key} as present")
        require(not (ROOT / recorded_lifecycle[f"{key}_path"]).exists(),
                f"unexpected authority artifact exists: {key}")
    require(recorded_lifecycle["external_actions"] == lifecycle["external_actions"],
            "handoff lifecycle external-action drift")
    for slot in ("Kag_01", "Kag_02"):
        for phase in ("development", "confirmation", "robustness"):
            require(recorded_lifecycle[phase][slot] == lifecycle["phases"][slot][phase],
                    f"handoff lifecycle phase drift: {slot}/{phase}")

    handoff_candidates = {
        item["alias"]: item for item in handoff["candidate_decisions"] if item["slot"] in {"Kag_01", "Kag_02"}
    }
    plan_candidates = {item["candidate_alias"]: item for item in plan["candidates"]}
    for alias in ("tetsu_v16", "kaito_v22"):
        planned = plan_candidates[alias]
        recorded = handoff_candidates[alias]
        require(planned["status"] == "CLOSED", f"{alias} is not CLOSED")
        require(planned["candidate_sha256"] == recorded["source_sha256"], f"{alias} hash drift")
        require(planned["archive_name"] == recorded["archive_name"], f"{alias} archive-name drift")
        require(
            sha256(ROOT / planned["candidate_path"]) == recorded["source_sha256"],
            f"{alias} source bytes drift",
        )

    metrics = selection["consumed_screen_metrics"]
    for alias in ("tetsu_v16", "kaito_v22"):
        recorded = handoff_candidates[alias]["consumed_screen"]
        for key in ("games", "wins", "ties", "losses", "match_score", "mean_margin", "failures"):
            require(metrics[alias][key] == recorded[key], f"{alias} metric drift: {key}")

    ray = next(item for item in handoff["candidate_decisions"] if item["alias"] == "ray_c45_exact")
    for key in ("games", "wins", "ties", "losses", "match_score", "mean_margin", "failures"):
        require(metrics["ray_c45"][key] == ray["consumed_screen"][key], f"Ray metric drift: {key}")

    plan_pools = {}
    for candidate in plan["candidates"]:
        for phase, pool in candidate["seed_pools"].items():
            plan_pools[(candidate["slot"], phase)] = pool
    handoff_pools = {(pool["slot"], pool["phase"]): pool for pool in handoff["seed_freeze"]["pools"]}
    require(plan_pools.keys() == handoff_pools.keys(), "seed-pool identity drift")
    require(len(plan_pools) == 6, "expected exactly six seed pools")
    for key, pool in plan_pools.items():
        recorded = handoff_pools[key]
        for field in (
            "start",
            "end_inclusive",
            "count",
            "status",
            "opened",
            "consumed",
            "evaluated_games",
        ):
            require(pool[field] == recorded[field], f"seed-pool drift {key}: {field}")
        require(pool["status"] == "CLOSED", f"seed pool is not CLOSED: {key}")
        require(not pool["opened"] and not pool["consumed"], f"seed pool opened: {key}")
        require(pool["evaluated_games"] == 0, f"fresh games recorded for {key}")

    summary = scan["reservation_summary"]
    require(scan["status"] == "NO_COLLISIONS_ALL_POOLS_CLOSED", "collision scan status drift")
    require(summary["collisions"] == [], "reserved seed collision detected")
    require(summary["all_ranges_pairwise_disjoint"], "reserved pools overlap")
    require(summary["all_ranges_closed"], "collision scan says a pool is open")
    require(summary["fresh_games_executed"] == 0, "collision scan reports fresh games")
    require(sum(pool["count"] for pool in handoff_pools.values()) == 224, "reserved count drift")
    print("PASS candidates exact; all six seed pools CLOSED; fresh_games=0")


def verify_tetsu_ip(handoff: dict[str, Any]) -> None:
    release_dir = ROOT / "research/campaign_3000/07_release"
    spec = load_json(release_dir / "release_spec.json")
    local_manifest = load_json(release_dir / "local_build/release_manifest.json")
    ip = handoff["tetsu_conditional_ip"]
    require(ip["verdict"] == "CONDITIONAL_PASS_PRIVATE_SAVERUN_ONLY", "Tetsu verdict drift")
    require(spec["tetsu_ip_verdict"]["verdict"] == ip["verdict"], "release-spec verdict drift")
    require(spec["tetsu_ip_verdict"]["sha256"] == sha256(release_dir / "TETSU_IP_VERDICT.md"),
            "Tetsu verdict hash drift")
    for reference_key in ("evidence_receipt", "source_snapshot_receipt"):
        reference = spec[reference_key]
        require(sha256(ROOT / reference["path"]) == reference["sha256"].upper(),
                f"release-spec evidence hash drift: {reference_key}")

    prerequisites = spec["candidate_evaluation_prerequisites"]
    prerequisite_paths = {
        "candidate_plan": "research/campaign_3000/06_candidates/candidate_plan.json",
        "candidate_gate": "research/campaign_3000/06_candidates/gate_config.json",
        "candidate_manifest": "research/campaign_3000/06_candidates/manifest.json",
    }
    for key, expected_path in prerequisite_paths.items():
        prerequisite = prerequisites[key]
        require(prerequisite["path"] == expected_path, f"release prerequisite path drift: {key}")
        require(sha256(ROOT / expected_path) == prerequisite["sha256"].upper(),
                f"release prerequisite hash drift: {key}")
    require(prerequisites["development_result"]["status"] == "PENDING",
            "release spec bypasses fresh development")
    auditor_gate = prerequisites["independent_auditor_exact_private_saverun_release"]
    require(auditor_gate["required"] is True and auditor_gate["status"] == "PENDING",
            "release spec bypasses the final independent audit")

    raw_receipt_ref = spec["raw_source_archive"]
    raw_receipt_path = ROOT / raw_receipt_ref["path"]
    require(sha256(raw_receipt_path) == raw_receipt_ref["sha256"].upper(),
            "raw source receipt hash drift")
    raw_receipt = load_json(raw_receipt_path)
    require(raw_receipt["status"] == "PASS_EXACT_CURRENT_VERSION_SOURCE_ARCHIVED",
            "raw source archive status drift")
    require(
        raw_receipt["version_binding"]["status"]
        == "PASS_CURRENT_VERSION_AND_SOURCE_IN_SAME_OFFICIAL_API_RESPONSE",
        "raw source version-binding status drift",
    )
    require(
        raw_receipt["version_binding"]["response_envelope_archive_status"]
        == "PASS_TRACKED_SDK_SERIALIZED_GETKERNEL_RESPONSES",
        "raw source response-envelope archive drift",
    )
    require(raw_receipt["retrieval_boundary"]["external_mutation_performed"] is False,
            "raw source archive records an external mutation")
    raw_notebooks = {row["ref"]: row for row in raw_receipt["notebooks"]}
    spec_by_ref = {row["notebook_ref"]: row for row in spec["candidates"]}
    for notebook_ref, raw_notebook in raw_notebooks.items():
        expected = spec_by_ref[notebook_ref]
        response_ref = raw_notebook["getkernel_response"]
        response_path = ROOT / response_ref["path"]
        require(response_path.stat().st_size == response_ref["bytes"],
                f"GetKernel response byte-count drift: {notebook_ref}")
        require(sha256(response_path) == response_ref["sha256"].upper(),
                f"GetKernel response hash drift: {notebook_ref}")
        response = load_json(response_path)
        metadata = response["metadata"]
        require(metadata["ref"] == notebook_ref, f"GetKernel ref drift: {notebook_ref}")
        require(metadata["id"] == raw_notebook["kernel_id"],
                f"GetKernel id drift: {notebook_ref}")
        require(metadata["currentVersionNumber"] == expected["notebook_version"],
                f"GetKernel version drift: {notebook_ref}")
        require(metadata["isPrivate"] is False, f"GetKernel privacy drift: {notebook_ref}")
        require(metadata["competitionDataSources"] == ["kaggriculture"],
                f"GetKernel competition drift: {notebook_ref}")
        raw_path = ROOT / raw_notebook["path"]
        require(response["blob"]["source"].encode() == raw_path.read_bytes(),
                f"GetKernel blob is not byte-identical to raw notebook: {notebook_ref}")

    tetsu_spec = next(row for row in spec["candidates"] if row["sequence"] == "Kag_01")
    require(tetsu_spec["source_sha256"] == ip["main_sha256"], "Tetsu main mapping drift")
    require(tetsu_spec["notebook_version"] == 16, "Tetsu notebook version drift")
    require(tetsu_spec["notebook_source_sha256"] == ip["notebook_source_sha256"],
            "Tetsu notebook source drift")
    require(tetsu_spec["score_claim"].startswith("NO_SCORE_CLAIM_FOR_V16"),
            "Tetsu v16 score boundary drift")
    raw_tetsu = raw_notebooks[tetsu_spec["notebook_ref"]]
    require(raw_tetsu["current_version_number"] == tetsu_spec["notebook_version"],
            "raw Tetsu version drift")
    require(raw_tetsu["sha256"] == tetsu_spec["notebook_source_sha256"],
            "raw Tetsu notebook hash drift")
    require(raw_tetsu["getkernel_response"]["sha256"] == ip["getkernel_response_sha256"],
            "raw Tetsu GetKernel hash drift")
    require(sha256(ROOT / raw_tetsu["path"]) == raw_tetsu["sha256"],
            "raw Tetsu notebook bytes drift")
    require(raw_tetsu["extraction"]["main_sha256"] == ip["main_sha256"],
            "raw Tetsu extraction hash drift")
    kaito_spec = next(row for row in spec["candidates"] if row["sequence"] == "Kag_02")
    raw_kaito = raw_notebooks[kaito_spec["notebook_ref"]]
    require(raw_kaito["current_version_number"] == kaito_spec["notebook_version"],
            "raw Kaito version drift")
    require(raw_kaito["sha256"] == kaito_spec["notebook_source_sha256"],
            "raw Kaito notebook hash drift")
    require(sha256(ROOT / raw_kaito["path"]) == raw_kaito["sha256"],
            "raw Kaito notebook bytes drift")
    require(raw_kaito["extraction"]["main_sha256"] == kaito_spec["source_sha256"],
            "raw Kaito extraction hash drift")

    official_receipt = load_json(ROOT / spec["evidence_receipt"]["path"])
    tetsu_page = next(row for row in official_receipt["pages"]
                      if row["ref"] == tetsu_spec["notebook_ref"])
    page_boundary = ip["page_evidence_boundary"]
    require(tetsu_page["sha256"] == page_boundary["cutoff_capture_sha256"],
            "Tetsu cutoff page hash drift")
    require(tetsu_page["body_archive_status"] == page_boundary["cutoff_status"],
            "Tetsu cutoff archive boundary drift")
    require(page_boundary["cutoff_body_archived"] is False,
            "handoff overclaims a preserved cutoff page body")
    live_capture = tetsu_page["tracked_live_capture"]
    require(live_capture["path"] == page_boundary["tracked_live_capture_path"],
            "Tetsu live-page path drift")
    require(live_capture["sha256"] == page_boundary["tracked_live_capture_sha256"],
            "Tetsu live-page hash drift")
    require(sha256(ROOT / live_capture["path"]) == live_capture["sha256"],
            "Tetsu live-page bytes drift")
    require(live_capture["displayed_license"]
            == page_boundary["tracked_live_capture_displayed_license"],
            "Tetsu live-page license drift")
    live_score = tetsu_page["live_remote_score_evidence"]
    require(live_score["score"] == page_boundary["live_v16_remote_score"],
            "Tetsu live v16 score drift")
    require(live_score["claim_gate"] == page_boundary["live_v16_score_claim_gate"],
            "Tetsu live v16 score gate drift")

    built_tetsu = next(row for row in local_manifest["candidates"] if row["sequence"] == "Kag_01")
    require(built_tetsu["member_sha256"]["main.py"] == ip["main_sha256"],
            "built Tetsu main hash drift")
    require(
        built_tetsu["member_sha256"]["LICENSE"] == spec["license"]["source_sha256"],
        "built Tetsu license hash drift",
    )
    require(sha256(ROOT / spec["license"]["source_path"]) == spec["license"]["source_sha256"],
            "pinned Apache license drift")
    require(local_manifest["external_action_performed"] is False, "07 external action recorded")
    require(local_manifest["candidate_evaluation_prerequisites"] == prerequisites,
            "07 local manifest prerequisite drift")
    require(local_manifest["external_action_gate"]["status"] == "HOLD",
            "07 external action gate is not HOLD")
    worktree_binding = local_manifest["worktree_binding"]
    require(worktree_binding["status"] == "PENDING_FINAL_GIT_FREEZE",
            "07 local build claims a final Git freeze")
    require(sha256(ROOT / worktree_binding["builder"]["path"])
            == worktree_binding["builder"]["sha256"].upper(),
            "07 builder hash drift")
    require(sha256(ROOT / worktree_binding["spec"]["path"])
            == worktree_binding["spec"]["sha256"].upper(),
            "07 local-build spec hash drift")

    conditions = ip["blocking_conditions"]
    require([row["id"] for row in conditions] == [f"IP-{number}" for number in range(1, 8)],
            "Tetsu blocking-condition set drift")
    verdict_text = (release_dir / "TETSU_IP_VERDICT.md").read_text(encoding="utf-8")
    for marker in (
        ip["main_sha256"],
        ip["notebook_source_sha256"],
        ip["common_route_sha256"],
        "is_private=true",
        "enable_internet=false",
        "2703.1 V15",
        "not legal advice",
    ):
        require(marker in verdict_text, f"Tetsu verdict marker missing: {marker}")
    print("PASS Tetsu conditional private-SaveRun IP terms and score boundary")


def verify_authority(handoff: dict[str, Any]) -> None:
    external_manifest = load_json(ROOT / "research/campaign_3000/03_external/manifest.json")
    public_dir = ROOT / "research/campaign_3000/08_public_release"
    release = load_json(public_dir / "release_manifest.json")
    payload = load_json(public_dir / "external_action_payload.json")
    authority = handoff["authority"]

    require(external_manifest["external_writes"] == 0, "03 external writes are nonzero")
    require(authority["external_actions_observed"] == 0, "handoff external action count drift")
    require(authority["external_actions_authorized_by_this_handoff"] is False,
            "handoff claims external authority")
    require(payload["status"] == "DRAFT_ONLY_NOT_EXECUTED", "public payload status drift")
    require(payload["execution_authorized"] is False, "public payload is enabled")
    require(payload["external_calls_performed"] == [], "public payload records external calls")
    require(all(action["enabled"] is False for action in payload["actions"]),
            "public action unexpectedly enabled")
    require(release["status"] == "LOCAL_PUBLIC_RELEASE_DRAFT_NO_EXTERNAL_ACTION",
            "08 release status drift")
    release_artifacts = release["artifacts"]
    for artifact_key in ("archive", "notebook", "kernel_metadata", "discussion",
                         "external_action_payload"):
        artifact = release_artifacts[artifact_key]
        require(sha256(public_dir / artifact["path"]) == artifact["sha256"].upper(),
                f"08 release artifact hash drift: {artifact_key}")
    separation_evidence = release["strength_separation"]["evidence"]
    require(sha256(public_dir / separation_evidence["private_release_manifest_path"])
            == separation_evidence["private_release_manifest_sha256"].upper(),
            "08 private-release manifest copy drift")
    require(sha256(ROOT / "research/campaign_3000/07_release/local_build/release_manifest.json")
            == separation_evidence["private_release_manifest_sha256"].upper(),
            "08 private-release manifest is not the exact 07 final")
    require(sha256(public_dir / separation_evidence["private_release_spec_path"])
            == separation_evidence["private_release_spec_sha256"].upper(),
            "08 private-release spec copy drift")
    require(sha256(ROOT / "research/campaign_3000/07_release/release_spec.json")
            == separation_evidence["private_release_spec_sha256"].upper(),
            "08 private-release spec is not the exact 07 final")

    expected_order = [(1, "kaggle_discussion_create"), (2, "kaggle_code_push")]
    payload_order = [(row["sequence"], row["kind"]) for row in payload["actions"]]
    handoff_order = [(row["sequence"], row["action"]) for row in authority["public_action_order"]]
    require(payload_order == expected_order, "payload is not Discussion then Code")
    require(handoff_order == expected_order, "handoff is not Discussion then Code")
    require(release["authority"]["publication_order"] == ["discussion", "kaggle_code"],
            "release publication order drift")
    for field in (
        "external_publish_authorized",
        "kaggle_code_push_performed",
        "discussion_publish_performed",
        "competition_submission_performed",
        "browser_control_performed",
    ):
        require(release["authority"][field] is False, f"08 authority/action drift: {field}")

    submit = authority["competition_submission"]
    require(submit["status"] == "FORBIDDEN_ABSENT_EXACT_USER_PHRASE", "submit gate drift")
    require(submit["exact_authorizing_user_phrase_observed"] is None,
            "an exact submit phrase is unexpectedly recorded")
    require(submit["inference_or_paraphrase_is_authority"] is False,
            "submission inference was enabled")
    require(submit["forbidden_command"] in payload["forbidden_actions"],
            "competition submit is not explicitly forbidden")
    print("PASS external_actions=0; public order Discussion then Code; submit forbidden")


def git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    require(result.returncode == 0, f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def verify_freeze(
    handoff: dict[str, Any],
    *,
    final: bool,
    final_state_path: Path | None,
) -> None:
    template_freeze = handoff["freeze"]
    commit_fields = (
        "start_git_head",
        "end_git_head",
        "implementation_commit",
        "execution_commit",
        "remote_ref",
    )
    bindings = handoff["pending_bindings"]
    require(len(bindings) == 1 and bindings[0]["id"] == "candidate_execution_binding",
            "execution-binding placeholder missing")
    template_binding = bindings[0]

    for field in (*commit_fields, "tracked_status"):
        require(
            template_freeze[field] == PENDING,
            f"tracked template field is not PENDING_FREEZE: {field}",
        )
    require(template_binding["sha256"] == PENDING, "tracked binding hash is not pending")
    require(template_binding["status"] == PENDING, "tracked binding status is not pending")

    if not final:
        require(final_state_path is None, "--final-state requires --final")
        print("PASS draft freeze placeholders (final freeze intentionally pending)")
        return

    require(final_state_path is not None, "--final requires --final-state")
    overlay_path = final_state_path
    if not overlay_path.is_absolute():
        overlay_path = ROOT / overlay_path
    overlay_path = overlay_path.resolve()
    try:
        overlay_relative = overlay_path.relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise VerificationError("final-state overlay must be inside the workspace") from exc
    require(overlay_path.is_file(), f"final-state overlay is missing: {overlay_relative}")
    overlay = load_json(overlay_path)
    require(overlay["schema_version"] == 1, "unsupported final-state overlay schema")
    require(
        overlay["template_path"] == "research/campaign_3000/09_audit/audit_handoff.json",
        "final-state template path drift",
    )
    require(HEX64.fullmatch(overlay["template_sha256"]) is not None,
            "final-state template hash is not 64-hex")
    require(sha256(HANDOFF_PATH) == overlay["template_sha256"].upper(),
            "final-state template hash mismatch")
    ignored = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", overlay_relative],
        cwd=ROOT,
        check=False,
    )
    require(ignored.returncode == 0, "final-state overlay is not git-ignored")

    freeze = overlay["freeze"]
    for field in commit_fields:
        require(HEX40.fullmatch(freeze[field]) is not None, f"final field is not 40-hex: {field}")
    require(
        freeze["start_git_head"].lower() == freeze["implementation_commit"].lower(),
        "start_git_head does not equal implementation commit S",
    )
    require(
        freeze["end_git_head"].lower() == freeze["execution_commit"].lower(),
        "end_git_head does not equal execution commit E",
    )
    require(
        freeze["remote_ref"].lower() == freeze["execution_commit"].lower(),
        "remote/execution mismatch",
    )
    require(freeze["tracked_status"] == "CLEAN", "final tracked_status is not CLEAN")
    require(git_output("rev-parse", "HEAD").lower() == freeze["execution_commit"].lower(),
            "current HEAD does not equal execution commit")
    require(git_output("status", "--porcelain=v1", "--untracked-files=all") == "",
            "worktree is not clean")

    binding = overlay["execution_binding"]
    require(binding["path"] == template_binding["path"], "execution-binding path drift")
    require(binding["status"] == "FROZEN", "final execution-binding status is not FROZEN")
    binding_path = ROOT / binding["path"]
    require(binding_path.is_file(), "final execution binding is missing")
    require(HEX64.fullmatch(binding["sha256"]) is not None,
            "final execution-binding hash is not 64-hex")
    require(sha256(binding_path) == binding["sha256"].upper(),
            "final execution-binding hash mismatch")
    binding_payload = load_json(binding_path)
    require(
        binding_payload["implementation_commit"].lower()
        == freeze["implementation_commit"].lower(),
        "execution binding does not bind implementation commit S",
    )
    input_manifest = binding_payload["input_manifest"]
    require(
        input_manifest["path"] == "research/campaign_3000/06_candidates/manifest.json",
        "execution binding input-manifest path drift",
    )
    input_manifest_path = ROOT / input_manifest["path"]
    require(input_manifest_path.stat().st_size == input_manifest["bytes"],
            "execution binding input-manifest byte drift")
    require(sha256(input_manifest_path) == input_manifest["sha256"].upper(),
            "execution binding input-manifest hash drift")
    require(binding_payload["binding_excluded_from_input_manifest"] is True,
            "execution binding self-reference exclusion is false")
    changed_paths = git_output(
        "diff",
        "--name-only",
        freeze["implementation_commit"],
        freeze["execution_commit"],
    ).splitlines()
    require(changed_paths == [binding["path"]], "S-to-E diff is not exactly execution_binding.json")
    print("PASS final S/E, clean state, remote equality, and one-file execution binding")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--final",
        action="store_true",
        help="require exact frozen commits, clean state, and execution binding",
    )
    parser.add_argument(
        "--final-state",
        type=Path,
        help="ignored JSON overlay containing exact S/E/remote and binding hashes",
    )
    args = parser.parse_args()

    handoff = load_json(HANDOFF_PATH)
    require(handoff["schema_version"] == 1, "unsupported handoff schema")
    require(handoff["status"] == "DRAFT_PENDING_FREEZE", "unexpected handoff status")
    require(
        handoff["verdict"] == "HOLD_PENDING_EXACT_FREEZE_AND_SEPARATE_AUDIT",
        "handoff verdict is not HOLD",
    )
    index = verify_evidence_files(handoff)
    verify_declared_children(index)
    verify_populations(handoff)
    verify_current_qa_claims(handoff)
    verify_tools_and_skills(handoff)
    verify_candidates_and_seeds(handoff)
    verify_tetsu_ip(handoff)
    verify_authority(handoff)
    verify_freeze(handoff, final=args.final, final_state_path=args.final_state)
    mode = "FINAL" if args.final else "DRAFT"
    print(f"RESULT PASS_{mode}_HANDOFF")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
