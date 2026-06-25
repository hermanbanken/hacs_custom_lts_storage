"""Test fixtures for custom_lts_storage tests."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from pathlib import Path

import pytest

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


@pytest.fixture(scope="package")
def event_loop() -> asyncio.AbstractEventLoop:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def hass(event_loop: asyncio.AbstractEventLoop) -> HomeAssistant:
    """Provide a mock HomeAssistant instance."""
    from homeassistant.core import HomeAssistant

    return HomeAssistant()


@pytest.fixture
def config_entry() -> ...: 
    """Provide a mock config entry."""
    from homeassistant.config_entries import ConfigEntry

    return ConfigEntry(
        version=1,
        domain="custom_lts_storage",
        title="sensor.test_energy",
        data={
            "sensor_entity": "sensor.test_energy",
            "interval": 15,
            "metrics": ["sum", "mean"],
            "track_state_changes": False,
        },
        source="user",
        entry_id="test_entry_id",
    )