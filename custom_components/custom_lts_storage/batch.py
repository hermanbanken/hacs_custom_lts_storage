"""Daily batch task for reading and storing statistics."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from homeassistant.core import HomeAssistant
from homeassistant.components.recorder import get_instance

from .models import SensorEntry
from .readers import DailyBatchReader
from .reducers import reduce_to_interval
from .storage import BinaryStatsStore

_LOGGER = logging.getLogger(__name__)


async def run_daily_batch(
    hass: HomeAssistant,
    sensors: list[SensorEntry],
    stats_store: BinaryStatsStore,
) -> None:
    """Run the daily batch: read 5-min stats, reduce, deduplicate, store."""
    reader = DailyBatchReader(hass)
    now = datetime.now(timezone.utc)
    now_ts = now.timestamp()

    keep_days = get_instance(hass).keep_days

    for entry in sensors:
        entity_id = entry.entity_id
        last_run = stats_store.read_last_run(entity_id)

        if last_run is None:
            start_time = now - timedelta(days=keep_days)
        else:
            start_time = datetime.fromtimestamp(last_run, tz=timezone.utc)

        end_time = now

        try:
            all_metrics = reader.read_5min_stats(entity_id, start_time, end_time)
        except Exception:
            _LOGGER.warning(
                "Failed to read statistics for %s, will retry next run", entity_id
            )
            continue

        current_year = now.year

        for metric, rows in all_metrics.items():
            if not rows:
                continue
            if metric not in entry.metrics:
                continue

            reduced = reduce_to_interval(rows, entry.interval, metric)

            last_stored_ts = stats_store.get_last_timestamp(entity_id, current_year)

            new_rows = [
                (bucket_ts, value)
                for bucket_ts, value in reduced
                if last_stored_ts is None or bucket_ts > last_stored_ts
            ]

            if new_rows:
                try:
                    stats_store.write_rows_batch(entity_id, current_year, new_rows)
                except OSError as exc:
                    _LOGGER.error(
                        "Failed to write rows for %s/%s year=%s: %s",
                        entity_id,
                        metric,
                        current_year,
                        exc,
                    )

        stats_store.write_last_run(entity_id, now_ts)
        _LOGGER.info("Batch completed for %s", entity_id)