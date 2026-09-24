"""Organic click-through-rate curves by position.

A default curve (aggregate of public CTR studies, position 1..20) is replaced by the
customer's own curve when their Search Console has enough data - so opportunities are
judged against *their* SERPs, not an industry average.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

DEFAULT_CURVE = [
    0.28, 0.155, 0.10, 0.07, 0.052, 0.04, 0.032, 0.026, 0.022, 0.019,
    0.012, 0.010, 0.009, 0.008, 0.007, 0.006, 0.0055, 0.005, 0.0045, 0.004,
]  # fmt: skip
MIN_IMPRESSIONS_PER_BUCKET = 500


def expected_ctr(position: float, curve: list[float] | None = None) -> float:
    curve = curve or DEFAULT_CURVE
    if position < 1:
        position = 1.0
    index = min(round(position) - 1, len(curve) - 1)
    return curve[index]


def fit_curve(rows: Iterable[tuple[float, int, int]]) -> tuple[list[float], bool]:
    """(position, clicks, impressions) rows -> (curve, fitted_from_own_data)."""
    clicks: dict[int, int] = defaultdict(int)
    impressions: dict[int, int] = defaultdict(int)
    for position, c, i in rows:
        bucket = min(max(round(position), 1), len(DEFAULT_CURVE))
        clicks[bucket] += c
        impressions[bucket] += i
    curve = list(DEFAULT_CURVE)
    fitted = 0
    for bucket in range(1, len(DEFAULT_CURVE) + 1):
        if impressions[bucket] >= MIN_IMPRESSIONS_PER_BUCKET:
            curve[bucket - 1] = clicks[bucket] / impressions[bucket]
            fitted += 1
    # Keep it monotonic (noise can invert neighbours); never exceed the previous bucket.
    for i in range(1, len(curve)):
        curve[i] = min(curve[i], curve[i - 1])
    return curve, fitted >= 3  # noqa: PLR2004


def share_of_voice(
    positions: Iterable[tuple[float | None, int | None]], curve: list[float] | None = None
) -> float:
    """Estimated share of clicks captured across keywords.

    ``sum(ctr(position) * volume) / sum(ctr(1) * volume)``.

    Keywords without known volume weigh 1 (and the UI says volumes were unavailable).
    """
    captured = possible = 0.0
    top = expected_ctr(1, curve)
    for position, volume in positions:
        weight = float(volume) if volume else 1.0
        possible += weight * top
        if position is not None:
            captured += weight * expected_ctr(position, curve)
    return round(captured / possible, 4) if possible else 0.0
