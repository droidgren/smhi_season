# $\color{#FF0000}{Work~in~~progress!}$

# ![icon](./custom_components/icon_128.png) Meteorologisk Årstid for Home Assistant

A custom integration that calculates the meteorological seasons in Sweden.

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
- **Sensor 3:** `sensor.meteorologisk_arstid_logg` (Show last update)

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
- **Dagar sedan frost:** Number of days since the last frost (daily minimum temperature ≤ 0°C).
- **Vinterdygn 0/5:** Progress towards Winter.
- **Vårdygn 0/7:** Progress towards Spring.
- **Sommardygn 0/5:** Progress towards Summer.
- **Höstdygn 0/5:** Progress towards Autumn.
- **Förra dygnets medeltemp:** The calculated average used for the logic.

## Disclaimer
This project is an independent custom integration and is **not** affiliated with, endorsed by, or connected to **SMHI** (Swedish Meteorological and Hydrological Institute) in any way. It simply uses their public meteorological definitions to calculate seasons.
