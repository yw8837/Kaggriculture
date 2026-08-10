"""Deterministically build the Kag_03/Kag_04 CLOSED freeze manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTPUT = HERE / "freeze_manifest.json"

INPUTS = (
    ("eol_policy", ".gitattributes"),
    ("dependency_contract", "pyproject.toml"),
    ("persistent_directive", "CAMPAIGN_DIRECTIVE.md"),
    ("project_instruction_router", "CLAUDE.md"),
    ("harness_skill", ".claude/skills/kaggriculture-3000-orchestrator/SKILL.md"),
    ("cycle_skill", ".omc/skills/kaggriculture-campaign-cycle.md"),
    ("harness_lb_role", ".claude/agents/lb-replay-analyst.md"),
    ("harness_public_role", ".claude/agents/public-meta-researcher.md"),
    ("harness_external_role", ".claude/agents/external-methods-researcher.md"),
    ("harness_qa_role", ".claude/agents/qa-integrator.md"),
    ("cycle_checklist", "research/campaign_3000/13_cycle_20260810/00_checklist/checklist.json"),
    ("cycle_checklist_readme", "research/campaign_3000/13_cycle_20260810/00_checklist/README.md"),
    ("current_live_snapshot", "research/campaign_3000/13_cycle_20260810/04_synthesis/live_browser_snapshot.json"),
    ("current_synthesis", "research/campaign_3000/13_cycle_20260810/04_synthesis/README.md"),
    ("external_mechanism_addendum", "research/campaign_3000/13_cycle_20260810/04_synthesis/external_mechanism_addendum.md"),
    ("previous_submission_analysis", "research/campaign_3000/13_cycle_20260810/02_previous_submissions/comparison.md"),
    ("previous_submission_manifest", "research/campaign_3000/13_cycle_20260810/02_previous_submissions/evidence_manifest.json"),
    ("previous_submission_readme", "research/campaign_3000/13_cycle_20260810/02_previous_submissions/README.md"),
    ("external_source_delta_matrix", "research/campaign_3000/13_cycle_20260810/03_public_external/source_to_delta_matrix.json"),
    ("external_cycle_provenance", "research/campaign_3000/13_cycle_20260810/03_public_external/provenance_hashes.json"),
    ("external_cycle_query_log", "research/campaign_3000/13_cycle_20260810/03_public_external/query_log.md"),
    ("external_cycle_readme", "research/campaign_3000/13_cycle_20260810/03_public_external/README.md"),
    ("external_research_manifest", "research/campaign_3000/03_external/manifest.json"),
    ("selection_decision", "research/campaign_3000/13_cycle_20260810/05_autoresearch/final_selection.json"),
    ("variant_screen_summary", "research/campaign_3000/13_cycle_20260810/05_autoresearch/variant_screen/screen_summary.json"),
    ("variant_source_manifest", "research/campaign_3000/13_cycle_20260810/05_autoresearch/variant_screen/variant_manifest.json"),
    ("variant_report_index", "research/campaign_3000/13_cycle_20260810/05_autoresearch/variant_screen/report_index.json"),
    ("autoresearch_mission", "research/campaign_3000/13_cycle_20260810/05_autoresearch/mission.md"),
    ("autoresearch_evaluator", "research/campaign_3000/13_cycle_20260810/05_autoresearch/evaluator.json"),
    ("autoresearch_decision_log", "research/campaign_3000/13_cycle_20260810/05_autoresearch/runs/20260810T031000Z/decision-log.md"),
    ("kag03_reused_panel", "research/campaign_3000/13_cycle_20260810/05_autoresearch/diagnostic/kag_03_final_panel_reused.json"),
    ("kag04_reused_panel", "research/campaign_3000/13_cycle_20260810/05_autoresearch/diagnostic/kag_04_final_panel_reused.json"),
    ("campaign_readme", "research/campaign_3000/12_next_candidates/README.md"),
    ("qa_status", "research/campaign_3000/12_next_candidates/QA_STATUS.md"),
    ("candidate_catalog", "research/campaign_3000/12_next_candidates/candidate_catalog.json"),
    ("evaluation_plan", "research/campaign_3000/12_next_candidates/evaluation_plan.json"),
    ("development_scenarios", "research/campaign_3000/12_next_candidates/development_scenarios.json"),
    ("development_gate", "research/campaign_3000/12_next_candidates/development_gate.py"),
    ("freeze_builder", "research/campaign_3000/12_next_candidates/build_freeze_manifest.py"),
    ("freeze_verifier", "research/campaign_3000/12_next_candidates/verify_freeze.py"),
    ("seed_reservation_validator", "research/campaign_3000/12_next_candidates/seed_reservation.py"),
    ("seed_collision_receipt", "research/campaign_3000/12_next_candidates/seed_collision_scan.json"),
    ("construction_verification", "research/campaign_3000/12_next_candidates/verification.json"),
    ("kag03_readme", "research/campaign_3000/12_next_candidates/kag_03/README.md"),
    ("kag03_candidate", "research/campaign_3000/12_next_candidates/kag_03/main.py"),
    ("kag03_materialization_receipt", "research/campaign_3000/12_next_candidates/kag_03/freeze_receipt.json"),
    ("kag04_readme", "research/campaign_3000/12_next_candidates/kag_04/README.md"),
    ("kag04_design", "research/campaign_3000/12_next_candidates/kag_04/design.json"),
    ("kag04_artifact_manifest", "research/campaign_3000/12_next_candidates/kag_04/artifact_hashes.json"),
    ("kag04_candidate", "research/campaign_3000/12_next_candidates/kag_04/main.py"),
    ("kag04_materialization_receipt", "research/campaign_3000/12_next_candidates/kag_04/materialized_receipt.json"),
    ("kag04_rejected_iterations", "research/campaign_3000/12_next_candidates/kag_04/rejected_iterations.json"),
    ("kag04_static_diff_proof", "research/campaign_3000/12_next_candidates/kag_04/static_diff_proof.json"),
    ("rejected_kag03_weed_builder", "src/kaggriculture_lab/research/kag03_actor_local_weed.py"),
    ("rejected_kag03_weed_tests", "tests/test_kag03_actor_local_weed.py"),
    ("rejected_kag04_animal_prefix_builder", "src/kaggriculture_lab/research/kag04_animal_buy_prefix.py"),
    ("rejected_kag04_animal_prefix_tests", "tests/test_kag04_animal_buy_prefix.py"),
    ("rejected_kag04_liquidation_builder", "src/kaggriculture_lab/research/kag04_late_inventory_liquidation.py"),
    ("rejected_kag04_liquidation_tests", "tests/test_kag04_late_inventory_liquidation.py"),
    ("rejected_kag04_adjacent_swap_builder", "src/kaggriculture_lab/research/kag04_sheep_first_adjacent_swap.py"),
    ("rejected_kag04_adjacent_swap_tests", "tests/test_kag04_sheep_first_adjacent_swap.py"),
    ("kag03_builder", "src/kaggriculture_lab/research/kag03_preempt_horizon.py"),
    ("kag04_builder", "src/kaggriculture_lab/research/kag04_seat0_horizon4.py"),
    ("kag03_tests", "tests/test_kag03_preempt_horizon.py"),
    ("kag04_tests", "tests/test_kag04_seat0_horizon4.py"),
    ("shared_gate_tests", "tests/test_next_candidate_catalog.py"),
    ("runner", "src/kaggriculture_lab/evaluation/runner.py"),
    ("runner_tests", "tests/test_runner.py"),
    ("opponent_tetsu", "research/campaign_3000/06_candidates/snapshots/tetsu_v16.py"),
    ("opponent_ray", "research/campaign_3000/06_candidates/snapshots/ray_c45_exact.py"),
    ("opponent_boatlee", "research/campaign_3000/06_candidates/snapshots/boatlee_v14.py"),
    ("opponent_kaito", "research/campaign_3000/06_candidates/snapshots/kaito_v22.py"),
    ("opponent_fa04_g1", "experiments/source_snapshots/fa04_top_trace/G1_sell_guard.py"),
    ("tetsu_ip_verdict", "research/campaign_3000/07_release/TETSU_IP_VERDICT.md"),
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _load(relative: str) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {relative}")
    return value


def _pin(role: str, relative: str) -> dict[str, Any]:
    data = (ROOT / relative).read_bytes()
    return {"role": role, "path": relative, "bytes": len(data), "sha256": _sha256(data)}


def build_manifest() -> dict[str, Any]:
    catalog = _load("research/campaign_3000/12_next_candidates/candidate_catalog.json")
    plan = _load("research/campaign_3000/12_next_candidates/evaluation_plan.json")
    seed_scan = _load("research/campaign_3000/12_next_candidates/seed_collision_scan.json")
    selection = _load("research/campaign_3000/13_cycle_20260810/05_autoresearch/final_selection.json")
    verification = _load("research/campaign_3000/12_next_candidates/verification.json")
    inputs = [_pin(role, relative) for role, relative in INPUTS]
    slots = {
        slot: {
            "path": plan["slots"][slot]["candidate_path"],
            "sha256": plan["slots"][slot]["candidate_source_sha256"],
            "bytes": plan["slots"][slot]["candidate_source_bytes"],
            "development_pool": [
                next(item for item in catalog["slots"] if item["slot"] == slot)["seed_pools"]["development"]["start"],
                next(item for item in catalog["slots"] if item["slot"] == slot)["seed_pools"]["development"]["end_inclusive"],
            ],
            "reused_selection_report_sha256": selection["selected"][slot]["panel_report_sha256"],
        }
        for slot in ("Kag_03", "Kag_04")
    }
    current_scan = seed_scan["reservation_state"]["current_adapter_revalidation"]
    return {
        "schema_version": 2,
        "artifact_kind": "kag_03_kag_04_closed_implementation_freeze_manifest",
        "status": "CLOSED_IMPLEMENTATION_FREEZE_PENDING_S_E_BINDING",
        "implementation_commit": "PENDING_S_COMMIT",
        "binding_path": "research/campaign_3000/12_next_candidates/execution_binding.json",
        "manifest_policy": "The manifest excludes itself and execution_binding.json. S commits these exact inputs; E changes execution_binding.json only.",
        "authority": {
            "fresh_seed_execution": "FORBIDDEN_UNTIL_INDEPENDENT_AUDITOR_EXACT_OPEN",
            "save_run": "FORBIDDEN",
            "upload": "FORBIDDEN",
            "competition_submission": "FORBIDDEN",
            "publication": "FORBIDDEN",
        },
        "engine": plan["engine"],
        "candidates": slots,
        "development_contract": {
            "cells_per_candidate": 160,
            "opponents": [item["path"] for item in plan["runner"]["opponents"]],
            "seats": [0, 1],
            "scenario": "default",
            "causal_metrics": plan["development_gate"]["integrity"],
            "minimum_to_remain_a_candidate": "Strict direct Kag_01/Tetsu v16 match score > 0.50 AND mean margin > 0.0; equality is NO_GO.",
            "score_claim": "No local result guarantees a 3000 leaderboard score.",
        },
        "seed_collision_evidence": {
            "all_six_pools_closed_and_collision_free": True,
            "observed_seed_count": current_scan["observed_seed_count"],
            "observed_seed_values_sha256": current_scan["observed_seed_values_sha256"],
            "seed_evidence_files_sha256": current_scan["seed_evidence_files_sha256"],
            "fresh_games_executed": 0,
        },
        "selection_boundary": {
            "promotion_evidence": False,
            "fresh_reserved_games_executed": 0,
            "Kag_03_reused_panel": selection["selected"]["Kag_03"]["overall"],
            "Kag_04_reused_panel": selection["selected"]["Kag_04"]["overall"],
        },
        "qa": verification["qa_summary"],
        "input_count": len(inputs),
        "inputs": inputs,
    }


def main() -> int:
    manifest = build_manifest()
    OUTPUT.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="",
    )
    print(f"BUILT {OUTPUT.relative_to(ROOT).as_posix()} inputs={manifest['input_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
