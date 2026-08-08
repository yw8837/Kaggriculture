from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent

DOC_SOURCES = {
    "experiment_ledger": {
        "path": "experiments/ledger.jsonl",
        "sha256": "315609EB83FBEFB4577D97D3BAAFE072D6B7A16B4A0E37D59AC3343A094C2135",
    },
    "bot_design_spec": {
        "path": "docs/BOT_DESIGN_SPEC.md",
        "sha256": "93FF99DA450DEB74D5CD5DA232F46A1FFDF3E6BBD7936A003BD57CE8936DAE94",
    },
    "ge_current_state": {
        "path": "docs/current_state_2026-08-02_night.md",
        "sha256": "919E87BD70A5BEBEE371FA1BC73427BDEFF8218796FE52254841FF0B4E47D47E",
    },
    "submission_ledger": {
        "path": "submissions/ledger.jsonl",
        "sha256": "07E645248743B6CAE87B498CC90F263419E87A3038F7FC6E9DE402FC3C4DC11B",
    },
}


FILE_POLICIES: dict[str, dict[str, Any]] = {
    "fast_expansion.tar.gz": {
        "family": "initial_policy_baseline",
        "description": "Initial fast-expansion policy baseline.",
        "claim_basis": "FILENAME_AND_LOCAL_ARCHIVE_ONLY",
    },
    "cow_tilt.tar.gz": {
        "family": "initial_policy_baseline",
        "description": "Initial cow-focused policy baseline.",
        "claim_basis": "FILENAME_AND_LOCAL_ARCHIVE_ONLY",
    },
    "Fa_01 - Overflow-Safe Inventory.tar.gz": {
        "family": "fa_policy",
        "description": "Overflow-safe inventory policy candidate.",
        "claim_basis": "FILENAME_LOCAL_ARCHIVE_AND_PRIOR_AUDIT_HISTORY",
    },
    "Fa_02 - Last-Chance Tiebreak.tar.gz": {
        "family": "fa_policy",
        "description": "Last-chance task tiebreak policy candidate.",
        "claim_basis": "FILENAME_LOCAL_ARCHIVE_AND_PRIOR_AUDIT_HISTORY",
    },
    "Fa_03 - Meta Expansion.tar.gz": {
        "family": "fa_policy",
        "description": "Meta-expansion policy candidate.",
        "claim_basis": "FILENAME_LOCAL_ARCHIVE_AND_PRIOR_AUDIT_HISTORY",
    },
    "Fa_04 - Frontier Trace Guard.tar.gz": {
        "family": "public_replay_derived_tape",
        "description": "Frontier public-trace derivative with impossible-SELL guard; tracked G1 candidate source exists in the campaign worktree.",
        "claim_basis": "TRACKED_G1_SOURCE_AND_PRIOR_AUDIT_HISTORY;_HISTORICAL_UPLOAD_BYTES_UNAVAILABLE",
    },
    "bot_01 - Capacity Expansion.tar.gz": {
        "family": "policy_capacity_expansion",
        "description": "E013: more animal slots, sheep 2→6, hands 10→12, and HIRE ordered before buys.",
        "claim_basis": "EXPERIMENT_LEDGER_E013",
    },
    "bot_02 - Zero-Waste Tape.tar.gz": {
        "family": "public_replay_fixed_tape",
        "description": "E014 fixed tape re-extracted from public episode 89549522 seat 1 (zero waste), without terminal flush.",
        "claim_basis": "EXPERIMENT_LEDGER_E014",
    },
    "bot_03 - Terminal Flush Tape.tar.gz": {
        "family": "public_replay_fixed_tape",
        "description": "E014 zero-waste tape plus small terminal-flush branch.",
        "claim_basis": "EXPERIMENT_LEDGER_E014",
    },
    "bot_05 - Tetsuya Tape Shield.tar.gz": {
        "family": "public_replay_fixed_tape_with_market_overlay",
        "description": "Tetsuya-cluster tape with front-run/treasury-era shield branches; repeated filename across three submissions.",
        "claim_basis": "BOT_DESIGN_SPEC;_EXACT_VERSION_PER_SUBMISSION_UNVERIFIED",
    },
    "bot_07 - Meta Tape Shield.tar.gz": {
        "family": "public_replay_fixed_tape_with_market_overlay",
        "description": "r2897 morning-meta tape plus front_run and treasury branches.",
        "claim_basis": "BOT_DESIGN_SPEC",
    },
    "bot_08 - Terminal Wheat Graft.tar.gz": {
        "family": "public_replay_fixed_tape_graft",
        "description": "bot_05 base with day26–29 terminal wheat-blitz block grafted in.",
        "claim_basis": "BOT_DESIGN_SPEC",
    },
    "bot_11 - Live Market R2921.tar.gz": {
        "family": "public_replay_fixed_farm_with_live_market",
        "description": "r2921 farm tape plus state-reactive live-market overlay.",
        "claim_basis": "BOT_DESIGN_SPEC",
    },
    "bot_12 - Live Market R2914.tar.gz": {
        "family": "public_replay_fixed_farm_with_live_market",
        "description": "r2914 farm tape plus state-reactive live-market overlay.",
        "claim_basis": "BOT_DESIGN_SPEC",
    },
    "Ge_03.tar.gz": {
        "family": "ge_policy_fixed_opening",
        "description": "HIRE-first and staggered seed-buy fix; target herd cow7/sheep4; unrestricted milk selling.",
        "claim_basis": "GE_CURRENT_STATE",
    },
    "Ge_04.tar.gz": {
        "family": "ge_policy_fixed_opening_market_hold",
        "description": "Ge_03 plus sheep5, pre-day24 milk hold, shed>=85 overflow sell, and aggressive melon dump.",
        "claim_basis": "GE_CURRENT_STATE",
    },
}


