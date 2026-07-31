from __future__ import annotations

import hashlib
import json
from pathlib import Path

from kaggriculture_lab.evaluation import runner
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


def test_run_batch_writes_start_receipt_and_source_provenance(
    tmp_path: Path, monkeypatch,
) -> None:
    candidate = tmp_path / "candidate.py"
    opponent = tmp_path / "opponent.py"
    candidate.write_text("def agent(obs): return {}\n", encoding="utf-8")
    opponent.write_text("def agent(obs): return {}\n", encoding="utf-8")

    def fake_run(spec: runner.GameSpec) -> GameResult:
        return GameResult(
            spec.opponent_name, spec.seed, spec.seat, 10.0, 5.0,
            "DONE", "DONE", 0.01, None,
        )

    monkeypatch.setattr(runner, "_run_game", fake_run)
    output = tmp_path / "evaluation.json"
    report = runner.run_batch(
        "candidate.py", ["opponent.py"], [7], output, 1, tmp_path,
    )

    receipt = tmp_path / "evaluation.started.json"
    receipt_payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert receipt_payload["started_at_utc"] == report["started_at_utc"]
    assert receipt_payload["workers"] == 1
    assert report["sources_unchanged_during_run"] is True
    assert report["candidate_sha256_at_start"] == report["candidate_sha256_at_end"]
    assert report["start_receipt_sha256"] == hashlib.sha256(receipt.read_bytes()).hexdigest().upper()
