"""Tests for config flow and options flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.custom_lts_storage.config_flow import (
    CustomLTSStorageConfigFlow,
    CustomLTSStorageOptionsFlow,
)
from custom_components.custom_lts_storage.const import DOMAIN
from types import MappingProxyType

from homeassistant.config_entries import ConfigEntry


class MockConfigFlow(CustomLTSStorageConfigFlow):
    """Mock config flow that bypasses unique ID check."""

    def _abort_if_unique_id_configured(self, updates=None):
        pass

    async def async_set_unique_id(self, unique_id, *, raise_on_progress=True):
        pass


@pytest.mark.asyncio
async def test_config_flow_step_user() -> None:
    """Test config flow with valid sensor entity input."""
    flow = MockConfigFlow()
    flow.hass = MagicMock()

    result = await flow.async_step_user(
        {
            "sensor_entity": "sensor.test_energy",
            "interval": 15,
            "metrics": ["sum", "mean"],
            "track_state_changes": False,
        }
    )

    assert result["type"] == "create_entry"
    assert result["title"] == "sensor.test_energy"


@pytest.mark.asyncio
async def test_config_flow_show_form() -> None:
    """Test that the config flow shows the form when no input provided."""
    flow = MockConfigFlow()
    flow.hass = MagicMock()

    result = await flow.async_step_user(None)

    assert result["type"] == "form"
    assert result["step_id"] == "user"


@pytest.mark.asyncio
async def test_config_flow_invalid_entity() -> None:
    """Test that non-sensor entities produce a validation error."""
    flow = MockConfigFlow()
    flow.hass = MagicMock()

    result = await flow.async_step_user(
        {
            "sensor_entity": "light.test_light",
            "interval": 15,
            "metrics": ["sum"],
        }
    )

    assert result["type"] == "form"
    assert "sensor_entity" in result["errors"]


@pytest.mark.asyncio
async def test_config_flow_no_metrics() -> None:
    """Test that empty metrics selection produces a validation error."""
    flow = MockConfigFlow()
    flow.hass = MagicMock()

    result = await flow.async_step_user(
        {
            "sensor_entity": "sensor.test_energy",
            "interval": 15,
            "metrics": [],
        }
    )

    assert result["type"] == "form"
    assert "metrics" in result["errors"]


@pytest.mark.asyncio
async def test_options_flow_show_form() -> None:
    """Test that options flow shows the form with current settings."""
    entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="sensor.test_energy",
        data={
            "sensor_entity": "sensor.test_energy",
            "interval": 15,
            "metrics": ["sum", "mean"],
            "track_state_changes": False,
        },
        source="user",
        entry_id="test_entry_id",
        minor_version=0,
        options={},
        unique_id="sensor.test_energy",
        discovery_keys=MappingProxyType({}),
        subentries_data=None,
    )

    flow = CustomLTSStorageOptionsFlow(entry)
    flow.hass = MagicMock()

    result = await flow.async_step_init(None)

    assert result["type"] == "form"
    assert result["step_id"] == "init"