from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import random
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kaggriculture_lab.evaluation.metrics import wilson_interval

PUBLIC_ROOT = Path("artifacts/opponents/public_kaggle")
NIITS_ROOT = Path("references/niits-kaggriculture")
OPPONENT_PATHS = {
    "starter": "starter",
    "harvest_pulse": PUBLIC_ROOT / "harvest_pulse.py",
    "getting_started": PUBLIC_ROOT / "getting_started.py",
    "basic_simple": PUBLIC_ROOT / "basic_simple.py",
    "diversified_scheduler": PUBLIC_ROOT / "diversified_scheduler.py",
    "visualized_guide": PUBLIC_ROOT / "visualized_guide.py",
    "pavlo_baseline": PUBLIC_ROOT / "pavlo_baseline.py",
    "barnyard_economist": PUBLIC_ROOT / "barnyard_economist.py",
    "yumerous": PUBLIC_ROOT / "yumerous.py",
    "scenario_aware": PUBLIC_ROOT / "scenario_aware.py",
    "hamburger_current": PUBLIC_ROOT / "hamburger_current.py",
    "hamburger_base": PUBLIC_ROOT / "hamburger_base.py",
    "hamburger_cow": PUBLIC_ROOT / "hamburger_current.py",
    "chaitanya_mixed": PUBLIC_ROOT / "chaitanya_mixed.py",
    "niits_pro_tier": NIITS_ROOT / "src/kaggriculture/agents/kaggle_builtin/pro_tier_agent.py",
    "niits_many_hands": NIITS_ROOT / "src/kaggriculture/agents/baseline/many_hands.py",
}


@dataclass(frozen=True)
class GameSpec:
    candidate: str
    opponent: str
    opponent_name: str
    seed: int
    seat: int
    project_root: str
    scenario: str = "default"
    configuration: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GameResult:
    opponent: str
    seed: int
    seat: int
    candidate_money: float | None
    opponent_money: float | None
    candidate_status: str
    opponent_status: str
    elapsed_seconds: float
    error: str | None
    scenario: str = "default"
    effective_configuration: dict[str, Any] = field(default_factory=dict)
    effective_configuration_sha256: str | None = None
    environment_configuration: dict[str, Any] = field(default_factory=dict)
    environment_configuration_sha256: str | None = None
    resolved_environment_seed: int | None = None


def _effective_configuration(
    override: dict[str, Any], seed: int | None = None,
) -> dict[str, Any]:
    normalized_override = json.loads(json.dumps(override, sort_keys=True))
    configuration = {"episodeSteps": 720, **normalized_override}
    if seed is not None:
        configuration["seed"] = seed
    return configuration


def _resolve(reference: str, project_root: Path) -> str:
    value: str | Path = OPPONENT_PATHS.get(reference, reference)
    if value == "starter":
        return value
    path = Path(value)
    if not path.is_absolute():
        path = project_root / path
    if not path.is_file():
        raise FileNotFoundError(f"agent not found: {path}")
    return str(path.resolve())


def _run_game(spec: GameSpec) -> GameResult:
    project_root = Path(spec.project_root)
    niits_src = str((project_root / NIITS_ROOT / "src").resolve())
    if niits_src not in sys.path:
        sys.path.insert(0, niits_src)

    started = time.perf_counter()
    try:
        from kaggle_environments import make

        configuration = _effective_configuration(spec.configuration, spec.seed)
        env = make(
            "kaggriculture",
            configuration=configuration,
            debug=False,
        )
        environment_configuration = json.loads(
            json.dumps(dict(env.configuration), sort_keys=True)
        )
        resolved_environment_seed = int(env.info["seed"])
        agents = (
            [spec.candidate, spec.opponent]
            if spec.seat == 0
            else [spec.opponent, spec.candidate]
        )
        env.run(agents)
        final = env.steps[-1]
        candidate_state = final[spec.seat]
        opponent_state = final[1 - spec.seat]
        return GameResult(
            opponent=spec.opponent_name,
            seed=spec.seed,
            seat=spec.seat,
            candidate_money=(
                float(candidate_state.reward) if candidate_state.reward is not None else None
            ),
            opponent_money=(
                float(opponent_state.reward) if opponent_state.reward is not None else None
            ),
            candidate_status=str(candidate_state.status),
            opponent_status=str(opponent_state.status),
            elapsed_seconds=time.perf_counter() - started,
            error=None,
            scenario=spec.scenario,
            effective_configuration=configuration,
            effective_configuration_sha256=_json_sha256(configuration),
            environment_configuration=environment_configuration,
            environment_configuration_sha256=_json_sha256(environment_configuration),
            resolved_environment_seed=resolved_environment_seed,
        )
    except Exception as exc:  # noqa: BLE001 - batch failures must become auditable rows
        return GameResult(
            opponent=spec.opponent_name,
            seed=spec.seed,
            seat=spec.seat,
            candidate_money=None,
            opponent_money=None,
            candidate_status="EXCEPTION",
            opponent_status="UNKNOWN",
            elapsed_seconds=time.perf_counter() - started,
            error=f"{type(exc).__name__}: {exc}",
            scenario=spec.scenario,
            effective_configuration=_effective_configuration(spec.configuration, spec.seed),
            effective_configuration_sha256=_json_sha256(
                _effective_configuration(spec.configuration, spec.seed)
            ),
        )


