from __future__ import annotations

import datetime

from homeassistant.components.date import DateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from homeassistant.const import EntityCategory


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the debug date entity."""
    date_entity = SmhiDebugDate(entry)

    if entry.entry_id in hass.data.get(DOMAIN, {}):
        hass.data[DOMAIN][entry.entry_id]["debug_date"] = date_entity

    async_add_entities([date_entity])


class SmhiDebugDate(DateEntity):
    """Date entity to set the simulated date for debugging."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_registry_enabled_default = False
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize."""
        self._entry = entry
        self._attr_name = "Debug Date"
        self._attr_unique_id = f"{entry.entry_id}_debug_date"
        self._attr_native_value = datetime.date.today()

    async def async_set_value(self, value: datetime.date) -> None:
        """Update the date via UI directly."""
        self.set_date(value)

    def set_date(self, value: datetime.date) -> None:
        """Internal method to update the date."""
        self._attr_native_value = value
        self.async_write_ha_state()
