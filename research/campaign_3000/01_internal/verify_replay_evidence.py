from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[2]
INVENTORY = ROOT / "replay_inventory.jsonl"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_inventory() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in INVENTORY.read_text(encoding="utf-8").splitlines()
        if line
    ]


def normalized_inventory(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for original in rows:
        row = dict(original)
        episode_id = int(row["episode_id"])
        raw = ROOT / "replays_raw" / f"episode-{episode_id}-replay.json"
        row.pop("absolute_path_utf8", None)
        row["path"] = raw.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
        output.append(row)
    return output


def preserve_created_at_if_unchanged(
    output: Path, report: dict[str, Any]
) -> dict[str, Any]:
    """Keep verifier output byte-stable when only wall-clock time changed."""
    if not output.is_file():
        return report
    existing = json.loads(output.read_text(encoding="utf-8"))
    candidate = dict(report)
    candidate["created_at_utc"] = existing.get("created_at_utc")
    return existing if candidate == existing else report


def main() -> None:
    rows = normalized_inventory(read_inventory())
    inventory_text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    )
    INVENTORY.write_text(inventory_text, encoding="utf-8", newline="\n")

    status_counts: Counter[str] = Counter()
    cohort_requests: Counter[str] = Counter()
    cohort_episode_ids: dict[str, set[int]] = {}
    cohort_status_counts: dict[str, Counter[str]] = {}
    cohort_terminal_status_pairs: dict[str, Counter[str]] = {}
    terminal_status_pairs: Counter[str] = Counter()
    bad: list[dict[str, Any]] = []

    for row in rows:
        episode_id = int(row["episode_id"])
        relative = Path(row["path"])
        raw_path = REPO_ROOT / relative
        row_errors: list[str] = []
        if relative.is_absolute():
            row_errors.append("absolute_path")
        if not raw_path.is_file():
            row_errors.append("missing_file")
            bad.append({"episode_id": episode_id, "errors": row_errors})
            continue
        actual_bytes = raw_path.stat().st_size
        actual_sha = sha256(raw_path)
        if actual_bytes != int(row["bytes"]):
            row_errors.append("bytes_mismatch")
        if actual_sha != str(row["sha256"]).upper():
            row_errors.append("sha256_mismatch")

        replay = json.loads(raw_path.read_text(encoding="utf-8"))
        replay_episode_id = (replay.get("info") or {}).get("EpisodeId")
        if int(replay_episode_id or -1) != episode_id:
            row_errors.append("episode_id_mismatch")
        steps = replay.get("steps") or []
        if len(steps) != int(row["steps"]):
            row_errors.append("step_count_mismatch")
        row_cohorts = {
            str(request.get("cohort")) for request in row.get("requested_by") or []
        }
        for step in steps:
            for agent in step:
                status = str(agent.get("status"))
                status_counts[status] += 1
                for cohort in row_cohorts:
                    cohort_status_counts.setdefault(cohort, Counter())[status] += 1
        if steps:
            terminal_pair = "|".join(str(agent.get("status")) for agent in steps[-1])
            terminal_status_pairs[terminal_pair] += 1
            for cohort in row_cohorts:
                cohort_terminal_status_pairs.setdefault(cohort, Counter())[terminal_pair] += 1
        for request in row.get("requested_by") or []:
            cohort = str(request.get("cohort"))
            cohort_requests[cohort] += 1
            cohort_episode_ids.setdefault(cohort, set()).add(episode_id)
        if row_errors:
            bad.append({"episode_id": episode_id, "errors": row_errors})

    report = {
        "schema_version": 1,
        "created_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "inventory": {
            "path": INVENTORY.resolve().relative_to(REPO_ROOT.resolve()).as_posix(),
            "bytes": INVENTORY.stat().st_size,
            "sha256": sha256(INVENTORY),
            "rows": len(rows),
            "authoritative_path_contract": "campaign-worktree-relative POSIX path; no absolute path field",
        },
        "raw_replays": {
            "verified": len(rows) - len(bad),
            "failed": len(bad),
            "total": len(rows),
            "status_counts_all_agent_steps": dict(sorted(status_counts.items())),
            "terminal_status_pairs": dict(sorted(terminal_status_pairs.items())),
        },
        "selection": {
            "requests_by_cohort": dict(sorted(cohort_requests.items())),
            "unique_episodes_by_cohort": {
                key: len(value) for key, value in sorted(cohort_episode_ids.items())
            },
            "status_counts_all_agents_by_unique_episode_cohort": {
                cohort: dict(sorted(counts.items()))
                for cohort, counts in sorted(cohort_status_counts.items())
            },
            "terminal_status_pairs_by_unique_episode_cohort": {
                cohort: dict(sorted(counts.items()))
                for cohort, counts in sorted(cohort_terminal_status_pairs.items())
            },
        },
        "failures": bad,
    }
    output = ROOT / "replay_integrity_report.json"
    report = preserve_created_at_if_unchanged(output, report)
    output_text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if not output.is_file() or output.read_text(encoding="utf-8") != output_text:
        output.write_text(output_text, encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