def _outcome(row: GameResult) -> float:
    if row.candidate_money is None or row.opponent_money is None:
        raise ValueError("outcome unavailable for failed game")
    if row.candidate_money > row.opponent_money:
        return 1.0
    if row.candidate_money < row.opponent_money:
        return 0.0
    return 0.5


def summarize(results: list[GameResult]) -> dict[str, Any]:
    valid = [
        row
        for row in results
        if row.error is None
        and row.candidate_status == "DONE"
        and row.opponent_status == "DONE"
        and row.candidate_money is not None
        and row.opponent_money is not None
    ]
    wins = sum(_outcome(row) == 1.0 for row in valid)
    losses = sum(_outcome(row) == 0.0 for row in valid)
    ties = sum(_outcome(row) == 0.5 for row in valid)
    decisive = wins + losses
    low, high = wilson_interval(wins, decisive) if decisive else (0.0, 1.0)

    by_pair: dict[tuple[str, str, int], dict[int, GameResult]] = {}
    for row in valid:
        by_pair.setdefault((row.scenario, row.opponent, row.seed), {})[row.seat] = row
    pair_scores = []
    seat_differences = []
    for (scenario, opponent, seed), seats in sorted(by_pair.items()):
        if 0 not in seats or 1 not in seats:
            seat_differences.append(
                {
                    "scenario": scenario,
                    "opponent": opponent,
                    "seed": seed,
                    "reason": "missing_seat",
                }
            )
            continue
        first, second = seats[0], seats[1]
        pair_scores.append((_outcome(first) + _outcome(second)) / 2.0)
        if (first.candidate_money, first.opponent_money) != (
            second.candidate_money,
            second.opponent_money,
        ):
            seat_differences.append(
                {
                    "scenario": scenario,
                    "opponent": opponent,
                    "seed": seed,
                    "seat0": [first.candidate_money, first.opponent_money],
                    "seat1": [second.candidate_money, second.opponent_money],
                }
            )

    cluster_ci = [0.0, 1.0]
    if pair_scores:
        rng = random.Random(0)
        boot = sorted(
            statistics.mean(rng.choice(pair_scores) for _ in pair_scores) for _ in range(10_000)
        )
        cluster_ci = [boot[249], boot[9749]]

    money = [float(row.candidate_money) for row in valid]
    margins = [float(row.candidate_money - row.opponent_money) for row in valid]
    return {
        "raw_games": len(results),
        "valid_raw_games": len(valid),
        "failed_raw_games": len(results) - len(valid),
        "seed_opponent_pairs": len(pair_scores),
        "scenario_opponent_seed_pairs": len(pair_scores),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "match_score": (wins + 0.5 * ties) / len(valid) if valid else None,
        "decisive_win_rate": wins / decisive if decisive else None,
        "decisive_win_rate_wilson_95_naive_raw_games": [low, high],
        "match_score_cluster_bootstrap_95": cluster_ci,
        "money_mean": statistics.mean(money) if money else None,
        "money_median": statistics.median(money) if money else None,
        "money_min": min(money) if money else None,
        "margin_mean": statistics.mean(margins) if margins else None,
        "margin_median": statistics.median(margins) if margins else None,
        "seat_pair_differences": seat_differences,
        "elapsed_seconds_total": sum(row.elapsed_seconds for row in results),
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _json_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def _git_head(project_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def _file_hash_or_none(reference: str) -> str | None:
    path = Path(reference)
    return _sha256(path) if path.is_file() else None


def _load_partition(path: Path, partition: str) -> tuple[list[int], list[str]]:
    config = json.loads(path.read_text(encoding="utf-8"))
    section = config[partition]
    if "seeds" not in section or "opponents" not in section:
        raise ValueError(f"partition {partition} does not define seeds and opponents")
    return [int(seed) for seed in section["seeds"]], list(section["opponents"])


def _load_scenarios(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload.get("scenarios", payload)
    if not isinstance(raw, dict) or not raw:
        raise ValueError("scenario config must define a non-empty scenarios mapping")
    scenarios: dict[str, dict[str, Any]] = {}
    for name, configuration in raw.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("scenario names must be non-empty strings")
        if not isinstance(configuration, dict):
            raise TypeError(f"scenario {name} configuration must be an object")
        forbidden = {"seed", "episodeSteps"} & configuration.keys()
        if forbidden:
            raise ValueError(
                f"scenario {name} cannot override runner-controlled keys: {sorted(forbidden)}"
            )
        scenarios[name] = configuration
    return scenarios


def run_batch(
    candidate_ref: str,
    opponents: list[str],
    seeds: list[int],
    output: Path,
    workers: int,
    project_root: Path,
    scenarios: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    candidate = _resolve(candidate_ref, project_root)
    resolved_opponents = {name: _resolve(name, project_root) for name in opponents}
    scenarios = scenarios or {"default": {}}
    if not scenarios:
        raise ValueError("at least one evaluation scenario is required")
    effective_scenarios = {
        name: _effective_configuration(configuration)
        for name, configuration in scenarios.items()
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(UTC).isoformat()
    git_head = _git_head(project_root)
    candidate_hash_start = _file_hash_or_none(candidate)
    opponent_hashes_start = {
        name: _file_hash_or_none(path) for name, path in resolved_opponents.items()
    }
    start_receipt = {
        "schema_version": 1,
        "started_at_utc": started_at,
        "git_head_at_start": git_head,
        "candidate": candidate_ref,
        "candidate_path": candidate,
        "candidate_sha256_at_start": candidate_hash_start,
        "opponents": opponents,
        "opponent_paths": resolved_opponents,
        "opponent_sha256_at_start": opponent_hashes_start,
        "seeds": seeds,
        "seat_policy": "both seats",
        "workers": workers,
        "scenario_overrides": scenarios,
        "effective_scenarios": effective_scenarios,
        "effective_scenarios_sha256": _json_sha256(effective_scenarios),
    }
    receipt_path = output.with_name(f"{output.stem}.started.json")
    receipt_path.write_text(json.dumps(start_receipt, indent=2) + "\n", encoding="utf-8")
    receipt_sha256 = _sha256(receipt_path)
    specs = [
        GameSpec(
            candidate,
            resolved_opponents[opponent_name],
            opponent_name,
            seed,
            seat,
            str(project_root),
            scenario_name,
            scenario_configuration,
        )
        for scenario_name, scenario_configuration in scenarios.items()
        for opponent_name in opponents
        for seed in seeds
        for seat in (0, 1)
    ]

    if workers == 1:
        results = [_run_game(spec) for spec in specs]
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(_run_game, specs))
    results.sort(key=lambda row: (row.scenario, row.opponent, row.seed, row.seat))

    candidate_path = Path(candidate)
    completed_at = datetime.now(UTC).isoformat()
    candidate_hash_end = _file_hash_or_none(candidate)
    opponent_hashes_end = {
        name: _file_hash_or_none(path) for name, path in resolved_opponents.items()
    }
    sources_unchanged = (
        candidate_hash_start == candidate_hash_end
        and opponent_hashes_start == opponent_hashes_end
    )
    report = {
        "schema_version": 1,
        "created_at_utc": completed_at,
        "started_at_utc": started_at,
        "completed_at_utc": completed_at,
        "git_head_at_start": git_head,
        "workers": workers,
        "scenario_overrides": scenarios,
        "effective_scenarios": effective_scenarios,
        "effective_scenarios_sha256": _json_sha256(effective_scenarios),
        "start_receipt": receipt_path.as_posix(),
        "start_receipt_sha256": receipt_sha256,
        "candidate": candidate_ref,
        "candidate_path": candidate,
        "candidate_sha256": _sha256(candidate_path),
        "candidate_sha256_at_start": candidate_hash_start,
        "candidate_sha256_at_end": candidate_hash_end,
        "opponents": opponents,
        "opponent_sha256_at_start": opponent_hashes_start,
        "opponent_sha256_at_end": opponent_hashes_end,
        "sources_unchanged_during_run": sources_unchanged,
        "seeds": seeds,
        "seat_policy": "both seats scored; confidence interval is clustered by seed/opponent pair",
        "summary": summarize(results),
        "games": [asdict(row) for row in results],
    }
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run paired Kaggriculture evaluations")
    parser.add_argument("--agent", required=True, help="candidate path or registered name")
    parser.add_argument(
        "--partition", choices=("development", "validation", "holdout", "confirmation")
    )
    parser.add_argument("--opponents", help="comma-separated registered opponents")
    parser.add_argument("--seeds", help="comma-separated integer seeds")
    parser.add_argument("--config", type=Path, default=Path("configs/evaluation_splits.json"))
    parser.add_argument(
        "--scenario-config",
        type=Path,
        help="JSON scenarios mapping with Kaggriculture configuration overrides",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    args = parser.parse_args()

    if args.partition:
        seeds, opponents = _load_partition(args.config, args.partition)
    elif args.opponents and args.seeds:
        opponents = [value.strip() for value in args.opponents.split(",") if value.strip()]
        seeds = [int(value) for value in args.seeds.split(",") if value.strip()]
    else:
        parser.error("use --partition or both --opponents and --seeds")
    if not 1 <= args.workers <= 12:
        parser.error("--workers must be between 1 and 12")

    scenarios = _load_scenarios(args.scenario_config) if args.scenario_config else None
    report = run_batch(
        args.agent,
        opponents,
        seeds,
        args.output,
        args.workers,
        Path.cwd().resolve(),
        scenarios,
    )
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
