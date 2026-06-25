"""State-change event listener for mode/select sensors."""

from __future__ import annotations

import logging
import time

from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from .state_change_store import StateChangeStore

_LOGGER = logging.getLogger(__name__)


class StateChangeTracker:
    """Listens to state_changed events and records changes to binary + enum files."""

    def __init__(
        self,
        hass: HomeAssistant,
        entity_id: str,
        store: StateChangeStore,
    ) -> None:
        self._hass = hass
        self._entity_id = entity_id
        self._store = store
        self._cancel_listener: callable | None = None

    def start(self) -> None:
        """Register the state_changed event listener."""
        self._cancel_listener = async_track_state_change_event(
            self._hass,
            [self._entity_id],
            self._on_state_change,
        )

    def stop(self) -> None:
        """Unregister the listener."""
        if self._cancel_listener:
            self._cancel_listener()
            self._cancel_listener = None

    @callback
    def _on_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Handle a state_changed event."""
        new_state = event.data.get("new_state")
        if new_state is None or new_state.state is None:
            return

        state_value = new_state.state
        now = time.time()

        self._store.record_state_change(
            self._entity_id, now, state_value
        )