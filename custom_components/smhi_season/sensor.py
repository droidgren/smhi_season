"""Sensor platform for SMHI Meteorological Season."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, date
import statistics

from homeassistant.components.sensor import SensorEntity, RestoreSensor
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change

from .const import (
    DOMAIN,
    CONF_TEMPERATURE_SENSOR,
    CONF_HISTORY_SPRING,
    CONF_HISTORY_SUMMER,
    CONF_HISTORY_AUTUMN,
    CONF_HISTORY_WINTER,
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
    
    config = {**entry.data, **entry.options}
    temp_sensor_id = config.get(CONF_TEMPERATURE_SENSOR)
    
    # Initialize sensors
    history_sensor = SmhiHistorySensor(entry.entry_id)
    main_sensor = SmhiSeasonSensor(hass, entry.entry_id, temp_sensor_id, history_sensor)

    # --- PROCESS MANUAL DATES ---
    current_year = date.today().year
    
    # Map config keys to season constants
    date_map = {
        SEASON_SPRING: config.get(CONF_HISTORY_SPRING),
        SEASON_SUMMER: config.get(CONF_HISTORY_SUMMER),
        SEASON_AUTUMN: config.get(CONF_HISTORY_AUTUMN),
        SEASON_WINTER: config.get(CONF_HISTORY_WINTER),
    }

    # Distribute dates to correct sensor based on year
    for season, date_str in date_map.items():
        if date_str:
            try:
                # date_str comes as 'YYYY-MM-DD' from selector
                d_obj = date.fromisoformat(str(date_str))
                formatted_date = main_sensor._format_date_swedish(d_obj)

                if d_obj.year == current_year:
                    # Current year -> Main Sensor
                    main_sensor.set_manual_arrival_date(season, formatted_date)
                else:
                    # Previous year -> History Sensor
                    history_sensor.update_history(season, formatted_date)
            except ValueError:
                continue

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
            # We restore state, but manually provided dates in __init__ (via async_setup_entry) 
            # will override these via the update_history call which happens before adding.
            # However, since async_added_to_hass runs AFTER setup, we need to be careful not to overwrite manual config with old state.
            
            restored = dict(state.attributes)
            for k, v in restored.items():
                # Only restore if we haven't already set it via manual config in setup
                if self._state_attributes.get(k) is None:
                    self._state_attributes[k] = v

    def update_history(self, season, date_str):
        """Update a specific historical date."""
        key = f"{season}s ankomstdatum"
        if season == SEASON_WINTER:
            key = "Vinterns ankomstdatum"
        self._state_attributes[key] = date_str
        # Note: async_write_ha_state() cannot be called before entity is added, 
        # but in async_setup_entry we just set the dict, which is fine.


class SmhiSeasonSensor(RestoreSensor, SensorEntity):
    """Main sensor calculating the meteorological season."""

    def __init__(self, hass, entry_id, temp_sensor_id, history_sensor):
        self.hass = hass
        self._temp_sensor_id = temp_sensor_id
        self._history_sensor = history_sensor
        
        self._attr_name = "Meteorologisk årstid"
        self._attr_unique_id = f"{entry_id}_main"
        self._attr_icon = "mdi:weather-partly-cloudy"
        
        self.current_season = SEASON_UNKNOWN
        self.season_arrival_date = None
        self.consecutive_days = 0
        self.last_update = None
        self.daily_avg_temp = None

        self.arrival_dates = {
            SEASON_SPRING: None,
            SEASON_SUMMER: None,
            SEASON_AUTUMN: None,
            SEASON_WINTER: None,
        }

    def set_manual_arrival_date(self, season, date_str):
        """Set arrival date manually from config."""
        self.arrival_dates[season] = date_str
        # If the manual date is for the 'current' season logic, we might want to update season_arrival_date too,
        # but determining 'current' from just dates is tricky without temperature context.
        # For now, we just populate the attribute list.

    @property
    def native_value(self):
        return self.current_season

    @property
    def extra_state_attributes(self):
        target = self.target_season()
        def get_count(season, limit):
            if target == season:
                return f"{self.consecutive_days}/{limit}"
            return f"0/{limit}"

        attrs = {
            "Ankomstdatum": self.season_arrival_date,
            "Förra dygnets medeltemp": f"{self.daily_avg_temp:.1f}°C" if self.daily_avg_temp is not None else None,
            "Senast uppdaterad": self.last_update,
            "Vinterdygn": get_count(SEASON_WINTER, 5),
            "Vårdygn": get_count(SEASON_SPRING, 7),
            "Sommardygn": get_count(SEASON_SUMMER, 5),
            "Höstdygn": get_count(SEASON_AUTUMN, 5),
            "Vårens ankomstdatum": self.arrival_dates[SEASON_SPRING],
            "Sommarens ankomstdatum": self.arrival_dates[SEASON_SUMMER],
            "Höstens ankomstdatum": self.arrival_dates[SEASON_AUTUMN],
            "Vinterns ankomstdatum": self.arrival_dates[SEASON_WINTER],
        }
        return attrs

    def target_season(self):
        if self.current_season == SEASON_WINTER: return SEASON_SPRING
        if self.current_season == SEASON_SPRING: return SEASON_SUMMER
        if self.current_season == SEASON_SUMMER: return SEASON_AUTUMN
        if self.current_season == SEASON_AUTUMN: return SEASON_WINTER
        return SEASON_WINTER

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if (state := await self.async_get_last_state()) is not None:
            self.current_season = state.state
            self.season_arrival_date = state.attributes.get("Ankomstdatum")
            
            # Restore counts
            for s, limit in [(SEASON_WINTER, 5), (SEASON_SPRING, 7), (SEASON_SUMMER, 5), (SEASON_AUTUMN, 5)]:
                val = state.attributes.get(f"{s}dygn")
                if not val:
                    val = state.attributes.get(f"{s}dygn X/{limit}")
                if val and val != f"0/{limit}":
                    try:
                        self.consecutive_days = int(val.split('/')[0])
                    except (ValueError, IndexError):
                        self.consecutive_days = 0

            # Only restore dates if NOT set manually in setup
            for s in [SEASON_SPRING, SEASON_SUMMER, SEASON_AUTUMN, SEASON_WINTER]:
                if self.arrival_dates[s] is None:
                    # Restore from DB
                    key = f"{s}s ankomstdatum" if s != SEASON_WINTER else "Vinterns ankomstdatum"
                    self.arrival_dates[s] = state.attributes.get(key)

        async_track_time_change(self.hass, self._daily_check, hour=0, minute=0, second=10)

    async def _daily_check(self, now):
        yesterday = now - timedelta(days=1)
        start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)

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
        data_date = today_date - timedelta(days=1)
        next_season = self.target_season()
        criteria_met = False
        days_needed = 5

        if next_season == SEASON_SPRING:
            days_needed = 7
            is_valid_date = (data_date.month > 2 or (data_date.month == 2 and data_date.day >= 15)) and \
                            (data_date.month < 7 or (data_date.month == 7 and data_date.day <= 31))
            if avg_temp > 0.0 and is_valid_date:
                criteria_met = True

        elif next_season == SEASON_SUMMER:
            days_needed = 5
            if avg_temp >= 10.0:
                criteria_met = True

        elif next_season == SEASON_AUTUMN:
            days_needed = 5
            is_valid_date = (data_date.month >= 8) or \
                            (data_date.month < 2 or (data_date.month == 2 and data_date.day <= 14))
            if avg_temp < 10.0 and is_valid_date:
                criteria_met = True

        elif next_season == SEASON_WINTER:
            days_needed = 5
            if avg_temp <= 0.0:
                criteria_met = True

        if criteria_met:
            self.consecutive_days += 1
        else:
            self.consecutive_days = 0

        if self.consecutive_days >= days_needed:
            if self.arrival_dates[next_season]:
                 self._history_sensor.update_history(next_season, self.arrival_dates[next_season])

            self.current_season = next_season
            arrival = data_date - timedelta(days=days_needed - 1)
            formatted_date = self._format_date_swedish(arrival)
            
            self.season_arrival_date = formatted_date
            self.arrival_dates[next_season] = formatted_date
            self.consecutive_days = 0

    def _format_date_swedish(self, date_obj):
        months = [
            "januari", "februari", "mars", "april", "maj", "juni",
            "juli", "augusti", "september", "oktober", "november", "december"
        ]
        return f"{date_obj.day} {months[date_obj.month - 1]} {date_obj.year}"