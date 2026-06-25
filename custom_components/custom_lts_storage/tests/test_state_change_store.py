"""Tests for state-change storage."""

from pathlib import Path

import pytest

from custom_components.custom_lts_storage.state_change_store import StateChangeStore


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> str:
    return str(tmp_path / "custom_lts_storage" / "data")


def test_record_state_change(tmp_data_dir: str) -> None:
    """Test that state_changed events produce correct binary + enum files."""
    store = StateChangeStore(tmp_data_dir)
    entity_id = "sensor.test_mode"

    store.record_state_change(entity_id, 1700000000.0, "cooling")
    store.record_state_change(entity_id, 1700001000.0, "heating")
    store.record_state_change(entity_id, 1700002000.0, "cooling")

    known_states = store.get_known_states(entity_id, 2023)
    assert known_states == ["cooling", "heating"]


def test_deduplication_of_states(tmp_data_dir: str) -> None:
    """Test that states.txt deduplicates state values."""
    store = StateChangeStore(tmp_data_dir)
    entity_id = "sensor.test_mode"

    store.record_state_change(entity_id, 1700000000.0, "active")
    store.record_state_change(entity_id, 1700001000.0, "active")
    store.record_state_change(entity_id, 1700002000.0, "idle")

    known_states = store.get_known_states(entity_id, 2023)
    assert known_states == ["active", "idle"]


def test_state_index_lookup(tmp_data_dir: str) -> None:
    """Test that state index lookup returns correct index and appends new states."""
    store = StateChangeStore(tmp_data_dir)
    entity_id = "sensor.test_mode"
    year = 2025

    known = store.get_known_states(entity_id, year)
    index1 = store.get_state_index("running", known)
    assert index1 == 0
    assert known == ["running"]

    index2 = store.get_state_index("stopped", known)
    assert index2 == 1
    assert known == ["running", "stopped"]

    index3 = store.get_state_index("running", known)
    assert index3 == 0


def test_last_state_change_persistence(tmp_data_dir: str) -> None:
    """Test that last_state_change.json persists correctly."""
    store = StateChangeStore(tmp_data_dir)
    entity_id = "sensor.test_mode"

    store.write_last_state_change(entity_id, 1700000000.0, ["cooling", "heating"])

    data = store.read_last_state_change(entity_id)
    assert data is not None
    assert data["last_change_ts"] == 1700000000.0
    assert data["known_states"] == ["cooling", "heating"]