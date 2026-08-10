from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

STARTUP_ENVIRONMENT_NAMES = (
    "PYTHONPATH",
    "PYTHONHOME",
    "PYTHONSTARTUP",
    "PYTHONINSPECT",
    "PYTHONUSERBASE",
)


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit("usage: run_frozen_python.py PROJECT_ROOT {runner|gate} ...")
    project_root = Path(sys.argv[1]).resolve()
    mode = sys.argv[2]
    forwarded = sys.argv[3:]

    for name in STARTUP_ENVIRONMENT_NAMES:
        os.environ.pop(name, None)

    sys.path.insert(0, str(project_root / "src"))
    sys.path.insert(1, str(project_root / ".venv" / "Lib" / "site-packages"))

    if mode == "runner":
        sys.argv = ["kaggriculture_lab.evaluation.runner", *forwarded]
        runpy.run_module("kaggriculture_lab.evaluation.runner", run_name="__main__")
        return
    if mode == "gate":
        target = (
            project_root
            / "research"
            / "campaign_3000"
            / "12_next_candidates"
            / "development_gate.py"
        )
        sys.argv = [str(target), *forwarded]
        runpy.run_path(str(target), run_name="__main__")
        return
    raise SystemExit(f"unsupported frozen Python mode: {mode}")


if __name__ == "__main__":
    main()
