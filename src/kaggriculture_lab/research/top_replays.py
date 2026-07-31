from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def _tile_assets(tiles: list[list[Any]]) -> tuple[Counter, Counter]:
    crops: Counter = Counter()
    animals: Counter = Counter()
    for row in tiles:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            crop = tile.get("crop")
            animal = tile.get("animal")
            if crop:
                crops[crop] += 1
            if animal:
                animals[animal] += 1
    return crops, animals


def _stamp(observation: dict[str, Any]) -> dict[str, int]:
    return {
        "step": int(observation.get("step", 0)),
        "day": int(observation.get("day", 0)),
        "hour": int(observation.get("hour", 0)),
    }


def _first_reached(milestones: dict[str, Any], key: str, value: int, obs: dict) -> None:
    if value and key not in milestones:
        milestones[key] = _stamp(obs)


def analyze_agent(replay: dict[str, Any], player: int) -> dict[str, Any]:
    team = replay["info"]["TeamNames"][player]
    market_counts: Counter = Counter()
    market_quantities: Counter = Counter()
    unit_counts: Counter = Counter()
    plant_counts: Counter = Counter()
    place_counts: Counter = Counter()
    hires_by_day: defaultdict[int, int] = defaultdict(int)
    land_orders = []
    initial_market = None
    milestones: dict[str, Any] = {}
    peak_hands = 0
    peak_crops: Counter = Counter()
    peak_animals: Counter = Counter()

    for state in replay["steps"]:
        agent_state = state[player]
        obs = agent_state.get("observation") or {}
        farms = obs.get("farms") or []
        if player >= len(farms):
            continue
        farm = farms[player]
        hands = len(farm.get("hands") or [])
        peak_hands = max(peak_hands, hands)
        for target in (4, 8, 10, 12):
            if hands >= target:
                _first_reached(milestones, f"hands_{target}", hands, obs)
        quadrants = len(farm.get("unlocked_quadrants") or [])
        for target in (2, 3, 4):
            if quadrants >= target:
                _first_reached(milestones, f"quadrants_{target}", quadrants, obs)

        crops, animals = _tile_assets(farm.get("tiles") or [])
        peak_crops |= crops
        peak_animals |= animals
        for animal in ("GOOSE", "COW", "SHEEP"):
            if animals[animal]:
                _first_reached(milestones, f"first_{animal.lower()}", animals[animal], obs)

        action = agent_state.get("action") or {}
        if not isinstance(action, dict):
            continue
        market = action.get("market") or []
        if market and initial_market is None:
            initial_market = {**_stamp(obs), "orders": market}
        for order in market:
            if not order:
                continue
            name = str(order[0])
            item = str(order[1]) if len(order) > 1 else ""
            key = f"{name}:{item}" if item else name
            market_counts[key] += 1
            quantity = int(order[2]) if len(order) > 2 else 1
            market_quantities[key] += quantity
            if name == "HIRE":
                hires_by_day[int(obs.get("day", 0))] += 1
            elif name == "BUY_LAND":
                land_orders.append(_stamp(obs))

        units = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
        for unit_action in units:
            if not unit_action:
                continue
            name = str(unit_action[0])
            unit_counts[name] += 1
            if name == "PLANT" and len(unit_action) > 1:
                plant_counts[str(unit_action[1])] += 1
            if name == "PLACE" and len(unit_action) > 1:
                place_counts[str(unit_action[1])] += 1

    final_state = replay["steps"][-1][player]
    final_obs = final_state["observation"]
    final_farm = final_obs["farms"][player]
    final_crops, final_animals = _tile_assets(final_farm.get("tiles") or [])
    return {
        "team": team,
        "player": player,
        "reward": final_state.get("reward"),
        "status": final_state.get("status"),
        "initial_market": initial_market,
        "market_order_counts": dict(market_counts.most_common()),
        "market_quantities": dict(market_quantities.most_common()),
        "hires_by_day": dict(sorted(hires_by_day.items())),
        "land_orders": land_orders,
        "milestones": milestones,
        "peak_hands": peak_hands,
        "peak_crops": dict(peak_crops),
        "peak_animals": dict(peak_animals),
        "unit_action_counts": dict(unit_counts.most_common()),
        "plant_counts": dict(plant_counts.most_common()),
        "place_counts": dict(place_counts.most_common()),
        "final_money": final_farm.get("money"),
        "final_quadrants": final_farm.get("unlocked_quadrants"),
        "final_crops": dict(final_crops),
        "final_animals": dict(final_animals),
    }


def run(source: Path, output: Path) -> dict[str, Any]:
    episodes = []
    for path in sorted(source.glob("episode-*-replay.json")):
        raw = path.read_bytes()
        replay = json.loads(raw)
        episodes.append(
            {
                "episode_id": replay["info"]["EpisodeId"],
                "seed": replay["info"].get("seed"),
                "source": path.as_posix(),
                "source_sha256": hashlib.sha256(raw).hexdigest().upper(),
                "agents": [analyze_agent(replay, player) for player in range(2)],
            }
        )
    report = {"schema_version": 1, "episode_count": len(episodes), "episodes": episodes}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze targeted top-ladder replays")
    parser.add_argument("--source", type=Path, default=Path("references/top-replays"))
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/research/top_replay_report.json")
    )
    args = parser.parse_args()
    report = run(args.source, args.output)
    print(json.dumps({"episodes": report["episode_count"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
