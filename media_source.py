"""Media source for browsing and downloading stored statistics files."""

from __future__ import annotations

import csv
import io
import logging
import os
import struct
from pathlib import Path

from homeassistant.components.media_player import BrowseMedia, MediaClass, MediaType
from homeassistant.components.media_source.error import Unresolvable
from homeassistant.components.media_source.models import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
)
from homeassistant.core import HomeAssistant, callback

from .models import SensorEntry
from .storage import BinaryStatsStore, STATS_ROW_SIZE, FLOAT64_SIZE, TIMESTAMP_PACK, VALUE_PACK
from .state_change_store import StateChangeStore

_LOGGER = logging.getLogger(__name__)

MEDIA_SOURCE_DATA_KEY = "media_source"

URI_SCHEME = "media-source://"


class CustomLTSMediaSource(MediaSource):
    """Media source for custom LTS storage files."""

    name = "Custom LTS Storage"

    def __init__(
        self,
        hass: HomeAssistant,
        stats_store: BinaryStatsStore,
        state_store: StateChangeStore,
        sensors: list[SensorEntry],
    ) -> None:
        super().__init__("custom_lts_storage")
        self._hass = hass
        self._stats_store = stats_store
        self._state_store = state_store
        self._sensors = sensors

    async def async_register(self) -> None:
        """Register this media source with the media_source integration."""
        from homeassistant.components.media_source.const import MEDIA_SOURCE_DATA

        self._hass.data.setdefault(MEDIA_SOURCE_DATA, {})
        self._hass.data[MEDIA_SOURCE_DATA][self.domain] = self

    async def async_unregister(self) -> None:
        """Unregister this media source."""
        from homeassistant.components.media_source.const import MEDIA_SOURCE_DATA

        self._hass.data[MEDIA_SOURCE_DATA].pop(self.domain, None)

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        """Browse media items.

        Hierarchy: root → sensor list → year list → files
        """
        identifier = item.identifier

        if not identifier:
            return self._browse_root()

        parts = identifier.split("/")
        if len(parts) == 1:
            entity_id = parts[0]
            return self._browse_sensor_years(entity_id)

        if len(parts) == 2:
            entity_id, year_str = parts
            return self._browse_year_files(entity_id, int(year_str))

        raise Unresolvable("Unknown path format")

    def _browse_root(self) -> BrowseMediaSource:
        """Browse root: list all configured sensors."""
        children = []
        for sensor in self._sensors:
            children.append(
                BrowseMediaSource(
                    domain=self.domain,
                    identifier=sensor.entity_id,
                    media_class=MediaClass.DIRECTORY,
                    media_content_type=MediaType.APPS,
                    title=sensor.entity_id,
                    can_play=False,
                    can_expand=True,
                )
            )
        return BrowseMediaSource(
            domain=self.domain,
            identifier=None,
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.APPS,
            title="Custom LTS Storage",
            can_play=False,
            can_expand=True,
            children=children,
        )

    def _browse_sensor_years(self, entity_id: str) -> BrowseMediaSource:
        """Browse a sensor: list available years."""
        safe_name = entity_id.replace(".", "_")
        data_dir = self._stats_store.base_dir / safe_name
        if not data_dir.exists():
            return BrowseMediaSource(
                domain=self.domain,
                identifier=entity_id,
                media_class=MediaClass.DIRECTORY,
                media_content_type=MediaType.APPS,
                title=entity_id,
                can_play=False,
                can_expand=True,
            )

        years: set[int] = set()
        for fname in os.listdir(data_dir):
            if fname.endswith(".bin"):
                try:
                    year = int(fname.replace(".bin", ""))
                    years.add(year)
                except ValueError:
                    continue

        children = []
        for year in sorted(years):
            children.append(
                BrowseMediaSource(
                    domain=self.domain,
                    identifier=f"{entity_id}/{year}",
                    media_class=MediaClass.DIRECTORY,
                    media_content_type=MediaType.MEDIA,
                    title=f"{year}",
                    can_play=False,
                    can_expand=True,
                )
            )
        return BrowseMediaSource(
            domain=self.domain,
            identifier=entity_id,
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.APPS,
            title=entity_id,
            can_play=False,
            can_expand=True,
            children=children,
        )

    def _browse_year_files(self, entity_id: str, year: int) -> BrowseMediaSource:
        """Browse a year: list available binary files and CSV downloads."""
        safe_name = entity_id.replace(".", "_")
        path = self._stats_store.base_dir / safe_name / f"{year}.bin"
        states_path = self._state_store.base_dir / safe_name / f"{year}_states.txt"

        children = []

        if path.exists():
            children.append(
                BrowseMediaSource(
                    domain=self.domain,
                    identifier=f"{entity_id}/{year}/binary",
                    media_class=MediaClass.FILE,
                    media_content_type="application/octet-stream",
                    title=f"{year} - raw binary",
                    can_play=True,
                    can_expand=False,
                )
            )
            children.append(
                BrowseMediaSource(
                    domain=self.domain,
                    identifier=f"{entity_id}/{year}/csv",
                    media_class=MediaClass.FILE,
                    media_content_type="text/csv",
                    title=f"{year} - CSV",
                    can_play=True,
                    can_expand=False,
                )
            )

        if states_path.exists():
            children.append(
                BrowseMediaSource(
                    domain=self.domain,
                    identifier=f"{entity_id}/{year}/states",
                    media_class=MediaClass.FILE,
                    media_content_type="text/plain",
                    title=f"{year} - states",
                    can_play=True,
                    can_expand=False,
                )
            )

        return BrowseMediaSource(
            domain=self.domain,
            identifier=f"{entity_id}/{year}",
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.APPS,
            title=f"{year}",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve a media item to a playable file.

        Handles: {entity_id}/{year}/binary → raw .bin, {entity_id}/{year}/csv → CSV on-the-fly,
        {entity_id}/{year}/states → states.txt.
        """
        identifier = item.identifier
        if not identifier:
            raise Unresolvable("No identifier provided")

        parts = identifier.split("/")
        if len(parts) < 3:
            raise Unresolvable("Invalid identifier format")

        entity_id = parts[0]
        year_str = parts[1]
        fmt = parts[2]
        year = int(year_str)

        configured = {s.entity_id for s in self._sensors}
        if entity_id not in configured:
            raise Unresolvable(f"Sensor {entity_id} is not configured")

        safe_name = entity_id.replace(".", "_")

        if fmt == "states":
            path = self._state_store.base_dir / safe_name / f"{year}_states.txt"
            if not path.exists():
                raise Unresolvable(f"File not found: {path}")
            return PlayMedia(url=str(path), mime_type="text/plain")

        if fmt == "csv":
            bin_path = self._stats_store.base_dir / safe_name / f"{year}.bin"
            if not bin_path.exists():
                raise Unresolvable(f"File not found: {bin_path}")
            csv_data = self._convert_binary_to_csv(bin_path)
            tmp_path = self._stats_store.base_dir / safe_name / f"{year}_temp.csv"
            tmp_path.write_text(csv_data)
            return PlayMedia(url=str(tmp_path), mime_type="text/csv")

        if fmt == "binary":
            path = self._stats_store.base_dir / safe_name / f"{year}.bin"
            if not path.exists():
                raise Unresolvable(f"File not found: {path}")
            return PlayMedia(url=str(path), mime_type="application/octet-stream")

        raise Unresolvable(f"Unknown format: {fmt}")

    def _convert_binary_to_csv(self, bin_path: Path) -> str:
        """Convert a binary .bin file to CSV with timestamp,value columns."""
        if not bin_path.exists():
            return ""

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["timestamp", "value"])

        with open(bin_path, "rb") as f:
            while True:
                chunk = f.read(STATS_ROW_SIZE)
                if len(chunk) < STATS_ROW_SIZE:
                    break
                ts = struct.unpack(TIMESTAMP_PACK, chunk[:FLOAT64_SIZE])[0]
                val = struct.unpack(VALUE_PACK, chunk[FLOAT64_SIZE:])[0]
                writer.writerow([ts, val])

        return output.getvalue()