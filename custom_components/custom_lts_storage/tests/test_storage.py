"""Tests for the Custom LTS Storage binary file storage."""

from pathlib import Path
from typing import Any

import pytest

from custom_components.custom_lts_storage.storage import BinaryStatsStore


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> str:
    return str(tmp_path / "custom_lts_storage" / "data")


def test_write_and_read_rows(tmp_data_dir: str) -> None:
    """Test binary round-trip: write rows, read back, verify timestamps and values."""
    store = BinaryStatsStore(tmp_data_dir)
    entity_id = "sensor.test_sensor"
    year = 2025

    store.write_row(entity_id, year, 1000.0, 42.5)
    store.write_row(entity_id, year, 2000.0, 43.0)

    rows = store.read_rows(entity_id, year)
    assert len(rows) == 2
    assert rows[0] == (1000.0, 42.5)
    assert rows[1] == (2000.0, 43.0)


def test_get_last_timestamp(tmp_data_dir: str) -> None:
    """Test that get_last_timestamp returns the last written timestamp."""
    store = BinaryStatsStore(tmp_data_dir)
    entity_id = "sensor.test_sensor"
    year = 2025

    store.write_row(entity_id, year, 1000.0, 42.5)
    store.write_row(entity_id, year, 2000.0, 43.0)

    last_ts = store.get_last_timestamp(entity_id, year)
    assert last_ts == 2000.0


def test_empty_file_no_timestamp(tmp_data_dir: str) -> None:
    """Test that missing file returns None for last timestamp."""
    store = BinaryStatsStore(tmp_data_dir)
    entity_id = "sensor.test_sensor"
    year = 2025

    assert store.read_rows(entity_id, year) == []
    assert store.get_last_timestamp(entity_id, year) is None


def test_last_run_persistence(tmp_data_dir: str) -> None:
    """Test that last_run JSON is persisted and read correctly."""
    store = BinaryStatsStore(tmp_data_dir)
    entity_id = "sensor.test_sensor"

    store.write_last_run(entity_id, 3000.0)
    assert store.read_last_run(entity_id) == 3000.0

    store.write_last_run(entity_id, 4000.0)
    assert store.read_last_run(entity_id) == 4000.0


def test_corrupted_last_run(tmp_data_dir: str) -> None:
    """Test that corrupted last_run.json returns None."""
    store = BinaryStatsStore(tmp_data_dir)
    entity_id = "sensor.test_sensor"

    path = store._last_run_file(entity_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not valid json")

    assert store.read_last_run(entity_id) is None