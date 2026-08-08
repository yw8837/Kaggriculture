from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
import platform
import re
import statistics
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from importlib.metadata import distribution, version
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from kaggriculture_lab.evaluation import runner

CONFIG_PATH = HERE / "screen_config.json"
REGISTRY_PATH = HERE / "cell_registry.json"
RAW_REPORT_PATH = HERE / "raw" / "ray_c45_exact.json"
ABNORMAL_RE = re.compile(
    r"framework agent failure at step=(?P<step>\d+), "
    r"player=(?P<player>\d+), status=(?P<status>[A-Z_]+)"
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _json_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest().upper()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: Any) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite evidence: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def _git_head() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _config() -> dict[str, Any]:
    return _load(CONFIG_PATH)


def _inventory_row(config: dict[str, Any]) -> dict[str, Any]:
    provenance = config["notebook_provenance"]
    path = PROJECT_ROOT / provenance["inventory_path"]
    matches = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and json.loads(line).get("ref") == provenance["ref"]
    ]
    if len(matches) != 1:
        raise RuntimeError(f"expected one provenance row, found {len(matches)}")
    row = matches[0]
    if _json_sha256(row) != provenance["inventory_row_canonical_sha256"]:
        raise RuntimeError("notebook provenance row SHA mismatch")
    checks = {
        "version": provenance["version"],
        "license_name": provenance["license_name"],
        "best_score": provenance["observed_best_score"],
        "best_score_version": provenance["observed_best_score_version"],
        "source_sha256": provenance["notebook_source_sha256"],
        "source_bytes": provenance["notebook_source_bytes"],
        "metadata_sha256": provenance["metadata_sha256"],
        "page_reader_sha256": provenance["page_reader_sha256"],
    }
    for key, expected in checks.items():
        if row.get(key) != expected:
            raise RuntimeError(f"notebook provenance field mismatch: {key}")
    return row


def _source_paths(config: dict[str, Any]) -> dict[str, Path]:
    records = [config["runner"], config["candidate"], *config["opponents"]]
    paths = {record["path"]: PROJECT_ROOT / record["path"] for record in records}
    registry_path = config["seed_policy"]["historical_registry_path"]
    paths[registry_path] = PROJECT_ROOT / registry_path
    paths[_relative(CONFIG_PATH)] = CONFIG_PATH
    paths[_relative(HERE / "run_addendum.py")] = HERE / "run_addendum.py"
    return paths


def _source_snapshot(config: dict[str, Any]) -> dict[str, Any]:
    files = {
        name: {"bytes": path.stat().st_size, "sha256": _sha256(path)}
        for name, path in sorted(_source_paths(config).items())
    }
    row = _inventory_row(config)
    stable = {
        "files": files,
        "notebook_inventory_row_canonical_sha256": _json_sha256(row),
    }
    stable["snapshot_sha256"] = _json_sha256(stable)
    return stable


def _distribution_metadata() -> dict[str, dict[str, Any]]:
    dist = distribution("kaggle-environments")
    files: dict[str, dict[str, Any]] = {}
    for item in dist.files or []:
        name = str(item).replace("\\", "/")
        if not name.endswith((".dist-info/METADATA", ".dist-info/WHEEL")):
            continue
        path = Path(dist.locate_file(item))
        files[name] = {"bytes": path.stat().st_size, "sha256": _sha256(path)}
    return files


def _environment_snapshot(config: dict[str, Any]) -> dict[str, Any]:
    expected_version = config["engine"]["version"]
    actual_version = version("kaggle-environments")
    if actual_version != expected_version:
        raise RuntimeError(f"expected engine {expected_version}, got {actual_version}")

    from kaggle_environments import make
    from kaggle_environments.envs.kaggriculture import kaggriculture as engine

    engine_path = Path(inspect.getsourcefile(engine) or "").resolve()
    engine_files = {
        path.name: {"bytes": path.stat().st_size, "sha256": _sha256(path)}
        for path in sorted(engine_path.parent.iterdir())
        if path.is_file()
    }
    if (
        engine_files["kaggriculture.py"]["sha256"]
        != config["engine"]["kaggriculture_py_sha256"]
    ):
        raise RuntimeError("installed kaggriculture.py SHA mismatch")
    env = make(
        "kaggriculture",
        configuration={"episodeSteps": 720, "seed": 23000},
        debug=False,
    )
    environment_configuration = json.loads(
        json.dumps(dict(env.configuration), sort_keys=True)
    )
    stable = {
        "kaggle_environments_version": actual_version,
        "python_version": platform.python_version(),
        "python_executable": str(Path(sys.executable).resolve()),
        "engine_directory": str(engine_path.parent),
        "engine_files": engine_files,
        "engine_files_sha256": _json_sha256(engine_files),
        "distribution_metadata": _distribution_metadata(),
        "default_environment_configuration": environment_configuration,
        "default_environment_configuration_sha256": _json_sha256(
            environment_configuration
        ),
    }
    stable["snapshot_sha256"] = _json_sha256(stable)
    return stable


