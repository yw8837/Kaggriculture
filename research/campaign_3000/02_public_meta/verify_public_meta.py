"""Verify the public-meta inventory and static-output evidence contracts."""

from __future__ import annotations

import ast
import hashlib
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CAMPAIGN_ROOT = ROOT.parents[2]
SHA256_RE = re.compile(r"^[0-9A-Fa-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9A-Fa-f]{40}$")
B85_ROUTE_RE = re.compile(r"b85decode\('([^']+)'\)")
EXPECTED_HASHES = {
    "code_inventory.jsonl": "E510D00AB0AFB35E06B90EFD8EB8CC96DA08F29D8398DF682CDDDD060A7BEEC1",
    "discussion_inventory.jsonl": "8A296AE0C70728883FA9A2506B263DA3A3907678F03FCAB5D2357DF6B348B767",
    "model_inventory.jsonl": "073957AE03F99686ADA346111EB3F3FFC2B4D53C834E551350793AB875785C4E",
    "github_inventory.jsonl": "F0C4FDE4978D196B02A94EBB9DDAA3D03C31C7A22B78928D9B417344FCB30D87",
    "query_log.json": "EF4247B7915DBD544C21A68D3DEA18AAA7D60E63288B7C49E454B6287CF92AAF",
    "kernel_output_manifest.jsonl": "F72D9C5FECB8CA4213BBE07F76E5549C1FE1923C3655918E72C43C45CD5359AA",
    "kernel_output_provenance.jsonl": "43B4DF2E2E36551373F04A78E8310C1311C82F94931C6FF16A25EE18414CC3B0",
    "kernel_static_analysis.jsonl": "BD4AF58185A718F436756093F0C2713831A5632B30C7BAA8F3D9F627E39CE256",
    "tape_lineage.jsonl": "D95EA5E4AFF77025B4B8A8BEA71C1A8ECAE28208DB8845FF488C1F98D5AF0A5B",
    "tetsu_v16_provenance.json": "2DFAF0128B3E1DA60554B9D4D04BF5A5D7528BF0CD6A5DA2DE39F252309BE6AA",
}
MODEL_V8_EXPECTED_HASHES = {
    "model_v8/api_snapshot_v8.json": "2772796DC48E5B535B1A535644378302A4E5D0C4D1A0A2AE30CF467F239D7D10",
    "model_v8/checkpoint_static_analysis.json": "70D9AEC891EC1DB6A739997A7952235C180978E8FCBB0D52CAAAD7827F1B412B",
    "model_v8/disposition.json": "7200FCC24FBF68AEEE1F3C83D4DAB7923E9AD74142399F9620F3793845C9F520",
    "model_v8/file_inventory_v8.json": "B8541A5BE1C1F3FF82EAA9BFAD49CEC88D03B2E15678B95FE8D2642FF103C972",
    "model_v8/tool_evidence.json": "709B278A06B44653D6067E5653F6268FE33C4F2F33EBF89879C2E4B4387E5443",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _jsonl(name: str) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in (ROOT / name).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _verify_tetsu_provenance(code_by_ref: dict[str, dict[str, Any]]) -> None:
    provenance = json.loads((ROOT / "tetsu_v16_provenance.json").read_text(encoding="utf-8"))
    notebook = provenance["notebook"]
    inventory = code_by_ref[notebook["ref"]]
    _require(inventory["version"] == notebook["version"] == 16, "Tetsu version")
    _require(inventory["id"] == notebook["id"] == 129434690, "Tetsu id")
    _require(inventory["source_sha256"] == notebook["source_sha256"], "Tetsu source join")
    _require(inventory["source_bytes"] == notebook["source_bytes"], "Tetsu source bytes")
    _require(inventory["license_name"] == notebook["license_name"] == "UNVERIFIED", "Tetsu license")
    _require(inventory["license_url"] is notebook["license_url"] is None, "Tetsu license URL")

    source_path = (
        CAMPAIGN_ROOT
        / "dist/campaign_3000_public_sources/tetsutani__adaptive-farming-strategy-for-kaggriculture/adaptive-farming-strategy-for-kaggriculture.ipynb"
    )
    metadata_path = source_path.with_name("kernel-metadata.json")
    agent_paths = {
        "tetsu": CAMPAIGN_ROOT
        / "dist/campaign_3000_public_agents/tetsutani__adaptive-farming-strategy-for-kaggriculture.py",
        "boatlee": CAMPAIGN_ROOT
        / "dist/campaign_3000_public_agents/boatlee__84-84-base-public-holdout-v14-clone-preemption.py",
        "flex": CAMPAIGN_ROOT
        / "dist/campaign_3000_public_agents/flexonafft__kaggriculture-adaptive-replay-agent.py",
    }
    extracted = provenance["extracted_agent"]
    for path, expected_bytes, expected_sha, label in (
        (source_path, notebook["source_bytes"], notebook["source_sha256"], "Tetsu notebook"),
        (metadata_path, notebook["metadata_bytes"], notebook["metadata_sha256"], "Tetsu metadata"),
        (agent_paths["tetsu"], extracted["bytes"], extracted["sha256"], "Tetsu agent"),
    ):
        _require(path.is_file(), f"missing {label}: {path}")
        _require(path.stat().st_size == expected_bytes, f"{label} bytes")
        _require(_sha(path) == expected_sha, f"{label} hash")

    extraction_manifest_path = CAMPAIGN_ROOT / extracted["extraction_manifest_path"]
    _require(extraction_manifest_path.stat().st_size == extracted["extraction_manifest_bytes"], "extraction manifest bytes")
    _require(_sha(extraction_manifest_path) == extracted["extraction_manifest_sha256"], "extraction manifest hash")
    extraction_manifest = json.loads(extraction_manifest_path.read_text(encoding="utf-8"))
    extraction_rows = [
        row
        for row in extraction_manifest["agents"]
        if row["output_sha256"] == extracted["sha256"]
    ]
    _require(len(extraction_rows) == 1, "Tetsu extraction row")
    extraction_row = extraction_rows[0]
    _require(extraction_row["bytes"] == extracted["bytes"], "Tetsu extraction bytes")
    _require(extraction_row["method"] == extracted["method"] == "WRITEFILE_MAIN_PY", "Tetsu extraction method")
    _require(extraction_row["cell_index"] == extracted["notebook_cell_index"] == 14, "Tetsu extraction cell")
    _require(extraction_row["compile"] == extracted["static_compile"] == "PASS", "Tetsu extraction compile")

    sources = {name: path.read_text(encoding="utf-8") for name, path in agent_paths.items()}
    compile(sources["tetsu"], str(agent_paths["tetsu"]), "exec")
    route_payloads: dict[str, str] = {}
    for name, source in sources.items():
        match = B85_ROUTE_RE.search(source)
        _require(match is not None, f"missing {name} route payload")
        route_payloads[name] = match.group(1)
    _require(len(set(route_payloads.values())) == 1, "Tetsu/Boatlee/Flex route mismatch")
    route = next(iter(route_payloads.values())).encode("ascii")
    lineage = provenance["lineage"]
    _require(len(route) == lineage["common_route_b85_bytes"] == 9297, "common route bytes")
    _require(hashlib.sha256(route).hexdigest().upper() == lineage["common_route_b85_sha256"], "common route hash")
    _require(_sha(agent_paths["boatlee"]) == lineage["boatlee_agent_sha256"], "Boatlee agent hash")
    _require(_sha(agent_paths["flex"]) == lineage["flex_agent_sha256"], "Flex agent hash")

    boatlee_tree = ast.parse(sources["boatlee"])
    first = boatlee_tree.body[0]
    _require(
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str),
        "Boatlee docstring",
    )
    boatlee_without_docstring = "\n".join(sources["boatlee"].splitlines()[first.end_lineno :]).strip()
    _require(boatlee_without_docstring == sources["flex"].strip(), "Boatlee/Flex runtime body")
    _require("for horizon in (3, 2, 1):" in sources["tetsu"], "Tetsu 3-2-1 preemption")
    _require('state["due_step"] = step + horizon' in sources["tetsu"], "Tetsu repayment horizon")
    tetsu_full_text = source_path.read_text(encoding="utf-8").lower() + sources["tetsu"].lower()
    _require("boatlee" not in tetsu_full_text and "flexonafft" not in tetsu_full_text, "Tetsu upstream-name scan")
    _require(
        provenance["license_boundary"]["decision"] == "HOLD_FOR_INDEPENDENT_AUDIT_BEFORE_COPYING_OR_PACKAGING",
        "Tetsu license boundary",
    )


