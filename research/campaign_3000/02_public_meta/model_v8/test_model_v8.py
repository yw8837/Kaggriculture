from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from inspect_checkpoint import inspect_checkpoint

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[3]
RAW = PROJECT / "dist/model-v8-download/dqn_baseline_weights.pth"


def test_checkpoint_static_inspection_never_imports_torch() -> None:
    sys.modules.pop("torch", None)
    report = inspect_checkpoint(RAW)
    assert "torch" not in sys.modules
    assert report["execution_safety"] == {
        "arbitrary_code_executed": False,
        "pickle_unpickled": False,
        "pytorch_imported": False,
        "technique": "zipfile + pickletools opcode scan only",
    }
    assert report["state_dict"]["tensor_shapes"] == {
        "fc1.weight": [64, 10],
        "fc1.bias": [64],
        "fc2.weight": [4, 64],
        "fc2.bias": [4],
    }


def test_checkpoint_byte_mutation_is_rejected(tmp_path: Path) -> None:
    mutated = tmp_path / "mutated.pth"
    payload = bytearray(RAW.read_bytes())
    payload[-1] ^= 1
    mutated.write_bytes(payload)
    with pytest.raises(ValueError, match="SHA-256 drift"):
        inspect_checkpoint(mutated)


def test_published_interface_is_explicitly_rejected() -> None:
    analysis = json.loads((ROOT / "checkpoint_static_analysis.json").read_text(encoding="utf-8"))
    disposition = json.loads((ROOT / "disposition.json").read_text(encoding="utf-8"))
    assert analysis["architecture_comparison"]["published_interface_compatible"] is False
    assert disposition["design_impact"]["used_in_kag_01_or_kag_02"] is False
    assert disposition["decision"] == "UNUSABLE_WITH_PUBLISHED_INTERFACE_AND_UNVERIFIED_FOR_KAGGRICULTURE"