def _validate(config: dict[str, Any]) -> None:
    records = [config["runner"], config["candidate"], *config["opponents"]]
    for record in records:
        path = PROJECT_ROOT / record["path"]
        if _sha256(path) != record["sha256"]:
            raise RuntimeError(f"SHA mismatch: {record['path']}")
        if "bytes" in record and path.stat().st_size != record["bytes"]:
            raise RuntimeError(f"byte-size mismatch: {record['path']}")
    registry = config["seed_policy"]
    if (
        _sha256(PROJECT_ROOT / registry["historical_registry_path"])
        != registry["historical_registry_sha256"]
    ):
        raise RuntimeError("historical seed registry SHA mismatch")
    runner_text = (PROJECT_ROOT / config["runner"]["path"]).read_text(encoding="utf-8")
    if config["runner"]["required_failure_guard"] not in runner_text:
        raise RuntimeError("hardened hidden-status guard missing")
    candidate_path = PROJECT_ROOT / config["candidate"]["path"]
    candidate_bytes = candidate_path.read_bytes()
    compile(candidate_bytes, config["candidate"]["path"], "exec")
    _inventory_row(config)
    _environment_snapshot(config)


def _cell_key(opponent: str, seed: int, seat: int) -> str:
    return (
        "engine=1.32.6|candidate=ray_c45_exact|"
        f"opponent={opponent}|seed={seed}|candidate_seat={seat}|scenario=default"
    )


def prepare() -> None:
    config = _config()
    _validate(config)
    cells = [
        {
            "exact_cell_key": _cell_key(opponent["alias"], seed, seat),
            "engine_version": config["engine"]["version"],
            "candidate": config["candidate"]["alias"],
            "opponent": opponent["alias"],
            "seed": seed,
            "seed_status": "CONSUMED_SCREEN",
            "candidate_seat": seat,
            "scenario": "default",
        }
        for opponent in config["opponents"]
        for seed in config["seed_policy"]["seeds"]
        for seat in (0, 1)
    ]
    if len(cells) != config["design"]["exact_cells"]:
        raise RuntimeError("cell count mismatch")
    if len({cell["exact_cell_key"] for cell in cells}) != len(cells):
        raise RuntimeError("duplicate exact cell key")
    core = {
        "schema_version": 1,
        "run_id": config["run_id"],
        "seed_status": "CONSUMED_SCREEN",
        "promotion_eligible": False,
        "cells": cells,
    }
    _write(REGISTRY_PATH, {**core, "canonical_registry_sha256": _json_sha256(core)})
    print(
        json.dumps(
            {
                "registry": _relative(REGISTRY_PATH),
                "sha256": _sha256(REGISTRY_PATH),
                "cells": len(cells),
            },
            indent=2,
        )
    )


