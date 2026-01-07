"""Config flow for SMHI Meteorological Season integration."""
from __future__ import annotations

from typing import Any
from datetime import date

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult, section
from homeassistant.helpers import selector

from .const import (
    DOMAIN, 
    CONF_TEMPERATURE_SENSOR,
    CONF_HISTORY_SPRING,
    CONF_HISTORY_SUMMER,
    CONF_HISTORY_AUTUMN,
    CONF_HISTORY_WINTER,
    CONF_SET_CURRENT_SPRING,
    CONF_SET_CURRENT_SUMMER,
    CONF_SET_CURRENT_AUTUMN,
    CONF_SET_CURRENT_WINTER,
)

CONF_MANUAL_RESET = "MANUAL_RESET"

class OptionalDateSelector(selector.DateSelector):
    """Custom DateSelector that accepts empty values."""
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
    
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step (Sensor Selection)."""
        errors = {}

        if user_input is not None:
            self._config_data = user_input
            # Go to menu to ask about history
            return await self.async_step_menu()

        schema = vol.Schema({
            vol.Required(CONF_TEMPERATURE_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
            ),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show menu to choose between configuring history or finishing."""
        return self.async_show_menu(
            step_id="menu",
            menu_options=["history_settings", "finish"]
        )

    async def async_step_history_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the history settings step."""
        errors = {}

        if user_input is not None:
            flat_input = {}
            for key, value in user_input.items():
                if isinstance(value, dict):
                    flat_input.update(value)
                else:
                    flat_input[key] = value
            user_input = flat_input

            if user_input.get("reset_spring"): user_input[CONF_HISTORY_SPRING] = CONF_MANUAL_RESET
            if user_input.get("reset_summer"): user_input[CONF_HISTORY_SUMMER] = CONF_MANUAL_RESET
            if user_input.get("reset_autumn"): user_input[CONF_HISTORY_AUTUMN] = CONF_MANUAL_RESET
            if user_input.get("reset_winter"): user_input[CONF_HISTORY_WINTER] = CONF_MANUAL_RESET
            
            set_current_flags = {
                CONF_SET_CURRENT_SPRING: user_input.pop(CONF_SET_CURRENT_SPRING, False),
                CONF_SET_CURRENT_SUMMER: user_input.pop(CONF_SET_CURRENT_SUMMER, False),
                CONF_SET_CURRENT_AUTUMN: user_input.pop(CONF_SET_CURRENT_AUTUMN, False),
                CONF_SET_CURRENT_WINTER: user_input.pop(CONF_SET_CURRENT_WINTER, False),
            }
            
            for key in ["reset_spring", "reset_summer", "reset_autumn", "reset_winter"]:
                user_input.pop(key, None)

            self._normalize_dates(user_input)
            
            if self._validate_dates(user_input, errors):
                final_data = {**self._config_data, **user_input}
                final_data.update(set_current_flags)
                return self.async_create_entry(
                    title="Meteorologisk Årstid", data=final_data
                )

        schema = self._get_history_schema()
        return self.async_show_form(
            step_id="history_settings",
            data_schema=schema,
            errors=errors,
        )
    
    async def async_step_finish(self, user_input=None):
        """Finish the flow without history."""
        return self.async_create_entry(
            title="Meteorologisk Årstid", data=self._config_data
        )

    def _get_history_schema(self, defaults=None):
        if defaults is None:
            defaults = {}
        
        return vol.Schema({
            vol.Optional("section_spring"): section(
                vol.Schema({
                    vol.Optional(CONF_HISTORY_SPRING, default=defaults.get(CONF_HISTORY_SPRING)): OptionalDateSelector(),
                    vol.Optional(CONF_SET_CURRENT_SPRING, default=False): bool,
                    vol.Optional("reset_spring", default=False): bool,
                }),
                {"collapsed": True}
            ),
            vol.Optional("section_summer"): section(
                vol.Schema({
                    vol.Optional(CONF_HISTORY_SUMMER, default=defaults.get(CONF_HISTORY_SUMMER)): OptionalDateSelector(),
                    vol.Optional(CONF_SET_CURRENT_SUMMER, default=False): bool,
                    vol.Optional("reset_summer", default=False): bool,
                }),
                {"collapsed": True}
            ),
            vol.Optional("section_autumn"): section(
                vol.Schema({
                    vol.Optional(CONF_HISTORY_AUTUMN, default=defaults.get(CONF_HISTORY_AUTUMN)): OptionalDateSelector(),
                    vol.Optional(CONF_SET_CURRENT_AUTUMN, default=False): bool,
                    vol.Optional("reset_autumn", default=False): bool,
                }),
                {"collapsed": True}
            ),
            vol.Optional("section_winter"): section(
                vol.Schema({
                    vol.Optional(CONF_HISTORY_WINTER, default=defaults.get(CONF_HISTORY_WINTER)): OptionalDateSelector(),
                    vol.Optional(CONF_SET_CURRENT_WINTER, default=False): bool,
                    vol.Optional("reset_winter", default=False): bool,
                }),
                {"collapsed": True}
            ),
        })

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

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the Main Menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["sensor_settings", "history_settings"]
        )

    async def async_step_sensor_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage Sensor Settings."""
        errors = {}
        if user_input is not None:
            self.config_entry.options = {**self.config_entry.options, **user_input}
            return self.async_create_entry(title="", data=self.config_entry.options)

        defaults = {**self.config_entry.data, **self.config_entry.options}
        schema = vol.Schema({
            vol.Required(CONF_TEMPERATURE_SENSOR, default=defaults.get(CONF_TEMPERATURE_SENSOR)): selector.EntitySelector(
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
        """Manage History Settings with Sections."""
        errors = {}
        
        if user_input is not None:
            flat_input = {}
            for key, value in user_input.items():
                if isinstance(value, dict):
                    flat_input.update(value)
                else:
                    flat_input[key] = value
            user_input = flat_input

            if user_input.get("reset_spring"): user_input[CONF_HISTORY_SPRING] = CONF_MANUAL_RESET
            if user_input.get("reset_summer"): user_input[CONF_HISTORY_SUMMER] = CONF_MANUAL_RESET
            if user_input.get("reset_autumn"): user_input[CONF_HISTORY_AUTUMN] = CONF_MANUAL_RESET
            if user_input.get("reset_winter"): user_input[CONF_HISTORY_WINTER] = CONF_MANUAL_RESET
            
            set_current_flags = {
                CONF_SET_CURRENT_SPRING: user_input.pop(CONF_SET_CURRENT_SPRING, False),
                CONF_SET_CURRENT_SUMMER: user_input.pop(CONF_SET_CURRENT_SUMMER, False),
                CONF_SET_CURRENT_AUTUMN: user_input.pop(CONF_SET_CURRENT_AUTUMN, False),
                CONF_SET_CURRENT_WINTER: user_input.pop(CONF_SET_CURRENT_WINTER, False),
            }
            
            for key in ["reset_spring", "reset_summer", "reset_autumn", "reset_winter"]:
                user_input.pop(key, None)

            self._normalize_dates(user_input)

            if self._validate_dates(user_input, errors):
                current_options = dict(self.config_entry.options)
                current_options.update(user_input)
                current_options.update(set_current_flags)
                return self.async_create_entry(title="", data=current_options)

        defaults = {**self.config_entry.data, **self.config_entry.options}
        
        for key in [CONF_HISTORY_SPRING, CONF_HISTORY_SUMMER, CONF_HISTORY_AUTUMN, CONF_HISTORY_WINTER]:
            if defaults.get(key) == CONF_MANUAL_RESET:
                defaults[key] = None

        # Re-use schema with sections
        schema = vol.Schema({
            vol.Optional("section_spring"): section(
                vol.Schema({
                    vol.Optional(CONF_HISTORY_SPRING, default=defaults.get(CONF_HISTORY_SPRING)): OptionalDateSelector(),
                    vol.Optional(CONF_SET_CURRENT_SPRING, default=False): bool,
                    vol.Optional("reset_spring", default=False): bool,
                }),
                {"collapsed": True}
            ),
            vol.Optional("section_summer"): section(
                vol.Schema({
                    vol.Optional(CONF_HISTORY_SUMMER, default=defaults.get(CONF_HISTORY_SUMMER)): OptionalDateSelector(),
                    vol.Optional(CONF_SET_CURRENT_SUMMER, default=False): bool,
                    vol.Optional("reset_summer", default=False): bool,
                }),
                {"collapsed": True}
            ),
            vol.Optional("section_autumn"): section(
                vol.Schema({
                    vol.Optional(CONF_HISTORY_AUTUMN, default=defaults.get(CONF_HISTORY_AUTUMN)): OptionalDateSelector(),
                    vol.Optional(CONF_SET_CURRENT_AUTUMN, default=False): bool,
                    vol.Optional("reset_autumn", default=False): bool,
                }),
                {"collapsed": True}
            ),
            vol.Optional("section_winter"): section(
                vol.Schema({
                    vol.Optional(CONF_HISTORY_WINTER, default=defaults.get(CONF_HISTORY_WINTER)): OptionalDateSelector(),
                    vol.Optional(CONF_SET_CURRENT_WINTER, default=False): bool,
                    vol.Optional("reset_winter", default=False): bool,
                }),
                {"collapsed": True}
            ),
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