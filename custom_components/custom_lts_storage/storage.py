"""Binary file storage layer for Custom LTS Storage."""

from __future__ import annotations

import json
import logging
import os
import struct
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

STATS_ROW_SIZE = 16
FLOAT64_SIZE = 8
TIMESTAMP_PACK = ">d"
VALUE_PACK = ">d"

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024

LAST_RUN_FILENAME = "_last_run.json"


class BinaryStatsStore:
    """Manages per-year binary files for sensor statistics."""

    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)

    def _sensor_dir(self, entity_id: str) -> Path:
        safe_name = entity_id.replace(".", "_")
        return self.base_dir / safe_name

    def _year_file(self, entity_id: str, year: int) -> Path:
        return self._sensor_dir(entity_id) / f"{year}.bin"

    def _last_run_file(self, entity_id: str) -> Path:
        return self._sensor_dir(entity_id) / LAST_RUN_FILENAME

    def ensure_year_file(self, entity_id: str, year: int) -> None:
        path = self._year_file(entity_id, year)
        self._sensor_dir(entity_id).mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.touch()

    def write_row(self, entity_id: str, year: int, timestamp: float, value: float) -> None:
        path = self._year_file(entity_id, year)
        self.ensure_year_file(entity_id, year)
        with open(path, "ab") as f:
            f.write(struct.pack(TIMESTAMP_PACK, timestamp))
            f.write(struct.pack(VALUE_PACK, value))

    def write_rows_batch(
        self, entity_id: str, year: int, rows: list[tuple[float, float]]
    ) -> None:
        path = self._year_file(entity_id, year)
        self.ensure_year_file(entity_id, year)
        with open(path, "ab") as f:
            for timestamp, value in rows:
                f.write(struct.pack(TIMESTAMP_PACK, timestamp))
                f.write(struct.pack(VALUE_PACK, value))

    def read_rows(self, entity_id: str, year: int) -> list[tuple[float, float]]:
        path = self._year_file(entity_id, year)
        if not path.exists():
            return []
        if path.stat().st_size > MAX_FILE_SIZE_BYTES:
            _LOGGER.error("File %s exceeds max size (%d bytes)", path, MAX_FILE_SIZE_BYTES)
            return []
        rows: list[tuple[float, float]] = []
        with open(path, "rb") as f:
            while True:
                chunk = f.read(STATS_ROW_SIZE)
                if len(chunk) < STATS_ROW_SIZE:
                    break
                ts = struct.unpack(TIMESTAMP_PACK, chunk[:FLOAT64_SIZE])[0]
                val = struct.unpack(VALUE_PACK, chunk[FLOAT64_SIZE:])[0]
                rows.append((ts, val))
        return rows

    def get_last_timestamp(self, entity_id: str, year: int) -> float | None:
        path = self._year_file(entity_id, year)
        if not path.exists() or path.stat().st_size < STATS_ROW_SIZE:
            return None
        file_size = path.stat().st_size
        last_offset = file_size - STATS_ROW_SIZE
        with open(path, "rb") as f:
            f.seek(last_offset)
            chunk = f.read(STATS_ROW_SIZE)
        if len(chunk) < STATS_ROW_SIZE:
            return None
        ts = struct.unpack(TIMESTAMP_PACK, chunk[:FLOAT64_SIZE])[0]
        return ts

    def read_last_run(self, entity_id: str) -> float | None:
        path = self._last_run_file(entity_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return data.get("last_run")
        except (json.JSONDecodeError, OSError):
            _LOGGER.warning("Corrupted _last_run.json for %s, resetting", entity_id)
            return None

    def write_last_run(self, entity_id: str, timestamp: float) -> None:
        path = self._last_run_file(entity_id)
        self._sensor_dir(entity_id).mkdir(parents=True, exist_ok=True)
        data = {"last_run": timestamp}
        path.write_text(json.dumps(data))