"""Verify the tracked v8 model evidence and optionally the ignored raw download."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from inspect_checkpoint import inspect_checkpoint

ROOT = Path(__file__).resolve().parent
SHA256_RE_LENGTH = 64


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--download-dir", type=Path)
    args = parser.parse_args()

    api = json.loads((ROOT / "api_snapshot_v8.json").read_text(encoding="utf-8"))
    files = json.loads((ROOT / "file_inventory_v8.json").read_text(encoding="utf-8"))
    analysis = json.loads((ROOT / "checkpoint_static_analysis.json").read_text(encoding="utf-8"))
    disposition = json.loads((ROOT / "disposition.json").read_text(encoding="utf-8"))
    tools = json.loads((ROOT / "tool_evidence.json").read_text(encoding="utf-8"))

    require(api["model"]["id"] == 737778, "model id")
    require(api["variation"]["version_number"] == 8, "model version")
    require(api["variation"]["license_name"] == "Apache 2.0", "model license")
    require(api["variation"]["total_uncompressed_bytes"] == 1070833, "model bytes")
    require(
        api["variation"]["usage_observed"]["declared_layers"][-1] == "Linear(128,4)",
        "usage architecture",
    )
    require(len(api["variation"]["usage_sha256"]) == SHA256_RE_LENGTH, "usage hash")

    by_name = {row["name"]: row for row in files["files"]}
    require(set(by_name) == {"README.md", "README.md.metadata.json", "banner.jpg", "dqn_baseline_weights.pth"}, "file set")
    require(sum(row["bytes"] for row in by_name.values()) == 1070833, "file byte total")
    upstream_readme = (ROOT / "upstream_README.md").read_text(encoding="utf-8")
    require("input_dim=10, output_dim=4" in upstream_readme, "README dimensions")
    require("nn.Linear(input_dim, 256)" in upstream_readme, "README first layer")
    require(
        json.loads((ROOT / "upstream_README.metadata.json").read_text(encoding="utf-8"))["summary"]
        == "Advanced Kaggriculture README",
        "README metadata",
    )

    require(analysis["execution_safety"]["arbitrary_code_executed"] is False, "execution safety")
    require(analysis["execution_safety"]["pickle_unpickled"] is False, "pickle safety")
    require(analysis["state_dict"]["tensor_shapes"] == {
        "fc1.weight": [64, 10],
        "fc1.bias": [64],
        "fc2.weight": [4, 64],
        "fc2.bias": [4],
    }, "tensor shapes")
    require(analysis["state_dict"]["parameter_count"] == 964, "parameter count")
    require(analysis["architecture_comparison"]["published_interface_compatible"] is False, "architecture mismatch")
    require(disposition["decision"] == "UNUSABLE_WITH_PUBLISHED_INTERFACE_AND_UNVERIFIED_FOR_KAGGRICULTURE", "disposition")
    require(disposition["design_impact"]["used_in_kag_01_or_kag_02"] is False, "candidate use")
    require(len(disposition["missing_contracts"]) == 6, "missing contracts")
    require(tools["agent_reach"]["authoritative_model_evidence_source"] is False, "Agent-Reach claim")

    if args.download_dir is not None:
        download = args.download_dir.resolve()
        for name, row in by_name.items():
            path = download / name
            require(path.is_file(), f"missing raw file: {path}")
            require(path.stat().st_size == row["bytes"], f"raw bytes: {name}")
            require(sha256(path) == row["sha256"], f"raw hash: {name}")
        reproduced = inspect_checkpoint(download / "dqn_baseline_weights.pth")
        require(reproduced["state_dict"] == analysis["state_dict"], "static checkpoint reproduction")
        require(reproduced["pickle"] == analysis["pickle"], "pickle reproduction")
        require(reproduced["zip_members"] == analysis["zip_members"], "ZIP reproduction")

    print(json.dumps({"files": 4, "model": "v8", "status": "PASS_STATIC_ONLY"}, sort_keys=True))


if __name__ == "__main__":
    main()
