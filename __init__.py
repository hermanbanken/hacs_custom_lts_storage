"""The Custom LTS Storage integration."""

from __future__ import annotations

import logging
from datetime import timedelta, datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

from .batch import run_daily_batch
from .const import DOMAIN
from .media_source import CustomLTSMediaSource
from .models import SensorEntry
from .services import async_register_services
from .storage import BinaryStatsStore
from .state_change_store import StateChangeStore
from .state_tracker import StateChangeTracker

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data_dir = hass.config.path("custom_lts_storage/data")

    stats_store = BinaryStatsStore(data_dir)
    state_store = StateChangeStore(data_dir)

    entry_data = entry.data
    sensors: list[SensorEntry] = []
    trackers: list[StateChangeTracker] = []

    sensor_entity = entry_data.get("sensor_entity")
    if sensor_entity:
        interval = entry_data.get("interval", 15)
        metrics = set(entry_data.get("metrics", []))
        track_state_changes = entry_data.get("track_state_changes", False)

        sensor_entry = SensorEntry(
            entity_id=sensor_entity,
            interval=interval,
            metrics=metrics,
            track_state_changes=track_state_changes,
        )
        sensors.append(sensor_entry)

        if track_state_changes:
            tracker = StateChangeTracker(hass, sensor_entity, state_store)
            tracker.start()
            trackers.append(tracker)

    media_source = CustomLTSMediaSource(hass, stats_store, state_store, sensors)
    await media_source.async_register()

    @callback
    def _run_daily_batch(now: datetime) -> None:
        hass.async_create_task(run_daily_batch(hass, sensors, stats_store))

    cancellation = async_track_time_interval(
        hass, _run_daily_batch, timedelta(hours=24)
    )

    async_register_services(hass, stats_store, state_store, sensors)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "sensors": sensors,
        "stats_store": stats_store,
        "state_store": state_store,
        "media_source": media_source,
        "trackers": trackers,
        "cancel_batch": cancellation,
        "cancel_services": lambda: (
            hass.services.async_remove(DOMAIN, "download_statistics"),
            hass.services.async_remove(DOMAIN, "download_current_year"),
        ),
    }

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = hass.data[DOMAIN].pop(entry.entry_id, {})

    if cancel := data.get("cancel_batch"):
        cancel()

    if cancel_services := data.get("cancel_services"):
        cancel_services()

    for tracker in data.get("trackers", []):
        tracker.stop()

    media_source = data.get("media_source")
    if media_source:
        await media_source.async_unregister()

    return True