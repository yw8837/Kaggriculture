from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def median(values: Iterable[float | int | None]) -> float | None:
    clean = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    return None if not clean else statistics.median(clean)


def mean(values: Iterable[float | int | None]) -> float | None:
    clean = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    return None if not clean else statistics.fmean(clean)


def quantile(values: Iterable[float | int | None], q: float) -> float | None:
    clean = sorted(float(value) for value in values if value is not None and math.isfinite(float(value)))
    if not clean:
        return None
    position = (len(clean) - 1) * q
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return clean[low]
    return clean[low] * (high - position) + clean[high] * (position - low)


def stable_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def selected_observations() -> list[dict[str, Any]]:
    inventory = read_jsonl(ROOT / "replay_inventory.jsonl")
    feature_report = json.loads((ROOT / "replay_feature_report.json").read_text(encoding="utf-8"))
    features = {int(row["episode_id"]): row for row in feature_report["episodes"]}
    output = []
    for replay_row in inventory:
        episode_id = int(replay_row["episode_id"])
        replay_features = features[episode_id]
        for request in replay_row["requested_by"]:
            player = int(request["target_seat"])
            agent = next(row for row in replay_features["agents"] if int(row["player"]) == player)
            opponent = next(row for row in replay_features["agents"] if int(row["player"]) != player)
            output.append(
                {
                    **request,
                    "replay_sha256": replay_row["sha256"],
                    "replay_bytes": replay_row["bytes"],
                    "seed": replay_row["seed"],
                    "feature": agent,
                    "opponent_feature": opponent,
                }
            )
    return output


def milestone_step(agent: dict[str, Any], key: str) -> int | None:
    row = agent["milestones"].get(key)
    return None if row is None else int(row["step"])


def day_row(agent: dict[str, Any], day: int) -> dict[str, Any] | None:
    return next((row for row in agent["daily"] if int(row["day"]) == day), None)


