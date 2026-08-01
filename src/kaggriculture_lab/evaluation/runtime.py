from __future__ import annotations

import argparse
import hashlib
import json
import runpy
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any


def percentile(values: list[float], probability: float) -> float:
    if not values:
        raise ValueError("values must not be empty")
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be between zero and one")
    ordered = sorted(values)
    index = round((len(ordered) - 1) * probability)
    return ordered[index]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _load_agent(path: Path) -> Callable[[dict[str, Any]], dict[str, Any]]:
    namespace = runpy.run_path(str(path))
    agent = namespace.get("agent")
    if not callable(agent):
        raise TypeError(f"agent callable not found in {path}")
    return agent


def benchmark(source: Path, replay_path: Path, player: int) -> dict[str, Any]:
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    observations = [state[player]["observation"] for state in replay["steps"]]
    agent = _load_agent(source)

    for observation in observations[:10]:
        agent(observation)

    timings_ms = []
    invalid_outputs = 0
    for observation in observations:
        started = time.perf_counter_ns()
        action = agent(observation)
        timings_ms.append((time.perf_counter_ns() - started) / 1_000_000)
        if not isinstance(action, dict) or not {"farmer", "hands", "market"} <= action.keys():
            invalid_outputs += 1

    return {
        "schema_version": 1,
        "source": source.as_posix(),
        "source_sha256": _sha256(source),
        "replay": replay_path.as_posix(),
        "replay_sha256": _sha256(replay_path),
        "player": player,
        "calls": len(timings_ms),
        "invalid_outputs": invalid_outputs,
        "p50_ms": percentile(timings_ms, 0.50),
        "p95_ms": percentile(timings_ms, 0.95),
        "p99_ms": percentile(timings_ms, 0.99),
        "max_ms": max(timings_ms),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark a Kaggriculture agent on replay observations")
    parser.add_argument("--agent", type=Path, required=True)
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--player", type=int, choices=(0, 1), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = benchmark(args.agent, args.replay, args.player)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
