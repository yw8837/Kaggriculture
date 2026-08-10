from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from kaggriculture_lab.research.kag04_seat0_horizon4 import (
    _HORIZON_LOOP,
    _SEAT0_HORIZON_LOOP,
    TETSU_V16_BASE_PATH,
    TETSU_V16_SHA256,
    build_source,
    materialize_file,
)


def _base_bytes() -> bytes:
    return TETSU_V16_BASE_PATH.read_bytes()


def _namespace() -> dict[str, object]:
    namespace: dict[str, object] = {}
    exec(build_source(_base_bytes()), namespace)  # noqa: S102
    return namespace


def test_pinned_base_builds_deterministically_with_one_horizon_delta() -> None:
    base = _base_bytes()
    built = build_source(base)

    assert hashlib.sha256(base).hexdigest().upper() == TETSU_V16_SHA256
    assert built == build_source(base)
    assert base.decode("utf-8").count(_HORIZON_LOOP) == 1
    assert built.count(_HORIZON_LOOP) == 0
    assert built.count(_SEAT0_HORIZON_LOOP) == 1
    assert built.count("            _kag04_record_preemption(horizon)\n") == 1
    compile(built, "kag04.py", "exec")


def test_metrics_wrap_without_changing_base_return_object() -> None:
    namespace = _namespace()
    namespace["reset_rescue_metrics"]()
    expected = {"farmer": ["PASS"], "hands": [], "market": []}
    namespace["_kag04_base_agent"] = lambda obs: expected

    assert namespace["agent"]({"player": 0}) is expected
    namespace["_kag04_record_preemption"](4)
    namespace["_kag04_record_preemption"](3)

    assert namespace["rescue_metrics"]() == {
        "calls": 1,
        "preemptions": 2,
        "horizon4_preemptions": 1,
    }
    assert namespace["reset_rescue_metrics"]() == {
        "calls": 0,
        "preemptions": 0,
        "horizon4_preemptions": 0,
    }


def test_wrong_base_is_rejected() -> None:
    with pytest.raises(ValueError, match="pinned Tetsu v16"):
        build_source(b"def agent(obs):\n    return {}\n")


def test_materialization_receipt_binds_output(tmp_path: Path) -> None:
    output_path = tmp_path / "main.py"
    receipt_path = tmp_path / "receipt.json"

    receipt = materialize_file(TETSU_V16_BASE_PATH, output_path, receipt_path)

    assert receipt["base_sha256"] == TETSU_V16_SHA256
    assert receipt["output_sha256"] == hashlib.sha256(output_path.read_bytes()).hexdigest().upper()
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == receipt
