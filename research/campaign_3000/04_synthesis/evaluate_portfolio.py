from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
PUBLIC_INVENTORY = ROOT / "research/campaign_3000/02_public_meta/code_inventory.jsonl"
ENGINE_SUMMARY = ROOT / "research/campaign_3000/05_engine_screen/summary.json"
RAY_SUMMARY = (
    ROOT
    / "research/campaign_3000/05_engine_screen_ray_c45_addendum/summary.json"
)

CANDIDATES: dict[str, dict[str, Any]] = {
    "tetsu_v16": {
        "source_sha256": "997E6BFC5234534E246E945BC61C87858EBF997AB85B0A5C9427DD4ED710F1B6",
        "license": "UNVERIFIED",
        "public_score": None,
        "g1_match_score": 1.0,
        "status": "LICENSE_HOLD",
    },
    "boatlee_v14": {
        "source_sha256": "A7F827B9438885B34B7FD5BF8165458A72F8BB83031A288DD4640F21ADE3294B",
        "license": "UNVERIFIED",
        "public_score": None,
        "g1_match_score": 1.0,
        "status": "LICENSE_HOLD",
    },
    "kaito_v22": {
        "source_sha256": "62FB5A5F66F0011092A2B51E3192879BA583D5D815D761F176091C615657147A",
        "license": "Apache 2.0",
        "public_score": 2957.6,
        "g1_match_score": 1.0,
        "status": "AUDIT_CANDIDATE",
    },
    "ray_c45": {
        "source_sha256": "6CC3B69E487052A8DEDC1A90D0D1296BA38577349E8D3BA8147E583605378F73",
        "license": "Apache 2.0",
        "public_score": 2927.4,
        "g1_match_score": 1.0,
        "status": "AUDIT_CANDIDATE",
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def evaluate(portfolio: list[str]) -> dict[str, Any]:
    reasons: list[str] = []
    if len(portfolio) != 2 or len(set(portfolio)) != 2:
        reasons.append("portfolio must contain exactly two unique candidates")
    unknown = sorted(set(portfolio) - CANDIDATES.keys())
    if unknown:
        reasons.append(f"unknown candidates: {unknown}")

    rows = [CANDIDATES[name] for name in portfolio if name in CANDIDATES]
    for name, row in zip(portfolio, rows, strict=False):
        if row["license"] != "Apache 2.0":
            reasons.append(f"{name}: exact artifact license is not verified Apache 2.0")
        public_score = row["public_score"]
        if not isinstance(public_score, (int, float)) or isinstance(public_score, bool):
            reasons.append(f"{name}: no finite public score provenance")
        elif not math.isfinite(float(public_score)) or public_score < 2900:
            reasons.append(f"{name}: public score {public_score} is below 2900")
        if row["g1_match_score"] < 1.0:
            reasons.append(f"{name}: did not sweep frozen G1 on consumed current-engine screen")

    observed_scores = [float(row["public_score"]) for row in rows if row["public_score"]]
    score = min(observed_scores) if len(observed_scores) == 2 else 0.0
    return {
        "schema_version": 1,
        "pass": not reasons,
        "score": score,
        "portfolio": portfolio,
        "candidate_rows": rows,
        "failure_reasons": reasons,
        "claim_boundary": (
            "This selects an immediately auditable private-SaveRun portfolio. "
            "It is not a local promotion verdict or a 3000-rating guarantee."
        ),
        "input_hashes": {
            "public_inventory_sha256": sha256(PUBLIC_INVENTORY),
            "engine_summary_sha256": sha256(ENGINE_SUMMARY),
            "ray_addendum_summary_sha256": sha256(RAY_SUMMARY),
        },
        "evaluated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--portfolio", nargs=2, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.portfolio)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pass": result["pass"], "score": result["score"]}))


if __name__ == "__main__":
    main()
