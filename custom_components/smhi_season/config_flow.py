"""Config flow for SMHI Meteorological Season integration."""
from __future__ import annotations

from typing import Any
from datetime import date

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
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
        errors = {}

        if user_input is not None:
            # Normalize empty string dates to None for proper saving/resetting
            date_keys = [CONF_HISTORY_SPRING, CONF_HISTORY_SUMMER, CONF_HISTORY_AUTUMN, CONF_HISTORY_WINTER]
            for key in date_keys:
                if key in user_input and user_input[key] == "":
                    user_input[key] = None
                    
            # Validate dates are not in the future
            if not self._validate_dates(user_input, errors):
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._get_schema(user_input),
                    errors=errors,
                )

            return self.async_create_entry(
                title="Meteorologisk Årstid", data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=self._get_schema(),
            errors=errors,
        )

    def _validate_dates(self, user_input, errors):
        """Check if any provided date is in the future."""
        today = date.today()
        date_keys = [CONF_HISTORY_SPRING, CONF_HISTORY_SUMMER, CONF_HISTORY_AUTUMN, CONF_HISTORY_WINTER]
        
        for key in date_keys:
            if input_date_str := user_input.get(key):
                try:
                    input_date = date.fromisoformat(str(input_date_str))
                    if input_date > today:
                        errors["base"] = "cannot_be_future"
                        return False
                except ValueError:
                    pass
        return True

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
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors = {}
        
        if user_input is not None:
            # Normalize empty string dates to None for proper saving/resetting
            date_keys = [CONF_HISTORY_SPRING, CONF_HISTORY_SUMMER, CONF_HISTORY_AUTUMN, CONF_HISTORY_WINTER]
            for key in date_keys:
                if key in user_input and user_input[key] == "":
                    user_input[key] = None
                    
            # Validate dates are not in the future
            if not self._validate_dates(user_input, errors):
                schema = self._build_schema(user_input)
                return self.async_show_form(step_id="init", data_schema=schema, errors=errors)

            return self.async_create_entry(title="", data=user_input)

        # Default Schema Load
        current_config = {**self.config_entry.data, **self.config_entry.options}
        schema = self._build_schema(current_config)
        
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )

    def _validate_dates(self, user_input, errors):
        """Check if any provided date is in the future."""
        today = date.today()
        date_keys = [CONF_HISTORY_SPRING, CONF_HISTORY_SUMMER, CONF_HISTORY_AUTUMN, CONF_HISTORY_WINTER]
        
        for key in date_keys:
            if input_date_str := user_input.get(key):
                try:
                    input_date = date.fromisoformat(str(input_date_str))
                    if input_date > today:
                        errors["base"] = "cannot_be_future"
                        return False
                except ValueError:
                    pass
        return True

    def _build_schema(self, defaults):
        """Build schema with defaults."""
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