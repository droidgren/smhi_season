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
    
    history_sensor = SmhiHistorySensor(entry.entry_id)
    main_sensor = SmhiSeasonSensor(hass, entry.entry_id, temp_sensor_id, history_sensor)

    current_year = date.today().year
    
    date_map = {
        SEASON_SPRING: config.get(CONF_HISTORY_SPRING),
        SEASON_SUMMER: config.get(CONF_HISTORY_SUMMER),
        SEASON_AUTUMN: config.get(CONF_HISTORY_AUTUMN),
        SEASON_WINTER: config.get(CONF_HISTORY_WINTER),
    }

    for season, date_str in date_map.items():
        if date_str:
            try:
                d_obj = date.fromisoformat(str(date_str))
                formatted_date = main_sensor._format_date_swedish(d_obj)

                if d_obj.year == current_year:
                    main_sensor.set_manual_arrival_date(season, formatted_date)
                else:
                    history_sensor.update_history(season, formatted_date)
            except ValueError:
                _LOGGER.warning("Invalid date format for %s: %s", season, date_str)
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
        
        self.current_season = SEASON_UNKNOWN
        self.season_arrival_date = None
        
        self.consecutive_counts = {
            SEASON_SPRING: 0, 
            SEASON_SUMMER: 0, 
            SEASON_AUTUMN: 0, 
            SEASON_WINTER: 0,
        }

        self.last_update = None
        self.daily_avg_temp = None

        self.arrival_dates = {
            SEASON_SPRING: None,
            SEASON_SUMMER: None,
            SEASON_AUTUMN: None,
            SEASON_WINTER: None,
        }
        
        self._manual_flags = {
            SEASON_SPRING: False,
            SEASON_SUMMER: False,
            SEASON_AUTUMN: False,
            SEASON_WINTER: False,
        }
        
        self.days_needed = {
            SEASON_SPRING: 7,
            SEASON_SUMMER: 5,
            SEASON_AUTUMN: 5,
            SEASON_WINTER: 5,
        }

    def set_manual_arrival_date(self, season, date_str):
        """Set arrival date manually from config."""
        self.arrival_dates[season] = date_str
        self._manual_flags[season] = True

    @property
    def native_value(self):
        return self.current_season

    @property
    def extra_state_attributes(self):
        def get_count(season, limit):
            return f"{self.consecutive_counts.get(season, 0)}/{limit}"

        attrs = {
            "Ankomstdatum": self.season_arrival_date,
            "Förra dygnets medeltemp": f"{self.daily_avg_temp:.1f}°C" if self.daily_avg_temp is not None else None,
            "Senast uppdaterad": self.last_update,
            "Vinterdygn": get_count(SEASON_WINTER, self.days_needed[SEASON_WINTER]),
            "Vårdygn": get_count(SEASON_SPRING, self.days_needed[SEASON_SPRING]),
            "Sommardygn": get_count(SEASON_SUMMER, self.days_needed[SEASON_SUMMER]),
            "Höstdygn": get_count(SEASON_AUTUMN, self.days_needed[SEASON_AUTUMN]),
            "Vårens ankomstdatum": self.arrival_dates[SEASON_SPRING],
            "Sommarens ankomstdatum": self.arrival_dates[SEASON_SUMMER],
            "Höstens ankomstdatum": self.arrival_dates[SEASON_AUTUMN],
            "Vinterns ankomstdatum": self.arrival_dates[SEASON_WINTER],
            "manual_flags": self._manual_flags
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
            
            if self.current_season in ("unknown", "unavailable", None):
                self.current_season = SEASON_UNKNOWN
            
            self.season_arrival_date = state.attributes.get("Ankomstdatum")
            
            # Restore counts
            for s in self.consecutive_counts.keys():
                val = state.attributes.get(f"{s}dygn")
                if val:
                    try:
                        self.consecutive_counts[s] = int(val.split('/')[0])
                    except (ValueError, IndexError):
                        self.consecutive_counts[s] = 0

            # Restore Manual Flags
            saved_flags = state.attributes.get("manual_flags", {})
            has_history = len(saved_flags) > 0 # Check if we have history from new version
            
            if saved_flags:
                for s in self._manual_flags:
                    if s in saved_flags:
                        self._manual_flags[s] = saved_flags[s]

            # Restore Dates Logic
            for s in self.arrival_dates.keys():
                if self.arrival_dates[s] is None:
                    # Date is NOT in current config (User might have cleared it)
                    
                    was_manual = self._manual_flags.get(s, False)
                    
                    # LOGIC FIX:
                    # 1. If it was flagged manual before, and is gone now -> User Reset it. (Do not restore)
                    # 2. If we have NO history of flags (Migration), and it's gone now -> Assume User Reset it to be safe. (Do not restore)
                    # 3. Otherwise (It was calculated), restore it.
                    
                    should_restore = True
                    
                    if was_manual:
                         should_restore = False
                    elif not has_history:
                         # Migration edge case: Old version didn't have flags.
                         # If date is missing from config, we assume user wanted to clear it.
                         should_restore = False
                    
                    if should_restore:
                        key = f"{s}s ankomstdatum" if s != SEASON_WINTER else "Vinterns ankomstdatum"
                        self.arrival_dates[s] = state.attributes.get(key)
                    else:
                        # Ensure flag is reset if we decided not to restore
                        self._manual_flags[s] = False

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
            _LOGGER.warning("[%s] No temperature data found for yesterday for %s", yesterday.date(), self._temp_sensor_id)
            return

        avg_temp = statistics.mean(temps)
        self.daily_avg_temp = avg_temp
        self.last_update = now.isoformat()
        
        self._process_smhi_logic(avg_temp, now.date())
        self.async_write_ha_state()

    def _process_smhi_logic(self, avg_temp, today_date):
        data_date = today_date - timedelta(days=1)
        
        _LOGGER.info(
            "[%s] Daily check started. Average temperature was %.1f°C. Current Season: %s",
            data_date, avg_temp, self.current_season
        )
        
        # Criteria Logic
        is_spring_day = avg_temp > 0.0 and \
                        (data_date.month > 2 or (data_date.month == 2 and data_date.day >= 15)) and \
                        (data_date.month < 7 or (data_date.month == 7 and data_date.day <= 31))
        
        is_summer_day = avg_temp >= 10.0
        
        is_autumn_day = avg_temp < 10.0 and \
                        ((data_date.month >= 8) or \
                        (data_date.month < 2 or (data_date.month == 2 and data_date.day <= 14)))

        is_winter_day = avg_temp <= 0.0

        criteria_map = {
            SEASON_SPRING: is_spring_day,
            SEASON_SUMMER: is_summer_day,
            SEASON_AUTUMN: is_autumn_day,
            SEASON_WINTER: is_winter_day,
        }
        
        new_counts = self.consecutive_counts.copy()
        
        for season, is_day in criteria_map.items():
            if is_day:
                new_counts[season] = self.consecutive_counts[season] + 1
                _LOGGER.debug(
                    "[%s] Criteria met for '%s'. Counter increased to %d/%d.",
                    data_date, season, new_counts[season], self.days_needed[season]
                )
            else:
                if self.consecutive_counts[season] > 0:
                    _LOGGER.debug(
                        "[%s] Criteria NOT met for '%s'. Counter reset from %d to 0.",
                        data_date, season, self.consecutive_counts[season]
                    )
                new_counts[season] = 0

        self.consecutive_counts = new_counts
        next_season = self.target_season()

        for season, count in self.consecutive_counts.items():
            days_needed_for_season = self.days_needed[season]
            
            if count >= days_needed_for_season:
                
                if season != next_season:
                    _LOGGER.info(
                        "[%s] Criteria met for '%s' (%d/%d), but logical next season is '%s'. Transition blocked.",
                        data_date, season, count, days_needed_for_season, next_season
                    )
                    continue 
                
                arrival_dt = data_date - timedelta(days=days_needed_for_season - 1)
                
                existing_date_str = self.arrival_dates.get(season)
                should_update = True
                
                if existing_date_str:
                    existing_dt = self._parse_date_swedish(existing_date_str, arrival_dt.year)
                    if existing_dt:
                        diff = arrival_dt - existing_dt
                        if diff.days < 180 and diff.days > -180:
                            should_update = False
                            _LOGGER.info(
                                "[%s] *** Season change SKIPPED ***: Criteria met for '%s', but date is already set recently (%s).",
                                data_date, season, existing_date_str
                            )
                        else:
                            _LOGGER.info(
                                "[%s] Existing date for '%s' (%s) is old. Moving to history and updating.",
                                data_date, season, existing_date_str
                            )
                            self._history_sensor.update_history(season, existing_date_str)
                    
                if should_update:
                    self.current_season = season
                    formatted_date = self._format_date_swedish(arrival_dt)
                    
                    self.season_arrival_date = formatted_date
                    self.arrival_dates[season] = formatted_date
                    
                    self._manual_flags[season] = False
                    
                    _LOGGER.info(
                        "[%s] *** SEASON CHANGE ***: Transitioned to '%s'. Arrival date set to %s.",
                        data_date, season, formatted_date
                    )
                    
                    self.consecutive_counts[season] = 0
                else:
                    self.consecutive_counts[season] = 0

        _LOGGER.info(
            "[%s] Daily check finished. Current Season: %s, Next Target: %s, Transition Counters: %s",
            data_date, self.current_season, self.target_season(), dict(self.consecutive_counts)
        )

    def _format_date_swedish(self, date_obj):
        months = [
            "januari", "februari", "mars", "april", "maj", "juni",
            "juli", "augusti", "september", "oktober", "november", "december"
        ]
        return f"{date_obj.day} {months[date_obj.month - 1]} {date_obj.year}"

    def _parse_date_swedish(self, date_str, fallback_year):
        try:
            parts = date_str.split(" ")
            day = int(parts[0])
            month_str = parts[1]
            year = int(parts[2])
            
            months = [
                "januari", "februari", "mars", "april", "maj", "juni",
                "juli", "augusti", "september", "oktober", "november", "december"
            ]
            
            if month_str in months:
                month = months.index(month_str) + 1
                return date(year, month, day)
        except (ValueError, IndexError, AttributeError):
            pass
        return None