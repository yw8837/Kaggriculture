"""Replay-faithful runtime benchmark for the Fa05 player-one trace policy."""

from __future__ import annotations

import copy
import hashlib
import json
import runpy
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _load_agent(path: Path) -> Callable[[dict[str, Any]], dict[str, Any]]:
    namespace = runpy.run_path(str(path))
    agent = namespace.get("agent")
    if not callable(agent):
        raise TypeError(f"agent callable not found in {path}")
    return agent


def _percentile(values: list[float], probability: float) -> float:
    if not values:
        raise ValueError("values must not be empty")
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * probability)]


def reconstruct_player_observations(
    replay: dict[str, Any], player: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Copy player observations and restore only a missing shared step field."""
    raw_steps = replay.get("steps")
    if not isinstance(raw_steps, list) or len(raw_steps) != 720:
        raise ValueError("Fa05 runtime replay must contain exactly 720 steps")
    observations: list[dict[str, Any]] = []
    injected = 0
    preserved = 0
    player_private_preserved = True
    for index, raw_state in enumerate(raw_steps):
        if not isinstance(raw_state, list) or len(raw_state) != 2:
            raise ValueError(f"replay step {index} must contain two player states")
        player_state = raw_state[player]
        shared_state = raw_state[0]
        if not isinstance(player_state, dict) or not isinstance(shared_state, dict):
            raise TypeError(f"replay step {index} states must be mappings")
        original = player_state.get("observation")
        shared = shared_state.get("observation")
        if not isinstance(original, dict) or not isinstance(shared, dict):
            raise TypeError(f"replay step {index} observations must be mappings")
        observation = copy.deepcopy(original)
        original_player = copy.deepcopy(observation.get("player"))
        original_private = copy.deepcopy(observation.get("private"))
        if "step" in observation:
            step = observation["step"]
            preserved += 1
        else:
            step = shared.get("step")
            injected += 1
        if isinstance(step, bool) or not isinstance(step, int) or step != index:
            raise ValueError(
                f"replay step {index} shared step must be exact integer {index}"
            )
        observation["step"] = step
        player_private_preserved &= (
            observation.get("player") == original_player
            and observation.get("private") == original_private
        )
        observations.append(observation)
    observed_steps = [int(observation["step"]) for observation in observations]
    if observed_steps != list(range(720)) or len(set(observed_steps)) != 720:
        raise ValueError("Fa05 runtime did not reconstruct exact schedule steps 0-719")
    return observations, {
        "method": "copy_player_observation_and_fill_only_missing_step_from_player0",
        "observed_steps": observed_steps,
        "observed_step_start": 0,
        "observed_step_end": 719,
        "unique_observed_steps": 720,
        "injected_missing_steps": injected,
        "preserved_existing_steps": preserved,
        "player_and_private_preserved": player_private_preserved,
    }


def benchmark_player_replay(
    source: Path, replay_path: Path, player: int
) -> dict[str, Any]:
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    observations, step_provenance = reconstruct_player_observations(replay, player)

    warmup_agent = _load_agent(source)
    for observation in observations[:10]:
        warmup_agent(copy.deepcopy(observation))
    agent = _load_agent(source)

    timings_ms: list[float] = []
    invalid_outputs = 0
    emitted_actions: list[dict[str, Any]] = []
    for observation in observations:
        started = time.perf_counter_ns()
        action = agent(copy.deepcopy(observation))
        timings_ms.append((time.perf_counter_ns() - started) / 1_000_000)
        if not isinstance(action, dict) or not {"farmer", "hands", "market"} <= action.keys():
            invalid_outputs += 1
            emitted_actions.append({})
        else:
            emitted_actions.append(action)

    recorded_actions = [state[player].get("action") for state in replay["steps"]]
    # Kaggle replays attach the action emitted from observation i to replay state i+1.
    comparable = list(
        zip(emitted_actions[:719], recorded_actions[1:], strict=True)
    )
    if any(recorded is None for _, recorded in comparable):
        raise ValueError("Fa05 replay is missing an aligned recorded action")
    matches = sum(emitted == recorded for emitted, recorded in comparable)
    return {
        "schema_version": 1,
        "source": source.as_posix(),
        "source_sha256": _sha256(source),
        "replay": replay_path.as_posix(),
        "replay_sha256": _sha256(replay_path),
        "player": player,
        "calls": len(timings_ms),
        "invalid_outputs": invalid_outputs,
        "p50_ms": _percentile(timings_ms, 0.50),
        "p95_ms": _percentile(timings_ms, 0.95),
        "p99_ms": _percentile(timings_ms, 0.99),
        "max_ms": max(timings_ms),
        "observations": len(observations),
        "recorded_actions": len(comparable),
        "recorded_action_offset": 1,
        "recorded_action_matches": matches,
        "recorded_action_differences": len(comparable) - matches,
        "step_provenance": step_provenance,
    }