def summarize_observation(row: dict[str, Any]) -> dict[str, Any]:
    agent = row["feature"]
    opponent = row["opponent_feature"]
    market_counts = Counter(agent["market_order_counts"])
    market_quantities = Counter(agent["market_quantities"])
    unit_counts = Counter(agent["unit_action_counts"])
    daily = agent["daily"]
    capacity = sum(int(day["unit_action_capacity"]) for day in daily)
    non_pass = sum(int(day["unit_non_pass_actions"]) for day in daily)
    last_days = [day for day in daily if int(day["day"]) >= 27]
    shed_snapshots = []
    for day in daily:
        for label in ("opening", "last_observation"):
            snapshot = day.get(label) or {}
            shed_snapshots.append(sum(int(value) for value in (snapshot.get("shed") or {}).values()))
    own_money = float(agent["final_money"])
    opponent_money = float(opponent["final_money"])
    return {
        "cohort": row["cohort"],
        "episode_id": row["episode_id"],
        "replay_sha256": row["replay_sha256"],
        "seed": row["seed"],
        "seat": row["target_seat"],
        "rank": row.get("rank"),
        "team_id": row.get("team_id"),
        "team_name": row.get("team_name") or agent["team"],
        "submission_id": row.get("submission_id") or row["submission_id_queried"],
        "file_name": row.get("file_name"),
        "public_score": float(row["submission_public_score"]),
        "final_money": own_money,
        "opponent_money": opponent_money,
        "margin": own_money - opponent_money,
        "win": int(own_money > opponent_money),
        "draw": int(own_money == opponent_money),
        "first_land_step": int(agent["land_orders"][0]["step"]) if agent["land_orders"] else None,
        "land_orders": len(agent["land_orders"]),
        "quadrant2_step": milestone_step(agent, "quadrants_2"),
        "quadrant3_step": milestone_step(agent, "quadrants_3"),
        "quadrant4_step": milestone_step(agent, "quadrants_4"),
        "hands4_step": milestone_step(agent, "hands_4"),
        "hands8_step": milestone_step(agent, "hands_8"),
        "hands10_step": milestone_step(agent, "hands_10"),
        "hands12_step": milestone_step(agent, "hands_12"),
        "peak_hands": int(agent["peak_hands"]),
        "total_hire_orders": int(market_counts["HIRE"]),
        "first_cow_step": milestone_step(agent, "first_cow"),
        "first_sheep_step": milestone_step(agent, "first_sheep"),
        "first_goose_step": milestone_step(agent, "first_goose"),
        "peak_crops_total": sum(int(value) for value in agent["peak_crops"].values()),
        "peak_strawberry": int(agent["peak_crops"].get("STRAWBERRY", 0)),
        "peak_melon": int(agent["peak_crops"].get("MELON", 0)),
        "peak_wheat": int(agent["peak_crops"].get("WHEAT", 0)),
        "peak_animals_total": sum(int(value) for value in agent["peak_animals"].values()),
        "peak_cow": int(agent["peak_animals"].get("COW", 0)),
        "peak_sheep": int(agent["peak_animals"].get("SHEEP", 0)),
        "peak_goose": int(agent["peak_animals"].get("GOOSE", 0)),
        "sell_order_turns": sum(value for key, value in market_counts.items() if key.startswith("SELL:")),
        "sell_requested_units": sum(value for key, value in market_quantities.items() if key.startswith("SELL:")),
        "sell_wool_turns": int(market_counts["SELL:WOOL"]),
        "sell_milk_turns": int(market_counts["SELL:MILK"]),
        "sell_strawberry_turns": int(market_counts["SELL:STRAWBERRY"]),
        "sell_melon_turns": int(market_counts["SELL:MELON"]),
        "sell_wheat_turns": int(market_counts["SELL:WHEAT"]),
        "non_pass_rate": non_pass / capacity if capacity else None,
        "pass_actions": int(unit_counts["PASS"]),
        "movement_actions": sum(unit_counts[key] for key in ("NORTH", "SOUTH", "EAST", "WEST")),
        "productive_actions": sum(
            unit_counts[key]
            for key in (
                "PLANT",
                "WATER",
                "FERTILIZE",
                "HARVEST",
                "FEED",
                "CARE",
                "COLLECT_FERTILIZER",
                "PICKUP",
                "DROP",
                "PLACE",
            )
        ),
        "max_shed_units": max(shed_snapshots) if shed_snapshots else None,
        "final_shed_units": sum(int(value) for value in agent["final_shed"].values()),
        "final_seed_units": sum(int(value) for value in agent["final_seeds"].values()),
        "final_carried_units": sum(int(value) for value in agent["final_carried"].values()),
        "endgame_sell_turns_d27plus": sum(
            value
            for day in last_days
            for key, value in day["market_order_counts"].items()
            if key.startswith("SELL:")
        ),
        "endgame_sell_units_requested_d27plus": sum(
            value
            for day in last_days
            for key, value in day["market_quantities_requested"].items()
            if key.startswith("SELL:")
        ),
        "endgame_cash_delta_d27plus": sum(float(day["cash_delta"]) for day in last_days),
        **{
            f"money_close_day{day}": (
                None if day_row(agent, day) is None else float(day_row(agent, day)["money_close_after_actions"])
            )
            for day in (7, 10, 13, 20, 27, 29)
        },
    }


