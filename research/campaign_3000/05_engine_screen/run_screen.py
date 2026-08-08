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
from collections import Counter, defaultdict
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
CELL_REGISTRY_PATH = HERE / "cell_registry.json"
ABNORMAL_RE = re.compile(
    r"framework agent failure at step=(?P<step>\d+), "
    r"player=(?P<player>\d+), status=(?P<status>[A-Z_]+)"
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _json_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
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
    return result.stdout.strip() or None if result.returncode == 0 else None


def _config() -> dict[str, Any]:
    return _load_json(CONFIG_PATH)


def _public_agents(config: dict[str, Any]) -> list[dict[str, Any]]:
    return list(config["public_agents"])


def _agent_by_alias(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {agent["alias"]: agent for agent in _public_agents(config)}


def _source_paths(config: dict[str, Any]) -> dict[str, Path]:
    paths = {
        config["runner"]["path"]: PROJECT_ROOT / config["runner"]["path"],
        config["fa04_g1"]["path"]: PROJECT_ROOT / config["fa04_g1"]["path"],
        config["public_manifest"]["path"]: (
            PROJECT_ROOT / config["public_manifest"]["path"]
        ),
        config["seed_policy"]["historical_registry_path"]: (
            PROJECT_ROOT / config["seed_policy"]["historical_registry_path"]
        ),
        "pyproject.toml": PROJECT_ROOT / "pyproject.toml",
        "uv.lock": PROJECT_ROOT / "uv.lock",
        _relative(CONFIG_PATH): CONFIG_PATH,
        _relative(HERE / "run_screen.py"): HERE / "run_screen.py",
    }
    for agent in _public_agents(config):
        paths[agent["path"]] = PROJECT_ROOT / agent["path"]
    return paths


def _source_snapshot(config: dict[str, Any]) -> dict[str, Any]:
    files = {
        name: {"bytes": path.stat().st_size, "sha256": _sha256(path)}
        for name, path in sorted(_source_paths(config).items())
    }
    return {"files": files, "snapshot_sha256": _json_sha256(files)}


def _distribution_files_snapshot() -> dict[str, dict[str, Any]]:
    dist = distribution("kaggle-environments")
    selected: dict[str, dict[str, Any]] = {}
    for item in dist.files or []:
        item_text = str(item).replace("\\", "/")
        if not item_text.endswith((".dist-info/METADATA", ".dist-info/WHEEL")):
            continue
        path = Path(dist.locate_file(item))
        selected[item_text] = {"bytes": path.stat().st_size, "sha256": _sha256(path)}
    return selected


def _environment_snapshot(expected_version: str) -> dict[str, Any]:
    installed_version = version("kaggle-environments")
    if installed_version != expected_version:
        raise RuntimeError(
            f"expected kaggle-environments {expected_version}, got {installed_version}"
        )

    from kaggle_environments import make
    from kaggle_environments.envs.kaggriculture import kaggriculture as engine

    engine_path = Path(inspect.getsourcefile(engine) or "").resolve()
    engine_dir = engine_path.parent
    engine_files = {
        path.name: {"bytes": path.stat().st_size, "sha256": _sha256(path)}
        for path in sorted(engine_dir.iterdir())
        if path.is_file()
    }
    env = make(
        "kaggriculture",
        configuration={"episodeSteps": 720, "seed": 23000},
        debug=False,
    )
    default_configuration = json.loads(
        json.dumps(dict(env.configuration), sort_keys=True)
    )
    stable = {
        "kaggle_environments_version": installed_version,
        "python_version": platform.python_version(),
        "python_executable": str(Path(sys.executable).resolve()),
        "engine_directory": str(engine_dir),
        "engine_files": engine_files,
        "engine_files_sha256": _json_sha256(engine_files),
        "distribution_metadata_files": _distribution_files_snapshot(),
        "default_environment_configuration": default_configuration,
        "default_environment_configuration_sha256": _json_sha256(default_configuration),
    }
    stable["snapshot_sha256"] = _json_sha256(stable)
    return stable


def _validate_frozen_inputs(config: dict[str, Any], expected_version: str) -> None:
    checks = [
        (config["runner"], "runner"),
        (config["fa04_g1"], "fa04_g1"),
        (config["public_manifest"], "public_manifest"),
        *[(agent, agent["alias"]) for agent in _public_agents(config)],
    ]
    for record, label in checks:
        path = PROJECT_ROOT / record["path"]
        actual = _sha256(path)
        if actual != record["sha256"]:
            raise RuntimeError(f"{label} SHA mismatch: expected {record['sha256']}, got {actual}")
        if "bytes" in record and path.stat().st_size != record["bytes"]:
            raise RuntimeError(f"{label} byte-size mismatch")

    registry = config["seed_policy"]
    registry_path = PROJECT_ROOT / registry["historical_registry_path"]
    if _sha256(registry_path) != registry["historical_registry_sha256"]:
        raise RuntimeError("historical seed registry SHA mismatch")

    runner_text = (PROJECT_ROOT / config["runner"]["path"]).read_text(encoding="utf-8")
    if config["runner"]["required_failure_guard"] not in runner_text:
        raise RuntimeError("hardened runner failure guard is absent")

    public_manifest = _load_json(PROJECT_ROOT / config["public_manifest"]["path"])
    manifest_hashes = {item["output_sha256"] for item in public_manifest["agents"]}
    configured_hashes = {item["sha256"] for item in _public_agents(config)}
    if manifest_hashes != configured_hashes:
        raise RuntimeError("public-agent manifest and screen config disagree")

    for agent in _public_agents(config):
        source = (PROJECT_ROOT / agent["path"]).read_bytes()
        compile(source, agent["path"], "exec")

    environment = _environment_snapshot(expected_version)
    expected_engine_sha = next(
        item["kaggriculture_py_sha256"]
        for item in config["engines"].values()
        if item["version"] == expected_version
    )
    actual_engine_sha = environment["engine_files"]["kaggriculture.py"]["sha256"]
    if actual_engine_sha != expected_engine_sha:
        raise RuntimeError(
            f"engine SHA mismatch: expected {expected_engine_sha}, got {actual_engine_sha}"
        )


def _logical_cell_key(
    lane: str,
    candidate: str,
    opponent: str,
    seed: int,
    seat: int,
) -> str:
    return (
        f"lane={lane}|candidate={candidate}|opponent={opponent}|seed={seed}|"
        f"candidate_seat={seat}|scenario=default"
    )


def _cell_record(
    engine_version: str,
    lane: str,
    candidate: str,
    opponent: str,
    seed: int,
    seat: int,
    raw_report: str,
    role: str,
) -> dict[str, Any]:
    logical_key = _logical_cell_key(lane, candidate, opponent, seed, seat)
    return {
        "exact_cell_key": f"engine={engine_version}|{logical_key}",
        "logical_cell_key": logical_key,
        "engine_version": engine_version,
        "lane": lane,
        "candidate": candidate,
        "opponent": opponent,
        "seed": seed,
        "seed_status": "CONSUMED_SCREEN",
        "candidate_seat": seat,
        "scenario": "default",
        "role": role,
        "raw_report": raw_report,
    }


def _report_path(version_value: str, lane: str, candidate: str) -> str:
    return (
        f"research/campaign_3000/05_engine_screen/raw/engine_{version_value}/"
        f"{lane}/{candidate}.json"
    )


def _build_cell_registry(config: dict[str, Any]) -> dict[str, Any]:
    aliases = [agent["alias"] for agent in _public_agents(config)]
    seeds = config["seed_policy"]["seeds"]
    comparison_seeds = config["seed_policy"]["comparison_seeds"]
    cells: list[dict[str, Any]] = []

    for alias in aliases:
        report = _report_path("1.32.6", "fa04_g1", alias)
        for seed in seeds:
            for seat in (0, 1):
                cells.append(
                    _cell_record(
                        "1.32.6",
                        "fa04_g1",
                        alias,
                        "fa04_g1",
                        seed,
                        seat,
                        report,
                        "main_screen",
                    )
                )

    for index, alias in enumerate(aliases[:-1]):
        report = _report_path("1.32.6", "public_round_robin", alias)
        for opponent in aliases[index + 1 :]:
            for seed in seeds:
                for seat in (0, 1):
                    cells.append(
                        _cell_record(
                            "1.32.6",
                            "public_round_robin",
                            alias,
                            opponent,
                            seed,
                            seat,
                            report,
                            "main_screen",
                        )
                    )

    for alias in aliases:
        report = _report_path("1.32.2", "fa04_g1", alias)
        for seed in comparison_seeds:
            for seat in (0, 1):
                cells.append(
                    _cell_record(
                        "1.32.2",
                        "fa04_g1",
                        alias,
                        "fa04_g1",
                        seed,
                        seat,
                        report,
                        "engine_comparison",
                    )
                )

    keys = [cell["exact_cell_key"] for cell in cells]
    if len(keys) != len(set(keys)):
        raise RuntimeError("duplicate exact cell key")
    expected = config["design"]["registry_total_engine_specific_cells"]
    if len(cells) != expected:
        raise RuntimeError(f"expected {expected} registry cells, got {len(cells)}")
    core = {
        "schema_version": 1,
        "run_id": config["run_id"],
        "seed_status": "CONSUMED_SCREEN",
        "promotion_eligible": False,
        "cells": cells,
    }
    return {**core, "canonical_registry_sha256": _json_sha256(core)}


def prepare() -> None:
    config = _config()
    _validate_frozen_inputs(config, config["engines"]["main"]["version"])
    registry = _build_cell_registry(config)
    _write_json(CELL_REGISTRY_PATH, registry)
    print(
        json.dumps(
            {
                "cell_registry": _relative(CELL_REGISTRY_PATH),
                "file_sha256": _sha256(CELL_REGISTRY_PATH),
                "canonical_registry_sha256": registry["canonical_registry_sha256"],
                "cells": len(registry["cells"]),
                "seed_status": registry["seed_status"],
            },
            indent=2,
        )
    )


def _phase_reports(
    config: dict[str, Any], engine_version: str
) -> list[dict[str, Any]]:
    aliases = [agent["alias"] for agent in _public_agents(config)]
    if engine_version == "1.32.6":
        reports = [
            {
                "lane": "fa04_g1",
                "candidate": alias,
                "opponents": ["fa04_g1"],
                "seeds": config["seed_policy"]["seeds"],
                "path": _report_path(engine_version, "fa04_g1", alias),
            }
            for alias in aliases
        ]
        reports.extend(
            {
                "lane": "public_round_robin",
                "candidate": alias,
                "opponents": aliases[index + 1 :],
                "seeds": config["seed_policy"]["seeds"],
                "path": _report_path(engine_version, "public_round_robin", alias),
            }
            for index, alias in enumerate(aliases[:-1])
        )
        return reports
    if engine_version == "1.32.2":
        return [
            {
                "lane": "fa04_g1",
                "candidate": alias,
                "opponents": ["fa04_g1"],
                "seeds": config["seed_policy"]["comparison_seeds"],
                "path": _report_path(engine_version, "fa04_g1", alias),
            }
            for alias in aliases
        ]
    raise ValueError(f"unsupported engine version: {engine_version}")


def _register_opponents(config: dict[str, Any]) -> None:
    runner.OPPONENT_PATHS[config["fa04_g1"]["alias"]] = Path(
        config["fa04_g1"]["path"]
    )
    for agent in _public_agents(config):
        runner.OPPONENT_PATHS[agent["alias"]] = Path(agent["path"])


def _phase_receipt_path(engine_version: str, suffix: str) -> Path:
    return HERE / "receipts" / f"engine_{engine_version}.{suffix}.json"


def _artifact_hashes_for_reports(reports: list[dict[str, Any]]) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    for spec in reports:
        report_path = PROJECT_ROOT / spec["path"]
        started_path = report_path.with_name(f"{report_path.stem}.started.json")
        artifacts[_relative(report_path)] = _sha256(report_path)
        artifacts[_relative(started_path)] = _sha256(started_path)
    return dict(sorted(artifacts.items()))


def run_phase(engine_version: str) -> None:
    config = _config()
    if not CELL_REGISTRY_PATH.is_file():
        raise FileNotFoundError("run prepare before an engine phase")
    _validate_frozen_inputs(config, engine_version)
    reports = _phase_reports(config, engine_version)
    start_path = _phase_receipt_path(engine_version, "started")
    complete_path = _phase_receipt_path(engine_version, "completed")
    target_paths = [PROJECT_ROOT / spec["path"] for spec in reports]
    occupied = [
        path
        for report_path in target_paths
        for path in (report_path, report_path.with_name(f"{report_path.stem}.started.json"))
        if path.exists()
    ]
    occupied.extend(path for path in (start_path, complete_path) if path.exists())
    if occupied:
        raise FileExistsError(f"refusing to overwrite phase evidence: {occupied}")

    source_start = _source_snapshot(config)
    environment_start = _environment_snapshot(engine_version)
    start_receipt = {
        "schema_version": 1,
        "run_id": config["run_id"],
        "engine_version": engine_version,
        "started_at_utc": _now(),
        "git_head_at_start": _git_head(),
        "authority": config["authority"],
        "seed_policy": config["seed_policy"],
        "workers": config["execution"]["workers"],
        "seat_policy": config["execution"]["seat_policy"],
        "scenario_override": config["execution"]["scenario_override"],
        "cell_registry_path": _relative(CELL_REGISTRY_PATH),
        "cell_registry_sha256_at_start": _sha256(CELL_REGISTRY_PATH),
        "planned_reports": reports,
        "planned_cells": sum(
            len(spec["opponents"]) * len(spec["seeds"]) * 2 for spec in reports
        ),
        "sources_at_start": source_start,
        "environment_at_start": environment_start,
    }
    _write_json(start_path, start_receipt)
    start_receipt_sha = _sha256(start_path)

    _register_opponents(config)
    agents = _agent_by_alias(config)
    for spec in reports:
        output = PROJECT_ROOT / spec["path"]
        report = runner.run_batch(
            agents[spec["candidate"]]["path"],
            spec["opponents"],
            spec["seeds"],
            output,
            config["execution"]["workers"],
            PROJECT_ROOT,
            {"default": config["execution"]["scenario_override"]},
        )
        expected_games = len(spec["opponents"]) * len(spec["seeds"]) * 2
        if report["summary"]["raw_games"] != expected_games:
            raise RuntimeError(f"{spec['path']} returned the wrong game count")
        if not report["sources_unchanged_during_run"]:
            raise RuntimeError(f"{spec['path']} source changed during runner batch")
        print(
            json.dumps(
                {
                    "engine": engine_version,
                    "lane": spec["lane"],
                    "candidate": spec["candidate"],
                    "games": expected_games,
                    "failures": report["summary"]["failed_raw_games"],
                    "match_score": report["summary"]["match_score"],
                    "margin_mean": report["summary"]["margin_mean"],
                    "elapsed_seconds_total": report["summary"]["elapsed_seconds_total"],
                },
                sort_keys=True,
            ),
            flush=True,
        )

    source_end = _source_snapshot(config)
    environment_end = _environment_snapshot(engine_version)
    artifact_hashes = _artifact_hashes_for_reports(reports)
    completed_receipt = {
        "schema_version": 1,
        "run_id": config["run_id"],
        "engine_version": engine_version,
        "completed_at_utc": _now(),
        "git_head_at_end": _git_head(),
        "start_receipt": _relative(start_path),
        "start_receipt_sha256": start_receipt_sha,
        "cell_registry_sha256_at_end": _sha256(CELL_REGISTRY_PATH),
        "sources_at_end": source_end,
        "environment_at_end": environment_end,
        "sources_unchanged_during_phase": (
            source_start["snapshot_sha256"] == source_end["snapshot_sha256"]
        ),
        "environment_unchanged_during_phase": (
            environment_start["snapshot_sha256"] == environment_end["snapshot_sha256"]
        ),
        "config_unchanged_during_phase": (
            source_start["files"][_relative(CONFIG_PATH)]["sha256"]
            == source_end["files"][_relative(CONFIG_PATH)]["sha256"]
        ),
        "cell_registry_unchanged_during_phase": (
            start_receipt["cell_registry_sha256_at_start"] == _sha256(CELL_REGISTRY_PATH)
        ),
        "raw_artifacts": artifact_hashes,
        "executed_reports": len(reports),
        "executed_cells": sum(
            len(spec["opponents"]) * len(spec["seeds"]) * 2 for spec in reports
        ),
    }
    _write_json(complete_path, completed_receipt)
    integrity = [
        completed_receipt["sources_unchanged_during_phase"],
        completed_receipt["environment_unchanged_during_phase"],
        completed_receipt["config_unchanged_during_phase"],
        completed_receipt["cell_registry_unchanged_during_phase"],
    ]
    if not all(integrity):
        raise RuntimeError(f"phase {engine_version} provenance changed during execution")
    print(
        json.dumps(
            {
                "completed_receipt": _relative(complete_path),
                "sha256": _sha256(complete_path),
                "executed_cells": completed_receipt["executed_cells"],
                "integrity": "PASS",
            },
            indent=2,
        )
    )


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _valid(record: dict[str, Any]) -> bool:
    return bool(
        record["error"] is None
        and record["candidate_status"] == "DONE"
        and record["opponent_status"] == "DONE"
        and record["candidate_money"] is not None
        and record["opponent_money"] is not None
    )


def _aggregate(records: list[dict[str, Any]], include_seats: bool = True) -> dict[str, Any]:
    valid = [record for record in records if _valid(record)]
    scores = [float(record["score"]) for record in valid]
    money = [float(record["candidate_money"]) for record in valid]
    margins = [float(record["margin"]) for record in valid]
    runtimes = [float(record["elapsed_seconds"]) for record in records]
    result = {
        "raw_games": len(records),
        "valid_games": len(valid),
        "failures": len(records) - len(valid),
        "hidden_abnormal_status_failures": sum(
            record["hidden_abnormal_status"] is not None for record in records
        ),
        "status_pairs": dict(
            sorted(
                Counter(
                    f"{record['candidate_status']}/{record['opponent_status']}"
                    for record in records
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
            "mean": statistics.mean(runtimes) if runtimes else None,
            "median": statistics.median(runtimes) if runtimes else None,
            "p95": _percentile(runtimes, 0.95),
            "p99": _percentile(runtimes, 0.99),
            "max": max(runtimes) if runtimes else None,
            "total": sum(runtimes),
        },
        "failure_examples": [
            {
                "exact_cell_key": record["exact_cell_key"],
                "error": record["error"],
                "hidden_abnormal_status": record["hidden_abnormal_status"],
            }
            for record in records
            if not _valid(record)
        ][:10],
    }
    if include_seats:
        result["by_candidate_seat"] = {
            str(seat): _aggregate(
                [record for record in records if record["candidate_seat"] == seat],
                include_seats=False,
            )
            for seat in (0, 1)
        }
    return result


def _score(candidate_money: float, opponent_money: float) -> float:
    if candidate_money > opponent_money:
        return 1.0
    if candidate_money < opponent_money:
        return 0.0
    return 0.5


def _raw_records(config: dict[str, Any]) -> list[dict[str, Any]]:
    registry = _load_json(CELL_REGISTRY_PATH)
    registered = {cell["exact_cell_key"]: cell for cell in registry["cells"]}
    records: list[dict[str, Any]] = []
    for engine_version in ("1.32.6", "1.32.2"):
        for spec in _phase_reports(config, engine_version):
            report_path = PROJECT_ROOT / spec["path"]
            report = _load_json(report_path)
            report_sha = _sha256(report_path)
            for row_index, row in enumerate(report["games"]):
                logical_key = _logical_cell_key(
                    spec["lane"],
                    spec["candidate"],
                    row["opponent"],
                    int(row["seed"]),
                    int(row["seat"]),
                )
                exact_key = f"engine={engine_version}|{logical_key}"
                if exact_key not in registered:
                    raise RuntimeError(f"unregistered executed cell: {exact_key}")
                abnormal_match = ABNORMAL_RE.search(row["error"] or "")
                abnormal: dict[str, Any] | None = None
                abnormal_agent: str | None = None
                if abnormal_match:
                    player = int(abnormal_match.group("player"))
                    abnormal_agent = (
                        spec["candidate"]
                        if player == int(row["seat"])
                        else row["opponent"]
                    )
                    abnormal = {
                        "step": int(abnormal_match.group("step")),
                        "player": player,
                        "status": abnormal_match.group("status"),
                        "agent": abnormal_agent,
                    }
                is_valid = bool(
                    row["error"] is None
                    and row["candidate_status"] == "DONE"
                    and row["opponent_status"] == "DONE"
                    and row["candidate_money"] is not None
                    and row["opponent_money"] is not None
                )
                candidate_money = row["candidate_money"]
                opponent_money = row["opponent_money"]
                records.append(
                    {
                        **registered[exact_key],
                        "raw_report_sha256": report_sha,
                        "raw_report_row_index": row_index,
                        "candidate_money": candidate_money,
                        "opponent_money": opponent_money,
                        "margin": (
                            float(candidate_money) - float(opponent_money)
                            if is_valid
                            else None
                        ),
                        "score": (
                            _score(float(candidate_money), float(opponent_money))
                            if is_valid
                            else None
                        ),
                        "candidate_status": row["candidate_status"],
                        "opponent_status": row["opponent_status"],
                        "error": row["error"],
                        "hidden_abnormal_status": abnormal,
                        "abnormal_agent": abnormal_agent,
                        "elapsed_seconds": row["elapsed_seconds"],
                        "effective_configuration_sha256": row[
                            "effective_configuration_sha256"
                        ],
                        "environment_configuration_sha256": row.get(
                            "environment_configuration_sha256"
                        ),
                        "resolved_environment_seed": row.get(
                            "resolved_environment_seed"
                        ),
                    }
                )
    executed = {record["exact_cell_key"] for record in records}
    if len(executed) != len(records):
        raise RuntimeError("duplicate executed exact cell key")
    if executed != set(registered):
        missing = sorted(set(registered) - executed)
        extra = sorted(executed - set(registered))
        raise RuntimeError(f"cell registry mismatch; missing={missing}, extra={extra}")
    return sorted(records, key=lambda record: record["exact_cell_key"])


def _perspective(record: dict[str, Any], agent: str) -> dict[str, Any]:
    if record["candidate"] == agent:
        return record
    if record["opponent"] != agent:
        raise ValueError(f"agent {agent} not present in cell")
    swapped = dict(record)
    swapped["candidate"] = agent
    swapped["opponent"] = record["candidate"]
    swapped["candidate_seat"] = 1 - int(record["candidate_seat"])
    swapped["candidate_money"] = record["opponent_money"]
    swapped["opponent_money"] = record["candidate_money"]
    swapped["candidate_status"] = record["opponent_status"]
    swapped["opponent_status"] = record["candidate_status"]
    if _valid(record):
        swapped["margin"] = -float(record["margin"])
        swapped["score"] = 1.0 - float(record["score"])
    return swapped


def _result_vector_groups(
    records: list[dict[str, Any]], aliases: list[str]
) -> list[dict[str, Any]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for alias in aliases:
        vector = [
            (
                record["seed"],
                record["candidate_seat"],
                record["candidate_money"],
                record["opponent_money"],
                record["candidate_status"],
                record["opponent_status"],
                record["error"],
            )
            for record in sorted(
                (item for item in records if item["candidate"] == alias),
                key=lambda item: (item["seed"], item["candidate_seat"]),
            )
        ]
        groups[_json_sha256(vector)].append(alias)
    return [
        {"result_vector_sha256": vector_hash, "agents": group}
        for vector_hash, group in sorted(groups.items())
    ]


def _configuration_diff(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    keys = sorted(set(old) | set(new))
    return {
        key: {"engine_1.32.2": old.get(key), "engine_1.32.6": new.get(key)}
        for key in keys
        if old.get(key) != new.get(key)
    }


def _mean(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def _engine_comparison(
    config: dict[str, Any], records: list[dict[str, Any]]
) -> dict[str, Any]:
    comparison_seeds = set(config["seed_policy"]["comparison_seeds"])
    old = {
        record["logical_cell_key"]: record
        for record in records
        if record["engine_version"] == "1.32.2"
    }
    new = {
        record["logical_cell_key"]: record
        for record in records
        if record["engine_version"] == "1.32.6"
        and record["lane"] == "fa04_g1"
        and record["seed"] in comparison_seeds
    }
    if set(old) != set(new):
        raise RuntimeError("engine comparison logical-cell sets differ")

    pairs: list[dict[str, Any]] = []
    for logical_key in sorted(old):
        before = old[logical_key]
        after = new[logical_key]
        both_valid = _valid(before) and _valid(after)
        pairs.append(
            {
                "logical_cell_key": logical_key,
                "engine_1.32.2_exact_cell_key": before["exact_cell_key"],
                "engine_1.32.6_exact_cell_key": after["exact_cell_key"],
                "candidate": before["candidate"],
                "seed": before["seed"],
                "candidate_seat": before["candidate_seat"],
                "valid_under_both": both_valid,
                "result_equal_excluding_runtime": all(
                    before[key] == after[key]
                    for key in (
                        "candidate_money",
                        "opponent_money",
                        "candidate_status",
                        "opponent_status",
                        "error",
                    )
                ),
                "outcome_changed": (
                    before["score"] != after["score"] if both_valid else None
                ),
                "candidate_money_1.32.2": before["candidate_money"],
                "candidate_money_1.32.6": after["candidate_money"],
                "candidate_money_delta_1.32.6_minus_1.32.2": (
                    float(after["candidate_money"]) - float(before["candidate_money"])
                    if both_valid
                    else None
                ),
                "opponent_money_1.32.2": before["opponent_money"],
                "opponent_money_1.32.6": after["opponent_money"],
                "opponent_money_delta_1.32.6_minus_1.32.2": (
                    float(after["opponent_money"]) - float(before["opponent_money"])
                    if both_valid
                    else None
                ),
                "margin_1.32.2": before["margin"],
                "margin_1.32.6": after["margin"],
                "margin_delta_1.32.6_minus_1.32.2": (
                    float(after["margin"]) - float(before["margin"])
                    if both_valid
                    else None
                ),
                "runtime_seconds_1.32.2": before["elapsed_seconds"],
                "runtime_seconds_1.32.6": after["elapsed_seconds"],
                "environment_configuration_sha256_1.32.2": before[
                    "environment_configuration_sha256"
                ],
                "environment_configuration_sha256_1.32.6": after[
                    "environment_configuration_sha256"
                ],
            }
        )

    old_start = _load_json(_phase_receipt_path("1.32.2", "started"))
    new_start = _load_json(_phase_receipt_path("1.32.6", "started"))
    old_default = old_start["environment_at_start"]["default_environment_configuration"]
    new_default = new_start["environment_at_start"]["default_environment_configuration"]

    valid_pairs = [pair for pair in pairs if pair["valid_under_both"]]
    candidate_deltas = [
        float(pair["candidate_money_delta_1.32.6_minus_1.32.2"])
        for pair in valid_pairs
    ]
    opponent_deltas = [
        float(pair["opponent_money_delta_1.32.6_minus_1.32.2"])
        for pair in valid_pairs
    ]
    margin_deltas = [
        float(pair["margin_delta_1.32.6_minus_1.32.2"])
        for pair in valid_pairs
    ]
    aliases = [agent["alias"] for agent in _public_agents(config)]
    summary = {
        "paired_logical_cells": len(pairs),
        "valid_under_both": len(valid_pairs),
        "result_equal_excluding_runtime": sum(
            pair["result_equal_excluding_runtime"] for pair in pairs
        ),
        "result_changed_excluding_runtime": sum(
            not pair["result_equal_excluding_runtime"] for pair in pairs
        ),
        "outcome_changed": sum(pair["outcome_changed"] is True for pair in pairs),
        "candidate_money_delta_1.32.6_minus_1.32.2": {
            "mean": _mean(candidate_deltas),
            "median": statistics.median(candidate_deltas) if candidate_deltas else None,
            "min": min(candidate_deltas) if candidate_deltas else None,
            "max": max(candidate_deltas) if candidate_deltas else None,
        },
        "opponent_money_delta_1.32.6_minus_1.32.2": {
            "mean": _mean(opponent_deltas),
            "median": statistics.median(opponent_deltas) if opponent_deltas else None,
            "min": min(opponent_deltas) if opponent_deltas else None,
            "max": max(opponent_deltas) if opponent_deltas else None,
        },
        "margin_delta_1.32.6_minus_1.32.2": {
            "mean": _mean(margin_deltas),
            "median": statistics.median(margin_deltas) if margin_deltas else None,
            "min": min(margin_deltas) if margin_deltas else None,
            "max": max(margin_deltas) if margin_deltas else None,
        },
        "engine_1.32.2": _aggregate(list(old.values())),
        "engine_1.32.6": _aggregate(list(new.values())),
        "by_agent": {},
    }
    for alias in aliases:
        agent_pairs = [pair for pair in pairs if pair["candidate"] == alias]
        summary["by_agent"][alias] = {
            "paired_cells": len(agent_pairs),
            "result_equal_excluding_runtime": sum(
                pair["result_equal_excluding_runtime"] for pair in agent_pairs
            ),
            "outcome_changed": sum(
                pair["outcome_changed"] is True for pair in agent_pairs
            ),
            "margin_delta_mean_1.32.6_minus_1.32.2": _mean(
                [
                    float(pair["margin_delta_1.32.6_minus_1.32.2"])
                    for pair in agent_pairs
                    if pair["valid_under_both"]
                ]
            ),
        }

    return {
        "schema_version": 1,
        "run_id": config["run_id"],
        "comparison_definition": (
            "Same candidate, Fa04 G1 opponent, seed, candidate seat, default scenario, "
            "and exact agent bytes; only kaggle-environments version changes."
        ),
        "comparison_seeds": config["seed_policy"]["comparison_seeds"],
        "seed_status": "CONSUMED_SCREEN",
        "default_environment_configuration_sha256": {
            "1.32.2": old_start["environment_at_start"][
                "default_environment_configuration_sha256"
            ],
            "1.32.6": new_start["environment_at_start"][
                "default_environment_configuration_sha256"
            ],
        },
        "default_environment_configuration_diff": _configuration_diff(
            old_default, new_default
        ),
        "summary": summary,
        "pairs": pairs,
    }


def analyze() -> None:
    config = _config()
    for engine_version in ("1.32.6", "1.32.2"):
        completed = _load_json(_phase_receipt_path(engine_version, "completed"))
        integrity_keys = (
            "sources_unchanged_during_phase",
            "environment_unchanged_during_phase",
            "config_unchanged_during_phase",
            "cell_registry_unchanged_during_phase",
        )
        if not all(completed[key] for key in integrity_keys):
            raise RuntimeError(f"engine {engine_version} phase receipt failed integrity")

    records = _raw_records(config)
    raw_payload = {
        "schema_version": 1,
        "run_id": config["run_id"],
        "created_at_utc": _now(),
        "cell_registry": _relative(CELL_REGISTRY_PATH),
        "cell_registry_sha256": _sha256(CELL_REGISTRY_PATH),
        "records": records,
    }
    raw_path = HERE / "raw_games.json"
    _write_json(raw_path, raw_payload)

    aliases = [agent["alias"] for agent in _public_agents(config)]
    main = [record for record in records if record["engine_version"] == "1.32.6"]
    fa04 = [record for record in main if record["lane"] == "fa04_g1"]
    round_robin = [
        record for record in main if record["lane"] == "public_round_robin"
    ]

    fa04_by_agent = {
        alias: _aggregate([record for record in fa04 if record["candidate"] == alias])
        for alias in aliases
    }
    rr_pairs = {
        f"{candidate}__vs__{opponent}": _aggregate(
            [
                record
                for record in round_robin
                if record["candidate"] == candidate and record["opponent"] == opponent
            ]
        )
        for candidate in aliases
        for opponent in aliases
        if any(
            record["candidate"] == candidate and record["opponent"] == opponent
            for record in round_robin
        )
    }
    rr_standings: dict[str, Any] = {}
    for alias in aliases:
        perspective = [
            _perspective(record, alias)
            for record in round_robin
            if alias in (record["candidate"], record["opponent"])
        ]
        rr_standings[alias] = {
            **_aggregate(perspective),
            "attributed_hidden_abnormal_failures": sum(
                record["abnormal_agent"] == alias for record in round_robin
            ),
        }

    comparison = _engine_comparison(config, records)
    comparison_path = HERE / "engine_comparison.json"
    _write_json(comparison_path, comparison)

    completed_receipts = {
        engine_version: {
            "path": _relative(_phase_receipt_path(engine_version, "completed")),
            "sha256": _sha256(_phase_receipt_path(engine_version, "completed")),
        }
        for engine_version in ("1.32.6", "1.32.2")
    }
    summary = {
        "schema_version": 1,
        "run_id": config["run_id"],
        "created_at_utc": _now(),
        "verdict": "SCREEN_EXECUTED_NON_PROMOTION",
        "seed_policy": config["seed_policy"],
        "authority": config["authority"],
        "provenance": {
            "config": {"path": _relative(CONFIG_PATH), "sha256": _sha256(CONFIG_PATH)},
            "cell_registry": {
                "path": _relative(CELL_REGISTRY_PATH),
                "sha256": _sha256(CELL_REGISTRY_PATH),
            },
            "raw_games": {"path": _relative(raw_path), "sha256": _sha256(raw_path)},
            "engine_comparison": {
                "path": _relative(comparison_path),
                "sha256": _sha256(comparison_path),
            },
            "completed_receipts": completed_receipts,
        },
        "executed_cells": {
            "engine_1.32.6": len(main),
            "engine_1.32.6_fa04_g1": len(fa04),
            "engine_1.32.6_public_round_robin": len(round_robin),
            "engine_1.32.2_comparison": sum(
                record["engine_version"] == "1.32.2" for record in records
            ),
            "engine_specific_total": len(records),
        },
        "engine_1.32.6_fa04_g1": {
            "overall": _aggregate(fa04),
            "by_public_agent": fa04_by_agent,
            "equal_result_vector_groups": _result_vector_groups(fa04, aliases),
        },
        "engine_1.32.6_public_round_robin": {
            "overall_runner_candidate_perspective": _aggregate(round_robin),
            "pair_results": rr_pairs,
            "agent_standings": rr_standings,
        },
        "engine_comparison": comparison["summary"],
        "definitions": {
            "failure": (
                "A row is invalid if runner error is non-null, either terminal status is not "
                "DONE, or either reward is null."
            ),
            "hidden_abnormal_status": (
                "The hardened runner scans all env.steps and records the first status outside "
                "ACTIVE/INACTIVE/DONE, even if the terminal interpreter later reports DONE."
            ),
            "score": "Win=1, tie=0.5, loss=0, calculated only for valid rows.",
            "margin": "candidate final reward minus opponent final reward.",
            "runtime": (
                "Wall-clock seconds for the whole local game, not isolated per-agent compute."
            ),
        },
        "limitations": [
            "All seeds are consumed development-screen seeds and are promotion-ineligible.",
            "The 1.32.2/1.32.6 comparison has only 20 paired logical cells.",
            "Local game wall time includes engine and both agents.",
            "Equal result vectors do not prove source equivalence or action-trace equivalence.",
        ],
    }
    summary_path = HERE / "summary.json"
    _write_json(summary_path, summary)
    print(
        json.dumps(
            {
                "summary": _relative(summary_path),
                "summary_sha256": _sha256(summary_path),
                "raw_records": len(records),
                "main_failures": _aggregate(main)["failures"],
                "main_hidden_abnormal": _aggregate(main)[
                    "hidden_abnormal_status_failures"
                ],
                "comparison_result_changes": comparison["summary"][
                    "result_changed_excluding_runtime"
                ],
            },
            indent=2,
        )
    )


def manifest() -> None:
    config = _config()
    manifest_path = HERE / "manifest.json"
    sidecar_path = HERE / "manifest.sha256"
    if manifest_path.exists() or sidecar_path.exists():
        raise FileExistsError("refusing to overwrite manifest evidence")
    required = [
        HERE / "summary.json",
        HERE / "engine_comparison.json",
        HERE / "raw_games.json",
        HERE / "verification" / "pytest.txt",
        HERE / "verification" / "ruff.txt",
        HERE / "README.md",
    ]
    missing = [path for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"manifest prerequisites missing: {missing}")

    artifact_files = {
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
    completed_receipts = {
        engine_version: _load_json(_phase_receipt_path(engine_version, "completed"))
        for engine_version in ("1.32.6", "1.32.2")
    }
    payload = {
        "schema_version": 1,
        "run_id": config["run_id"],
        "created_at_utc": _now(),
        "git_head": _git_head(),
        "artifact_root": _relative(HERE),
        "artifact_files": artifact_files,
        "artifact_files_canonical_sha256": _json_sha256(artifact_files),
        "external_frozen_sources_at_manifest": _source_snapshot(config),
        "phase_integrity": {
            engine_version: {
                key: receipt[key]
                for key in (
                    "sources_unchanged_during_phase",
                    "environment_unchanged_during_phase",
                    "config_unchanged_during_phase",
                    "cell_registry_unchanged_during_phase",
                )
            }
            for engine_version, receipt in completed_receipts.items()
        },
        "manifest_exclusions": [
            "manifest.json (self)",
            "manifest.sha256 (manifest sidecar)",
            "__pycache__/**",
            "*.pyc",
        ],
    }
    _write_json(manifest_path, payload)
    manifest_sha = _sha256(manifest_path)
    sidecar_path.write_text(f"{manifest_sha}  manifest.json\n", encoding="ascii")
    print(
        json.dumps(
            {
                "manifest": _relative(manifest_path),
                "manifest_sha256": manifest_sha,
                "sidecar": _relative(sidecar_path),
                "artifact_files": len(artifact_files),
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Campaign 3000 engine/public-agent screen")
    parser.add_argument(
        "command",
        choices=("prepare", "run-1326", "run-1322", "analyze", "manifest"),
    )
    args = parser.parse_args()
    if args.command == "prepare":
        prepare()
    elif args.command == "run-1326":
        run_phase("1.32.6")
    elif args.command == "run-1322":
        run_phase("1.32.2")
    elif args.command == "analyze":
        analyze()
    else:
        manifest()


if __name__ == "__main__":
    main()
