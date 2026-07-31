from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import tarfile
from pathlib import Path

NUMBERED_ARTIFACT = re.compile(r"^Fa_\d{2} - [A-Za-z0-9][A-Za-z0-9 _-]*\.tar\.gz$")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def prepare_save_run(
    artifact: Path,
    output_dir: Path,
    kernel_id: str,
    title: str,
    competition: str,
) -> dict:
    """Create a private Kaggle notebook that emits the exact verified archive bytes."""
    if not NUMBERED_ARTIFACT.fullmatch(artifact.name):
        raise ValueError("artifact name must follow Fa_XX - Short Description.tar.gz")

    payload = artifact.read_bytes()
    artifact_sha256 = _sha256(payload)
    with tarfile.open(artifact, "r:gz") as archive:
        if archive.getnames() != ["main.py"]:
            raise ValueError("submission archive must contain only root main.py")
        extracted = archive.extractfile("main.py")
        if extracted is None:
            raise ValueError("submission archive is missing main.py")
        source = extracted.read()
        compile(source, "main.py", "exec")

    output_dir.mkdir(parents=True, exist_ok=True)
    notebook_name = f"{artifact.name.removesuffix('.tar.gz')}.ipynb"
    encoded = base64.b64encode(payload).decode("ascii")
    code = f'''# Emit the already-tested agent byte-for-byte; do not rebuild or edit it here.
import base64
import hashlib
import json
import tarfile
from pathlib import Path

ARTIFACT_NAME = {artifact.name!r}
EXPECTED_SHA256 = {artifact_sha256!r}
PAYLOAD_B64 = {encoded!r}

# Kaggle persists files written to /kaggle/working as Save & Run outputs.
working_dir = Path("/kaggle/working")
if not working_dir.exists():
    working_dir = Path.cwd()  # Local verification fallback.
output_path = working_dir / ARTIFACT_NAME
payload = base64.b64decode(PAYLOAD_B64)
actual_sha256 = hashlib.sha256(payload).hexdigest().upper()
assert actual_sha256 == EXPECTED_SHA256
output_path.write_bytes(payload)

# Fail the run if the archive contract changes or acquires an extra file.
with tarfile.open(output_path, "r:gz") as archive:
    members = archive.getnames()
assert members == ["main.py"]

print(json.dumps({{
    "artifact": ARTIFACT_NAME,
    "sha256": actual_sha256,
    "bytes": len(payload),
    "members": members,
}}))
'''
    notebook = {
        "cells": [
            {
                "id": "strategy-overview",
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    f"# {title}\n",
                    "\n",
                    "This private Save & Run wrapper emits the exact locally verified agent. ",
                    "The strategy source is intentionally not edited in this notebook, so the ",
                    "local and Kaggle artifact hashes remain identical.\n",
                ],
            },
            {
                "id": "emit-verified-artifact",
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": code.splitlines(keepends=True),
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
        "code_file": notebook_name,
        "language": "python",
        "kernel_type": "notebook",
        "is_private": True,
        "enable_gpu": False,
        "enable_tpu": False,
        "enable_internet": False,
        "machine_shape": "",
        "dataset_sources": [],
        "competition_sources": [competition],
        "kernel_sources": [],
        "model_sources": [],
    }
    notebook_path = output_dir / notebook_name
    metadata_path = output_dir / "kernel-metadata.json"
    notebook_path.write_text(
        json.dumps(notebook, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return {
        "artifact": artifact.as_posix(),
        "artifact_sha256": artifact_sha256,
        "artifact_bytes": len(payload),
        "kernel_id": kernel_id,
        "notebook": notebook_path.as_posix(),
        "metadata": metadata_path.as_posix(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a numbered Kaggle Save & Run notebook")
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--kernel-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--competition", default="kaggriculture")
    args = parser.parse_args()
    result = prepare_save_run(
        args.artifact,
        args.output_dir,
        args.kernel_id,
        args.title,
        args.competition,
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
