"""Sampling statistics: AI answers vary run to run, so rates carry confidence intervals."""

from __future__ import annotations

import math
from dataclasses import dataclass

Z95 = 1.959964


@dataclass(frozen=True)
class Rate:
    successes: int
    trials: int
    rate: float | None
    low: float | None
    high: float | None


def wilson(successes: int, trials: int, z: float = Z95) -> Rate:
    """Wilson score interval: well-behaved for small samples and rates near 0 or 1."""
    if trials <= 0:
        return Rate(successes, trials, None, None, None)
    p = successes / trials
    denom = 1 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denom
    margin = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denom
    return Rate(
        successes,
        trials,
        round(p, 4),
        round(max(0.0, centre - margin), 4),
        round(min(1.0, centre + margin), 4),
    )
