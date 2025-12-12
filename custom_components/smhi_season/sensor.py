"""Sensor platform for SMHI Meteorological Season."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
import statistics

from homeassistant.components.sensor import SensorEntity, RestoreSensor
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_TEMPERATURE_SENSOR,
    SEASON_WINTER,
    SEASON_SPRING,
    SEASON_SUMMER,
    SEASON_AUTUMN,
    SEASON_UNKNOWN,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    temp_sensor_id = entry.data[CONF_TEMPERATURE_SENSOR]
    
    # Create the history sensor first so the main sensor can update it
    history_sensor = SmhiHistorySensor(entry.entry_id)
    main_sensor = SmhiSeasonSensor(hass, entry.entry_id, temp_sensor_id, history_sensor)

    async_add_entities([main_sensor, history_sensor])


class SmhiHistorySensor(RestoreSensor, SensorEntity):
    """Sensor showing historical arrival dates."""

    def __init__(self, entry_id):
        self._attr_name = "Meteorologisk årstid historisk"
        self._attr_unique_id = f"{entry_id}_history"
        self._attr_has_entity_name = True
        self._attr_icon = "mdi:calendar-clock"
        self._state_attributes = {
            "Vårens ankomstdatum": None,
            "Sommarens ankomstdatum": None,
            "Höstens ankomstdatum": None,
            "Vinterns ankomstdatum": None,
        }
        self._attr_native_value = "Historik"

    @property
    def extra_state_attributes(self):
        return self._state_attributes

    async def async_added_to_hass(self):
        """Restore state."""
        await super().async_added_to_hass()
        if (state := await self.async_get_last_state()) is not None:
            self._state_attributes = dict(state.attributes)

    def update_history(self, season, date_str):
        """Update a specific historical date."""
        key = f"{season}s ankomstdatum"
        if season == SEASON_WINTER: # Special grammar case
            key = "Vinterns ankomstdatum"
            
        self._state_attributes[key] = date_str
        self.async_write_ha_state()


class SmhiSeasonSensor(RestoreSensor, SensorEntity):
    """Main sensor calculating the meteorological season."""

    def __init__(self, hass, entry_id, temp_sensor_id, history_sensor):
        self.hass = hass
        self._temp_sensor_id = temp_sensor_id
        self._history_sensor = history_sensor
        
        self._attr_name = "Meteorologisk årstid"
        self._attr_unique_id = f"{entry_id}_main"
        self._attr_icon = "mdi:weather-partly-cloudy"
        
        # Internal state tracking
        self.current_season = SEASON_UNKNOWN
        self.season_arrival_date = None
        self.consecutive_days = 0
        self.last_update = None
        self.daily_avg_temp = None

        # Current arrival dates (for the current cycle)
        self.arrival_dates = {
            SEASON_SPRING: None,
            SEASON_SUMMER: None,
            SEASON_AUTUMN: None,
            SEASON_WINTER: None,
        }

    @property
    def native_value(self):
        return self.current_season

    @property
    def extra_state_attributes(self):
        attrs = {
            "Ankomstdatum": self.season_arrival_date,
            "Förra dygnets medeltemp": f"{self.daily_avg_temp:.1f}°C" if self.daily_avg_temp is not None else None,
            "Senast uppdaterad": self.last_update,
            "Vinterdygn X/5": f"{self.consecutive_days}/5" if self.target_season() == SEASON_WINTER else "0/5",
            "Vårdygn X/7": f"{self.consecutive_days}/7" if self.target_season() == SEASON_SPRING else "0/7",
            "Sommardygn X/5": f"{self.consecutive_days}/5" if self.target_season() == SEASON_SUMMER else "0/5",
            "Höstdygn X/5": f"{self.consecutive_days}/5" if self.target_season() == SEASON_AUTUMN else "0/5",
        }
        
        # Add the current cycle arrival dates
        attrs["Vårens ankomstdatum"] = self.arrival_dates[SEASON_SPRING]
        attrs["Sommarens ankomstdatum"] = self.arrival_dates[SEASON_SUMMER]
        attrs["Höstens ankomstdatum"] = self.arrival_dates[SEASON_AUTUMN]
        attrs["Vinterns ankomstdatum"] = self.arrival_dates[SEASON_WINTER]
        
        return attrs

    def target_season(self):
        """Determine which season we are currently tracking towards."""
        if self.current_season == SEASON_WINTER: return SEASON_SPRING
        if self.current_season == SEASON_SPRING: return SEASON_SUMMER
        if self.current_season == SEASON_SUMMER: return SEASON_AUTUMN
        if self.current_season == SEASON_AUTUMN: return SEASON_WINTER
        return SEASON_WINTER # Default

    async def async_added_to_hass(self):
        """Register callbacks and restore state."""
        await super().async_added_to_hass()
        
        # Restore state
        if (state := await self.async_get_last_state()) is not None:
            self.current_season = state.state
            self.season_arrival_date = state.attributes.get("Ankomstdatum")
            
            # Restore arrival dates
            self.arrival_dates[SEASON_SPRING] = state.attributes.get("Vårens ankomstdatum")
            self.arrival_dates[SEASON_SUMMER] = state.attributes.get("Sommarens ankomstdatum")
            self.arrival_dates[SEASON_AUTUMN] = state.attributes.get("Höstens ankomstdatum")
            self.arrival_dates[SEASON_WINTER] = state.attributes.get("Vinterns ankomstdatum")
            
            # Try to restore consecutive days from the active counter
            for s, limit in [(SEASON_WINTER, 5), (SEASON_SPRING, 7), (SEASON_SUMMER, 5), (SEASON_AUTUMN, 5)]:
                key = f"{s}dygn X/{limit}"
                if val := state.attributes.get(key):
                    if val != f"0/{limit}":
                        try:
                            self.consecutive_days = int(val.split('/')[0])
                        except (ValueError, IndexError):
                            self.consecutive_days = 0

        # Run check every night at 00:00:10 to allow DB to settle
        async_track_time_change(self.hass, self._daily_check, hour=0, minute=0, second=10)

    async def _daily_check(self, now):
        """Calculate yesterday's average and update logic."""
        
        # Calculate start and end of yesterday
        yesterday = now - timedelta(days=1)
        start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Get history from recorder
        from homeassistant.components.recorder import history
        
        events = await self.hass.async_add_executor_job(
            history.state_changes_during_period,
            self.hass,
            start_time,
            end_time,
            self._temp_sensor_id,
        )

        temps = []
        if self._temp_sensor_id in events:
            for event in events[self._temp_sensor_id]:
                try:
                    if event.state not in ("unknown", "unavailable"):
                        temps.append(float(event.state))
                except ValueError:
                    pass
        
        # Also get the state at the exact start of the day (midnight reading)
        # to ensure we have data covering the full period
        start_state = self.hass.states.get(self._temp_sensor_id)
        if start_state and start_state.state not in ("unknown", "unavailable"):
             try:
                temps.append(float(start_state.state))
             except ValueError:
                pass

        if not temps:
            _LOGGER.warning("No temperature data found for yesterday for %s", self._temp_sensor_id)
            return

        avg_temp = statistics.mean(temps)
        self.daily_avg_temp = avg_temp
        self.last_update = now.isoformat()
        
        self._process_smhi_logic(avg_temp, now.date())
        self.async_write_ha_state()

    def _process_smhi_logic(self, avg_temp, today_date):
        """Implement SMHI State Machine."""
        
        # Determine month/day for logic
        # Note: 'today_date' is technically the day the check runs (00:00), 
        # but the avg temp is for 'yesterday'. 
        # SMHI counts arrival as Day 1 of the sequence.
        
        # To handle dates correctly (Feb 15, etc), we look at the date of the data (yesterday)
        data_date = today_date - timedelta(days=1)
        
        next_season = self.target_season()
        criteria_met = False
        days_needed = 5

        # Rule Definitions
        if next_season == SEASON_SPRING:
            # > 0.0°C, 7 days. Earliest Feb 15. Latest Jul 31.
            days_needed = 7
            is_valid_date = (data_date.month > 2 or (data_date.month == 2 and data_date.day >= 15)) and \
                            (data_date.month < 7 or (data_date.month == 7 and data_date.day <= 31))
            if avg_temp > 0.0 and is_valid_date:
                criteria_met = True

        elif next_season == SEASON_SUMMER:
            # >= 10.0°C, 5 days.
            days_needed = 5
            if avg_temp >= 10.0:
                criteria_met = True

        elif next_season == SEASON_AUTUMN:
            # < 10.0°C, 5 days. Earliest Aug 1. Latest Feb 14.
            days_needed = 5
            is_valid_date = (data_date.month >= 8) or \
                            (data_date.month < 2 or (data_date.month == 2 and data_date.day <= 14))
            if avg_temp < 10.0 and is_valid_date:
                criteria_met = True

        elif next_season == SEASON_WINTER:
            # <= 0.0°C, 5 days.
            days_needed = 5
            if avg_temp <= 0.0:
                criteria_met = True

        # Logic Execution
        if criteria_met:
            self.consecutive_days += 1
        else:
            self.consecutive_days = 0

        # Check if season changed
        if self.consecutive_days >= days_needed:
            # Move current season date to history sensor before overwriting
            if self.arrival_dates[next_season]:
                 self._history_sensor.update_history(next_season, self.arrival_dates[next_season])

            # Change Season
            self.current_season = next_season
            
            # Arrival date is the first day of the sequence
            arrival = data_date - timedelta(days=days_needed - 1)
            formatted_date = self._format_date_swedish(arrival)
            
            self.season_arrival_date = formatted_date
            self.arrival_dates[next_season] = formatted_date
            
            # Reset counter
            self.consecutive_days = 0
            
            # Clear future dates in current cycle (e.g. if Winter arrives, clear Spring date from this cycle)
            # This logic depends on if you want to keep the "2025" dates visible until they are replaced.
            # Based on prompt "stored in previous year date", we keep them in attributes until overwritten.
            pass

    def _format_date_swedish(self, date_obj):
        months = [
            "januari", "februari", "mars", "april", "maj", "juni",
            "juli", "augusti", "september", "oktober", "november", "december"
        ]
        return f"{date_obj.day} {months[date_obj.month - 1]} {date_obj.year}"