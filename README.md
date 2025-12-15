# <img src="custom_components/icon.png" width="64" align="left" alt="Logo"> Meteorologisk Årstid (SMHI) for Home Assistant

A custom integration that calculates the meteorological season based on SMHI (Swedish Meteorological and Hydrological Institute) definitions.

## Features
- Calculates daily average temperature automatically.
- Tracks **all season counters simultaneously** - even when a season is already set, counters continue to track qualifying days.
- Follows strict SMHI date and temperature rules:
  - **Vinter:** ≤ 0.0°C (5 days)
  - **Vår:** > 0.0°C (7 days, earliest Feb 15)
  - **Sommar:** ≥ 10.0°C (5 days)
  - **Höst:** < 10.0°C (5 days, earliest Aug 1)
- **Manual date override:** Set season arrival dates manually in configuration. The integration will track counters but won't override manually set dates.
- **Optional dates:** All dates are optional. Leave blank to let the integration calculate automatically, or set to override.
- **Year rollover:** Automatically moves dates to history when a new year begins.
- **Extensive logging:** View detailed logs showing temperature calculations, season criteria evaluation, and counter updates.
- **Sensor 1:** `sensor.meteorologisk_arstid` (Shows current season, progress count, and arrival dates for current cycle).
- **Sensor 2:** `sensor.meteorologisk_arstid_historisk` (Shows arrival dates for the previous cycle).

## Installation

### HACS (Recommended)
1. Ensure [HACS](https://hacs.xyz/) is installed.
2. Go to HACS -> Integrations -> 3 dots (top right) -> Custom repositories.
3. Add the URL to this repository. Category: **Integration**.
4. Click "Download".
5. Restart Home Assistant.

### Manual
1. Copy the `custom_components/smhi_season` folder to your HA `custom_components` directory.
2. Restart Home Assistant.

## Configuration
1. Go to **Settings** -> **Devices & Services**.
2. Click **Add Integration**.
3. Search for "Meteorologisk årstid".
4. Select your outdoor temperature sensor (e.g., `sensor.outdoor_temperature`).
5. Optionally set season arrival dates manually. Leave blank for automatic calculation.
   - **To clear a previously set date:** Simply remove the date from the field in the configuration UI and save.

## Logging
The integration provides detailed logging to help you understand what's happening:

- **INFO level:** Daily temperature averages, season changes, and important decisions
- **DEBUG level:** Detailed criteria evaluation for each season and counter updates

Example log output:
```
INFO: === Starting daily season check at 2025-12-15T00:00:10 ===
INFO: Average temperature for 2025-12-14 was 5.6°C (from 144 readings)
INFO: Processing season logic for date 2025-12-14 with avg temp 5.6°C. Current season: Vinter
DEBUG: Winter criteria NOT met (5.6°C > 0.0°C). Resetting counter from 0 to 0
DEBUG: Spring criteria met (5.6°C > 0.0°C, date valid). Counter: 1/7
DEBUG: Summer criteria NOT met (5.6°C < 10.0°C). Resetting counter from 0 to 0
DEBUG: Autumn criteria met (5.6°C < 10.0°C, date valid). Counter: 1/5
INFO: Höst threshold reached (5/5 days), but Höst date already set this year. NOT updating.
INFO: === Daily season check completed ===
```

To enable debug logging, add this to your `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.smhi_season: debug
```

## Attributes
The main sensor provides:
- **Current State:** Shows the current season (Okänd, Vinter, Vår, Sommar, or Höst) - never "unavailable"
- **Ankomstdatum:** Date the current season started.
- **Vinterdygn X/5:** Progress towards Winter (tracks continuously, even if winter is already set).
- **Vårdygn X/7:** Progress towards Spring (tracks continuously, even if spring is already set).
- **Sommardygn X/5:** Progress towards Summer (tracks continuously, even if summer is already set).
- **Höstdygn X/5:** Progress towards Autumn (tracks continuously, even if autumn is already set).
- **Förra dygnets medeltemp:** The calculated average used for the logic.
- **Vårens/Sommarens/Höstens/Vinterns ankomstdatum:** Individual arrival dates for each season.

## How It Works

### Simultaneous Counter Tracking
Unlike traditional sequential season tracking, this integration tracks **all four season counters at the same time**:

- If temperature is 5°C in December, both Spring (> 0°C) and Autumn (< 10°C) counters will increment
- Winter and Summer counters would reset since criteria aren't met
- This gives you a complete picture of qualifying days for all seasons

### Manual Date Protection
When you manually set a season's arrival date:
- The integration still tracks that season's counter
- It logs when the threshold is reached
- But it **won't override** your manual date
- To allow automatic calculation again, simply clear the date in configuration

### Year Rollover
When all arrival dates are from a previous year:
- The integration automatically moves them to the historical sensor
- Clears current year dates to begin fresh calculations
- This ensures smooth transitions between years
