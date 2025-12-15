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
    SEASON_THRESHOLDS,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    
    # Merge data (original setup) and options (changes made via Configure)
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


class SmhiSeasonSensor(RestoreSensor, SensorEntity):
    """Main sensor calculating the meteorological season."""

    def __init__(self, hass, entry_id, temp_sensor_id, history_sensor):
        self.hass = hass
        self._temp_sensor_id = temp_sensor_id
        self._history_sensor = history_sensor
        
        self._attr_name = "Meteorologisk årstid"
        self._attr_unique_id = f"{entry_id}_main"
        self._attr_icon = "mdi:weather-partly-cloudy"
        
        self.current_season = SEASON_WINTER  # Start with winter instead of unknown
        self.season_arrival_date = None
        self.last_update = None
        self.daily_avg_temp = None

        # Track counters for ALL seasons simultaneously
        self.season_counters = {
            SEASON_WINTER: 0,
            SEASON_SPRING: 0,
            SEASON_SUMMER: 0,
            SEASON_AUTUMN: 0,
        }

        self.arrival_dates = {
            SEASON_SPRING: None,
            SEASON_SUMMER: None,
            SEASON_AUTUMN: None,
            SEASON_WINTER: None,
        }
        
        # Track which dates are manually set (to avoid overriding)
        self.manual_dates = {
            SEASON_SPRING: False,
            SEASON_SUMMER: False,
            SEASON_AUTUMN: False,
            SEASON_WINTER: False,
        }

    def set_manual_arrival_date(self, season, date_str):
        """Set arrival date manually from config."""
        self.arrival_dates[season] = date_str
        self.manual_dates[season] = True
        _LOGGER.info("Manually set %s arrival date to %s", season, date_str)

    @property
    def native_value(self):
        return self.current_season

    @property
    def extra_state_attributes(self):
        attrs = {
            "Ankomstdatum": self.season_arrival_date,
            "Förra dygnets medeltemp": f"{self.daily_avg_temp:.1f}°C" if self.daily_avg_temp is not None else None,
            "Senast uppdaterad": self.last_update,
            "Vinterdygn": f"{self.season_counters[SEASON_WINTER]}/{SEASON_THRESHOLDS[SEASON_WINTER]}",
            "Vårdygn": f"{self.season_counters[SEASON_SPRING]}/{SEASON_THRESHOLDS[SEASON_SPRING]}",
            "Sommardygn": f"{self.season_counters[SEASON_SUMMER]}/{SEASON_THRESHOLDS[SEASON_SUMMER]}",
            "Höstdygn": f"{self.season_counters[SEASON_AUTUMN]}/{SEASON_THRESHOLDS[SEASON_AUTUMN]}",
            "Vårens ankomstdatum": self.arrival_dates[SEASON_SPRING],
            "Sommarens ankomstdatum": self.arrival_dates[SEASON_SUMMER],
            "Höstens ankomstdatum": self.arrival_dates[SEASON_AUTUMN],
            "Vinterns ankomstdatum": self.arrival_dates[SEASON_WINTER],
        }
        return attrs

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if (state := await self.async_get_last_state()) is not None:
            # Restore state, but never set to "unknown" or "unavailable"
            if state.state in [SEASON_WINTER, SEASON_SPRING, SEASON_SUMMER, SEASON_AUTUMN]:
                self.current_season = state.state
            
            self.season_arrival_date = state.attributes.get("Ankomstdatum")
            
            # Restore all season counters
            for season in [SEASON_WINTER, SEASON_SPRING, SEASON_SUMMER, SEASON_AUTUMN]:
                val = state.attributes.get(f"{season}dygn")
                if val:
                    try:
                        count = int(val.split('/')[0])
                        self.season_counters[season] = count
                    except (ValueError, IndexError):
                        self.season_counters[season] = 0

            # Only restore dates if NOT set manually in setup
            for s in [SEASON_SPRING, SEASON_SUMMER, SEASON_AUTUMN, SEASON_WINTER]:
                if not self.manual_dates[s]:
                    # Restore from DB
                    key = f"{s}s ankomstdatum" if s != SEASON_WINTER else "Vinterns ankomstdatum"
                    restored_date = state.attributes.get(key)
                    if restored_date:
                        self.arrival_dates[s] = restored_date

        _LOGGER.info("SMHI Season sensor initialized. Current season: %s", self.current_season)
        async_track_time_change(self.hass, self._daily_check, hour=0, minute=0, second=10)

    async def _daily_check(self, now):
        """Daily check at midnight to process temperature data."""
        _LOGGER.info("=== Starting daily season check at %s ===", now.isoformat())
        
        # Calculate start and end of yesterday
        yesterday = now - timedelta(days=1)
        start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)

        _LOGGER.debug("Fetching temperature data for %s (from %s to %s)", 
                     yesterday.date(), start_time, end_time)

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
            _LOGGER.warning("No temperature data found for %s from sensor %s. Skipping daily check.", 
                          yesterday.date(), self._temp_sensor_id)
            return

        avg_temp = statistics.mean(temps)
        self.daily_avg_temp = avg_temp
        self.last_update = now.isoformat()
        
        _LOGGER.info("Average temperature for %s was %.1f°C (from %d readings)", 
                    yesterday.date(), avg_temp, len(temps))
        
        self._process_smhi_logic(avg_temp, now.date())
        self.async_write_ha_state()
        
        _LOGGER.info("=== Daily season check completed ===")


    def _process_smhi_logic(self, avg_temp, today_date):
        """Process SMHI meteorological season logic with comprehensive logging."""
        # Use yesterday's date for logic (since temp is from yesterday)
        data_date = today_date - timedelta(days=1)
        
        _LOGGER.info("Processing season logic for date %s with avg temp %.1f°C. Current season: %s",
                    data_date, avg_temp, self.current_season)
        
        # Check for year rollover - if we're in a new year and all dates are from previous year
        self._check_year_rollover(data_date)
        
        # Track which seasons meet criteria today
        seasons_criteria = {}
        
        # Check WINTER criteria: <= 0.0°C, 5 days needed
        if avg_temp <= 0.0:
            seasons_criteria[SEASON_WINTER] = True
            self.season_counters[SEASON_WINTER] += 1
            _LOGGER.debug("Winter criteria met (%.1f°C <= 0.0°C). Counter: %d/5",
                         avg_temp, self.season_counters[SEASON_WINTER])
        else:
            if self.season_counters[SEASON_WINTER] > 0:
                _LOGGER.debug("Winter criteria NOT met (%.1f°C > 0.0°C). Resetting counter from %d to 0",
                             avg_temp, self.season_counters[SEASON_WINTER])
            self.season_counters[SEASON_WINTER] = 0
        
        # Check SPRING criteria: > 0.0°C, earliest Feb 15, latest Jul 31, 7 days needed
        is_valid_spring_date = (data_date.month > 2 or (data_date.month == 2 and data_date.day >= 15)) and \
                               (data_date.month < 7 or (data_date.month == 7 and data_date.day <= 31))
        if avg_temp > 0.0 and is_valid_spring_date:
            seasons_criteria[SEASON_SPRING] = True
            self.season_counters[SEASON_SPRING] += 1
            _LOGGER.debug("Spring criteria met (%.1f°C > 0.0°C, date valid). Counter: %d/7",
                         avg_temp, self.season_counters[SEASON_SPRING])
        else:
            if self.season_counters[SEASON_SPRING] > 0:
                reason = "temp too low" if avg_temp <= 0.0 else "date out of range"
                _LOGGER.debug("Spring criteria NOT met (%.1f°C, %s). Resetting counter from %d to 0",
                             avg_temp, reason, self.season_counters[SEASON_SPRING])
            self.season_counters[SEASON_SPRING] = 0
        
        # Check SUMMER criteria: >= 10.0°C, 5 days needed
        if avg_temp >= 10.0:
            seasons_criteria[SEASON_SUMMER] = True
            self.season_counters[SEASON_SUMMER] += 1
            _LOGGER.debug("Summer criteria met (%.1f°C >= 10.0°C). Counter: %d/5",
                         avg_temp, self.season_counters[SEASON_SUMMER])
        else:
            if self.season_counters[SEASON_SUMMER] > 0:
                _LOGGER.debug("Summer criteria NOT met (%.1f°C < 10.0°C). Resetting counter from %d to 0",
                             avg_temp, self.season_counters[SEASON_SUMMER])
            self.season_counters[SEASON_SUMMER] = 0
        
        # Check AUTUMN criteria: < 10.0°C, earliest Aug 1, latest Feb 14, 5 days needed
        is_valid_autumn_date = (data_date.month >= 8) or \
                               (data_date.month < 2 or (data_date.month == 2 and data_date.day <= 14))
        if avg_temp < 10.0 and is_valid_autumn_date:
            seasons_criteria[SEASON_AUTUMN] = True
            self.season_counters[SEASON_AUTUMN] += 1
            _LOGGER.debug("Autumn criteria met (%.1f°C < 10.0°C, date valid). Counter: %d/5",
                         avg_temp, self.season_counters[SEASON_AUTUMN])
        else:
            if self.season_counters[SEASON_AUTUMN] > 0:
                reason = "temp too high" if avg_temp >= 10.0 else "date out of range"
                _LOGGER.debug("Autumn criteria NOT met (%.1f°C, %s). Resetting counter from %d to 0",
                             avg_temp, reason, self.season_counters[SEASON_AUTUMN])
            self.season_counters[SEASON_AUTUMN] = 0
        
        # Check if any season threshold is reached
        for season, threshold in SEASON_THRESHOLDS.items():
            if self.season_counters[season] >= threshold:
                if self.manual_dates[season]:
                    _LOGGER.info("%s threshold reached (%d/%d days), but %s date is manually set. NOT updating.",
                               season, self.season_counters[season], threshold, season)
                    # Reset counter since we've "reached" the season
                    self.season_counters[season] = 0
                elif self.arrival_dates[season] is not None:
                    _LOGGER.info("%s threshold reached (%d/%d days), but %s date already set this year. NOT updating.",
                               season, self.season_counters[season], threshold, season)
                    # Reset counter since we've already recorded this season
                    self.season_counters[season] = 0
                else:
                    # Trigger season change
                    self._change_season(season, threshold, data_date)
    
    def _change_season(self, new_season, days_needed, data_date):
        """Handle changing to a new season."""
        _LOGGER.info("=== SEASON CHANGE TRIGGERED: %s -> %s ===", self.current_season, new_season)
        
        # Move current season date to history sensor before overwriting
        if self.arrival_dates[new_season]:
            self._history_sensor.update_history(new_season, self.arrival_dates[new_season])
            _LOGGER.info("Moved previous %s date to history: %s", new_season, self.arrival_dates[new_season])

        # Change Season
        self.current_season = new_season
        
        # Arrival date is the first day of the sequence
        arrival = data_date - timedelta(days=days_needed - 1)
        formatted_date = self._format_date_swedish(arrival)
        
        self.season_arrival_date = formatted_date
        self.arrival_dates[new_season] = formatted_date
        
        _LOGGER.info("Season changed to %s. Arrival date: %s", new_season, formatted_date)
        
        # Reset counter
        self.season_counters[new_season] = 0
    
    def _check_year_rollover(self, current_date):
        """Check if we need to rollover dates to history for a new year."""
        current_year = current_date.year
        
        # Check if any arrival dates exist
        has_dates = any(date_str is not None for date_str in self.arrival_dates.values())
        if not has_dates:
            return
        
        # Check if all dates are from a previous year
        all_dates_old = True
        for season, date_str in self.arrival_dates.items():
            if date_str:
                # Parse the Swedish date format
                try:
                    # Extract year from format like "15 januari 2025"
                    parts = date_str.split()
                    if len(parts) >= 3:
                        year = int(parts[-1])
                        if year == current_year:
                            all_dates_old = False
                            break
                except (ValueError, IndexError):
                    continue
        
        # If all dates are from previous year, move them to history and clear for new year
        if all_dates_old:
            _LOGGER.info("Year rollover detected. Moving all dates to history for year %d", current_year)
            for season, date_str in self.arrival_dates.items():
                if date_str and not self.manual_dates[season]:
                    self._history_sensor.update_history(season, date_str)
                    self.arrival_dates[season] = None
                    _LOGGER.info("Moved %s date to history: %s", season, date_str)

    def _format_date_swedish(self, date_obj):
        months = [
            "januari", "februari", "mars", "april", "maj", "juni",
            "juli", "augusti", "september", "oktober", "november", "december"
        ]
        return f"{date_obj.day} {months[date_obj.month - 1]} {date_obj.year}"