def _verify_model_v8() -> None:
    for relative, expected in MODEL_V8_EXPECTED_HASHES.items():
        actual = _sha(ROOT / relative)
        _require(actual == expected, f"model-v8 evidence hash: {relative}: {actual} != {expected}")

    model_root = ROOT / "model_v8"
    api = json.loads((model_root / "api_snapshot_v8.json").read_text(encoding="utf-8"))
    files = json.loads((model_root / "file_inventory_v8.json").read_text(encoding="utf-8"))
    analysis = json.loads((model_root / "checkpoint_static_analysis.json").read_text(encoding="utf-8"))
    disposition = json.loads((model_root / "disposition.json").read_text(encoding="utf-8"))
    tools = json.loads((model_root / "tool_evidence.json").read_text(encoding="utf-8"))
    _require(api["model"]["id"] == 737778, "model-v8 id")
    _require(api["variation"]["version_number"] == 8, "model-v8 version")
    _require(api["variation"]["license_name"] == "Apache 2.0", "model-v8 license")
    _require(api["variation"]["total_uncompressed_bytes"] == 1_070_833, "model-v8 total bytes")

    by_name = {row["name"]: row for row in files["files"]}
    _require(
        set(by_name) == {"README.md", "README.md.metadata.json", "banner.jpg", "dqn_baseline_weights.pth"},
        "model-v8 file set",
    )
    _require(sum(row["bytes"] for row in by_name.values()) == 1_070_833, "model-v8 file sum")
    _require(
        analysis["state_dict"]["tensor_shapes"]
        == {"fc1.weight": [64, 10], "fc1.bias": [64], "fc2.weight": [4, 64], "fc2.bias": [4]},
        "model-v8 state dict",
    )
    _require(analysis["state_dict"]["parameter_count"] == 964, "model-v8 parameter count")
    _require(analysis["execution_safety"]["arbitrary_code_executed"] is False, "model-v8 execution safety")
    _require(
        disposition["decision"] == "UNUSABLE_WITH_PUBLISHED_INTERFACE_AND_UNVERIFIED_FOR_KAGGRICULTURE",
        "model-v8 disposition",
    )
    _require(disposition["design_impact"]["used_in_kag_01_or_kag_02"] is False, "model-v8 candidate use")
    _require(tools["agent_reach"]["authoritative_model_evidence_source"] is False, "model-v8 Agent-Reach claim")

    download = CAMPAIGN_ROOT / "dist/model-v8-download"
    for name, row in by_name.items():
        path = download / name
        _require(path.is_file(), f"missing model-v8 raw download: {path}")
        _require(path.stat().st_size == row["bytes"], f"model-v8 raw bytes: {name}")
        _require(_sha(path) == row["sha256"], f"model-v8 raw hash: {name}")


