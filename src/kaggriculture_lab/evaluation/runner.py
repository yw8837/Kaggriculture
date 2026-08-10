from __future__ import annotations

import argparse
import ast
import concurrent.futures
import hashlib
import importlib
import importlib.metadata
import inspect
import json
import os
import random
import statistics
import subprocess
import sys
import time
import types
import uuid
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
PYTHON_STARTUP_ENV_NAMES = (
    "PYTHONPATH",
    "PYTHONHOME",
    "PYTHONSTARTUP",
    "PYTHONINSPECT",
    "PYTHONUSERBASE",
)
RUNTIME_DEPENDENCY_RELATIVE_PATHS = {
    "package_init": Path("kaggle_environments/__init__.py"),
    "core": Path("kaggle_environments/core.py"),
    "utils": Path("kaggle_environments/utils.py"),
    "agent": Path("kaggle_environments/agent.py"),
    "kaggriculture_py": Path(
        "kaggle_environments/envs/kaggriculture/kaggriculture.py"
    ),
    "kaggriculture_json": Path(
        "kaggle_environments/envs/kaggriculture/kaggriculture.json"
    ),
}
RUNTIME_IMPORTED_MODULE_NAMES = {
    "package_init": "kaggle_environments",
    "core": "kaggle_environments.core",
    "utils": "kaggle_environments.utils",
    "agent": "kaggle_environments.agent",
    "kaggriculture_py": (
        "kaggle_environments.envs.kaggriculture.kaggriculture"
    ),
}
EXPECTED_MAKE_CALLABLE = {
    "package_make_is_core_make": True,
    "function_type": True,
    "globals_is_core_module": True,
    "module": "kaggle_environments.core",
    "qualname": "make",
    "source_path_matches_core": True,
    "compiled_make_count": 1,
    "ast_make_count": 1,
    "ast_function_sha256": "7A9BCC66212C822AF494904756ECC915F6EC5DEEAF316EDB417648787E09E340",
    "function_source_sha256": "3090CF7871CCF6C046138987B22B47956DE1B3C2B7CFF9FC3D5ED617AFEDFEB7",
    "code_equals_compiled_source": True,
    "startup_environment": {
        "PYTHONPATH": None,
        "PYTHONHOME": None,
        "PYTHONSTARTUP": None,
        "PYTHONINSPECT": None,
        "PYTHONUSERBASE": None,
    },
    "defaults_sha256": "310DDDF0453ADA7D5A566EF2CDC450C58912C9FC466C552322FA9A0D27D0371C",
}
EXECUTION_BINDING_RELATIVE_PATH = Path(
    "research/campaign_3000/12_next_candidates/execution_binding.json"
)
IMPLEMENTATION_MANIFEST_RELATIVE_PATH = Path(
    "research/campaign_3000/12_next_candidates/freeze_manifest.json"
)


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
    candidate_source: str | None = None
    candidate_source_sha256: str | None = None
    opponent_source: str | None = None
    opponent_source_sha256: str | None = None


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
    candidate_metrics: dict[str, int] | None = None
    hidden_abnormal_status: dict[str, int | str] | None = None
    runtime_make_callable: dict[str, Any] = field(default_factory=dict)
    candidate_execution_sha256: str | None = None
    opponent_execution_sha256: str | None = None


def _make_callable_snapshot() -> tuple[Any, dict[str, Any]]:
    distribution = importlib.metadata.distribution("kaggle-environments")
    root = Path(distribution.locate_file("")).resolve()
    core_path = (root / "kaggle_environments/core.py").resolve()
    package_module = importlib.import_module("kaggle_environments")
    core_module = importlib.import_module("kaggle_environments.core")
    make_callable = getattr(package_module, "make", None)
    core_make = getattr(core_module, "make", None)
    function_type = isinstance(make_callable, types.FunctionType)
    core_text = core_path.read_text(encoding="utf-8")
    compiled_module = compile(core_text, str(core_path), "exec")
    compiled_make = [
        value
        for value in compiled_module.co_consts
        if isinstance(value, types.CodeType) and value.co_name == "make"
    ]
    parsed_module = ast.parse(core_text, filename=str(core_path))
    ast_make = [
        node
        for node in parsed_module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "make"
    ]
    ast_dump = (
        ast.dump(ast_make[0], annotate_fields=True, include_attributes=True).encode()
        if len(ast_make) == 1
        else b""
    )
    source_segment = (
        (ast.get_source_segment(core_text, ast_make[0]) or "").encode()
        if len(ast_make) == 1
        else b""
    )
    try:
        source_path = Path(inspect.getsourcefile(make_callable) or "").resolve()
    except (TypeError, OSError):
        source_path = Path.cwd()
    try:
        defaults_sha = _json_sha256(
            {
                "defaults": getattr(make_callable, "__defaults__", None),
                "kwdefaults": getattr(make_callable, "__kwdefaults__", None),
            }
        )
    except (TypeError, ValueError):
        defaults_sha = None
    snapshot = {
        "package_make_is_core_make": make_callable is core_make,
        "function_type": function_type,
        "globals_is_core_module": function_type
        and make_callable.__globals__ is core_module.__dict__,
        "module": getattr(make_callable, "__module__", None),
        "qualname": getattr(make_callable, "__qualname__", None),
        "source_path_matches_core": source_path == core_path,
        "compiled_make_count": len(compiled_make),
        "ast_make_count": len(ast_make),
        "ast_function_sha256": hashlib.sha256(ast_dump).hexdigest().upper(),
        "function_source_sha256": hashlib.sha256(source_segment).hexdigest().upper(),
        "code_equals_compiled_source": function_type
        and len(compiled_make) == 1
        and make_callable.__code__ == compiled_make[0],
        "startup_environment": {
            name: None if os.environ.get(name) in (None, "") else os.environ[name]
            for name in PYTHON_STARTUP_ENV_NAMES
        },
        "defaults_sha256": defaults_sha,
    }
    return make_callable, snapshot