METRIC_KEYS = (
    "public_score",
    "final_money",
    "margin",
    "first_land_step",
    "land_orders",
    "quadrant2_step",
    "quadrant3_step",
    "hands4_step",
    "hands8_step",
    "hands10_step",
    "peak_hands",
    "total_hire_orders",
    "first_cow_step",
    "first_sheep_step",
    "peak_crops_total",
    "peak_strawberry",
    "peak_melon",
    "peak_wheat",
    "peak_animals_total",
    "peak_cow",
    "peak_sheep",
    "sell_order_turns",
    "sell_requested_units",
    "sell_wool_turns",
    "sell_milk_turns",
    "sell_strawberry_turns",
    "sell_melon_turns",
    "sell_wheat_turns",
    "non_pass_rate",
    "pass_actions",
    "movement_actions",
    "productive_actions",
    "max_shed_units",
    "final_shed_units",
    "final_seed_units",
    "final_carried_units",
    "endgame_sell_turns_d27plus",
    "endgame_sell_units_requested_d27plus",
    "endgame_cash_delta_d27plus",
    "money_close_day7",
    "money_close_day10",
    "money_close_day13",
    "money_close_day20",
    "money_close_day27",
    "money_close_day29",
)


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "observations": len(rows),
        "unique_episodes": len({row["episode_id"] for row in rows}),
        "unique_seeds": len({row["seed"] for row in rows}),
        "seat0": sum(int(row["seat"]) == 0 for row in rows),
        "seat1": sum(int(row["seat"]) == 1 for row in rows),
        "wins": sum(row["win"] for row in rows),
        "draws": sum(row["draw"] for row in rows),
        "win_rate": mean(row["win"] for row in rows),
    }
    for key in METRIC_KEYS:
        values = [row.get(key) for row in rows]
        result[key] = {
            "mean": mean(values),
            "median": median(values),
            "p10": quantile(values, 0.1),
            "p90": quantile(values, 0.9),
            "non_null": sum(value is not None for value in values),
        }
    return result


def full_episode_performance() -> dict[str, Any]:
    submissions = json.loads((ROOT / "our_submissions.json").read_text(encoding="utf-8"))["submissions"]
    episodes = read_jsonl(ROOT / "our_episode_inventory.jsonl")
    by_submission: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in episodes:
        if row["type"] == "EPISODE_TYPE_PUBLIC" and row["state"] == "COMPLETED":
            by_submission[int(row["submission_id_queried"])].append(row)
    result = []
    for submission in submissions:
        submission_id = int(submission["ref"])
        games = []
        for episode in by_submission[submission_id]:
            seats = episode["queried_team_seats"]
            if len(seats) != 1 or len(episode["agents"]) != 2:
                continue
            seat = int(seats[0])
            own = episode["agents"][seat]
            opponent = episode["agents"][1 - seat]
            own_reward = own.get("reward")
            opponent_reward = opponent.get("reward")
            if own_reward is None or opponent_reward is None:
                continue
            games.append(
                {
                    "episode_id": episode["episode_id"],
                    "seat": seat,
                    "own_reward": float(own_reward),
                    "opponent_reward": float(opponent_reward),
                    "margin": float(own_reward) - float(opponent_reward),
                    "win": int(float(own_reward) > float(opponent_reward)),
                    "draw": int(float(own_reward) == float(opponent_reward)),
                    "opponent_team": opponent.get("teamName"),
                    "opponent_team_id": opponent.get("teamId"),
                }
            )
        result.append(
            {
                "submission_id": submission_id,
                "file_name": submission.get("fileName"),
                "date": submission.get("date"),
                "public_score_at_snapshot": float(submission["publicScore"]),
                "games": len(games),
                "wins": sum(game["win"] for game in games),
                "draws": sum(game["draw"] for game in games),
                "losses": len(games) - sum(game["win"] + game["draw"] for game in games),
                "win_rate": mean(game["win"] for game in games),
                "mean_reward": mean(game["own_reward"] for game in games),
                "mean_margin": mean(game["margin"] for game in games),
                "p10_margin": quantile((game["margin"] for game in games), 0.1),
                "seat0_win_rate": mean(game["win"] for game in games if game["seat"] == 0),
                "seat1_win_rate": mean(game["win"] for game in games if game["seat"] == 1),
                "unique_opponents": len({game["opponent_team_id"] for game in games}),
            }
        )
    return {"submissions": result}


