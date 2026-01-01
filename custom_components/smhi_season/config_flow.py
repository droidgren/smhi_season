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
    CONF_HISTORY_WINTER,
    CONF_CURRENT_SEASON,
    SEASON_SPRING,
    SEASON_SUMMER,
    SEASON_AUTUMN,
    SEASON_WINTER
)

CONF_MANUAL_RESET = "MANUAL_RESET"
OPTION_AUTO = "Automatisk"

class OptionalDateSelector(selector.DateSelector):
    """Custom DateSelector that accepts empty values (None or empty string)."""
    def __call__(self, value):
        if value is None or value == "" or str(value) == "None":
            return None
        try:
            return super().__call__(value)
        except vol.Invalid:
            return None

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
            # Handle Resets
            if user_input.get("reset_spring"): user_input[CONF_HISTORY_SPRING] = CONF_MANUAL_RESET
            if user_input.get("reset_summer"): user_input[CONF_HISTORY_SUMMER] = CONF_MANUAL_RESET
            if user_input.get("reset_autumn"): user_input[CONF_HISTORY_AUTUMN] = CONF_MANUAL_RESET
            if user_input.get("reset_winter"): user_input[CONF_HISTORY_WINTER] = CONF_MANUAL_RESET
            
            # Clean up reset keys
            for key in ["reset_spring", "reset_summer", "reset_autumn", "reset_winter"]:
                user_input.pop(key, None)

            self._normalize_dates(user_input)
            
            if self._validate_dates(user_input, errors):
                final_data = {**self._config_data, **user_input}
                return self.async_create_entry(
                    title="Meteorologisk Årstid", data=final_data
                )

        schema = vol.Schema({
            vol.Optional(CONF_HISTORY_SPRING): OptionalDateSelector(),
            vol.Optional("reset_spring", default=False): bool,
            
            vol.Optional(CONF_HISTORY_SUMMER): OptionalDateSelector(),
            vol.Optional("reset_summer", default=False): bool,
            
            vol.Optional(CONF_HISTORY_AUTUMN): OptionalDateSelector(),
            vol.Optional("reset_autumn", default=False): bool,
            
            vol.Optional(CONF_HISTORY_WINTER): OptionalDateSelector(),
            vol.Optional("reset_winter", default=False): bool,
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
                if input_date_str == CONF_MANUAL_RESET:
                    continue
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
        """Manage the main options menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["sensor_settings", "history_settings", "season_settings"]
        )

    async def async_step_sensor_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the temperature sensor selection."""
        errors = {}
        
        if user_input is not None:
            # Update options
            current_options = dict(self.config_entry.options)
            current_options[CONF_TEMPERATURE_SENSOR] = user_input[CONF_TEMPERATURE_SENSOR]
            return self.async_create_entry(title="", data=current_options)

        current_sensor = self.config_entry.options.get(
            CONF_TEMPERATURE_SENSOR, 
            self.config_entry.data.get(CONF_TEMPERATURE_SENSOR)
        )

        schema = vol.Schema({
            vol.Required(CONF_TEMPERATURE_SENSOR, default=current_sensor): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
            ),
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
            if user_input.get("reset_spring"): user_input[CONF_HISTORY_SPRING] = CONF_MANUAL_RESET
            if user_input.get("reset_summer"): user_input[CONF_HISTORY_SUMMER] = CONF_MANUAL_RESET
            if user_input.get("reset_autumn"): user_input[CONF_HISTORY_AUTUMN] = CONF_MANUAL_RESET
            if user_input.get("reset_winter"): user_input[CONF_HISTORY_WINTER] = CONF_MANUAL_RESET
            
            for key in ["reset_spring", "reset_summer", "reset_autumn", "reset_winter"]:
                user_input.pop(key, None)

            self._normalize_dates(user_input)

            if self._validate_dates(user_input, errors):
                current_options = dict(self.config_entry.options)
                current_options.update(user_input)
                
                return self.async_create_entry(title="", data=current_options)

        defaults = {**self.config_entry.data, **self.config_entry.options}
        
        # Hide manual reset sentinels from UI
        for key in [CONF_HISTORY_SPRING, CONF_HISTORY_SUMMER, CONF_HISTORY_AUTUMN, CONF_HISTORY_WINTER]:
            if defaults.get(key) == CONF_MANUAL_RESET:
                defaults[key] = None

        schema = vol.Schema({
            vol.Optional(CONF_HISTORY_SPRING, default=defaults.get(CONF_HISTORY_SPRING)): OptionalDateSelector(),
            vol.Optional("reset_spring", default=False): bool,
            
            vol.Optional(CONF_HISTORY_SUMMER, default=defaults.get(CONF_HISTORY_SUMMER)): OptionalDateSelector(),
            vol.Optional("reset_summer", default=False): bool,
            
            vol.Optional(CONF_HISTORY_AUTUMN, default=defaults.get(CONF_HISTORY_AUTUMN)): OptionalDateSelector(),
            vol.Optional("reset_autumn", default=False): bool,
            
            vol.Optional(CONF_HISTORY_WINTER, default=defaults.get(CONF_HISTORY_WINTER)): OptionalDateSelector(),
            vol.Optional("reset_winter", default=False): bool,
        })

        return self.async_show_form(
            step_id="history_settings",
            data_schema=schema,
            errors=errors
        )

    async def async_step_season_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual season override."""
        errors = {}

        if user_input is not None:
            current_options = dict(self.config_entry.options)
            
            selected_season = user_input.get(CONF_CURRENT_SEASON)
            if selected_season == OPTION_AUTO:
                # Remove override
                current_options.pop(CONF_CURRENT_SEASON, None)
            else:
                current_options[CONF_CURRENT_SEASON] = selected_season

            return self.async_create_entry(title="", data=current_options)

        current_val = self.config_entry.options.get(CONF_CURRENT_SEASON, OPTION_AUTO)

        schema = vol.Schema({
            vol.Required(CONF_CURRENT_SEASON, default=current_val): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        OPTION_AUTO,
                        SEASON_SPRING,
                        SEASON_SUMMER,
                        SEASON_AUTUMN,
                        SEASON_WINTER
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN
                )
            )
        })

        return self.async_show_form(
            step_id="season_settings",
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
                if input_date_str == CONF_MANUAL_RESET:
                    continue
                try:
                    input_date = date.fromisoformat(str(input_date_str))
                    if input_date > today:
                        errors["base"] = "cannot_be_future"
                        return False
                except ValueError:
                    pass
        return True
