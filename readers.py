"""Data readers for reading short-term statistics from the recorder."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from homeassistant.components.recorder.statistics import (
    statistics_during_period,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

MAX_SHORT_TERM_RETENTION_DAYS = 10


class DailyBatchReader:
    """Reads 5-minute short-term statistics from the recorder for batch processing."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    def read_5min_stats(
        self,
        entity_id: str,
        start_time: datetime,
        end_time: datetime | None,
    ) -> dict[str, list]:
        """Read 5-minute statistics for a given entity_id and time range.

        Returns a dict keyed by metric type (sum, mean, max, min, state)
        with lists of (start_ts, value) tuples.
        """
        result: dict[str, list[tuple[float, float]]] = {}

        try:
            stats = statistics_during_period(
                self._hass,
                start_time,
                end_time,
                {entity_id},
                "5minute",
                units=None,
                types={"sum", "mean", "max", "min", "state"},
            )
        except Exception:
            _LOGGER.warning("Failed to read stats for %s", entity_id)
            return result

        rows = stats.get(entity_id, [])
        for row in rows:
            start_ts = float(row["start"])
            for key in ("sum", "mean", "max", "min", "state"):
                value = row.get(key)
                if value is not None:
                    result.setdefault(key, []).append((start_ts, float(value)))

        return result