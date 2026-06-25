"""Entity model for the Custom LTS Storage integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass(slots=True)
class SensorEntry:
    """Configuration for a single sensor's storage."""

    entity_id: str
    interval: int
    metrics: set[str] = field(default_factory=set)
    track_state_changes: bool = False