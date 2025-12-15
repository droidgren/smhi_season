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
    
    def __init__(self):
        """Initialize the config flow."""
        self._config_data = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step (Sensor Selection)."""
        errors = {}

        if user_input is not None:
            # Store the sensor selection and move to next step
            self._config_data.update(user_input)
            return await self.async_step_history()

        # Schema for Step 1: Just the sensor
        schema = vol.Schema({
            vol.Required(CONF_TEMPERATURE_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
            )
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_history(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the second step (History Dates)."""
        errors = {}

        if user_input is not None:
            # Normalize empty strings
            self._normalize_dates(user_input)
            
            # Validate
            if self._validate_dates(user_input, errors):
                # Merge with previous step data
                final_data = {**self._config_data, **user_input}
                return self.async_create_entry(
                    title="Meteorologisk Årstid", data=final_data
                )

        # Schema for Step 2: Dates (All optional)
        schema = vol.Schema({
            vol.Optional(CONF_HISTORY_SPRING): selector.DateSelector(),
            vol.Optional(CONF_HISTORY_SUMMER): selector.DateSelector(),
            vol.Optional(CONF_HISTORY_AUTUMN): selector.DateSelector(),
            vol.Optional(CONF_HISTORY_WINTER): selector.DateSelector(),
        })

        return self.async_show_form(
            step_id="history",
            data_schema=schema,
            errors=errors,
        )

    def _normalize_dates(self, user_input):
        """Convert empty strings to None."""
        date_keys = [CONF_HISTORY_SPRING, CONF_HISTORY_SUMMER, CONF_HISTORY_AUTUMN, CONF_HISTORY_WINTER]
        for key in date_keys:
            if key in user_input and user_input[key] == "":
                user_input[key] = None

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


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for SMHI Season with Menu."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["sensor_settings", "history_settings"]
        )

    async def async_step_sensor_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle sensor settings sub-dialog."""
        errors = {}
        
        if user_input is not None:
            # Get current options to preserve other settings
            current_options = dict(self.config_entry.options)
            current_options.update(user_input)
            
            return self.async_create_entry(title="", data=current_options)

        # Default: Current sensor
        current_sensor = self.config_entry.options.get(
            CONF_TEMPERATURE_SENSOR, 
            self.config_entry.data.get(CONF_TEMPERATURE_SENSOR)
        )

        schema = vol.Schema({
            vol.Required(CONF_TEMPERATURE_SENSOR, default=current_sensor): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
            )
        })

        return self.async_show_form(
            step_id="sensor_settings",
            data_schema=schema,
            errors=errors
        )

    async def async_step_history_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle history settings sub-dialog."""
        errors = {}
        
        if user_input is not None:
            # Handle Resets
            if user_input.get("reset_spring"): user_input[CONF_HISTORY_SPRING] = None
            if user_input.get("reset_summer"): user_input[CONF_HISTORY_SUMMER] = None
            if user_input.get("reset_autumn"): user_input[CONF_HISTORY_AUTUMN] = None
            if user_input.get("reset_winter"): user_input[CONF_HISTORY_WINTER] = None
            
            # Clean up reset keys
            for key in ["reset_spring", "reset_summer", "reset_autumn", "reset_winter"]:
                user_input.pop(key, None)

            # Normalize empty strings
            self._normalize_dates(user_input)

            if self._validate_dates(user_input, errors):
                # Update options
                current_options = dict(self.config_entry.options)
                current_options.update(user_input)
                return self.async_create_entry(title="", data=current_options)

        # Load defaults
        defaults = {**self.config_entry.data, **self.config_entry.options}

        schema = vol.Schema({
            vol.Optional(CONF_HISTORY_SPRING, default=defaults.get(CONF_HISTORY_SPRING)): selector.DateSelector(),
            vol.Optional("reset_spring", default=False): bool,
            
            vol.Optional(CONF_HISTORY_SUMMER, default=defaults.get(CONF_HISTORY_SUMMER)): selector.DateSelector(),
            vol.Optional("reset_summer", default=False): bool,
            
            vol.Optional(CONF_HISTORY_AUTUMN, default=defaults.get(CONF_HISTORY_AUTUMN)): selector.DateSelector(),
            vol.Optional("reset_autumn", default=False): bool,
            
            vol.Optional(CONF_HISTORY_WINTER, default=defaults.get(CONF_HISTORY_WINTER)): selector.DateSelector(),
            vol.Optional("reset_winter", default=False): bool,
        })

        return self.async_show_form(
            step_id="history_settings",
            data_schema=schema,
            errors=errors
        )

    def _normalize_dates(self, user_input):
        """Convert empty strings to None."""
        date_keys = [CONF_HISTORY_SPRING, CONF_HISTORY_SUMMER, CONF_HISTORY_AUTUMN, CONF_HISTORY_WINTER]
        for key in date_keys:
            if key in user_input and user_input[key] == "":
                user_input[key] = None

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