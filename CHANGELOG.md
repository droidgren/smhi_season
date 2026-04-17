# Changelog

## 1.0.35

- **Changed:** Season day counters no longer reset to 0 after a season transition is confirmed. The counter continues to increment (e.g., 8/7, 9/7) as long as the season criteria are met, showing the total number of consecutive qualifying days. The counter resets only when a day no longer meets the criteria.
- **Fixed:** Prevented unnecessary daily log noise for seasons that have already been confirmed. Transition logic is now skipped entirely for the active season.

## 1.0.34 (beta)

- **Added:** "Set as current season" override option for manual dates.
- **Added:** One-shot bootstrap overrides are cleared after setup applies them.
- **Fixed:** Season transition from unknown state now allowed.
- **Fixed:** Stale season state after manual current-season override (fixes #7).
- **Fixed:** Reconcile `current_season` / arrival date when automatic logic reaches a season whose arrival date already exists.

## 1.0.33

- **Added:** State-specific icons for the season sensor (snowflake, flower, sun, leaf).

## 1.0.32

- **Changed:** Moved images to `imgs/` subfolder.
- **Changed:** Updated HACS metadata.

## 1.0.31

- **Fixed:** Bug fixes in sensor logic.
- **Updated:** Translation strings (en/sv).

## 1.0.30

- **Added:** Screenshot to README.
- **Updated:** README documentation.

## 1.0.29

- **Changed:** Updated HACS and manifest metadata.

## 1.0.28

- **Changed:** Manifest updates.

## 1.0.27

- **Added:** `hassfest.yaml` validation workflow.
- **Updated:** README and manifest.

## 1.0.26

- **Added:** `validate.yaml` CI workflow.
- **Changed:** Moved `hacs.json` to repository root.
- **Changed:** Sensor updates.

## 1.0.25

- **Refactored:** Config flow to use sectioned history settings.

## 1.0.24

- **Refactored:** Manual season set logic and cleanup flags.
- **Updated:** README.

## 1.0.23

- **Added:** "Set as current season" option when entering manual dates.

## 1.0.22

- **Refactored:** Manual season date handling.
- **Updated:** Translations.

## 1.0.21

- **Fixed:** Improved season key mapping in `update_history`.

## 1.0.20

- **Reverted:** Season settings, config flow, and translation changes from 1.0.19.

## 1.0.19

- **Added:** Current season override support.
- **Added:** Config flow settings for season management.
- **Changed:** Renamed component.
- **Updated:** Translations.

## 1.0.18

- **Added:** Green Winter support — allow Autumn → Spring transition (skipping Winter).
- **Added:** Disclaimer to README.

## 1.0.17

- **Refactored:** Frost date lookup to use long-term statistics.

## 1.0.16

- **Added:** Tracking for days since last frost (`Dagar sedan frost`).

## 1.0.15

- **Added:** Log sensor (`sensor.meteorologisk_arstid_logg`).
- **Added:** Enhanced logging with logbook integration.

## 1.0.14

- **Fixed:** Typo in sensor.
- **Updated:** README logo.

## 1.0.13

- **Changed:** Sensors switched to event-driven updates.
- **Improved:** Logging.

## 1.0.12

- **Improved:** Manual reset and options flow for historical dates.

## 1.0.11

- **Added:** Reset options for historical season dates.

## 1.0.10

- **Updated:** Sensor and translation strings.

## 1.0.9

- **Refactored:** Config flow and improved manual date handling.

## 1.0.8

- **Refactored:** Config and options flow to multi-step dialogs.

## 1.0.7

- **Added:** Reset option for historical season dates.

## 1.0.6.2

- **Fixed:** `OptionsFlowHandler` config entry handling.

## 1.0.6.1

- **Fixed:** Config flow fix.

## 1.0.6

- **Refactored:** Season transition logic.
- **Updated:** README, HACS metadata, and brand images.

## 1.0.5

- **Improved:** SMHI season logic and translations.

## 1.0.4

- **Added:** Manual date validation and improved config.

## 1.0.3

- **Refactored:** `OptionsFlowHandler` config entry handling.

## 1.0.2

- **Added:** Options flow with manual history dates support.

## 1.0.1

- **Changed:** Moved `sensor.py` to main component directory.

## 1.0.0

- **Initial release:** Meteorological season calculation based on SMHI definitions.
