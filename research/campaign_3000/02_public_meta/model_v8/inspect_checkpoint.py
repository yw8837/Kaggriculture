"""Statically inspect the pinned PyTorch checkpoint without unpickling it."""

from __future__ import annotations

import hashlib
import pickletools
import zipfile
from pathlib import Path
from typing import Any

EXPECTED_CHECKPOINT_SHA256 = "9756ADC933DA10D78ADDA449397A83D923995EF4585500B9814A9030CE3E6A3A"
EXPECTED_GLOBALS = {
    "collections OrderedDict",
    "torch FloatStorage",
    "torch._utils _rebuild_tensor_v2",
}
TENSOR_KEYS = ("fc1.weight", "fc1.bias", "fc2.weight", "fc2.bias")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _integer_arg(op_name: str, arg: Any) -> int | None:
    if op_name in {"BININT", "BININT1", "BININT2", "LONG", "LONG1", "LONG4", "INT"}:
        return int(arg)
    return None


def _tensor_shapes(data: bytes) -> dict[str, list[int]]:
    """Extract tensor shape tuples from the known state-dict pickle grammar."""
    ops = list(pickletools.genops(data))
    key_positions = {
        str(arg): index
        for index, (op, arg, _pos) in enumerate(ops)
        if op.name in {"BINUNICODE", "SHORT_BINUNICODE"} and arg in TENSOR_KEYS
    }
    shapes: dict[str, list[int]] = {}
    for key in TENSOR_KEYS:
        index = key_positions[key]
        persistent_index = next(
            i for i in range(index + 1, len(ops)) if ops[i][0].name == "BINPERSID"
        )
        values: list[int] = []
        tuple_arity = 0
        for op, arg, _pos in ops[persistent_index + 1 :]:
            if op.name in {"TUPLE1", "TUPLE2", "TUPLE3"}:
                tuple_arity = int(op.name[-1])
                break
            value = _integer_arg(op.name, arg)
            if value is not None:
                values.append(value)
        if tuple_arity < 1 or len(values) < tuple_arity + 1:
            raise ValueError(f"cannot extract shape for {key}")
        shapes[key] = values[1 : tuple_arity + 1]
    return shapes


def inspect_checkpoint(path: Path) -> dict[str, Any]:
    if path.stat().st_size != 6431:
        raise ValueError(f"checkpoint byte drift: {path.stat().st_size}")
    if sha256(path) != EXPECTED_CHECKPOINT_SHA256:
        raise ValueError("checkpoint SHA-256 drift")
    if not zipfile.is_zipfile(path):
        raise ValueError("checkpoint is not a ZIP-based PyTorch archive")

    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if any(Path(info.filename).is_absolute() or ".." in Path(info.filename).parts for info in infos):
            raise ValueError("unsafe checkpoint member path")
        names = [info.filename for info in infos]
        pickle_name = next(name for name in names if name.endswith("/data.pkl"))
        pickle_bytes = archive.read(pickle_name)
        globals_seen = sorted(
            {
                str(arg)
                for op, arg, _pos in pickletools.genops(pickle_bytes)
                if op.name == "GLOBAL"
            }
        )
        if set(globals_seen) != EXPECTED_GLOBALS:
            raise ValueError(f"unexpected pickle globals: {globals_seen}")
        shapes = _tensor_shapes(pickle_bytes)
        if shapes != {
            "fc1.weight": [64, 10],
            "fc1.bias": [64],
            "fc2.weight": [4, 64],
            "fc2.bias": [4],
        }:
            raise ValueError(f"checkpoint tensor drift: {shapes}")
        members = [
            {
                "compressed_bytes": info.compress_size,
                "crc32": f"{info.CRC:08X}",
                "name": info.filename,
                "uncompressed_bytes": info.file_size,
            }
            for info in infos
        ]

    return {
        "checkpoint": {
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "serialization": "PYTORCH_ZIP_STATIC_ONLY",
        },
        "execution_safety": {
            "arbitrary_code_executed": False,
            "pickle_unpickled": False,
            "pytorch_imported": False,
            "technique": "zipfile + pickletools opcode scan only",
        },
        "pickle": {
            "bytes": len(pickle_bytes),
            "globals": globals_seen,
            "sha256": hashlib.sha256(pickle_bytes).hexdigest().upper(),
        },
        "state_dict": {
            "inferred_compatible_linear_shapes": ["10->64", "64->4"],
            "parameter_count": 964,
            "tensor_keys": list(TENSOR_KEYS),
            "tensor_shapes": shapes,
        },
        "zip_members": members,
    }
