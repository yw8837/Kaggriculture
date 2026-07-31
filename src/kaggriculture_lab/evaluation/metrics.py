from __future__ import annotations

import math
from collections.abc import Iterable


def wilson_interval(wins: int, games: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if games <= 0:
        return (0.0, 1.0)
    p = wins / games
    denominator = 1.0 + z * z / games
    center = (p + z * z / (2.0 * games)) / denominator
    radius = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * games)) / games) / denominator
    return (max(0.0, center - radius), min(1.0, center + radius))


def mean(values: Iterable[float]) -> float:
    items = list(values)
    if not items:
        raise ValueError("mean requires at least one value")
    return sum(items) / len(items)

