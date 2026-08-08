"""Cluster public replay action traces without treating replay evidence as validation."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest().upper()


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _farm_only(action: Any) -> Any:
    if not isinstance(action, dict):
        return action
    return {"farmer": action.get("farmer"), "hands": action.get("hands")}


def analyze(root: Path) -> dict[str, Any]:
    inventory_path = root / "replay_inventory.jsonl"
    rows = [
        json.loads(line)
        for line in inventory_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    top_samples: list[dict[str, Any]] = []
    our_samples: list[dict[str, Any]] = []

    for row in rows:
        replay_path = root / "replays_raw" / f"episode-{row['episode_id']}-replay.json"
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
        for request in row["requested_by"]:
            cohort = request.get("cohort")
            if cohort not in {"leaderboard_top25", "our_submissions"}:
                continue
            if cohort == "leaderboard_top25":
                seats = range(len(request["agents"]))
            else:
                seats = [int(request["target_seat"])]
            for seat in seats:
                actions = [step[seat].get("action") for step in replay["steps"]]
                sample = {
                    "episode_id": int(row["episode_id"]),
                    "seat": seat,
                    "team": request["agents"][seat]["teamName"],
                    "reward": request["agents"][seat].get("reward"),
                    "full_action_sha256": _sha(actions),
                    "farm_action_sha256": _sha([_farm_only(action) for action in actions]),
                    "market_action_sha256": _sha(
                        [action.get("market") if isinstance(action, dict) else action for action in actions]
                    ),
                    "replay_sha256": row["sha256"],
                }
                if cohort == "leaderboard_top25":
                    top_samples.append(sample)
                else:
                    sample.update(
                        {
                            "submission_id": int(request["submission_id_queried"]),
                            "file_name": request["file_name"],
                        }
                    )
                    our_samples.append(sample)

    farm_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    full_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in top_samples:
        farm_groups[sample["farm_action_sha256"]].append(sample)
        full_groups[sample["full_action_sha256"]].append(sample)

    def summarize_groups(groups: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
        summary = []
        for digest, samples in groups.items():
            summary.append(
                {
                    "sha256": digest,
                    "sample_count": len(samples),
                    "team_count": len({sample["team"] for sample in samples}),
                    "teams": sorted({sample["team"] for sample in samples}),
                    "episodes": sorted({sample["episode_id"] for sample in samples}),
                    "reward_min": min(sample["reward"] for sample in samples),
                    "reward_max": max(sample["reward"] for sample in samples),
                }
            )
        return sorted(summary, key=lambda item: (-item["sample_count"], item["sha256"]))

    our_by_submission: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for sample in our_samples:
        our_by_submission[(sample["submission_id"], sample["file_name"])].append(sample)
    our_summary = []
    for (submission_id, file_name), samples in sorted(our_by_submission.items()):
        our_summary.append(
            {
                "submission_id": submission_id,
                "file_name": file_name,
                "sample_count": len(samples),
                "farm_action_hash_counts": dict(
                    sorted(Counter(s["farm_action_sha256"] for s in samples).items())
                ),
                "market_action_distinct": len({s["market_action_sha256"] for s in samples}),
                "rewards": [s["reward"] for s in samples],
                "episodes": [s["episode_id"] for s in samples],
            }
        )

    farm_summary = summarize_groups(farm_groups)
    return {
        "schema_version": 1,
        "created_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "interpretation": "HYPOTHESIS_EVIDENCE_ONLY_NOT_PROMOTION",
        "inputs": {
            "replay_inventory": str(inventory_path.relative_to(root.parent.parent.parent)),
            "replay_inventory_sha256": _file_sha(inventory_path),
            "replay_count": len(rows),
        },
        "top25": {
            "agent_samples": len(top_samples),
            "distinct_full_action_traces": len(full_groups),
            "distinct_farm_action_traces": len(farm_groups),
            "farm_clusters": farm_summary,
            "full_action_clusters": summarize_groups(full_groups),
            "modal_farm_share": (
                farm_summary[0]["sample_count"] / len(top_samples) if top_samples else None
            ),
        },
        "ours": our_summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.input_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "top25_agent_samples": report["top25"]["agent_samples"],
        "distinct_farm_traces": report["top25"]["distinct_farm_action_traces"],
        "modal_farm_share": report["top25"]["modal_farm_share"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
