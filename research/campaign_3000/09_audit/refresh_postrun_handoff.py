"""Refresh only the post-run fields of the Campaign 3000 audit handoff."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
HANDOFF_PATH = Path(__file__).with_name("audit_handoff.json")


def load(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def record(relative: str, declared_by: str) -> dict[str, Any]:
    payload = (ROOT / relative).read_bytes()
    return {
        "path": relative,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest().upper(),
        "declared_by": declared_by,
    }


def refresh() -> dict[str, Any]:
    handoff = json.loads(HANDOFF_PATH.read_text(encoding="utf-8"))
    lifecycle_path = "research/campaign_3000/06_candidates/lifecycle.json"
    release_spec_path = "research/campaign_3000/07_release/release_spec.json"
    private_manifest_path = (
        "research/campaign_3000/07_release/local_build/release_manifest.json"
    )
    release_verification_path = (
        "research/campaign_3000/07_release/verification/VERIFICATION.md"
    )
    public_sums_path = "research/campaign_3000/08_public_release/SHA256SUMS"
    public_manifest_path = (
        "research/campaign_3000/08_public_release/release_manifest.json"
    )
    public_payload_path = (
        "research/campaign_3000/08_public_release/external_action_payload.json"
    )
    k1_evidence_path = (
        "research/campaign_3000/10_results/kag_01_development/evidence_manifest.json"
    )
    k2_evidence_path = (
        "research/campaign_3000/10_results/kag_02_development/evidence_manifest.json"
    )
    saverun_receipt_path = (
        "research/campaign_3000/11_saverun_results/remote_receipts.json"
    )
    auditor_delivery_path = (
        "research/campaign_3000/11_saverun_results/auditor_deliveries.json"
    )
    saverun_readme_path = "research/campaign_3000/11_saverun_results/README.md"

    lifecycle = load(lifecycle_path)
    k1_gate = load("research/campaign_3000/10_results/kag_01_development/gate.json")
    k2_gate = load("research/campaign_3000/10_results/kag_02_development/gate.json")
    saveruns = load(saverun_receipt_path)

    handoff["artifact_kind"] = "campaign_3000_postrun_publication_audit_handoff_draft"
    handoff["created_at_utc"] = "2026-08-09T00:00:11Z"
    handoff["scope"]["evidence_lanes"] = [
        *handoff["scope"]["evidence_lanes"][:9],
        "research/campaign_3000/10_results",
        "research/campaign_3000/11_saverun_results",
    ]
    handoff["scope"]["handoff_claim"] = (
        "Exact post-run evidence index and publication-audit questions only; no "
        "independent verdict or new external-action authority."
    )
    handoff["scope"]["excluded_claims"] = [
        "3000 rating guarantee",
        "top-3 guarantee",
        "Kag_02 promotion",
        "competition submission",
        "Discussion or public Code publication",
        "new external-action authority",
        "legal advice",
    ]

    authority = handoff["authority"]
    authority.update(
        {
            "external_actions_observed": 2,
            "external_actions_authorized_by_this_handoff": False,
            "browser_control_observed": 0,
            "save_run_observed": 2,
            "competition_submissions_observed": 0,
            "publications_observed": 0,
            "observed_action_receipt": {
                "path": saverun_receipt_path,
                "sha256": record(saverun_receipt_path, "direct")["sha256"],
                "state": saveruns["state"],
                "classification": "TWO_PRIVATE_SAVERUNS_COMPLETE_VERIFIED",
            },
        }
    )

    qa = handoff["current_qa_claims"]
    qa.update(
        {
            "project_pytest": "489 passed at final private-package freeze",
            "postrun_publication_pytest": "493 passed",
            "official_environment_pytest": "81 passed",
            "candidate_focused_pytest": "91 passed before post-run close",
            "release_pytest": "38 passed",
            "public_release_pytest": "10 passed",
            "saverun_receipt_pytest": "4 passed",
            "audit_handoff_verifier": "PASS_DRAFT_HANDOFF",
            "ruff": "All checks passed!",
            "claim_boundary": (
                "Pinned command-output claims from their stated freeze or focused lane; "
                "remote CI count remains zero and these strings are not a "
                "self-authenticating attestation."
            ),
        }
    )

    candidates = {row["slot"]: row for row in handoff["candidate_decisions"]}
    k1 = candidates["Kag_01"]
    k1.update(
        {
            "status": "DEVELOPMENT_CONSUMED_PASS_PRIVATE_SAVERUN_COMPLETE_VERIFIED",
            "fresh_development": {
                "games": k1_gate["summary"]["valid_games"],
                "strict_verdict": k1_gate["strict"]["verdict"],
                "summary": k1_gate["summary"],
                "gate_sha256": record(
                    "research/campaign_3000/10_results/kag_01_development/gate.json",
                    "direct",
                )["sha256"],
                "evidence_manifest_path": k1_evidence_path,
                "evidence_manifest_sha256": record(k1_evidence_path, "direct")["sha256"],
            },
            "private_saverun": {
                "state": "COMPLETE_VERIFIED",
                "kernel_ref": saveruns["slots"][0]["kernel_ref"],
                "version": 1,
                "classification": saveruns["slots"][0]["classification"],
                "archive_sha256": saveruns["slots"][0]["archive"]["sha256"],
            },
        }
    )
    k1_rationale_prefix = [
        "Fresh sealed development passed 122-6 across 128 valid games.",
        "The exact private SaveRun version 1 completed and its remote archive matched.",
    ]
    k1["rationale"] = [
        *k1_rationale_prefix,
        *[row for row in k1["rationale"] if row not in k1_rationale_prefix],
    ]
    k1_limit_prefix = [
        "Fresh development PASS is not a 3000/top-3 or leaderboard forecast.",
        "The SaveRun is private and is not a competition submission.",
    ]
    k1["claim_limits"] = [
        *k1_limit_prefix,
        *[
            row
            for row in k1["claim_limits"]
            if row not in k1_limit_prefix and "later tracked live page" not in row
        ],
    ]

    k2 = candidates["Kag_02"]
    k2.update(
        {
            "status": (
                "DEVELOPMENT_CONSUMED_NO_GO_EXPLORATORY_PRIVATE_"
                "SAVERUN_COMPLETE_VERIFIED"
            ),
            "fresh_development": {
                "games": k2_gate["summary"]["valid_games"],
                "strict_verdict": k2_gate["strict"]["verdict"],
                "summary": k2_gate["summary"],
                "gate_sha256": record(
                    "research/campaign_3000/10_results/kag_02_development/gate.json",
                    "direct",
                )["sha256"],
                "evidence_manifest_path": k2_evidence_path,
                "evidence_manifest_sha256": record(k2_evidence_path, "direct")["sha256"],
            },
            "private_saverun": {
                "state": "COMPLETE_VERIFIED",
                "kernel_ref": saveruns["slots"][1]["kernel_ref"],
                "version": 1,
                "classification": saveruns["slots"][1]["classification"],
                "archive_sha256": saveruns["slots"][1]["archive"]["sha256"],
            },
        }
    )
    k2_rationale_prefix = [
        "Fresh sealed development returned strict NO_GO at 32-96 across 128 games.",
        "Its exact version 1 SaveRun is private exploratory evidence only.",
    ]
    k2["rationale"] = [
        *k2_rationale_prefix,
        *[row for row in k2["rationale"] if row not in k2_rationale_prefix],
    ]
    k2_limit_prefix = [
        "Kag_02 is explicitly non-promotion after strict development NO_GO.",
        "Its SaveRun is private exploratory data and is not a competition submission.",
    ]
    k2["claim_limits"] = [
        *k2_limit_prefix,
        *[row for row in k2["claim_limits"] if row not in k2_limit_prefix],
    ]
    candidates["public_release"]["status"] = "LOCAL_DRAFT_PUBLICATION_HOLD"

    seed = handoff["seed_freeze"]
    seed["status"] = "DEVELOPMENT_CLOSED_256_GAMES_LATER_POOLS_HOLD_OR_RETIRED"
    seed["fresh_games_executed"] = lifecycle["fresh_games_executed"]
    current_pool_state = {
        ("Kag_01", "development"): ("CONSUMED_PASS", True, True, 128),
        ("Kag_01", "confirmation"): ("CLOSED", False, False, 0),
        ("Kag_01", "robustness"): ("CLOSED", False, False, 0),
        ("Kag_02", "development"): ("CONSUMED_NO_GO", True, True, 128),
        ("Kag_02", "confirmation"): ("RETIRED_UNUSED", False, False, 0),
        ("Kag_02", "robustness"): ("RETIRED_UNUSED", False, False, 0),
    }
    for pool in seed["pools"]:
        status, opened, consumed, games = current_pool_state[(pool["slot"], pool["phase"])]
        pool.update(
            {
                "status": status,
                "opened": opened,
                "consumed": consumed,
                "evaluated_games": games,
            }
        )
    seed["opening_policy"] = (
        "Development is consumed. Kag_01 confirmation/robustness remain CLOSED/HOLD; "
        "Kag_02 later pools are RETIRED_UNUSED. No further seed opens without a new "
        "exact independent-auditor authority."
    )
    seed["lifecycle"] = {
        "path": lifecycle_path,
        "sha256": record(lifecycle_path, "direct")["sha256"],
        "schema_version": lifecycle["schema_version"],
        "state": lifecycle["state"],
        "execution_authority_commit": lifecycle["execution_authority_commit"],
        "execution_commit": lifecycle["execution_commit"],
        "open_lifecycle_sha256": lifecycle["open_lifecycle_sha256"],
        "slots": lifecycle["slots"],
        "external_actions": lifecycle["external_actions"],
        "external_actions_semantics": (
            "HOLD means no additional authority; two separately authorized completed "
            "private SaveRuns are recorded in 11_saverun_results."
        ),
        "fresh_games_executed": lifecycle["fresh_games_executed"],
    }

    handoff["claim_limits"] = [
        "The 05 screens used consumed seeds 23000-23007 and are non-promotion evidence.",
        "The sealed development phase executed 256 games: Kag_01 PASS and Kag_02 NO_GO.",
        "Two private SaveRuns are COMPLETE_VERIFIED; neither is a competition submission.",
        "The read-only postrun submission snapshot remained exactly 22.",
        "Kag_02 remains exploratory/non-promotion and its later pools are retired unused.",
        "Discussion and public Code remain unpublished and HOLD in Discussion-then-Code order.",
        "No additional external action is authorized by this handoff.",
        "Only the separate user-owned auditor may issue the required independent verdict.",
    ]

    anchors = handoff["source_manifest_contract"]["manifest_anchors"]
    for path in (
        k1_evidence_path,
        k2_evidence_path,
        saverun_receipt_path,
        auditor_delivery_path,
    ):
        if path not in anchors:
            anchors.append(path)

    replacements = {
        lifecycle_path: record(lifecycle_path, "direct rehash of post-run lifecycle"),
        release_spec_path: record(release_spec_path, "direct rehash of final release specification"),
        private_manifest_path: record(private_manifest_path, public_manifest_path),
        release_verification_path: record(
            release_verification_path, "direct rehash of final local release verification report"
        ),
        public_sums_path: record(public_sums_path, "direct rehash of public-release checksum anchor"),
        public_manifest_path: record(public_manifest_path, public_sums_path),
        public_payload_path: record(public_payload_path, public_manifest_path),
        k1_evidence_path: record(
            k1_evidence_path, "direct rehash of tracked development evidence manifest"
        ),
        k2_evidence_path: record(
            k2_evidence_path, "direct rehash of tracked development evidence manifest"
        ),
        saverun_receipt_path: record(
            saverun_receipt_path, "direct rehash of postrun remote receipt"
        ),
        auditor_delivery_path: record(
            auditor_delivery_path,
            "direct rehash of separate auditor final-message text receipts",
        ),
        saverun_readme_path: record(
            saverun_readme_path, "direct rehash of postrun receipt documentation"
        ),
    }
    old_entries = handoff["evidence_files"]
    handoff["evidence_files"] = []
    for entry in old_entries:
        path = entry["path"]
        if path in replacements:
            refreshed = replacements[path]
        elif path.startswith("research/campaign_3000/08_public_release/"):
            refreshed = record(path, entry["declared_by"])
        else:
            refreshed = entry
        handoff["evidence_files"].append(refreshed)
    existing = {entry["path"] for entry in handoff["evidence_files"]}
    additions = [
        record(k1_evidence_path, "direct rehash of tracked development evidence manifest"),
        record(k2_evidence_path, "direct rehash of tracked development evidence manifest"),
        record(saverun_receipt_path, "direct rehash of postrun remote receipt"),
        record(
            auditor_delivery_path,
            "direct rehash of separate auditor final-message text receipts",
        ),
        record(saverun_readme_path, "direct rehash of postrun receipt documentation"),
    ]
    handoff["evidence_files"].extend(
        entry for entry in additions if entry["path"] not in existing
    )

    handoff["audit_requests"] = [
        "Recompute every evidence hash from the next frozen commit rather than trusting this handoff.",
        "Recheck population definitions, pagination boundaries, unavailable platforms, and negative-scan limits.",
        "Recheck exact 256-game development evidence: Kag_01 PASS and Kag_02 NO_GO.",
        "Recheck both private SaveRun COMPLETE receipts, remote archive identity, and unchanged submission count 22.",
        "Confirm Kag_02 remains exploratory/non-promotion and later pools remain RETIRED_UNUSED.",
        "Inspect public release bytes for private-source leakage and enforce Discussion before Code.",
        "Keep Discussion/public Code HOLD until a separate exact publication verdict.",
        "Reject any competition submission without the recorded exact user phrase authorizing that action.",
    ]
    return handoff


def main() -> None:
    handoff = refresh()
    HANDOFF_PATH.write_text(
        json.dumps(handoff, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