def run() -> None:
    config = _config()
    if not REGISTRY_PATH.is_file():
        raise FileNotFoundError("run prepare first")
    _validate(config)
    start_path = HERE / "receipts" / "engine_1.32.6.started.json"
    completed_path = HERE / "receipts" / "engine_1.32.6.completed.json"
    runner_started_path = RAW_REPORT_PATH.with_name(f"{RAW_REPORT_PATH.stem}.started.json")
    occupied = [
        path
        for path in (start_path, completed_path, RAW_REPORT_PATH, runner_started_path)
        if path.exists()
    ]
    if occupied:
        raise FileExistsError(f"refusing to overwrite evidence: {occupied}")

    source_start = _source_snapshot(config)
    environment_start = _environment_snapshot(config)
    start = {
        "schema_version": 1,
        "run_id": config["run_id"],
        "started_at_utc": _now(),
        "git_head_at_start": _git_head(),
        "authority": config["authority"],
        "seed_policy": config["seed_policy"],
        "engine": config["engine"],
        "candidate": config["candidate"],
        "opponents": config["opponents"],
        "notebook_provenance": config["notebook_provenance"],
        "cell_registry": _relative(REGISTRY_PATH),
        "cell_registry_sha256_at_start": _sha256(REGISTRY_PATH),
        "planned_cells": config["design"]["exact_cells"],
        "sources_at_start": source_start,
        "environment_at_start": environment_start,
    }
    _write(start_path, start)

    for opponent in config["opponents"]:
        runner.OPPONENT_PATHS[opponent["alias"]] = Path(opponent["path"])
    report = runner.run_batch(
        config["candidate"]["path"],
        [opponent["alias"] for opponent in config["opponents"]],
        config["seed_policy"]["seeds"],
        RAW_REPORT_PATH,
        config["engine"]["workers"],
        PROJECT_ROOT,
        {"default": config["engine"]["scenario_override"]},
    )
    if report["summary"]["raw_games"] != config["design"]["exact_cells"]:
        raise RuntimeError("runner raw-game count mismatch")
    if not report["sources_unchanged_during_run"]:
        raise RuntimeError("runner source changed during batch")

    source_end = _source_snapshot(config)
    environment_end = _environment_snapshot(config)
    completed = {
        "schema_version": 1,
        "run_id": config["run_id"],
        "completed_at_utc": _now(),
        "git_head_at_end": _git_head(),
        "start_receipt": _relative(start_path),
        "start_receipt_sha256": _sha256(start_path),
        "cell_registry_sha256_at_end": _sha256(REGISTRY_PATH),
        "sources_at_end": source_end,
        "environment_at_end": environment_end,
        "sources_unchanged_during_phase": (
            source_start["snapshot_sha256"] == source_end["snapshot_sha256"]
        ),
        "environment_unchanged_during_phase": (
            environment_start["snapshot_sha256"] == environment_end["snapshot_sha256"]
        ),
        "cell_registry_unchanged_during_phase": (
            start["cell_registry_sha256_at_start"] == _sha256(REGISTRY_PATH)
        ),
        "raw_report": _relative(RAW_REPORT_PATH),
        "raw_report_sha256": _sha256(RAW_REPORT_PATH),
        "runner_start_receipt": _relative(runner_started_path),
        "runner_start_receipt_sha256": _sha256(runner_started_path),
        "executed_cells": report["summary"]["raw_games"],
    }
    _write(completed_path, completed)
    if not all(
        completed[key]
        for key in (
            "sources_unchanged_during_phase",
            "environment_unchanged_during_phase",
            "cell_registry_unchanged_during_phase",
        )
    ):
        raise RuntimeError("addendum provenance changed during run")
    print(
        json.dumps(
            {
                "games": report["summary"]["raw_games"],
                "failures": report["summary"]["failed_raw_games"],
                "match_score": report["summary"]["match_score"],
                "margin_mean": report["summary"]["margin_mean"],
                "completed_receipt_sha256": _sha256(completed_path),
                "integrity": "PASS",
            },
            indent=2,
        )
    )


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * quantile
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return values[lower]
    fraction = position - lower
    return values[lower] * (1 - fraction) + values[upper] * fraction


def _valid(row: dict[str, Any]) -> bool:
    return bool(
        row["error"] is None
        and row["candidate_status"] == "DONE"
        and row["opponent_status"] == "DONE"
        and row["candidate_money"] is not None
        and row["opponent_money"] is not None
    )


def _aggregate(rows: list[dict[str, Any]], include_seats: bool = True) -> dict[str, Any]:
    valid = [row for row in rows if _valid(row)]
    scores = [float(row["score"]) for row in valid]
    margins = [float(row["margin"]) for row in valid]
    money = [float(row["candidate_money"]) for row in valid]
    runtime = [float(row["elapsed_seconds"]) for row in rows]
    result = {
        "raw_games": len(rows),
        "valid_games": len(valid),
        "failures": len(rows) - len(valid),
        "hidden_abnormal_status_failures": sum(
            row["hidden_abnormal_status"] is not None for row in rows
        ),
        "status_pairs": dict(
            sorted(
                Counter(
                    f"{row['candidate_status']}/{row['opponent_status']}" for row in rows
                ).items()
            )
        ),
        "wins": sum(score == 1.0 for score in scores),
        "ties": sum(score == 0.5 for score in scores),
        "losses": sum(score == 0.0 for score in scores),
        "match_score": statistics.mean(scores) if scores else None,
        "candidate_money": {
            "mean": statistics.mean(money) if money else None,
            "median": statistics.median(money) if money else None,
            "min": min(money) if money else None,
            "max": max(money) if money else None,
        },
        "margin": {
            "mean": statistics.mean(margins) if margins else None,
            "median": statistics.median(margins) if margins else None,
            "min": min(margins) if margins else None,
            "max": max(margins) if margins else None,
        },
        "game_runtime_seconds": {
            "mean": statistics.mean(runtime) if runtime else None,
            "median": statistics.median(runtime) if runtime else None,
            "p95": _percentile(runtime, 0.95),
            "p99": _percentile(runtime, 0.99),
            "max": max(runtime) if runtime else None,
            "total": sum(runtime),
        },
        "failure_examples": [
            {
                "exact_cell_key": row["exact_cell_key"],
                "error": row["error"],
                "hidden_abnormal_status": row["hidden_abnormal_status"],
            }
            for row in rows
            if not _valid(row)
        ][:10],
    }
    if include_seats:
        result["by_candidate_seat"] = {
            str(seat): _aggregate(
                [row for row in rows if row["candidate_seat"] == seat],
                include_seats=False,
            )
            for seat in (0, 1)
        }
    return result


