"""Tests for data reduction module."""

import pytest

from custom_components.custom_lts_storage.reducers import reduce_to_interval


def test_reduce_5min_to_15min_sum() -> None:
    """Test reduction from 5-min to 15-min for sum metric (last value per bucket)."""
    rows = [
        (0.0, 10.0),
        (300.0, 15.0),
        (600.0, 20.0),
        (900.0, 25.0),
        (1200.0, 30.0),
        (1500.0, 35.0),
        (1800.0, 40.0),
        (2100.0, 45.0),
        (2400.0, 50.0),
        (2700.0, 55.0),
        (3000.0, 60.0),
        (3300.0, 65.0),
    ]

    result = reduce_to_interval(rows, 15, "sum")
    assert len(result) == 4
    assert result[0] == (0.0, 20.0)
    assert result[1] == (900.0, 35.0)
    assert result[2] == (1800.0, 50.0)
    assert result[3] == (2700.0, 65.0)


def test_reduce_5min_to_15min_mean() -> None:
    """Test reduction for mean metric (average of values in bucket)."""
    rows = [
        (0.0, 10.0),
        (300.0, 20.0),
        (600.0, 30.0),
    ]

    result = reduce_to_interval(rows, 15, "mean")
    assert len(result) == 1
    assert result[0][0] == 0.0
    assert result[0][1] == 20.0


def test_reduce_5min_to_15min_max() -> None:
    """Test reduction for max metric (max of values in bucket)."""
    rows = [
        (0.0, 10.0),
        (300.0, 30.0),
        (600.0, 20.0),
    ]

    result = reduce_to_interval(rows, 15, "max")
    assert len(result) == 1
    assert result[0][0] == 0.0
    assert result[0][1] == 30.0


def test_reduce_5min_to_15min_min() -> None:
    """Test reduction for min metric (min of values in bucket)."""
    rows = [
        (0.0, 10.0),
        (300.0, 30.0),
        (600.0, 20.0),
    ]

    result = reduce_to_interval(rows, 15, "min")
    assert len(result) == 1
    assert result[0][0] == 0.0
    assert result[0][1] == 10.0


def test_empty_rows() -> None:
    """Test that empty input returns empty list."""
    assert reduce_to_interval([], 15, "sum") == []
    assert reduce_to_interval([], 15, "mean") == []


def test_reduce_to_different_intervals() -> None:
    """Test reduction to different interval sizes."""
    rows = [
        (0.0, 10.0),
        (300.0, 20.0),
        (600.0, 30.0),
        (900.0, 40.0),
        (1200.0, 50.0),
    ]

    result_10min = reduce_to_interval(rows, 10, "sum")
    assert len(result_10min) >= 1

    result_30min = reduce_to_interval(rows, 30, "sum")
    assert len(result_30min) >= 1