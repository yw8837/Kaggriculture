from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = (
    ROOT
    / "research"
    / "campaign_3000"
    / "12_next_candidates"
    / "run_frozen_python.ps1"
)
PYTHON_LAUNCHER = LAUNCHER.with_suffix(".py")


def _launch(mode: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(LAUNCHER),
            mode,
            *arguments,
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )


def test_launcher_is_narrow_and_clears_python_startup_inputs() -> None:
    text = LAUNCHER.read_text(encoding="utf-8")
    python_text = PYTHON_LAUNCHER.read_text(encoding="utf-8")

    assert '[ValidateSet("runner", "gate")]' in text
    assert 'mode == "runner"' in python_text
    assert 'mode == "gate"' in python_text
    for name in (
        "PYTHONPATH",
        "PYTHONHOME",
        "PYTHONSTARTUP",
        "PYTHONINSPECT",
        "PYTHONUSERBASE",
    ):
        assert name in text
        assert f'"{name}"' in python_text
    assert "os.environ.pop(name, None)" in python_text
    combined = text + python_text
    assert "kaggle kernels push" not in combined
    assert "kaggle competitions submit" not in combined


def test_launcher_dispatches_runner_help_without_uv_trampoline() -> None:
    result = _launch("runner", "--help")

    assert result.returncode == 0, result.stderr
    assert "Run paired Kaggriculture evaluations" in result.stdout
    assert "uv trampoline" not in result.stderr


def test_launcher_dispatches_gate_help_without_uv_trampoline() -> None:
    result = _launch("gate", "--help")

    assert result.returncode == 0, result.stderr
    assert "Validate CLOSED next-candidate evaluation plans" in result.stdout
    assert "uv trampoline" not in result.stderr


def test_launcher_rejects_every_unlisted_mode() -> None:
    result = _launch("arbitrary", "--help")

    assert result.returncode != 0
    assert "ValidateSet" in result.stderr or "valid values" in result.stderr