def full_top25_episode_performance() -> dict[str, Any]:
    leaderboard = json.loads((ROOT / "leaderboard_top25.json").read_text(encoding="utf-8"))["rows"]
    episodes = read_jsonl(ROOT / "top25_episode_inventory.jsonl")
    by_submission: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in episodes:
        if row["type"] == "EPISODE_TYPE_PUBLIC" and row["state"] == "COMPLETED":
            by_submission[int(row["submission_id_queried"])].append(row)
    output = []
    for team in leaderboard:
        public_submissions = sorted(
            team["public_submissions"], key=lambda row: float(row.get("publicScore") or -1), reverse=True
        )
        if not public_submissions:
            output.append(
                {
                    "rank": team["rank"],
                    "team_id": team["team_id"],
                    "team_name": team["team_name"],
                    "leaderboard_score": team["score"],
                    "status": "UNVERIFIED_NO_PUBLIC_SUBMISSION",
                }
            )
            continue
        submission = public_submissions[0]
        submission_id = int(submission["id"])
        games = []
        for episode in by_submission[submission_id]:
            seats = episode["queried_team_seats"]
            if len(seats) != 1 or len(episode["agents"]) != 2:
                continue
            seat = int(seats[0])
            own = episode["agents"][seat]
            opponent = episode["agents"][1 - seat]
            if own.get("reward") is None or opponent.get("reward") is None:
                continue
            own_reward = float(own["reward"])
            opponent_reward = float(opponent["reward"])
            games.append(
                {
                    "seat": seat,
                    "own_reward": own_reward,
                    "opponent_reward": opponent_reward,
                    "margin": own_reward - opponent_reward,
                    "win": int(own_reward > opponent_reward),
                    "draw": int(own_reward == opponent_reward),
                    "opponent_team_id": opponent.get("teamId"),
                }
            )
        output.append(
            {
                "rank": team["rank"],
                "team_id": team["team_id"],
                "team_name": team["team_name"],
                "leaderboard_score": team["score"],
                "submission_id": submission_id,
                "submission_public_score": float(submission["publicScore"]),
                "games": len(games),
                "wins": sum(game["win"] for game in games),
                "draws": sum(game["draw"] for game in games),
                "losses": len(games) - sum(game["win"] + game["draw"] for game in games),
                "win_rate": mean(game["win"] for game in games),
                "mean_reward": mean(game["own_reward"] for game in games),
                "mean_margin": mean(game["margin"] for game in games),
                "p10_margin": quantile((game["margin"] for game in games), 0.1),
                "seat0_win_rate": mean(game["win"] for game in games if game["seat"] == 0),
                "seat1_win_rate": mean(game["win"] for game in games if game["seat"] == 1),
                "unique_opponents": len({game["opponent_team_id"] for game in games}),
            }
        )
    return {"teams": output}


