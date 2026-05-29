from __future__ import annotations

import datetime

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_ENABLE_DEBUG_ENTITIES
from homeassistant.const import EntityCategory


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the debug step button."""
    enable_debug = entry.options.get(CONF_ENABLE_DEBUG_ENTITIES, entry.data.get(CONF_ENABLE_DEBUG_ENTITIES, False))
    if not enable_debug:
        return

    button = SmhiDebugStep(entry)
    
    if entry.entry_id in hass.data.get(DOMAIN, {}):
        hass.data[DOMAIN][entry.entry_id]["debug_step"] = button

    async_add_entities([button])


class SmhiDebugStep(ButtonEntity):
    """Button to manually advance the day for debugging."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_registry_enabled_default = False
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the button."""
        self._entry = entry
        self._attr_name = "Debug Step Day"
        self._attr_unique_id = f"{entry.entry_id}_debug_step_day"

    async def async_press(self) -> None:
        """Handle the button press."""
        shared_data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id, {})
        
        main_sensor = shared_data.get("main_sensor")
        debug_date_entity = shared_data.get("debug_date")
        debug_temp_entity = shared_data.get("debug_temp")

        if not main_sensor or not debug_date_entity or not debug_temp_entity:
            return  # The other debug entities must also be active

        current_date_val = debug_date_entity.state
        if current_date_val in (None, "unknown", "unavailable"):
            return

        current_temp_val = debug_temp_entity.state
        if current_temp_val in (None, "unknown", "unavailable"):
            return

        # Execute debug step
        debug_date_dt = datetime.date.fromisoformat(current_date_val)
        await main_sensor.process_debug_step(debug_date_dt, current_temp_val)

        # Advance the date by 1 day automatically
        new_date = debug_date_dt + datetime.timedelta(days=1)
        debug_date_entity.set_date(new_date)
