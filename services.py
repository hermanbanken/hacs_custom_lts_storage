"""Service implementations for download_statistics and download_current_year."""

from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone

import voluptuous as vol

from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .models import SensorEntry
from .storage import BinaryStatsStore
from .state_change_store import StateChangeStore

_LOGGER = logging.getLogger(__name__)

DOWNLOAD_STATISTICS_SCHEMA = vol.Schema(
    {
        vol.Required("sensor_entity"): str,
        vol.Required("year"): int,
        vol.Optional("metric"): str,
    }
)

DOWNLOAD_CURRENT_YEAR_SCHEMA = vol.Schema(
    {
        vol.Required("sensor_entity"): str,
        vol.Optional("metric"): str,
    }
)


def async_register_services(
    hass: HomeAssistant,
    stats_store: BinaryStatsStore,
    state_store: StateChangeStore,
    sensors: list[SensorEntry],
) -> None:
    """Register download services."""

    async def handle_download_statistics(call: dict) -> None:
        sensor_entity: str = call.data["sensor_entity"]
        year: int = call.data["year"]
        metric: str | None = call.data.get("metric")

        configured_entities = {s.entity_id for s in sensors}
        if sensor_entity not in configured_entities:
            _LOGGER.warning(
                "Entity %s is not configured in custom_lts_storage", sensor_entity
            )
            return

        if metric == "states":
            entity_id = sensor_entity.replace(".", "_")
            path = state_store.base_dir / entity_id / f"{year}_states.txt"
            if path.exists():
                content = path.read_bytes()
                hass.bus.async_fire(
                    f"{DOMAIN}_file_ready",
                    {
                        "entity": sensor_entity,
                        "year": year,
                        "metric": metric,
                        "content": base64.b64encode(content).decode(),
                    },
                )
            else:
                _LOGGER.warning("File not found: %s", path)
            return

        entity_id = sensor_entity.replace(".", "_")
        path = stats_store.base_dir / entity_id / f"{year}.bin"
        if not path.exists():
            _LOGGER.warning("File not found: %s", path)
            return

        content = path.read_bytes()
        hass.bus.async_fire(
            f"{DOMAIN}_file_ready",
            {
                "entity": sensor_entity,
                "year": year,
                "metric": metric,
                "content": base64.b64encode(content).decode(),
            },
        )

    async def handle_download_current_year(call: dict) -> None:
        sensor_entity: str = call.data["sensor_entity"]
        metric: str | None = call.data.get("metric")
        year = datetime.now(timezone.utc).year

        await handle_download_statistics(
            {"data": {"sensor_entity": sensor_entity, "year": year, "metric": metric}}
        )

    hass.services.async_register(
        DOMAIN,
        "download_statistics",
        handle_download_statistics,
        schema=DOWNLOAD_STATISTICS_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        "download_current_year",
        handle_download_current_year,
        schema=DOWNLOAD_CURRENT_YEAR_SCHEMA,
    )