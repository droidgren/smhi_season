"""Config flow for SMHI Meteorological Season integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DOMAIN, 
    CONF_TEMPERATURE_SENSOR,
    CONF_HISTORY_SPRING,
    CONF_HISTORY_SUMMER,
    CONF_HISTORY_AUTUMN,
    CONF_HISTORY_WINTER
)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SMHI Season."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(
                title="Meteorologisk Årstid", data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=self._get_schema(),
        )

    def _get_schema(self, defaults=None):
        """Reusable schema for setup and options."""
        if defaults is None:
            defaults = {}

        return vol.Schema(
            {
                vol.Required(CONF_TEMPERATURE_SENSOR, default=defaults.get(CONF_TEMPERATURE_SENSOR)): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
                ),
                vol.Optional(CONF_HISTORY_SPRING, default=defaults.get(CONF_HISTORY_SPRING)): selector.DateSelector(),
                vol.Optional(CONF_HISTORY_SUMMER, default=defaults.get(CONF_HISTORY_SUMMER)): selector.DateSelector(),
                vol.Optional(CONF_HISTORY_AUTUMN, default=defaults.get(CONF_HISTORY_AUTUMN)): selector.DateSelector(),
                vol.Optional(CONF_HISTORY_WINTER, default=defaults.get(CONF_HISTORY_WINTER)): selector.DateSelector(),
            }
        )

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for SMHI Season."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Merge data and options to show current values as defaults
        current_config = {**self.config_entry.data, **self.config_entry.options}
        
        return self.async_show_form(
            step_id="init",
            data_schema=ConfigFlow._get_schema(None, current_config), # Use static method trick or redefine
        )

# Little helper to access schema from OptionsFlow 
# (Since _get_schema was defined on ConfigFlow instance, we make it standalone or duplicate logic)
# To keep it simple in this pasted code, I'll redefine the schema builder inside OptionsFlow or make ConfigFlow's static.
# I updated ConfigFlow._get_schema to be cleaner below:

    def _get_schema(self, defaults=None):
        """Duplicate schema builder for OptionsFlow to avoid class binding issues."""
        if defaults is None:
            defaults = {}
            
        return vol.Schema(
            {
                vol.Required(CONF_TEMPERATURE_SENSOR, default=defaults.get(CONF_TEMPERATURE_SENSOR)): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
                ),
                vol.Optional(CONF_HISTORY_SPRING, default=defaults.get(CONF_HISTORY_SPRING)): selector.DateSelector(),
                vol.Optional(CONF_HISTORY_SUMMER, default=defaults.get(CONF_HISTORY_SUMMER)): selector.DateSelector(),
                vol.Optional(CONF_HISTORY_AUTUMN, default=defaults.get(CONF_HISTORY_AUTUMN)): selector.DateSelector(),
                vol.Optional(CONF_HISTORY_WINTER, default=defaults.get(CONF_HISTORY_WINTER)): selector.DateSelector(),
            }
        )