def _validated_kaggle_make() -> tuple[Any, dict[str, Any]]:
    make_callable, snapshot = _make_callable_snapshot()
    if snapshot != EXPECTED_MAKE_CALLABLE:
        raise RuntimeError("kaggle_environments.make callable identity mismatch")
    return make_callable, snapshot


def _effective_configuration(
    override: dict[str, Any], seed: int | None = None,
) -> dict[str, Any]:
    normalized_override = json.loads(
        json.dumps(override, sort_keys=True, allow_nan=False)
    )
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


def _first_abnormal_status(steps: list[Any]) -> tuple[int, int, str] | None:
    """Return the first framework failure before the terminal interpreter can hide it."""
    allowed = {"ACTIVE", "INACTIVE", "DONE"}
    for step_index, states in enumerate(steps):
        for player, state in enumerate(states):
            status = str(getattr(state, "status", "UNKNOWN")).upper()
            if status not in allowed:
                return step_index, player, status
    return None


def _agent_from_immutable_source(
    reference: str,
    source: str | None,
    expected_sha256: str | None,
) -> tuple[Any, str | None]:
    """Compile the carried payload; the path is filename provenance, never input bytes."""
    if source is None:
        path = Path(reference)
        if not path.is_file():
            return reference, None
        try:
            payload = path.read_bytes()
            source = payload.decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ValueError(f"agent source is not exact UTF-8: {reference}") from exc
    else:
        if type(source) is not str:
            raise TypeError("immutable agent source must be an exact str")
        payload = source.encode("utf-8")
        if type(expected_sha256) is not str:
            raise ValueError("immutable agent source is missing its expected SHA256")
    actual_sha256 = hashlib.sha256(payload).hexdigest().upper()
    if expected_sha256 is not None and actual_sha256 != expected_sha256:
        raise ValueError("immutable agent source SHA256 mismatch")
    from kaggle_environments.agent import get_last_callable

    return get_last_callable(source, path=reference), actual_sha256


