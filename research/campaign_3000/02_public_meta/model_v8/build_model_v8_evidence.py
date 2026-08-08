"""Build deterministic model-v8 file and checkpoint evidence from a read-only download."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from inspect_checkpoint import inspect_checkpoint

ROOT = Path(__file__).resolve().parent
EXPECTED_FILES = {
    "README.md": (1738, "66F42BB08FCE8D01B3B13D59454F4DF6ABFD2E187B0E56E532D3FFABD0FFB790"),
    "README.md.metadata.json": (94, "760F1398C07FE1CE70D585912FBA9BC8FDDE4F926439FBECB2EFE84964D8914A"),
    "banner.jpg": (1062570, "466FA19151849BB2AEECF3350B85542F035640CA4970EA3F6EE46BDBFF4B9764"),
    "dqn_baseline_weights.pth": (6431, "9756ADC933DA10D78ADDA449397A83D923995EF4585500B9814A9030CE3E6A3A"),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def write_stable(path: Path, payload: dict[str, Any]) -> None:
    if path.is_file():
        existing = json.loads(path.read_text(encoding="utf-8"))
        candidate = dict(payload)
        candidate["retrieved_at_utc"] = existing.get("retrieved_at_utc")
        if candidate == existing:
            payload = existing
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if not path.is_file() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--download-dir", type=Path, required=True)
    args = parser.parse_args()
    download = args.download_dir.resolve()
    files = []
    for name, (expected_bytes, expected_sha) in EXPECTED_FILES.items():
        path = download / name
        if not path.is_file():
            raise ValueError(f"missing downloaded model file: {path}")
        actual = {"bytes": path.stat().st_size, "name": name, "sha256": sha256(path)}
        if actual["bytes"] != expected_bytes or actual["sha256"] != expected_sha:
            raise ValueError(f"download drift: {actual}")
        files.append(actual)
    if (download / "README.md").read_text(encoding="utf-8").rstrip("\r\n") != (
        ROOT / "upstream_README.md"
    ).read_text(encoding="utf-8").rstrip("\r\n"):
        raise ValueError("tracked upstream README normalized-text drift")
    if (download / "README.md.metadata.json").read_text(encoding="utf-8").rstrip("\r\n") != (
        ROOT / "upstream_README.metadata.json"
    ).read_text(encoding="utf-8").rstrip("\r\n"):
        raise ValueError("tracked upstream README metadata normalized-text drift")

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    file_payload = {
        "api_creation_date": "2026-08-08T19:45:18.739000Z",
        "download_command": "kaggle models instances versions download saitejabandaruin/kaggriculture-dqn-weights/PyTorch/pytorch-v1/8 --untar -f",
        "files": files,
        "population_boundary": "ONE_TEXT_SEARCH_HIT_ANALYZED;_NO_OFFICIAL_COMPETITION_MODEL_FILTER",
        "ref": "saitejabandaruin/kaggriculture-dqn-weights/PyTorch/pytorch-v1/8",
        "retrieved_at_utc": now,
        "schema_version": 1,
        "storage": {
            "large_banner_tracked": False,
            "raw_download": "IGNORED_LOCAL_DIST;_RETRIEVABLE_BY_PINNED_OFFICIAL_COMMAND",
            "small_upstream_text_tracked_normalized_lf": True,
            "weights_tracked": False,
        },
    }
    checkpoint = inspect_checkpoint(download / "dqn_baseline_weights.pth")
    checkpoint.update(
        {
            "architecture_comparison": {
                "api_usage_claim": "Sequential Linear(10,256), ReLU, Linear(256,128), ReLU, Linear(128,4)",
                "checkpoint_inferred": "Linear(10,64), unknown activation, Linear(64,4)",
                "checkpoint_keys": ["fc1.weight", "fc1.bias", "fc2.weight", "fc2.bias"],
                "published_readme_claim": "self.fc Sequential Linear(10,256), ReLU, Linear(256,128), ReLU, Linear(128,4)",
                "published_readme_expected_keys": [
                    "fc.0.weight",
                    "fc.0.bias",
                    "fc.2.weight",
                    "fc.2.bias",
                    "fc.4.weight",
                    "fc.4.bias",
                ],
                "published_interface_compatible": False,
            },
            "retrieved_at_utc": now,
            "schema_version": 1,
        }
    )
    write_stable(ROOT / "file_inventory_v8.json", file_payload)
    write_stable(ROOT / "checkpoint_static_analysis.json", checkpoint)
    print(json.dumps({"files": len(files), "status": "PASS_STATIC_ONLY"}, sort_keys=True))


if __name__ == "__main__":
    main()
