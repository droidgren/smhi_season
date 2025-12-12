<img src="brand.png" width="150" align="left" alt="Logo">
# Meteorologisk Årstid (SMHI) for Home Assistant

A custom integration that calculates the meteorological season based on SMHI (Swedish Meteorological and Hydrological Institute) definitions.

![SMHI Season](https://img.shields.io/badge/style-SMHI-blue)


## Features
- Calculates daily average temperature automatically.
- Tracks consecutive days to determine season changes.
- Follows strict SMHI date and temperature rules:
  - **Vinter:** ≤ 0.0°C (5 days)
  - **Vår:** > 0.0°C (7 days, earliest Feb 15)
  - **Sommar:** ≥ 10.0°C (5 days)
  - **Höst:** < 10.0°C (5 days, earliest Aug 1)
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

## Attributes
The main sensor provides:
- **Ankomstdatum:** Date the current season started.
- **Vinterdygn X/5:** Progress towards Winter.
- **Vårdygn X/7:** Progress towards Spring.
- **Sommardygn X/5:** Progress towards Summer.
- **Höstdygn X/5:** Progress towards Autumn.
- **Förra dygnets medeltemp:** The calculated average used for the logic.