"""Bootstrap the workspace runner with the bundled Python runtime.

This helper is diagnostic-only. It does not open a seed pool or alter the
runner contract; it supplies the editable source and existing venv packages on
``sys.path`` without setting startup-environment variables rejected by the
hardened engine gate.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
VENV_SITE = ROOT / ".venv" / "Lib" / "site-packages"
SRC = ROOT / "src"

for path in (str(SRC), str(VENV_SITE)):
    if path not in sys.path:
        sys.path.insert(0, path)

main = importlib.import_module("kaggriculture_lab.evaluation.runner").main


if __name__ == "__main__":
    main()