def _run_game(spec: GameSpec) -> GameResult:
    project_root = Path(spec.project_root)
    niits_src = str((project_root / NIITS_ROOT / "src").resolve())
    if niits_src not in sys.path:
        sys.path.insert(0, niits_src)

    started = time.perf_counter()
    hidden_abnormal_status: dict[str, int | str] | None = None
    runtime_make_callable: dict[str, Any] = {}
    candidate_execution_sha256: str | None = None
    opponent_execution_sha256: str | None = None
    try:
        make, runtime_make_callable = _validated_kaggle_make()

        configuration = _effective_configuration(spec.configuration, spec.seed)
        env = make(
            "kaggriculture",
            configuration=configuration,
            debug=False,
        )
        environment_configuration = json.loads(
            json.dumps(dict(env.configuration), sort_keys=True, allow_nan=False)
        )
        raw_environment_seed = env.info["seed"]
        if type(raw_environment_seed) is not int or raw_environment_seed != spec.seed:
            raise ValueError("environment resolved seed is not the exact requested int")
        resolved_environment_seed = raw_environment_seed
        candidate_agent, candidate_execution_sha256 = _agent_from_immutable_source(
            spec.candidate,
            spec.candidate_source,
            spec.candidate_source_sha256,
        )
        opponent_agent, opponent_execution_sha256 = _agent_from_immutable_source(
            spec.opponent,
            spec.opponent_source,
            spec.opponent_source_sha256,
        )
        metrics_callable = (
            candidate_agent.__globals__.get("rescue_metrics")
            if callable(candidate_agent) and hasattr(candidate_agent, "__globals__")
            else None
        )
        reset_callable = (
            candidate_agent.__globals__.get("reset_rescue_metrics")
            if callable(candidate_agent) and hasattr(candidate_agent, "__globals__")
            else None
        )
        if callable(reset_callable):
            reset_callable()
        agents = (
            [candidate_agent, opponent_agent]
            if spec.seat == 0
            else [opponent_agent, candidate_agent]
        )
        env.run(agents)
        abnormal = _first_abnormal_status(env.steps)
        if abnormal is not None:
            step_index, player, status = abnormal
            hidden_abnormal_status = {
                "step": step_index,
                "player": player,
                "status": status,
            }
            raise RuntimeError(
                f"framework agent failure at step={step_index}, player={player}, status={status}"
            )
        final = env.steps[-1]
        candidate_state = final[spec.seat]
        opponent_state = final[1 - spec.seat]
        candidate_metrics = metrics_callable() if callable(metrics_callable) else None
        if candidate_metrics is not None and (
            not isinstance(candidate_metrics, dict)
            or any(
                not isinstance(key, str)
                or isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
                for key, value in candidate_metrics.items()
            )
        ):
            raise TypeError("candidate rescue_metrics() returned an invalid counter mapping")
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
            candidate_metrics=candidate_metrics,
            hidden_abnormal_status=None,
            runtime_make_callable=runtime_make_callable,
            candidate_execution_sha256=candidate_execution_sha256,
            opponent_execution_sha256=opponent_execution_sha256,
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
            hidden_abnormal_status=hidden_abnormal_status,
            runtime_make_callable=runtime_make_callable,
            candidate_execution_sha256=candidate_execution_sha256,
            opponent_execution_sha256=opponent_execution_sha256,
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
    pair_scores_by_seed: dict[int, list[float]] = {}
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
        pair_score = (_outcome(first) + _outcome(second)) / 2.0
        pair_scores.append(pair_score)
        pair_scores_by_seed.setdefault(seed, []).append(pair_score)
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

    seed_cluster_scores = [
        statistics.mean(scores) for _, scores in sorted(pair_scores_by_seed.items())
    ]
    cluster_ci = [0.0, 1.0]
    if seed_cluster_scores:
        rng = random.Random(0)
        boot = sorted(
            statistics.mean(rng.choice(seed_cluster_scores) for _ in seed_cluster_scores)
            for _ in range(10_000)
        )
        cluster_ci = [boot[249], boot[9749]]

    money = [float(row.candidate_money) for row in valid]
    margins = [float(row.candidate_money - row.opponent_money) for row in valid]
    metric_keys = sorted(
        {key for row in valid for key in (row.candidate_metrics or {})}
    )
    candidate_metrics_total = {
        key: sum(int((row.candidate_metrics or {}).get(key, 0)) for row in valid)
        for key in metric_keys
    }
    return {
        "raw_games": len(results),
        "valid_raw_games": len(valid),
        "failed_raw_games": len(results) - len(valid),
        "seed_opponent_pairs": len(pair_scores),
        "scenario_opponent_seed_pairs": len(pair_scores),
        "bootstrap_seed_clusters": len(seed_cluster_scores),
        "bootstrap_cluster_unit": "seed",
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "match_score": (wins + 0.5 * ties) / len(valid) if valid else None,
        "decisive_win_rate": wins / decisive if decisive else None,
        "decisive_win_rate_wilson_95_naive_raw_games": [low, high],
        "match_score_cluster_bootstrap_95": cluster_ci,
        "match_score_seed_cluster_bootstrap_95": cluster_ci,
        "money_mean": statistics.mean(money) if money else None,
        "money_median": statistics.median(money) if money else None,
        "money_min": min(money) if money else None,
        "margin_mean": statistics.mean(margins) if margins else None,
        "margin_median": statistics.median(margins) if margins else None,
        "seat_pair_differences": seat_differences,
        "candidate_metrics_total": candidate_metrics_total,
        "candidate_metrics_games": sum(row.candidate_metrics is not None for row in valid),
        "hidden_abnormal_status_failures": sum(
            row.hidden_abnormal_status is not None for row in results
        ),
        "elapsed_seconds_total": sum(row.elapsed_seconds for row in results),
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _json_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def _json_bytes(value: Any) -> bytes:
    """Return the sole JSON serialization used for durable runner receipts."""
    return (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_bytes_exclusive(path: Path, payload: bytes) -> None:
    """Create one file exactly once without platform newline translation."""
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _write_json_exclusive(path: Path, value: Any) -> dict[str, Any]:
    payload = _json_bytes(value)
    _write_bytes_exclusive(path, payload)
    on_disk = path.read_bytes()
    if on_disk != payload:  # pragma: no cover - filesystem corruption evidence
        raise OSError(f"exclusive JSON write did not persist exact bytes: {path}")
    return {
        "path": path.resolve().as_posix(),
        "bytes": len(on_disk),
        "sha256": hashlib.sha256(on_disk).hexdigest().upper(),
    }


def _file_snapshot(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    try:
        payload = resolved.read_bytes()
    except OSError as exc:
        return {
            "path": resolved.as_posix(),
            "exists": False,
            "bytes": None,
            "sha256": None,
            "read_error": f"{type(exc).__name__}: {exc}",
        }
    return {
        "path": resolved.as_posix(),
        "exists": True,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest().upper(),
        "read_error": None,
    }


def _snapshot_from_payload(path: Path, payload: bytes) -> dict[str, Any]:
    return {
        "path": path.resolve().as_posix(),
        "exists": True,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest().upper(),
        "read_error": None,
    }


def _module_source_path(module_name: str) -> dict[str, Any]:
    try:
        module = importlib.import_module(module_name)
        raw_path = getattr(module, "__file__", None)
        if type(raw_path) is not str or not raw_path:
            raise TypeError("imported module does not expose an exact source path")
        return {"path": Path(raw_path).resolve().as_posix(), "error": None}
    except Exception as exc:  # noqa: BLE001  # pragma: no cover - drift evidence
        return {"path": None, "error": f"{type(exc).__name__}: {exc}"}


def _runtime_environment_snapshot() -> dict[str, Any]:
    """Capture the actual in-process engine and its six execution dependencies."""
    imported_module_paths = {
        label: _module_source_path(module_name)
        for label, module_name in RUNTIME_IMPORTED_MODULE_NAMES.items()
    }
    distribution_error = None
    try:
        distribution = importlib.metadata.distribution("kaggle-environments")
        distribution_version = distribution.version
        distribution_root = Path(distribution.locate_file("")).resolve()
    except Exception as exc:  # noqa: BLE001  # pragma: no cover - drift evidence
        distribution_error = f"{type(exc).__name__}: {exc}"
        distribution_version = None
        package_path = imported_module_paths["package_init"]["path"]
        distribution_root = (
            Path(package_path).resolve().parent.parent
            if type(package_path) is str
            else None
        )

    if distribution_root is None:  # pragma: no cover - defensive drift capture
        dependency_files = {
            label: {
                "path": None,
                "exists": False,
                "bytes": None,
                "sha256": None,
                "read_error": "distribution root unavailable",
            }
            for label in RUNTIME_DEPENDENCY_RELATIVE_PATHS
        }
    else:
        dependency_files = {
            label: _file_snapshot(distribution_root / relative_path)
            for label, relative_path in RUNTIME_DEPENDENCY_RELATIVE_PATHS.items()
        }
    try:
        _, make_callable = _make_callable_snapshot()
        make_callable_error = None
    except Exception as exc:  # noqa: BLE001  # pragma: no cover - drift evidence
        make_callable = None
        make_callable_error = f"{type(exc).__name__}: {exc}"

    return {
        "schema_version": 1,
        "distribution_name": "kaggle-environments",
        "distribution_version": distribution_version,
        "distribution_root": (
            distribution_root.as_posix() if distribution_root is not None else None
        ),
        "distribution_error": distribution_error,
        "python_executable": Path(sys.executable).resolve().as_posix(),
        "imported_module_paths": imported_module_paths,
        "runtime_dependency_files": dependency_files,
        "make_callable_contract": make_callable,
        "make_callable_contract_matches_expected": (
            make_callable == EXPECTED_MAKE_CALLABLE
        ),
        "make_callable_error": make_callable_error,
    }


def _normalize_input_paths(
    project_root: Path, input_paths: list[str | Path] | None,
) -> list[Path]:
    if input_paths is None:
        return []
    if type(input_paths) is not list:
        raise TypeError("input_paths must be an exact list of str or Path values")
    normalized: list[Path] = []
    seen: set[str] = set()
    for raw_path in input_paths:
        if not isinstance(raw_path, (str, Path)) or isinstance(raw_path, bool):
            raise TypeError("each input pin must be a str or Path")
        if isinstance(raw_path, str) and not raw_path.strip():
            raise ValueError("input pin paths must be non-empty")
        path = Path(raw_path)
        if not path.is_absolute():
            path = project_root / path
        path = path.resolve()
        if not path.is_file():
            raise FileNotFoundError(f"pinned execution input not found: {path}")
        key = os.path.normcase(str(path))
        if key not in seen:
            normalized.append(path)
            seen.add(key)
    return normalized


def _execution_input_snapshot(input_paths: list[Path]) -> dict[str, Any]:
    runner_path = Path(__file__).resolve()
    return {
        "schema_version": 1,
        "runner": _file_snapshot(runner_path),
        "pinned_inputs": {
            path.as_posix(): _file_snapshot(path)
            for path in sorted(input_paths, key=lambda item: item.as_posix())
        },
    }


def _git_command(
    project_root: Path, arguments: list[str], *, binary: bool = False,
) -> str | bytes:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=not binary,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(
            f"git {' '.join(arguments)} failed: {type(exc).__name__}: {exc}"
        ) from exc
    return result.stdout


def _git_head(project_root: Path) -> str | None:
    try:
        stdout = _git_command(project_root, ["rev-parse", "HEAD"])
    except RuntimeError:
        return None
    if not isinstance(stdout, str):  # pragma: no cover - internal contract
        return None
    return stdout.strip() or None


def _git_parent_commits(project_root: Path, commit: str) -> list[str]:
    stdout = _git_command(project_root, ["rev-list", "--parents", "-n", "1", commit])
    if not isinstance(stdout, str):  # pragma: no cover - internal contract
        raise TypeError("git parent output is not text")
    fields = stdout.strip().split()
    if not fields or fields[0].lower() != commit.lower():
        raise RuntimeError("git parent query did not return the requested commit")
    return fields[1:]


def _git_changed_paths(
    project_root: Path, base_commit: str, target_commit: str,
) -> list[str]:
    stdout = _git_command(
        project_root,
        ["diff", "--name-only", "--no-renames", base_commit, target_commit, "--"],
    )
    if not isinstance(stdout, str):  # pragma: no cover - internal contract
        raise TypeError("git diff output is not text")
    return [line.replace("\\", "/") for line in stdout.splitlines() if line]


def _git_blob_bytes(project_root: Path, commit: str, relative_path: str) -> bytes:
    stdout = _git_command(project_root, ["show", f"{commit}:{relative_path}"], binary=True)
    if not isinstance(stdout, bytes):  # pragma: no cover - internal contract
        raise TypeError("git blob output is not bytes")
    return stdout


def _tracked_worktree_snapshot(project_root: Path) -> dict[str, Any]:
    try:
        stdout = _git_command(
            project_root,
            ["status", "--porcelain=v1", "--untracked-files=no"],
        )
        if not isinstance(stdout, str):
            raise TypeError("git status output is not text")
        entries = stdout.splitlines()
        return {
            "schema_version": 1,
            "clean": not entries,
            "porcelain_v1": entries,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001 - end receipt must preserve failure
        return {
            "schema_version": 1,
            "clean": False,
            "porcelain_v1": [],
            "error": f"{type(exc).__name__}: {exc}",
        }


def _require_commit(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 40
        or any(character not in "0123456789abcdefABCDEF" for character in value)
    ):
        raise PermissionError(f"{label} is not an exact Git commit")
    return value.lower()


def _capture_execution_authority(
    project_root: Path, input_paths: list[Path],
) -> dict[str, Any]:
    """Validate and capture the exact CLOSED S->E execution boundary."""
    binding_path = (project_root / EXECUTION_BINDING_RELATIVE_PATH).resolve()
    if binding_path not in input_paths:
        raise PermissionError("exact execution_binding.json is not an execution input pin")
    try:
        binding = json.loads(binding_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PermissionError(f"execution binding is unreadable: {exc}") from exc
    if type(binding) is not dict:
        raise PermissionError("execution binding is not an exact object")
    if binding.get("status") != "CLOSED_EXECUTION_FREEZE":
        raise PermissionError("execution binding is not CLOSED_EXECUTION_FREEZE")

    current_head = _require_commit(_git_head(project_root), "current HEAD")
    implementation_commit = _require_commit(
        binding.get("implementation_commit"), "implementation_commit"
    )
    parents = [parent.lower() for parent in _git_parent_commits(project_root, current_head)]
    if parents != [implementation_commit]:
        raise PermissionError("current execution-freeze HEAD is not the sole child of S")
    binding_relative = EXECUTION_BINDING_RELATIVE_PATH.as_posix()
    expected_freeze = {
        "parent": "IMPLEMENTATION_COMMIT",
        "allowed_diff": [binding_relative],
    }
    if binding.get("expected_execution_freeze") != expected_freeze:
        raise PermissionError("execution binding does not declare the exact S->E diff")
    changed_paths = _git_changed_paths(
        project_root, implementation_commit, current_head
    )
    if changed_paths != [binding_relative]:
        raise PermissionError("S->E changed paths are not exactly execution_binding.json")

    binding_bytes = binding_path.read_bytes()
    committed_binding = _git_blob_bytes(project_root, current_head, binding_relative)
    if committed_binding != binding_bytes:
        raise PermissionError("on-disk execution binding is not the exact E commit blob")
    binding_snapshot = _snapshot_from_payload(binding_path, binding_bytes)

    manifest_pin = binding.get("implementation_manifest")
    if type(manifest_pin) is not dict:
        raise PermissionError("implementation manifest pin is missing")
    if set(manifest_pin) != {"path", "sha256", "bytes", "input_count"}:
        raise PermissionError("implementation manifest pin fields are not exact")
    manifest_reference = manifest_pin.get("path")
    if manifest_reference != IMPLEMENTATION_MANIFEST_RELATIVE_PATH.as_posix():
        raise PermissionError("implementation manifest path is not the exact freeze path")
    manifest_path = (project_root / manifest_reference).resolve()
    if manifest_path not in input_paths:
        raise PermissionError("implementation manifest is not an execution input pin")
    manifest_snapshot = _file_snapshot(manifest_path)
    if (
        manifest_snapshot["exists"] is not True
        or manifest_snapshot["sha256"] != manifest_pin.get("sha256")
        or manifest_snapshot["bytes"] != manifest_pin.get("bytes")
        or type(manifest_pin.get("input_count")) is not int
        or manifest_pin["input_count"] < 1
    ):
        raise PermissionError("implementation manifest bytes do not match the binding")
    try:
        manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PermissionError(f"implementation manifest is unreadable: {exc}") from exc
    if manifest_payload.get("input_count") != manifest_pin["input_count"]:
        raise PermissionError("implementation manifest input_count does not match")

    expected_lifecycle = {
        "all_six_pools": "CLOSED",
        "opened": False,
        "consumed": False,
        "fresh_games_executed": 0,
    }
    expected_auditor = {
        "status": "PENDING_INDEPENDENT_AUDITOR_EXACT_OPEN",
        "development_seed_execution": "FORBIDDEN",
    }
    expected_external = {
        "save_run": False,
        "upload": False,
        "competition_submission": False,
        "publication": False,
    }
    if binding.get("lifecycle") != expected_lifecycle:
        raise PermissionError("execution binding lifecycle is not pristine CLOSED")
    if binding.get("auditor_authority") != expected_auditor:
        raise PermissionError("execution binding auditor authority is not exact PENDING")
    if binding.get("external_actions") != expected_external:
        raise PermissionError("execution binding external-action HOLD is not exact")

    tracked = _tracked_worktree_snapshot(project_root)
    if tracked.get("clean") is not True:
        raise PermissionError("tracked worktree is not clean before execution")
    return {
        "schema_version": 1,
        "git_head_at_start": current_head,
        "tracked_worktree_at_start": tracked,
        "execution_binding": binding_snapshot,
        "execution_binding_status": binding["status"],
        "execution_binding_auditor_authority": binding["auditor_authority"],
        "execution_freeze_commit": current_head,
        "implementation_commit": implementation_commit,
        "execution_freeze_parent_commits": parents,
        "execution_freeze_changed_paths": changed_paths,
        "implementation_manifest": manifest_snapshot,
        "implementation_manifest_input_count": manifest_pin["input_count"],
    }


def _file_hash_or_none(reference: str) -> str | None:
    path = Path(reference)
    return _sha256(path) if path.is_file() else None


def _load_partition(path: Path, partition: str) -> tuple[list[int], list[str]]:
    config = json.loads(path.read_text(encoding="utf-8"))
    section = config[partition]
    if "seeds" not in section or "opponents" not in section:
        raise ValueError(f"partition {partition} does not define seeds and opponents")
    seeds = section["seeds"]
    opponents = section["opponents"]
    if type(seeds) is not list or any(type(seed) is not int for seed in seeds):
        raise TypeError("partition seeds must be an exact list of exact int values")
    if type(opponents) is not list or any(
        type(opponent) is not str or not opponent for opponent in opponents
    ):
        raise TypeError(
            "partition opponents must be an exact list of non-empty exact str values"
        )
    return list(seeds), list(opponents)


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
        forbidden = {"seed", "randomSeed", "episodeSteps"} & configuration.keys()
        if forbidden:
            raise ValueError(
                f"scenario {name} cannot override runner-controlled keys: {sorted(forbidden)}"
            )
        scenarios[name] = configuration
    return scenarios


def _new_run_id() -> str:
    return uuid.uuid4().hex.upper()


def _copy_source_exclusive(
    logical_reference: str, source: Path, destination: Path,
) -> tuple[dict[str, Any], str]:
    source = source.resolve()
    try:
        payload = source.read_bytes()
        source_text = payload.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise FileNotFoundError(f"source snapshot input is unreadable: {source}") from exc
    original = _snapshot_from_payload(source, payload)
    _write_bytes_exclusive(destination, payload)
    snapshot = _file_snapshot(destination)
    if (
        snapshot["exists"] is not True
        or snapshot["bytes"] != original["bytes"]
        or snapshot["sha256"] != original["sha256"]
    ):  # pragma: no cover - filesystem corruption evidence
        raise OSError(f"source snapshot does not match original bytes: {source}")
    return (
        {
            "logical_reference": logical_reference,
            "original": original,
            "snapshot": snapshot,
        },
        source_text,
    )


def _create_source_snapshots(
    output: Path,
    run_id: str,
    candidate_ref: str,
    candidate_path: str,
    opponents: list[str],
    opponent_paths: dict[str, str],
) -> tuple[
    dict[str, Any],
    str,
    dict[str, str],
    str,
    dict[str, str],
]:
    snapshot_directory = output.with_name(f"{output.stem}.sources.{run_id}").resolve()
    snapshot_directory.mkdir(exist_ok=False)
    candidate_source = Path(candidate_path)
    candidate_suffix = candidate_source.suffix or ".source"
    candidate_record, candidate_source = _copy_source_exclusive(
        candidate_ref,
        candidate_source,
        snapshot_directory / f"candidate{candidate_suffix}",
    )
    opponent_records: dict[str, dict[str, Any]] = {}
    executed_opponents: dict[str, str] = {}
    opponent_sources: dict[str, str] = {}
    for index, opponent_name in enumerate(opponents):
        opponent_source = Path(opponent_paths[opponent_name])
        opponent_suffix = opponent_source.suffix or ".source"
        record, source_text = _copy_source_exclusive(
            opponent_name,
            opponent_source,
            snapshot_directory / f"opponent_{index:03d}{opponent_suffix}",
        )
        opponent_records[opponent_name] = record
        executed_opponents[opponent_name] = record["snapshot"]["path"]
        opponent_sources[opponent_name] = source_text
    source_snapshots = {
        "schema_version": 1,
        "run_id": run_id,
        "snapshot_directory": snapshot_directory.as_posix(),
        "candidate": candidate_record,
        "opponents": opponent_records,
    }
    return (
        source_snapshots,
        candidate_record["snapshot"]["path"],
        executed_opponents,
        candidate_source,
        opponent_sources,
    )


def _refresh_source_snapshots(start: dict[str, Any]) -> dict[str, Any]:
    def refresh(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "logical_reference": record["logical_reference"],
            "original": _file_snapshot(Path(record["original"]["path"])),
            "snapshot": _file_snapshot(Path(record["snapshot"]["path"])),
        }

    return {
        "schema_version": start["schema_version"],
        "run_id": start["run_id"],
        "snapshot_directory": start["snapshot_directory"],
        "candidate": refresh(start["candidate"]),
        "opponents": {
            name: refresh(record) for name, record in start["opponents"].items()
        },
    }


def run_batch(
    candidate_ref: str,
    opponents: list[str],
    seeds: list[int],
    output: Path,
    workers: int,
    project_root: Path,
    scenarios: dict[str, dict[str, Any]] | None = None,
    input_paths: list[str | Path] | None = None,
) -> dict[str, Any]:
    if type(candidate_ref) is not str or not candidate_ref:
        raise TypeError("candidate_ref must be a non-empty exact str")
    if type(opponents) is not list or not opponents:
        raise TypeError("opponents must be a non-empty exact list")
    if any(type(opponent) is not str or not opponent for opponent in opponents):
        raise TypeError("opponents must contain only non-empty exact str values")
    if len(set(opponents)) != len(opponents):
        raise ValueError("opponents must be unique logical references")
    if type(seeds) is not list or not seeds:
        raise TypeError("seeds must be a non-empty exact list")
    if any(type(seed) is not int for seed in seeds):
        raise TypeError("seeds must contain only exact int values")
    if type(workers) is not int or workers < 1:
        raise TypeError("workers must be a positive exact int")
    if not isinstance(project_root, Path):
        raise TypeError("project_root must be a Path")
    if not isinstance(output, Path):
        raise TypeError("output must be a Path")
    project_root = project_root.resolve()
    if not output.is_absolute():
        output = project_root / output
    output = output.resolve()
    normalized_input_paths = _normalize_input_paths(project_root, input_paths)
    candidate = _resolve(candidate_ref, project_root)
    resolved_opponents = {name: _resolve(name, project_root) for name in opponents}
    if scenarios is None:
        scenarios = {"default": {}}
    if type(scenarios) is not dict:
        raise TypeError("scenarios must be an exact dict")
    if not scenarios:
        raise ValueError("at least one evaluation scenario is required")
    for name, configuration in scenarios.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("scenario names must be non-empty strings")
        if not isinstance(configuration, dict):
            raise TypeError(f"scenario {name} configuration must be an object")
        forbidden = {"seed", "randomSeed", "episodeSteps"} & configuration.keys()
        if forbidden:
            raise ValueError(
                f"scenario {name} cannot override runner-controlled keys: {sorted(forbidden)}"
            )
        _json_sha256(configuration)
    effective_scenarios = {
        name: _effective_configuration(configuration)
        for name, configuration in scenarios.items()
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    receipt_path = output.with_name(f"{output.stem}.started.json")
    if output.exists():
        raise FileExistsError(f"completed report target already exists: {output}")
    if receipt_path.exists():
        raise FileExistsError(f"started receipt target already exists: {receipt_path}")

    run_id = _new_run_id()
    if (
        type(run_id) is not str
        or len(run_id) != 32
        or any(character not in "0123456789ABCDEF" for character in run_id)
    ):
        raise RuntimeError("run_id generator did not return exact uppercase UUID hex")
    execution_authority_start = _capture_execution_authority(
        project_root, normalized_input_paths
    )
    started_at = datetime.now(UTC).isoformat()
    git_head = execution_authority_start["git_head_at_start"]
    candidate_hash_start = _file_hash_or_none(candidate)
    opponent_hashes_start = {
        name: _file_hash_or_none(path) for name, path in resolved_opponents.items()
    }
    runtime_environment_start = _runtime_environment_snapshot()
    execution_inputs_start = _execution_input_snapshot(normalized_input_paths)
    (
        source_snapshots_start,
        executed_candidate,
        executed_opponents,
        candidate_source,
        opponent_sources,
    ) = _create_source_snapshots(
        output,
        run_id,
        candidate_ref,
        candidate,
        opponents,
        resolved_opponents,
    )
    if source_snapshots_start["candidate"]["original"]["sha256"] != (
        candidate_hash_start
    ):
        raise PermissionError("candidate changed while its immutable snapshot was created")
    if any(
        source_snapshots_start["opponents"][name]["original"]["sha256"]
        != opponent_hashes_start[name]
        for name in opponents
    ):
        raise PermissionError("an opponent changed while its immutable snapshot was created")
    pre_receipt_head = _git_head(project_root)
    pre_receipt_tracked = _tracked_worktree_snapshot(project_root)
    if pre_receipt_head is None or pre_receipt_head.lower() != git_head:
        raise PermissionError("Git HEAD drifted before the started receipt write")
    if pre_receipt_tracked.get("clean") is not True:
        raise PermissionError("tracked worktree became dirty before the started receipt write")
    authority_start_sha256 = _json_sha256(execution_authority_start)
    start_receipt = {
        "schema_version": 2,
        "execution_context_schema_version": 2,
        "run_id": run_id,
        "started_receipt_write_mode": "CREATE_NEW_EXCLUSIVE",
        "started_at_utc": started_at,
        "git_head_at_start": git_head,
        "tracked_worktree_clean_at_start": True,
        "execution_authority_at_start": execution_authority_start,
        "execution_authority_at_start_sha256": authority_start_sha256,
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
        "runtime_environment_at_start": runtime_environment_start,
        "runtime_environment_at_start_sha256": _json_sha256(
            runtime_environment_start
        ),
        "execution_inputs_at_start": execution_inputs_start,
        "execution_inputs_at_start_sha256": _json_sha256(execution_inputs_start),
        "source_snapshots_at_start": source_snapshots_start,
        "source_snapshots_at_start_sha256": _json_sha256(source_snapshots_start),
    }
    receipt_record = _write_json_exclusive(receipt_path, start_receipt)
    specs = [
        GameSpec(
            executed_candidate,
            executed_opponents[opponent_name],
            opponent_name,
            seed,
            seat,
            str(project_root),
            scenario_name,
            scenario_configuration,
            candidate_source,
            source_snapshots_start["candidate"]["snapshot"]["sha256"],
            opponent_sources[opponent_name],
            source_snapshots_start["opponents"][opponent_name]["snapshot"][
                "sha256"
            ],
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
    runtime_environment_end = _runtime_environment_snapshot()
    execution_inputs_end = _execution_input_snapshot(normalized_input_paths)
    source_snapshots_end = _refresh_source_snapshots(source_snapshots_start)
    results.sort(key=lambda row: (row.scenario, row.opponent, row.seed, row.seat))

    completed_at = datetime.now(UTC).isoformat()
    candidate_hash_end = _file_hash_or_none(candidate)
    opponent_hashes_end = {
        name: _file_hash_or_none(path) for name, path in resolved_opponents.items()
    }
    sources_unchanged = (
        candidate_hash_start == candidate_hash_end
        and opponent_hashes_start == opponent_hashes_end
    )
    runtime_environment_unchanged = (
        runtime_environment_start == runtime_environment_end
    )
    execution_inputs_unchanged = execution_inputs_start == execution_inputs_end
    source_snapshots_unchanged = source_snapshots_start == source_snapshots_end
    git_head_end = _git_head(project_root)
    tracked_worktree_end = _tracked_worktree_snapshot(project_root)
    git_head_unchanged = (
        type(git_head_end) is str and git_head_end.lower() == git_head
    )
    tracked_worktree_clean_at_end = tracked_worktree_end.get("clean") is True
    tracked_worktree_clean_at_boundaries = tracked_worktree_clean_at_end
    expected_row_make_callable = runtime_environment_start.get(
        "make_callable_contract"
    )
    row_runtime_make_callable_matches_start = all(
        row.runtime_make_callable == expected_row_make_callable for row in results
    )
    row_execution_sources_match_start = all(
        row.candidate_execution_sha256
        == source_snapshots_start["candidate"]["snapshot"]["sha256"]
        and row.opponent in source_snapshots_start["opponents"]
        and row.opponent_execution_sha256
        == source_snapshots_start["opponents"][row.opponent]["snapshot"]["sha256"]
        for row in results
    )
    execution_context_unchanged = (
        sources_unchanged
        and runtime_environment_unchanged
        and execution_inputs_unchanged
        and source_snapshots_unchanged
        and git_head_unchanged
        and tracked_worktree_clean_at_boundaries
        and row_runtime_make_callable_matches_start
        and row_execution_sources_match_start
    )
    report = {
        "schema_version": 2,
        "execution_context_schema_version": 2,
        "run_id": run_id,
        "started_receipt_write_mode": "CREATE_NEW_EXCLUSIVE",
        "created_at_utc": completed_at,
        "started_at_utc": started_at,
        "completed_at_utc": completed_at,
        "git_head_at_start": git_head,
        "git_head_at_end": git_head_end,
        "git_head_unchanged_during_run": git_head_unchanged,
        "tracked_worktree_clean_at_start": True,
        "tracked_worktree_at_end": tracked_worktree_end,
        "tracked_worktree_clean_at_end": tracked_worktree_clean_at_end,
        "tracked_worktree_clean_at_boundaries": (
            tracked_worktree_clean_at_boundaries
        ),
        "execution_authority_at_start": execution_authority_start,
        "execution_authority_at_start_sha256": authority_start_sha256,
        "workers": workers,
        "scenario_overrides": scenarios,
        "effective_scenarios": effective_scenarios,
        "effective_scenarios_sha256": _json_sha256(effective_scenarios),
        "start_receipt": receipt_record["path"],
        "start_receipt_bytes": receipt_record["bytes"],
        "start_receipt_sha256": receipt_record["sha256"],
        "runtime_environment_at_start": runtime_environment_start,
        "runtime_environment_at_start_sha256": _json_sha256(
            runtime_environment_start
        ),
        "runtime_environment_at_end": runtime_environment_end,
        "runtime_environment_at_end_sha256": _json_sha256(runtime_environment_end),
        "runtime_environment_unchanged_during_run": runtime_environment_unchanged,
        "execution_inputs_at_start": execution_inputs_start,
        "execution_inputs_at_start_sha256": _json_sha256(execution_inputs_start),
        "execution_inputs_at_end": execution_inputs_end,
        "execution_inputs_at_end_sha256": _json_sha256(execution_inputs_end),
        "execution_inputs_unchanged_during_run": execution_inputs_unchanged,
        "source_snapshots_at_start": source_snapshots_start,
        "source_snapshots_at_start_sha256": _json_sha256(source_snapshots_start),
        "source_snapshots_at_end": source_snapshots_end,
        "source_snapshots_at_end_sha256": _json_sha256(source_snapshots_end),
        "source_snapshots_unchanged_during_run": source_snapshots_unchanged,
        "row_runtime_make_callable_matches_start": (
            row_runtime_make_callable_matches_start
        ),
        "row_execution_sources_match_start": row_execution_sources_match_start,
        "execution_context_unchanged_during_run": execution_context_unchanged,
        "execution_gate_valid": execution_context_unchanged,
        "execution_gate_status": (
            "COMPLETED_VALID" if execution_context_unchanged
            else "COMPLETED_CONTEXT_DRIFT"
        ),
        "candidate": candidate_ref,
        "candidate_path": candidate,
        "candidate_sha256": candidate_hash_end,
        "candidate_sha256_at_start": candidate_hash_start,
        "candidate_sha256_at_end": candidate_hash_end,
        "opponents": opponents,
        "opponent_sha256_at_start": opponent_hashes_start,
        "opponent_sha256_at_end": opponent_hashes_end,
        "sources_unchanged_during_run": sources_unchanged,
        "seeds": seeds,
        "seat_policy": "both seats scored; confidence interval is clustered by seed",
        "summary": summarize(results),
        "games": [asdict(row) for row in results],
    }
    _write_json_exclusive(output, report)
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
    parser.add_argument(
        "--input-pin",
        action="append",
        default=[],
        type=Path,
        help=(
            "repeatable file path whose exact bytes must remain unchanged during "
            "the batch"
        ),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    args = parser.parse_args()

    input_paths = list(args.input_pin)
    if args.partition:
        seeds, opponents = _load_partition(args.config, args.partition)
        input_paths.append(args.config)
    elif args.opponents and args.seeds:
        opponents = [value.strip() for value in args.opponents.split(",") if value.strip()]
        seeds = [int(value) for value in args.seeds.split(",") if value.strip()]
    else:
        parser.error("use --partition or both --opponents and --seeds")
    if not 1 <= args.workers <= 12:
        parser.error("--workers must be between 1 and 12")

    scenarios = _load_scenarios(args.scenario_config) if args.scenario_config else None
    if args.scenario_config:
        input_paths.append(args.scenario_config)
    report = run_batch(
        args.agent,
        opponents,
        seeds,
        args.output,
        args.workers,
        Path.cwd().resolve(),
        scenarios,
        input_paths,
    )
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
