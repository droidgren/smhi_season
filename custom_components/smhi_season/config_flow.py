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
            self._config_data.update(user_input)
            return await self.async_step_history()

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
            self._normalize_dates(user_input)
            if self._validate_dates(user_input, errors):
                final_data = {**self._config_data, **user_input}
                return self.async_create_entry(
                    title="Meteorologisk Årstid", data=final_data
                )

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
        date_keys = [CONF_HISTORY_SPRING, CONF_HISTORY_SUMMER, CONF_HISTORY_AUTUMN, CONF_HISTORY_WINTER]
        for key in date_keys:
            if key in user_input and user_input[key] == "":
                user_input[key] = None

    def _validate_dates(self, user_input, errors):
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
    """Handle options flow for SMHI Season."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the main options (Sensor Selection)."""
        errors = {}
        
        if user_input is not None:
            # If user wants to edit history, go to next step
            if user_input.get("edit_history"):
                # Save sensor selection to options temporarily or pass it along?
                # Actually, we can just update the entry with what we have if we aren't done,
                # but standard practice is to chain steps.
                
                # We need to preserve the sensor choice for the next save
                self.sensor_choice = user_input.get(CONF_TEMPERATURE_SENSOR)
                return await self.async_step_history_settings()
            
            # If not editing history, save and finish
            current_options = dict(self.config_entry.options)
            current_options[CONF_TEMPERATURE_SENSOR] = user_input[CONF_TEMPERATURE_SENSOR]
            
            return self.async_create_entry(title="", data=current_options)

        # Default Sensor
        current_sensor = self.config_entry.options.get(
            CONF_TEMPERATURE_SENSOR, 
            self.config_entry.data.get(CONF_TEMPERATURE_SENSOR)
        )

        schema = vol.Schema({
            vol.Required(CONF_TEMPERATURE_SENSOR, default=current_sensor): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
            ),
            vol.Optional("edit_history", default=False): bool
        })

        return self.async_show_form(
            step_id="init",
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
            
            # Clean up keys
            for key in ["reset_spring", "reset_summer", "reset_autumn", "reset_winter"]:
                user_input.pop(key, None)

            self._normalize_dates(user_input)

            if self._validate_dates(user_input, errors):
                # Update options
                current_options = dict(self.config_entry.options)
                current_options.update(user_input)
                
                # Update sensor if changed in previous step
                if hasattr(self, 'sensor_choice'):
                    current_options[CONF_TEMPERATURE_SENSOR] = self.sensor_choice
                
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
        date_keys = [CONF_HISTORY_SPRING, CONF_HISTORY_SUMMER, CONF_HISTORY_AUTUMN, CONF_HISTORY_WINTER]
        for key in date_keys:
            if key in user_input and user_input[key] == "":
                user_input[key] = None

    def _validate_dates(self, user_input, errors):
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