def analyze() -> None:
    config = _config()
    completed_path = HERE / "receipts" / "engine_1.32.6.completed.json"
    completed = _load(completed_path)
    if not all(
        completed[key]
        for key in (
            "sources_unchanged_during_phase",
            "environment_unchanged_during_phase",
            "cell_registry_unchanged_during_phase",
        )
    ):
        raise RuntimeError("completed receipt integrity failed")

    registry = _load(REGISTRY_PATH)
    cells = {cell["exact_cell_key"]: cell for cell in registry["cells"]}
    report = _load(RAW_REPORT_PATH)
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(report["games"]):
        exact_key = _cell_key(raw["opponent"], int(raw["seed"]), int(raw["seat"]))
        if exact_key not in cells:
            raise RuntimeError(f"unregistered raw cell: {exact_key}")
        abnormal_match = ABNORMAL_RE.search(raw["error"] or "")
        abnormal = None
        if abnormal_match:
            player = int(abnormal_match.group("player"))
            abnormal = {
                "step": int(abnormal_match.group("step")),
                "player": player,
                "status": abnormal_match.group("status"),
                "agent": (
                    config["candidate"]["alias"]
                    if player == int(raw["seat"])
                    else raw["opponent"]
                ),
            }
        is_valid = bool(
            raw["error"] is None
            and raw["candidate_status"] == "DONE"
            and raw["opponent_status"] == "DONE"
            and raw["candidate_money"] is not None
            and raw["opponent_money"] is not None
        )
        candidate_money = raw["candidate_money"]
        opponent_money = raw["opponent_money"]
        margin = (
            float(candidate_money) - float(opponent_money) if is_valid else None
        )
        score = None
        if is_valid:
            score = 1.0 if margin > 0 else 0.0 if margin < 0 else 0.5
        rows.append(
            {
                **cells[exact_key],
                "raw_report": _relative(RAW_REPORT_PATH),
                "raw_report_sha256": _sha256(RAW_REPORT_PATH),
                "raw_report_row_index": index,
                "candidate_money": candidate_money,
                "opponent_money": opponent_money,
                "margin": margin,
                "score": score,
                "candidate_status": raw["candidate_status"],
                "opponent_status": raw["opponent_status"],
                "error": raw["error"],
                "hidden_abnormal_status": abnormal,
                "elapsed_seconds": raw["elapsed_seconds"],
                "effective_configuration_sha256": raw[
                    "effective_configuration_sha256"
                ],
                "environment_configuration_sha256": raw[
                    "environment_configuration_sha256"
                ],
                "resolved_environment_seed": raw["resolved_environment_seed"],
            }
        )
    if {row["exact_cell_key"] for row in rows} != set(cells):
        raise RuntimeError("executed cells do not equal registry")

    rows.sort(key=lambda row: row["exact_cell_key"])
    raw_games_path = HERE / "raw_games.json"
    _write(
        raw_games_path,
        {
            "schema_version": 1,
            "run_id": config["run_id"],
            "created_at_utc": _now(),
            "cell_registry": _relative(REGISTRY_PATH),
            "cell_registry_sha256": _sha256(REGISTRY_PATH),
            "records": rows,
        },
    )
    by_opponent = {
        opponent["alias"]: _aggregate(
            [row for row in rows if row["opponent"] == opponent["alias"]]
        )
        for opponent in config["opponents"]
    }
    summary_path = HERE / "summary.json"
    summary = {
        "schema_version": 1,
        "run_id": config["run_id"],
        "created_at_utc": _now(),
        "verdict": "ADDENDUM_SCREEN_EXECUTED_NON_PROMOTION",
        "relationship": config["relationship"],
        "authority": config["authority"],
        "seed_policy": config["seed_policy"],
        "candidate": config["candidate"],
        "notebook_provenance": config["notebook_provenance"],
        "engine": config["engine"],
        "executed_cells": len(rows),
        "overall": _aggregate(rows),
        "by_opponent": by_opponent,
        "provenance": {
            "config": {"path": _relative(CONFIG_PATH), "sha256": _sha256(CONFIG_PATH)},
            "cell_registry": {
                "path": _relative(REGISTRY_PATH),
                "sha256": _sha256(REGISTRY_PATH),
            },
            "raw_report": {
                "path": _relative(RAW_REPORT_PATH),
                "sha256": _sha256(RAW_REPORT_PATH),
            },
            "raw_games": {
                "path": _relative(raw_games_path),
                "sha256": _sha256(raw_games_path),
            },
            "completed_receipt": {
                "path": _relative(completed_path),
                "sha256": _sha256(completed_path),
            },
        },
        "definitions": {
            "score": "Win=1, tie=0.5, loss=0 over valid games.",
            "margin": "Ray candidate final reward minus opponent final reward.",
            "runtime": "Whole-game wall time for engine plus both agents.",
            "hidden_abnormal_status": (
                "First env.steps status outside ACTIVE/INACTIVE/DONE caught by the "
                "hardened runner before a terminal DONE can hide it."
            ),
        },
        "limitations": [
            "All seeds are consumed and promotion-ineligible.",
            "Sixteen cells per opponent are a screen, not a confidence-qualified promotion set.",
            "Notebook best score 2927.4 is remote inventory context, not this local agent result.",
            "The candidate file's C45 docstring and C64_HORIZON25 version marker disagree.",
        ],
    }
    _write(summary_path, summary)
    print(
        json.dumps(
            {
                "summary": _relative(summary_path),
                "summary_sha256": _sha256(summary_path),
                "games": len(rows),
                "failures": summary["overall"]["failures"],
                "hidden_abnormal": summary["overall"][
                    "hidden_abnormal_status_failures"
                ],
                "match_score": summary["overall"]["match_score"],
                "margin_mean": summary["overall"]["margin"]["mean"],
            },
            indent=2,
        )
    )


