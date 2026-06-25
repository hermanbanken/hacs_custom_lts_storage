"""State-change file storage for mode/select sensors."""

from __future__ import annotations

import json
import logging
import struct
from datetime import datetime as dt, timezone
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

STATE_ROW_SIZE = 10
FLOAT64_SIZE = 8
UINT16_SIZE = 2
STATE_INDEX_PACK = ">H"

MAX_STATES_FILE_SIZE_BYTES = 1024 * 1024

LAST_STATE_CHANGE_FILENAME = "_last_state_change.json"


class StateChangeStore:
    """Stores state-change data as timestamp + index binary + states.txt enum."""

    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)

    def _sensor_dir(self, entity_id: str) -> Path:
        safe_name = entity_id.replace(".", "_")
        return self.base_dir / safe_name

    def _year_file(self, entity_id: str, year: int) -> Path:
        return self._sensor_dir(entity_id) / f"{year}.bin"

    def _states_file(self, entity_id: str, year: int) -> Path:
        return self._sensor_dir(entity_id) / f"{year}_states.txt"

    def _last_state_change_file(self, entity_id: str) -> Path:
        return self._sensor_dir(entity_id) / LAST_STATE_CHANGE_FILENAME

    def get_known_states(self, entity_id: str, year: int) -> list[str]:
        path = self._states_file(entity_id, year)
        if not path.exists():
            return []
        if path.stat().st_size > MAX_STATES_FILE_SIZE_BYTES:
            _LOGGER.error(
                "States file %s exceeds max size (%d bytes)", path, MAX_STATES_FILE_SIZE_BYTES
            )
            return []
        text = path.read_text()
        return text.strip().split("\n") if text.strip() else []

    def _ensure_state_file(self, entity_id: str, year: int) -> None:
        path = self._states_file(entity_id, year)
        self._sensor_dir(entity_id).mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.touch()

    def get_state_index(self, state_value: str, known_states: list[str]) -> int:
        if state_value not in known_states:
            known_states.append(state_value)
            return len(known_states) - 1
        return known_states.index(state_value)

    def _write_states_file(self, entity_id: str, year: int, known_states: list[str]) -> None:
        path = self._states_file(entity_id, year)
        self._ensure_state_file(entity_id, year)
        path.write_text("\n".join(known_states) + "\n")

    def ensure_year_file(self, entity_id: str, year: int) -> None:
        path = self._year_file(entity_id, year)
        self._sensor_dir(entity_id).mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.touch()

    def record_state_change(
        self, entity_id: str, timestamp: float, state_value: str
    ) -> None:
        year = dt.fromtimestamp(timestamp, tz=timezone.utc).year
        self.ensure_year_file(entity_id, year)

        known_states = self.get_known_states(entity_id, year)
        state_index = self.get_state_index(state_value, known_states)
        self._write_states_file(entity_id, year, known_states)

        path = self._year_file(entity_id, year)
        with open(path, "ab") as f:
            f.write(struct.pack(">d", timestamp))
            f.write(struct.pack(STATE_INDEX_PACK, state_index))

    def read_last_state_change(self, entity_id: str) -> dict[str, object] | None:
        path = self._last_state_change_file(entity_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            _LOGGER.warning(
                "Corrupted _last_state_change.json for %s, resetting", entity_id
            )
            return None

    def write_last_state_change(
        self, entity_id: str, timestamp: float, known_states: list[str]
    ) -> None:
        path = self._last_state_change_file(entity_id)
        self._sensor_dir(entity_id).mkdir(parents=True, exist_ok=True)
        data = {
            "last_change_ts": timestamp,
            "known_states": known_states,
        }
        path.write_text(json.dumps(data))