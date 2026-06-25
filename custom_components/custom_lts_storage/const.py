"""Constants for the Custom LTS Storage integration."""

from typing import Literal

DOMAIN = "custom_lts_storage"

CONF_SENSOR_ENTITY = "sensor_entity"
CONF_INTERVAL = "interval"
CONF_METRICS = "metrics"
CONF_TRACK_STATE_CHANGES = "track_state_changes"

DEFAULT_INTERVAL = 15

METRIC_LITERALS = Literal["sum", "mean", "max", "min", "state"]
VALID_METRICS: set[str] = {"sum", "mean", "max", "min", "state"}

DATA_DIR = "custom_lts_storage/data"

INTERVAL_OPTIONS: list[int] = [5, 10, 15, 30, 60]