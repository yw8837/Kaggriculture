from __future__ import annotations

import importlib.util
import tarfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR_PATH = (
    PROJECT_ROOT / "research/campaign_3000/06_candidates/orchestrator.py"
)
SPEC = importlib.util.spec_from_file_location("campaign_3000_results", ORCHESTRATOR_PATH)
assert SPEC and SPEC.loader
orchestrator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(orchestrator)


def test_development_close_recomputes_both_exact_tracked_gates() -> None:
    result = orchestrator.validate_development_close()

    assert result["status"] == "DEVELOPMENT_CLOSED_VALIDATED"
    assert result["fresh_games_executed"] == 256
    assert result["external_actions"] == "HOLD"
    assert [(row["slot"], row["valid_games"], row["strict_verdict"]) for row in result["results"]] == [
        ("Kag_01", 128, "PASS"),
        ("Kag_02", 128, "NO_GO"),
    ]


def test_closed_results_cannot_reopen_or_extend_seed_authority() -> None:
    with pytest.raises(PermissionError, match="no exact independent-auditor OPEN receipt"):
        orchestrator.require_open_authority("Kag_01", "development")
    with pytest.raises(PermissionError, match="no exact independent-auditor OPEN receipt"):
        orchestrator.require_open_authority("Kag_02", "confirmation")


def test_close_rejects_spoofed_historic_o_parent(monkeypatch: pytest.MonkeyPatch) -> None:
    real_git_text = orchestrator._git_text

    def spoofed_git_text(project_root: Path, *arguments: str) -> str:
        if arguments[:3] == ("rev-list", "--parents", "-n"):
            return f"{orchestrator.EXECUTION_AUTHORITY_COMMIT} {'0' * 40}"
        return real_git_text(project_root, *arguments)

    monkeypatch.setattr(orchestrator, "_git_text", spoofed_git_text)
    with pytest.raises(ValueError, match="exact sole parent E"):
        orchestrator._validate_historic_open_authority_lineage()


def test_close_rejects_spoofed_historic_open_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(orchestrator, "_git_blob", lambda *_args: b"{}\n")
    with pytest.raises(ValueError, match="lifecycle blob SHA"):
        orchestrator._validate_historic_open_authority_lineage()


def test_exploratory_release_requires_package_and_independent_auditor() -> None:
    summary = orchestrator.validate_tracked_development_evidence("Kag_01")
    gate = orchestrator._load(
        PROJECT_ROOT
        / "research/campaign_3000/10_results/kag_01_development/gate.json"
    )
    metrics = gate["summary"]

    package_only = orchestrator.evaluate_exploratory_readiness(metrics, True, True, False)
    auditor_only = orchestrator.evaluate_exploratory_readiness(metrics, True, False, True)
    both = orchestrator.evaluate_exploratory_readiness(metrics, True, True, True)

    assert summary["strict_verdict"] == "PASS"
    assert package_only["verdict"] == "NOT_READY"
    assert package_only["checks"]["package_gate_pass"] is True
    assert package_only["checks"]["independent_auditor_release_pass"] is False
    assert auditor_only["verdict"] == "NOT_READY"
    assert both["verdict"] == "EXPLORATORY_PRIVATE_SAVERUN_READY_NON_PROMOTION"


def _assert_no_private_evidence(payload: bytes, label: str) -> None:
    forbidden = (
        b"research/campaign_3000/10_results",
        b"research\\campaign_3000\\10_results",
        b"research\\\\campaign_3000\\\\10_results",
        b"C:\\Users\\",
        b"C:\\\\Users\\\\",
        "최용우".encode(),
        b"\\ucd5c\\uc6a9\\uc6b0",
    )
    assert not [needle for needle in forbidden if needle in payload], label


def test_private_results_never_enter_kaggle_or_public_payloads() -> None:
    release_root = PROJECT_ROOT / "research/campaign_3000/07_release/local_build"
    for path in sorted(release_root.rglob("*.ipynb")):
        _assert_no_private_evidence(path.read_bytes(), path.as_posix())
    for path in sorted(release_root.rglob("*.tar.gz")):
        with tarfile.open(path, "r:gz") as archive:
            for member in archive.getmembers():
                if member.isfile():
                    extracted = archive.extractfile(member)
                    assert extracted is not None
                    _assert_no_private_evidence(
                        extracted.read(), f"{path.as_posix()}::{member.name}"
                    )

    public_root = PROJECT_ROOT / "research/campaign_3000/08_public_release"
    public_payloads = [
        public_root / "discussion_draft.md",
        public_root / "external_action_payload.json",
        public_root / "public_source/main.py",
        public_root / "kaggle_code_draft/kaggriculture-fixed-trace-safety-baseline.ipynb",
        public_root / "kaggle_code_draft/kernel-metadata.json",
    ]
    for path in public_payloads:
        _assert_no_private_evidence(path.read_bytes(), path.as_posix())
    for path in sorted((public_root / "artifact").glob("*.tar.gz")):
        with tarfile.open(path, "r:gz") as archive:
            for member in archive.getmembers():
                if member.isfile():
                    extracted = archive.extractfile(member)
                    assert extracted is not None
                    _assert_no_private_evidence(
                        extracted.read(), f"{path.as_posix()}::{member.name}"
                    )
