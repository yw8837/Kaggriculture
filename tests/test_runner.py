from __future__ import annotations

from kaggriculture_lab.evaluation.runner import GameResult, summarize


def _row(seat: int, mine: float, theirs: float) -> GameResult:
    return GameResult("opponent", 7, seat, mine, theirs, "DONE", "DONE", 1.0, None)


def test_summary_clusters_but_scores_both_seats() -> None:
    summary = summarize([_row(0, 10, 5), _row(1, 10, 5)])
    assert summary["raw_games"] == 2
    assert summary["seed_opponent_pairs"] == 1
    assert summary["wins"] == 2
    assert summary["seat_pair_differences"] == []


def test_summary_flags_seat_difference() -> None:
    summary = summarize([_row(0, 10, 5), _row(1, 9, 5)])
    assert len(summary["seat_pair_differences"]) == 1
