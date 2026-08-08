from __future__ import annotations

import argparse
import json
from pathlib import Path

from orchestrator import execute_authorized_run_receipt


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Authority-gated campaign_3000 development runner"
    )
    parser.add_argument("--run-receipt", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(execute_authorized_run_receipt(args.run_receipt), indent=2))


if __name__ == "__main__":
    main()