def action_fingerprints(observations: list[dict[str, Any]]) -> dict[str, Any]:
    needed: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for observation in observations:
        needed[int(observation["episode_id"])].append(observation)
    fingerprints = []
    for episode_id, requests in needed.items():
        replay = json.loads((ROOT / "replays_raw" / f"episode-{episode_id}-replay.json").read_text(encoding="utf-8"))
        for request in requests:
            player = int(request["seat"])
            actions = [state[player].get("action") for state in replay["steps"]]
            farm = [
                None
                if action is None
                else {"farmer": action.get("farmer"), "hands": action.get("hands")}
                for action in actions
            ]
            market = [None if action is None else action.get("market") for action in actions]
            fingerprints.append(
                {
                    "cohort": request["cohort"],
                    "rank": request.get("rank"),
                    "team_name": request["team_name"],
                    "file_name": request.get("file_name"),
                    "submission_id": request["submission_id"],
                    "episode_id": episode_id,
                    "seed": request["seed"],
                    "seat": player,
                    "action_steps": len(actions),
                    "full_action_sha256": stable_hash(actions),
                    "farm_action_sha256": stable_hash(farm),
                    "market_action_sha256": stable_hash(market),
                    "full_actions": actions,
                    "farm_actions": farm,
                    "market_actions": market,
                }
            )
    comparisons = []
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in fingerprints:
        key = (
            row["cohort"],
            row["team_name"] if row["cohort"] == "leaderboard_top25" else row["file_name"],
            row["submission_id"],
        )
        groups[key].append(row)
    for key, rows in groups.items():
        if len(rows) < 2:
            comparisons.append({"key": key, "status": "UNVERIFIED_ONLY_ONE_SAMPLE", "samples": len(rows)})
            continue
        a, b = rows[:2]
        full_diff = sum(x != y for x, y in zip(a["full_actions"], b["full_actions"], strict=True))
        farm_diff = sum(x != y for x, y in zip(a["farm_actions"], b["farm_actions"], strict=True))
        market_diff = sum(x != y for x, y in zip(a["market_actions"], b["market_actions"], strict=True))
        comparisons.append(
            {
                "cohort": key[0],
                "identity": key[1],
                "submission_id": key[2],
                "episode_ids": [a["episode_id"], b["episode_id"]],
                "seats": [a["seat"], b["seat"]],
                "seeds": [a["seed"], b["seed"]],
                "full_action_hash_equal": a["full_action_sha256"] == b["full_action_sha256"],
                "farm_action_hash_equal": a["farm_action_sha256"] == b["farm_action_sha256"],
                "market_action_hash_equal": a["market_action_sha256"] == b["market_action_sha256"],
                "full_action_different_steps": full_diff,
                "farm_action_different_steps": farm_diff,
                "market_action_different_steps": market_diff,
            }
        )
    public_rows = [row for row in fingerprints if row["cohort"] == "leaderboard_top25"]
    clusters = []
    for farm_hash, rows in defaultdict(list, {
        key: [row for row in public_rows if row["farm_action_sha256"] == key]
        for key in {row["farm_action_sha256"] for row in public_rows}
    }).items():
        identities = sorted({row["team_name"] for row in rows})
        clusters.append(
            {
                "farm_action_sha256": farm_hash,
                "observations": len(rows),
                "unique_teams": len(identities),
                "teams": identities,
                "ranks": sorted({row["rank"] for row in rows}),
                "submission_ids": sorted({row["submission_id"] for row in rows}),
            }
        )
    return {
        "observations": [
            {key: value for key, value in row.items() if key not in ("full_actions", "farm_actions", "market_actions")}
            for row in fingerprints
        ],
        "within_policy_two_game_comparisons": comparisons,
        "top25_farm_hash_clusters": sorted(
            clusters, key=lambda row: (-row["unique_teams"], row["farm_action_sha256"])
        ),
    }


def main() -> None:
    raw = selected_observations()
    observations = [summarize_observation(row) for row in raw]
    top = [row for row in observations if row["cohort"] == "leaderboard_top25"]
    ours = [row for row in observations if row["cohort"] == "our_submissions"]
    by_top_team = {
        name: aggregate(rows)
        for name, rows in sorted(
            ((name, [row for row in top if row["team_name"] == name]) for name in {row["team_name"] for row in top}),
            key=lambda item: min(row["rank"] for row in item[1]),
        )
    }
    by_our_file = {
        name: aggregate([row for row in ours if row["file_name"] == name])
        for name in {row["file_name"] for row in ours}
    }
    report = {
        "schema_version": 1,
        "sampling_contract": {
            "top25": "Two newest public completed episodes, one per seat where available, from each team's highest publicScore active submission in the pinned snapshot.",
            "ours": "Two newest public completed episodes, one per seat where available, from every one of 22 account submissions.",
            "limitations": [
                "The 2-game raw replay sample per policy is descriptive and cannot estimate generalization by itself.",
                "Full metadata win/margin summaries use all 1,017 observed account episode rows, but raw replay mechanics are sampled.",
                "Action fingerprint equality across only two games is evidence of a fixed tape; inequality does not prove robust state adaptation.",
            ],
        },
        "top25_sample": aggregate(top),
        "our_sample": aggregate(ours),
        "top25_by_team": by_top_team,
        "ours_by_file": by_our_file,
        "observations": observations,
        "action_fingerprint_analysis": action_fingerprints(observations),
        "full_our_episode_performance": full_episode_performance(),
        "full_top25_episode_performance": full_top25_episode_performance(),
    }
    path = ROOT / "comparative_metrics.json"
    path.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    raw_bytes = path.read_bytes()
    print(
        json.dumps(
            {
                "path": path.as_posix(),
                "bytes": len(raw_bytes),
                "sha256": hashlib.sha256(raw_bytes).hexdigest().upper(),
                "top25_observations": len(top),
                "our_observations": len(ours),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
