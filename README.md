# Custom LTS Storage

A HACS custom integration that replaces the Home Assistant LTS (long-term statistics) pipeline for specific sensors by:

1. Reading 5-minute short-term statistics from the recorder's `statistics_short_term` table
2. Reducing them to configurable intervals (default 15 min)
3. Storing the reduced statistics in per-year binary files (`timestamp + value`)
4. Tracking raw state changes for mode/select sensors (e.g., heatpump status) in separate files
5. Exposing stored data via media_source for HA-UI browsing/download

## Installation

Install via [HACS](https://hacs.xyz/) by adding this repository as a custom integration.

## Configuration

1. Go to **Settings** → **Devices & Services** → **+ Add Integration** → **Custom LTS Storage**
2. Select sensor type: "Statistics sensor" or "State-change sensor"
3. For statistics: pick entity_id (dropdown, filtered to `sensor.*`), set interval (default 15 min), choose metrics (sum/mean/max/min/state checkboxes)
4. For state-change: pick entity_id (dropdown)
5. Done → creates config entry

## Services

### `custom_lts_storage.download_statistics`

Downloads a specific year file for a sensor.

| Field | Type | Required | Description |
|---|---|---|---|
| `sensor_entity` | text | ✅ | Entity ID of the sensor |
| `year` | integer | ✅ | Year to download (e.g., 2025) |
| `metric` | select | ❌ | Which metric file to download (sum, mean, max, min, state). None for mode sensor. |

### `custom_lts_storage.download_current_year`

Downloads the current year's active file.

| Field | Type | Required | Description |
|---|---|---|---|
| `sensor_entity` | text | ✅ | Entity ID of the sensor |
| `metric` | select | ❌ | Which metric file to download (sum, mean, max, min, state). None for mode sensor. |

## File Format

```
config/custom_lts_storage/data/
  sensor.energy_consumption/
    2025.bin             # statistics: float64 ts + float64 value (16B/row)
    2026.bin             # current year, active append
    _last_run.json       # { "last_run": 1700000000.0 }
  sensor.heatpump_mode/
    2025.bin             # timestamp + uint16 state_index (10B/row)
    2025_states.txt      # deduplicated enum: "cooling\nheating\nidle"
    2026.bin
    2026_states.txt
    _last_state_change.json  # { "last_change_ts": ..., "known_states": [...] }
```

- **Statistics**: 8-byte float64 Unix timestamp + 8-byte float64 value = 16 bytes/row
- **Mode sensor**: 8-byte float64 Unix timestamp + 2-byte uint16 state_index = 10 bytes/row
- All values big-endian (network byte order) for portability

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Home Assistant Recorder                                    │
│  ┌─────────────────────┐  ┌──────────────────────┐         │
│  │ statistics_short_term│  │ statistics (hourly)  │         │
│  │ (5-min data)        │  │ (1h LTS)            │         │
│  └─────────────────────┘  └──────────────────────┘         │
│          ▲ read 5min                                      │
└──────────┼────────────────────────────────────────────────┘
           │
           │ statistics_during_period(period="5minute")
           │
┌──────────┼────────────────────────────────────────────────┐
│  custom_lts_storage (daily batch job)                   │
│                                                         │
│  1. Read 5-min stats for target sensors                  │
│     (last_run → now, max 10 days)                       │
│  2. Reduce to configured interval (e.g. 15 min)        │
│  3. Deduplicate: skip rows already stored              │
│  4. Write to per-year binary files                      │
│  5. Update last_run timestamp                           │
│                                                         │
│  State-change listener (separate)                         │
│  ┌──────────────────────────────────────┐                │
│  │ state_changed event → log to file   │                │
│  │ Append new states to states.txt     │                │
│  │ Write timestamp+index to .bin       │                │
│  └──────────────────────────────────────┘                │
│                                                         │
│  Media source (download)                                 │
│  ┌──────────────────────────────────────┐                │
│  │ Browse per-sensor, per-year files   │                │
│  │ Download full year or current year │                │
│  └──────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────┘
```

## License

MIT