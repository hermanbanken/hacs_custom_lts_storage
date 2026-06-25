"""Daily batch task for reading and storing statistics."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from homeassistant.core import HomeAssistant

from .models import SensorEntry
from .readers import DailyBatchReader
from .reducers import reduce_to_interval
from .storage import BinaryStatsStore

_LOGGER = logging.getLogger(__name__)

MAX_SHORT_TERM_RETENTION_DAYS = 10


async def run_daily_batch(
    hass: HomeAssistant,
    sensors: list[SensorEntry],
    stats_store: BinaryStatsStore,
) -> None:
    """Run the daily batch: read 5-min stats, reduce, deduplicate, store."""
    reader = DailyBatchReader(hass)
    now = datetime.now(timezone.utc)
    now_ts = now.timestamp()

    for entry in sensors:
        entity_id = entry.entity_id
        last_run = stats_store.read_last_run(entity_id)

        if last_run is None:
            start_time = now - timedelta(days=MAX_SHORT_TERM_RETENTION_DAYS)
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
        total_written = 0

        for metric, rows in all_metrics.items():
            if not rows:
                continue
            if metric not in entry.metrics:
                continue

            reduced = reduce_to_interval(rows, entry.interval, metric)

            last_stored_ts = stats_store.get_last_timestamp(entity_id, current_year)

            for bucket_ts, value in reduced:
                if last_stored_ts is not None and bucket_ts <= last_stored_ts:
                    continue
                try:
                    stats_store.write_row(entity_id, current_year, bucket_ts, value)
                    total_written += 1
                except OSError as exc:
                    _LOGGER.error(
                        "Failed to write row for %s/%s year=%s: %s",
                        entity_id,
                        metric,
                        current_year,
                        exc,
                    )

        stats_store.write_last_run(entity_id, now_ts)
        _LOGGER.info(
            "Batch completed for %s: %d rows written",
            entity_id,
            total_written,
        )