GE_BY_SUBMISSION = {
    55185505: {
        "family": "ge_policy_v1_day0_bankruptcy",
        "description": "Ge_01 first upload: day-0 animals plus three seed types left about 34 money and blocked hiring.",
        "claim_basis": "GE_CURRENT_STATE",
    },
    55185510: {
        "family": "ge_policy_v1_day0_bankruptcy",
        "description": "Ge_02 first upload: same documented day-0 bankruptcy class.",
        "claim_basis": "GE_CURRENT_STATE",
    },
    55185691: {
        "family": "ge_policy_v2_hire_slot_displacement",
        "description": "Ge_01 second upload: seed/animal orders occupied the 10 market slots before HIRE, leaving zero hands.",
        "claim_basis": "GE_CURRENT_STATE",
    },
    55185695: {
        "family": "ge_policy_v2_hire_slot_displacement",
        "description": "Ge_02 second upload: same documented HIRE-slot displacement class.",
        "claim_basis": "GE_CURRENT_STATE",
    },
}


def main() -> None:
    provenance = json.loads((ROOT / "our_submission_provenance.json").read_text(encoding="utf-8"))
    rows = []
    for submission in provenance["rows"]:
        submission_id = int(submission["submission_id"])
        policy = GE_BY_SUBMISSION.get(submission_id) or FILE_POLICIES[submission["file_name"]]
        mapping = submission["local_source_mapping"]
        local_candidates = []
        for archive in mapping["local_filename_matches"]:
            main = next(
                (member for member in archive.get("members", []) if member["name"] == "main.py"),
                None,
            )
            local_candidates.append(
                {
                    "archive_path": archive["path"],
                    "archive_sha256": archive["sha256"],
                    "archive_bytes": archive["bytes"],
                    "main_sha256": main["sha256"] if main else None,
                    "main_bytes": main["bytes"] if main else None,
                }
            )
        if submission_id == 55171193:
            local_candidates.append(
                {
                    "source_path": "experiments/source_snapshots/fa04_top_trace/G1_sell_guard.py",
                    "source_sha256": "81159A18DF3CD1A5CAABE5EDBBA0A597561775F77A49465FA39DF6802A706922",
                    "source_bytes": 197808,
                    "status": "TRACKED_HISTORICAL_CANDIDATE;_UPLOAD_BYTE_IDENTITY_UNVERIFIED",
                }
            )
        rows.append(
            {
                "submission_id": submission_id,
                "file_name": submission["file_name"],
                "public_score": submission["public_score"],
                "submitted_at_utc": submission["submitted_at_utc"],
                **policy,
                "local_source_candidates": local_candidates,
                "upload_byte_identity": "UNVERIFIED_KAGGLE_HISTORICAL_UPLOAD_BYTES_UNAVAILABLE",
            }
        )
    output = {
        "schema_version": 1,
        "created_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "external_desktop_worktree": {
            "path": "C:/Users/최용우/Desktop/Kaggriculture",
            "mode": "READ_ONLY_DIRTY_EXTERNAL_WORKTREE",
            "document_sources": DOC_SOURCES,
        },
        "limitations": [
            "Policy descriptions are provenance joins from filename, frozen local candidate bytes, and the cited historical ledgers/docs.",
            "Kaggle does not expose historical submitted archive bytes, so no local candidate is asserted byte-equal to a competition submission.",
            "Documents themselves contain stale or later-retracted evaluation conclusions; this map uses them for implementation lineage, not for promotion claims.",
        ],
        "rows": rows,
    }
    (ROOT / "submission_policy_source_map.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
