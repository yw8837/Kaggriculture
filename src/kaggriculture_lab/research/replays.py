from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def _seat_rows(episodes: pd.DataFrame) -> pd.DataFrame:
    common = ["episode_id", "type", "state"]
    rows = []
    for seat in (0, 1):
        other = 1 - seat
        frame = episodes[
            common
            + [
                f"sub_{seat}",
                f"team_{seat}",
                f"bank_{seat}",
                f"rating_{seat}",
                f"bank_{other}",
            ]
        ].copy()
        frame.columns = common + [
            "submission_id",
            "team_id",
            "final_money",
            "rating_after",
            "opponent_money",
        ]
        frame["seat"] = seat
        rows.append(frame)
    return pd.concat(rows, ignore_index=True)


def _safe_median(series: pd.Series) -> float | None:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return None if values.empty else float(values.median())


def _summarize(group: pd.DataFrame) -> dict[str, float | int | None]:
    decisive = group["final_money"].ne(group["opponent_money"])
    return {
        "games": len(group),
        "wins": int(group["final_money"].gt(group["opponent_money"]).sum()),
        "draws": int(group["final_money"].eq(group["opponent_money"]).sum()),
        "win_rate": float(group["final_money"].gt(group["opponent_money"]).mean()),
        "decisive_win_rate": (
            float(group.loc[decisive, "final_money"].gt(group.loc[decisive, "opponent_money"]).mean())
            if decisive.any()
            else None
        ),
        "median_final_money": _safe_median(group["final_money"]),
        "median_margin": _safe_median(group["final_money"] - group["opponent_money"]),
        "median_peak_crew": _safe_median(group["peak_crew"]),
        "median_total_hires": _safe_median(group["total_hires"]),
        "median_first_land_day": _safe_median(group["first_land_day"]),
        "land_purchase_rate": float(group["first_land_day"].notna().mean()),
        "median_tiles_planted": _safe_median(group["tiles_planted"]),
    }


def analyze(dataset: Path) -> dict:
    episodes = pd.read_csv(dataset / "episodes.csv")
    features = pd.read_csv(dataset / "episode_features.csv")
    teams = pd.read_csv(dataset / "teams.csv")

    public = episodes[
        episodes["type"].eq("EPISODE_TYPE_PUBLIC") & episodes["state"].eq("COMPLETED")
    ].copy()
    seats = _seat_rows(public)
    data = seats.merge(features, on=["episode_id", "seat"], how="inner", suffixes=("", "_feature"))
    data["final_money"] = data["final_money"].fillna(data["final_money_feature"])
    data = data.merge(teams[["team_id", "team_name", "ladder_score"]], on="team_id", how="left")

    ranked = teams.dropna(subset=["ladder_score"]).sort_values("ladder_score", ascending=False)
    top5 = set(ranked.head(5)["team_id"])
    next15 = set(ranked.iloc[5:20]["team_id"])
    data["tier"] = np.select(
        [data["team_id"].isin(top5), data["team_id"].isin(next15)],
        ["top5", "rank6_20"],
        default="rest",
    )

    crop_columns = [column for column in data.columns if column.startswith("plants_")]
    team_summaries = []
    for team_id, group in data.groupby("team_id", dropna=False):
        name = group["team_name"].dropna()
        score = group["ladder_score"].dropna()
        summary = {
            "team_id": int(team_id),
            "team_name": None if name.empty else str(name.iloc[0]),
            "ladder_score": None if score.empty else float(score.iloc[0]),
            **_summarize(group),
        }
        crop_totals = group[crop_columns].sum().sort_values(ascending=False)
        summary["top_crop"] = crop_totals.index[0].removeprefix("plants_") if crop_totals.sum() else None
        team_summaries.append(summary)

    tier_summaries = {
        tier: _summarize(group) for tier, group in data.groupby("tier", observed=True)
    }
    seat_summaries = {
        str(int(seat)): _summarize(group) for seat, group in data.groupby("seat")
    }

    return {
        "snapshot": {
            "episodes_total": len(episodes),
            "public_completed": len(public),
            "public_replays_with_features": int(data["episode_id"].nunique()),
            "teams_ranked": int(ranked["team_id"].nunique()),
        },
        "tier_summaries": tier_summaries,
        "seat_summaries": seat_summaries,
        "top_teams": sorted(
            team_summaries,
            key=lambda row: -float(row["ladder_score"] or -1),
        )[:20],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = analyze(args.dataset)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