def manifest() -> None:
    config = _config()
    manifest_path = HERE / "manifest.json"
    sidecar_path = HERE / "manifest.sha256"
    if manifest_path.exists() or sidecar_path.exists():
        raise FileExistsError("refusing to overwrite manifest")
    required = [
        HERE / "README.md",
        HERE / "summary.json",
        HERE / "raw_games.json",
        HERE / "verification" / "pytest.txt",
        HERE / "verification" / "ruff.txt",
    ]
    missing = [path for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"manifest prerequisites missing: {missing}")
    artifacts = {
        path.relative_to(HERE).as_posix(): {
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in sorted(HERE.rglob("*"))
        if path.is_file()
        and path not in (manifest_path, sidecar_path)
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    }
    completed = _load(HERE / "receipts" / "engine_1.32.6.completed.json")
    payload = {
        "schema_version": 1,
        "run_id": config["run_id"],
        "created_at_utc": _now(),
        "git_head": _git_head(),
        "artifact_root": _relative(HERE),
        "artifact_files": artifacts,
        "artifact_files_canonical_sha256": _json_sha256(artifacts),
        "external_frozen_sources_at_manifest": _source_snapshot(config),
        "phase_integrity": {
            key: completed[key]
            for key in (
                "sources_unchanged_during_phase",
                "environment_unchanged_during_phase",
                "cell_registry_unchanged_during_phase",
            )
        },
        "manifest_exclusions": [
            "manifest.json (self)",
            "manifest.sha256 (sidecar)",
            "__pycache__/**",
            "*.pyc",
        ],
    }
    _write(manifest_path, payload)
    digest = _sha256(manifest_path)
    sidecar_path.write_text(f"{digest}  manifest.json\n", encoding="ascii")
    print(
        json.dumps(
            {
                "manifest": _relative(manifest_path),
                "manifest_sha256": digest,
                "artifact_files": len(artifacts),
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Ray C45 engine-screen addendum")
    parser.add_argument("command", choices=("prepare", "run", "analyze", "manifest"))
    args = parser.parse_args()
    if args.command == "prepare":
        prepare()
    elif args.command == "run":
        run()
    elif args.command == "analyze":
        analyze()
    else:
        manifest()


if __name__ == "__main__":
    main()
