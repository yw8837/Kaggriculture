from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def prepare_public_notebook(
    source: Path,
    output_dir: Path,
    kernel_id: str,
    title: str,
    competition: str,
) -> dict:
    """Create a readable public notebook that builds a deterministic agent archive."""
    payload = source.read_bytes()
    compile(payload, "main.py", "exec")
    source_sha256 = _sha256(payload)
    output_dir.mkdir(parents=True, exist_ok=True)

    source_text = payload.decode("utf-8")
    write_cell = "%%writefile main.py\n" + source_text
    overview = f"""# {title}

This notebook is a readable, reproducible starting agent for Kaggriculture. It demonstrates
conditional early land expansion, a mixed crop and cow/sheep plan, a wheat feed reserve, and
deterministic task assignment for a larger workforce.

The goal is to make the policy easy to inspect and test. It is a public learning baseline, not a
leaderboard promise or the current private competition agent.
"""
    timeline = """## Strategy timeline

| Phase | What the agent does | Trade-off to inspect |
|---|---|---|
| Opening, days 0-4 | Starts the fixed crop and herd plan while preserving working capital. | Fixed targets are simple but cannot react to the opponent. |
| Expansion, days 5-18 | Conditionally buys up to two additional land quadrants when the budget buffer permits. | Earlier land increases capacity but can delay animals, seeds, or labor. |
| Production | Runs mixed crops, cow/sheep slots, a wheat feed reserve, and up to twelve hands. | The simple hiring target can overpay when little useful work remains. |
| Late horizon | Harvests held output, sells inventory, and returns carried goods near the end. | The end-game and near-capacity routing rules are intentionally basic. |

These are descriptions of the visible source below, not claims about a fixed leaderboard rating.
"""
    api_contract = """## Agent API contract

`agent(obs)` reads the current public farm state plus the player's official private observation
fields. It returns exactly three action channels:

- `farmer`: one action for the farmer;
- `hands`: one action per hired hand;
- `market`: a bounded list of buy, sell, hire, and land orders.

The policy is deterministic, uses only the Python standard library, and does not require internet
access or external data.
"""
    evaluation = """## A fair evaluation checklist

Use this checklist when changing one rule:

1. Run the baseline and challenger on the same seed list in both seats.
2. Score the full 720-turn horizon; do not stop after a strong opening.
3. Keep development and confirmation seed sets separate.
4. Record completed games, failures, invalid actions, and both match and money deltas.
5. Report runtime percentiles and the slowest call, not only an average.
6. Inspect cash, carried inventory, shed inventory, land timing, labor, and end-game actions.

A single ladder snapshot is useful feedback, but it is not a stable estimate of general strength.
"""
    verification = f"""## Deterministic package verification

The packaging cell below rereads the exact public source, verifies source SHA-256
`{source_sha256}`, and writes a deterministic archive containing only root `main.py`. It fixes tar
metadata and gzip time so identical source bytes produce identical archive bytes. The cell prints
the resulting source hash, archive hash, and byte count for verification.

## Known limitations and useful experiments

- Labor sizing is fixed and can overpay.
- Crop and herd targets do not condition on the opponent.
- Late-horizon adaptation and near-capacity inventory routing are simple.
- There is no standalone reuse license in this release; check the applicable Kaggle terms before
  reusing the source elsewhere.

Useful next experiments include changing one of labor sizing, crop mix, herd composition, or the
end game while keeping the paired both-seat evaluation contract unchanged.
"""
    package_cell = f'''import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path

SOURCE_PATH = Path("main.py")
OUTPUT_NAME = "public_expansion_baseline.tar.gz"
EXPECTED_SOURCE_SHA256 = {source_sha256!r}

payload = SOURCE_PATH.read_bytes()
actual_source_sha256 = hashlib.sha256(payload).hexdigest().upper()
assert actual_source_sha256 == EXPECTED_SOURCE_SHA256

compressed = io.BytesIO()
with (
    gzip.GzipFile(filename="", mode="wb", fileobj=compressed, mtime=0) as gz,
    tarfile.open(fileobj=gz, mode="w") as archive,
):
    info = tarfile.TarInfo("main.py")
    info.size = len(payload)
    info.mode = 0o644
    info.mtime = 0
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    archive.addfile(info, io.BytesIO(payload))

output_path = Path("/kaggle/working") / OUTPUT_NAME
output_path.write_bytes(compressed.getvalue())
with tarfile.open(output_path, "r:gz") as archive:
    assert archive.getnames() == ["main.py"]

print(json.dumps({{
    "artifact": OUTPUT_NAME,
    "source_sha256": actual_source_sha256,
    "archive_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest().upper(),
    "archive_bytes": output_path.stat().st_size,
}}))
'''
    notebook = {
        "cells": [
            {
                "id": "public-strategy-overview",
                "cell_type": "markdown",
                "metadata": {},
                "source": overview.splitlines(keepends=True),
            },
            {
                "id": "strategy-timeline",
                "cell_type": "markdown",
                "metadata": {},
                "source": timeline.splitlines(keepends=True),
            },
            {
                "id": "agent-api-contract",
                "cell_type": "markdown",
                "metadata": {},
                "source": api_contract.splitlines(keepends=True),
            },
            {
                "id": "readable-agent-source",
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": write_cell.splitlines(keepends=True),
            },
            {
                "id": "evaluation-checklist",
                "cell_type": "markdown",
                "metadata": {},
                "source": evaluation.splitlines(keepends=True),
            },
            {
                "id": "deterministic-package",
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": package_cell.splitlines(keepends=True),
            },
            {
                "id": "package-verification-and-limitations",
                "cell_type": "markdown",
                "metadata": {},
                "source": verification.splitlines(keepends=True),
            },
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    metadata = {
        "id": kernel_id,
        "title": title,
        "code_file": "public-expansion-baseline.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": False,
        "enable_gpu": False,
        "enable_tpu": False,
        "enable_internet": False,
        "machine_shape": "",
        "dataset_sources": [],
        "competition_sources": [competition],
        "kernel_sources": [],
        "model_sources": [],
    }
    notebook_path = output_dir / metadata["code_file"]
    metadata_path = output_dir / "kernel-metadata.json"
    notebook_path.write_text(
        json.dumps(notebook, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return {
        "source": source.as_posix(),
        "source_sha256": source_sha256,
        "kernel_id": kernel_id,
        "notebook": notebook_path.as_posix(),
        "metadata": metadata_path.as_posix(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a public Kaggle baseline notebook")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--kernel-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--competition", default="kaggriculture")
    args = parser.parse_args()
    print(
        json.dumps(
            prepare_public_notebook(
                args.source,
                args.output_dir,
                args.kernel_id,
                args.title,
                args.competition,
            ),
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
