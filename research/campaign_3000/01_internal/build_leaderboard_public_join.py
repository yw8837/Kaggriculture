from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
PUBLIC_ROOT = ROOT.parent / "02_public_meta"


EXPECTED = {
    "code_inventory.jsonl": {
        "sha256": "E510D00AB0AFB35E06B90EFD8EB8CC96DA08F29D8398DF682CDDDD060A7BEEC1",
        "bytes": 328991,
        "population": "155 current public Kaggriculture code refs returned by official kernels_list pagination through the first empty page",
        "observed_at_utc": "2026-08-08T18:03:31Z/2026-08-08T18:08:30Z",
    },
    "discussion_inventory.jsonl": {
        "sha256": "8A296AE0C70728883FA9A2506B263DA3A3907678F03FCAB5D2357DF6B348B767",
        "bytes": 43333,
        "population": "57 discussion IDs collected by the separate public-meta lane; some page authors remain unverified",
        "observed_at_utc": "2026-08-08T18:06:25.995844Z/2026-08-08T18:07:31.603370Z",
    },
    "model_inventory.jsonl": {
        "sha256": "6807E5AC0DB8B02EBE5BFF62AC764454A5CD208C3F6C8A2666934C61F8C8D60E",
        "bytes": 485,
        "population": "1 unverified model inventory record; official CLI lacks a competition filter and UI search observed no result",
        "observed_at_utc": "2026-08-08T18:07:36.430544Z",
    },
    "lineage_summary.json": {
        "sha256": "C93AB3BEEA82FD3D88A2A8167B12C68DB43D49EF2FB101DFD9948C225B0D6F06",
        "bytes": 2311,
        "population": "18 high-score public kernel outputs plus a partial 61-of-155 current source literal-tape scan",
        "observed_at_utc": "2026-08-08T18:16:41.929464Z/2026-08-08T18:23:06.335683Z",
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    source_evidence = {}
    for name, contract in EXPECTED.items():
        path = PUBLIC_ROOT / name
        actual = {"bytes": path.stat().st_size, "sha256": sha256(path)}
        if actual["bytes"] != contract["bytes"] or actual["sha256"] != contract["sha256"]:
            raise ValueError(f"public inventory contract mismatch: {name}: {actual}")
        source_evidence[name] = {
            "path": path.resolve().relative_to(ROOT.parents[2].resolve()).as_posix(),
            **contract,
        }

    code_rows = {row["ref"]: row for row in read_jsonl(PUBLIC_ROOT / "code_inventory.jsonl")}
    exact_ray_refs = [
        "raykkretzschmar/kaggriculture-findings-from-zero-to-top-meta",
        "raykkretzschmar/kaggriculture-rank-your-agent",
    ]
    inferred_lester_ref = "fleongg/kaggriculture-public-2830-4-v21-1-no-preemption"
    selected = exact_ray_refs + [inferred_lester_ref]
    public_refs = {}
    for ref in selected:
        row = code_rows[ref]
        public_refs[ref] = {
            key: row.get(key)
            for key in (
                "ref",
                "id",
                "author",
                "title",
                "url",
                "version",
                "votes",
                "source_sha256",
                "source_bytes",
                "license_name",
                "license_url",
                "claim_status",
                "reproduction_status",
                "retrieved_at_utc",
            )
        }

    leaderboard = json.loads((ROOT / "leaderboard_top25.json").read_text(encoding="utf-8"))
    rows = []
    for row in leaderboard["rows"]:
        team = row["team_name"]
        exact: list[dict[str, Any]] = []
        inferred: list[dict[str, Any]] = []
        if team == "Rayk Kretzschmar":
            exact = [public_refs[ref] for ref in exact_ray_refs]
            code_status = "EXACT_DISPLAY_NAME_MATCH_OBSERVED_IN_CURRENT_155_REF_INVENTORY"
        elif team == "Lester Leong":
            inferred = [
                {
                    **public_refs[inferred_lester_ref],
                    "identity_status": "UNVERIFIED_INFERENCE_ONLY",
                    "reason": "Plausible name/strategy association, but public author display is fle3n rather than Lester Leong.",
                }
            ]
            code_status = "NO_EXACT_DISPLAY_NAME_MATCH;_ONE_UNVERIFIED_INFERENCE_RECORDED"
        else:
            code_status = "NONE_OBSERVED_EXACT_DISPLAY_NAME_MATCH_IN_CURRENT_155_REF_INVENTORY"
        rows.append(
            {
                "rank": int(row["rank"]),
                "team_id": int(row["team_id"]),
                "team_name": team,
                "code": {
                    "status": code_status,
                    "exact_display_name_matches": exact,
                    "unverified_inferences": inferred,
                    "absence_scope": "No exact display-name/owner match in the frozen 155-ref current Code inventory; this is not proof that the team has no public code.",
                },
                "discussion": {
                    "status": "NONE_OBSERVED_EXACT_DISPLAY_NAME_MATCH_IN_57_ID_PARTIALLY_ATTRIBUTED_INVENTORY",
                    "refs": [],
                    "absence_scope": "Many discussion page authors were unverified; this is not proof of no authored discussion.",
                },
                "models": {
                    "status": "NONE_OBSERVED_EXACT_DISPLAY_NAME_MATCH_IN_ONE_UNVERIFIED_RECORD",
                    "refs": [],
                    "absence_scope": "The CLI has no competition filter and UI search returned none; this is not a zero-population claim.",
                },
            }
        )
    lineage = json.loads((PUBLIC_ROOT / "lineage_summary.json").read_text(encoding="utf-8"))
    output = {
        "schema_version": 1,
        "created_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "leaderboard_snapshot_observed_at_utc": leaderboard["observed_at_utc"],
        "source_evidence": source_evidence,
        "rows": rows,
        "lineage_note": {
            "dominant_farm_hash": "FC37F8688680DA949DB44C9444DCB9541488B4E10D9F432CC42648D6423F1B26",
            "status": "UNMAPPED_TO_PUBLIC_CODE_INVENTORY",
            "negative_scan": lineage,
            "evidence_status": "SHA_PINNED_LOCAL_UNCOMMITTED_AT_HANDOFF",
        },
    }
    (ROOT / "leaderboard_public_join.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
