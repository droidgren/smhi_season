from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import UnitOfTemperature

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the debug temperature entity."""
    number_entity = SmhiDebugTemp(entry)

    if entry.entry_id in hass.data.get(DOMAIN, {}):
        hass.data[DOMAIN][entry.entry_id]["debug_temp"] = number_entity

    async_add_entities([number_entity])


class SmhiDebugTemp(NumberEntity):
    """Number entity to set the simulated average temperature for debugging."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_registry_enabled_default = False
    _attr_native_min_value = -50.0
    _attr_native_max_value = 50.0
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize."""
        self._entry = entry
        self._attr_name = "Debug Avg Temp"
        self._attr_unique_id = f"{entry.entry_id}_debug_avg_temp"
        self._attr_native_value = 10.0

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self._attr_native_value = value
        self.async_write_ha_state()
