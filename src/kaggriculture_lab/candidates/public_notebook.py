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
                "source": [
                    f"# {title}\n",
                    "\n",
                    "A readable, reproducible expansion baseline for Kaggriculture. It buys ",
                    "land early, runs mixed crops and a mixed herd, and uses extra hands to work ",
                    "the larger farm. The source is fully visible below.\n",
                    "\n",
                    "## Important limitations\n",
                    "\n",
                    "The hiring rule is intentionally simple, targets are fixed, and the policy ",
                    "has no opponent conditioning and uses simple late-horizon/inventory rules. ",
                    "This is a public baseline, not our current private competition agent.\n",
                    "\n",
                    "Evaluate agents on paired seeds in both seats; a single ladder rating is a ",
                    "noisy early signal, not a guaranteed strength estimate.\n",
                ],
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
                "id": "deterministic-package",
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": package_cell.splitlines(keepends=True),
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
