from __future__ import annotations

import pytest

from kaggriculture_lab.evaluation.runtime import percentile


def test_percentile_uses_a_deterministic_nearest_rank() -> None:
    values = [4.0, 1.0, 3.0, 2.0]
    assert percentile(values, 0.0) == 1.0
    assert percentile(values, 0.5) == 3.0
    assert percentile(values, 1.0) == 4.0


def test_percentile_rejects_empty_values() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        percentile([], 0.5)
