"""Data reduction from 5-minute intervals to configurable intervals."""

from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)


def _bucket_boundary(timestamp: float, interval_minutes: int) -> float:
    """Compute the bucket start timestamp for the given interval."""
    interval_seconds = interval_minutes * 60
    return (int(timestamp) // interval_seconds) * interval_seconds


def reduce_to_interval(
    rows: list[tuple[float, float]],
    interval_minutes: int,
    metric: str,
) -> list[tuple[float, float]]:
    """Reduce 5-minute raw data rows to the configured interval.

    - For sum/state/change: takes the last value within each bucket
    - For mean/max/min: takes the appropriate aggregate of all 5-min values in the bucket

    Returns list of (bucket_start_ts, reduced_value) tuples.
    """
    if not rows:
        return []

    buckets: dict[float, list[float]] = {}

    for start_ts, value in rows:
        bucket = _bucket_boundary(start_ts, interval_minutes)
        buckets.setdefault(bucket, []).append(value)

    result: list[tuple[float, float]] = []
    for bucket_start in sorted(buckets):
        values = buckets[bucket_start]
        if metric in ("sum", "state", "change"):
            reduced = values[-1]
        elif metric == "mean":
            reduced = sum(values) / len(values)
        elif metric == "max":
            reduced = max(values)
        elif metric == "min":
            reduced = min(values)
        else:
            reduced = values[-1]
        result.append((float(bucket_start), reduced))

    return result