def main() -> None:
    for name, expected in EXPECTED_HASHES.items():
        actual = _sha(ROOT / name)
        _require(actual == expected, f"hash mismatch: {name}: {actual} != {expected}")

    code = _jsonl("code_inventory.jsonl")
    _require(len(code) == 155, f"code count {len(code)}")
    _require(len({row["ref"] for row in code}) == 155, "duplicate Code ref")
    _require(all(row.get("error") is None for row in code), "Code source retrieval failure")
    _require(
        all(SHA256_RE.fullmatch(row["source_sha256"]) for row in code),
        "malformed Code source hash",
    )
    _require(all(row["source_bytes"] > 0 for row in code), "empty Code source")
    _require(all(row["metadata"].get("isPrivate") is False for row in code), "private Code row")
    metadata_unlinked = [
        row["ref"]
        for row in code
        if "kaggriculture" not in (row["metadata"].get("competitionDataSources") or [])
    ]
    _require(
        metadata_unlinked == ["aanaakaliil/notebook858a103738"],
        f"unexpected Code metadata linkage gaps: {metadata_unlinked}",
    )

    discussions = _jsonl("discussion_inventory.jsonl")
    _require(len(discussions) == 57, f"discussion count {len(discussions)}")
    _require(len({row["id"] for row in discussions}) == 57, "duplicate Discussion id")
    _require(
        all(SHA256_RE.fullmatch(row["message_tree_sha256"]) for row in discussions),
        "malformed Discussion message hash",
    )

    models = _jsonl("model_inventory.jsonl")
    _require(len(models) == 1, f"model search-row count {len(models)}")
    _require(
        models[0]["competition_linkage"] == "TEXT_SEARCH_ONLY_NOT_OFFICIAL_COMPETITION_FILTER",
        "Model limitation lost",
    )
    _require(models[0]["current_version"]["version_number"] == 8, "Model current version")
    _require(
        models[0]["analysis"]["decision"]
        == "UNUSABLE_WITH_PUBLISHED_INTERFACE_AND_UNVERIFIED_FOR_KAGGRICULTURE",
        "Model analysis disposition",
    )
    _verify_model_v8()

    github = _jsonl("github_inventory.jsonl")
    kinds = Counter(row["kind"] for row in github)
    _require(
        kinds == Counter(repository=162, pull_request=90, issue=3, official_pull_request=1),
        f"GitHub kind counts {kinds}",
    )
    repositories = [row for row in github if row["kind"] == "repository"]
    _require(
        sum(COMMIT_RE.fullmatch(str(row.get("head_commit_sha", ""))) is not None for row in repositories)
        == 156,
        "GitHub head pin count changed",
    )

    query = json.loads((ROOT / "query_log.json").read_text(encoding="utf-8"))
    _require([row["count"] for row in query["kernel_pages"]] == [100, 55, 0], "Code paging")
    _require(
        [row["count"] for row in query["discussion_pages"]] == [20, 20, 17, 0],
        "Discussion paging",
    )
    _require(query["discussion_pages"][0]["declared_total_count"] == 57, "Discussion total")

    outputs = _jsonl("kernel_output_manifest.jsonl")
    _require(len(outputs) == 18, f"output ref count {len(outputs)}")
    _require(all(row["returncode"] == 0 for row in outputs), "output download failure")
    _require(sum(len(row["files"]) for row in outputs) == 89, "output file count")
    for row in outputs:
        for file in row["files"]:
            path = ROOT / "raw" / "kernel_outputs" / file["relative_path"]
            _require(path.is_file(), f"missing downloaded output: {path}")
            _require(path.stat().st_size == file["bytes"], f"output bytes: {path}")
            _require(_sha(path) == file["sha256"], f"output hash: {path}")

    output_provenance = _jsonl("kernel_output_provenance.jsonl")
    _require(len(output_provenance) == 18, "output provenance count")
    _require(
        {row["ref"] for row in output_provenance} == {row["ref"] for row in outputs},
        "output provenance refs",
    )
    code_by_ref = {row["ref"]: row for row in code}
    for row in output_provenance:
        inventory = code_by_ref[row["ref"]]
        _require(row["current_version"] == inventory["version"], "output version join")
        _require(row["current_source_sha256"] == inventory["source_sha256"], "output source join")

    _verify_tetsu_provenance(code_by_ref)

    static = _jsonl("kernel_static_analysis.jsonl")
    _require(len(static) == 18, f"static row count {len(static)}")
    _require(all(row["parse_status"] == "AST_PASS_STATIC_ONLY" for row in static), "AST failure")
    for row in static:
        path = ROOT / row["main_path"]
        _require(path.is_file(), f"missing static main: {path}")
        _require(_sha(path) == row["main_sha256"], f"static main hash: {path}")

    tape = _jsonl("tape_lineage.jsonl")
    _require(len(tape) == 155, f"tape-lineage population {len(tape)}")
    _require(sum(row["error"] is None for row in tape) == 61, "tape success count")
    _require(sum("429" in str(row["error"]) for row in tape) == 94, "tape 429 count")
    _require(
        not any(
            candidate["dominant_match_variants"]
            for row in tape
            for candidate in row["literal_tapes"]
        ),
        "unexpected dominant source-tape match",
    )

    lineage = json.loads((ROOT / "lineage_summary.json").read_text(encoding="utf-8"))
    _require(lineage["conclusion"] == "NO_EXACT_PUBLIC_LINEAGE_FOUND_IN_SCANNED_MATERIAL", "lineage conclusion")
    _require(lineage["current_source_literal_scan"]["source_requests_rate_limited_429"] == 94, "lineage limitation")
    _require((ROOT / "inventory_report.md").is_file(), "missing inventory report")
    _require((ROOT / "mechanisms.md").is_file(), "missing mechanisms report")

    result = {
        "status": "PASS",
        "finished_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "verifier_sha256": _sha(Path(__file__)),
        "verified_input_sha256": EXPECTED_HASHES,
        "code_refs": len(code),
        "discussion_ids": len(discussions),
        "model_search_rows": len(models),
        "model_v8_static_analysis": "PASS_NO_UNPICKLE_UNUSABLE_WITH_PUBLISHED_INTERFACE",
        "github_kinds": dict(kinds),
        "high_score_output_refs": len(outputs),
        "high_score_output_files": sum(len(row["files"]) for row in outputs),
        "static_ast_pass": len(static),
        "source_tape_scan_success": sum(row["error"] is None for row in tape),
        "source_tape_scan_429": sum(row["error"] is not None for row in tape),
        "tetsu_v16_provenance": "PASS_STATIC_ONLY_LICENSE_HOLD",
    }
    output = ROOT / "verification.json"
    if output.is_file():
        existing = json.loads(output.read_text(encoding="utf-8"))
        candidate = dict(result)
        candidate["finished_at_utc"] = existing.get("finished_at_utc")
        if candidate == existing:
            result = existing
    output_text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if not output.is_file() or output.read_text(encoding="utf-8") != output_text:
        output.write_text(output_text, encoding="utf-8", newline="\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
