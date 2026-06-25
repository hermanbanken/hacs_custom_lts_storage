"""Config flow for the Custom LTS Storage integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from .const import (
    CONF_INTERVAL,
    CONF_METRICS,
    CONF_SENSOR_ENTITY,
    CONF_TRACK_STATE_CHANGES,
    DEFAULT_INTERVAL,
    DOMAIN,
    INTERVAL_OPTIONS,
    VALID_METRICS,
)

_LOGGER = logging.getLogger(__name__)

STATISTICS_SENSOR_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SENSOR_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Required(CONF_INTERVAL, default=DEFAULT_INTERVAL): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=5, max=60, step=1, mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Required(CONF_METRICS): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    {"value": m, "label": m}
                    for m in sorted(VALID_METRICS)
                ],
                multiple=True,
            )
        ),
        vol.Optional(CONF_TRACK_STATE_CHANGES, default=False): bool,
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SENSOR_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
    }
)


class CustomLTSStorageConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Custom LTS Storage."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            entity_id = user_input[CONF_SENSOR_ENTITY]
            if not entity_id.startswith("sensor."):
                errors[CONF_SENSOR_ENTITY] = "invalid_entity"

            if not user_input.get(CONF_METRICS):
                errors[CONF_METRICS] = "no_metrics"

            if not errors:
                await self.async_set_unique_id(entity_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=entity_id,
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STATISTICS_SENSOR_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Create the options flow."""
        return CustomLTSStorageOptionsFlow(config_entry)


class CustomLTSStorageOptionsFlow(OptionsFlow):
    """Handle options for Custom LTS Storage."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self._config_entry.data
        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_INTERVAL,
                    default=current.get(CONF_INTERVAL, DEFAULT_INTERVAL),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5, max=60, step=1, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Required(
                    CONF_METRICS,
                    default=current.get(CONF_METRICS, []),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": m, "label": m}
                            for m in sorted(VALID_METRICS)
                        ],
                        multiple=True,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )