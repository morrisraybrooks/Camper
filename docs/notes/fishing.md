# project-camper-fishing

> Fishing page on the camper dashboard - solunar + pressure forecast built 2026-10-25; how it works and its gotchas

The user said: "we love fishing but haven't went all year", and wanted the pressure readings turned into a fishing chart. Built 2026-10-25:
- `/config/fishing/fishing_solunar.py` (stdlib + astral 2.2, no other deps) computes the moon (Schlyter low-precision; checked vs PyEphem to within about 4 min over 10 dates), the solunar windows (major = moon overhead/underfoot ±1 h, minor = moonrise/moonset ±30 min), sunrise/sunset, the phase, and a 0-100 score from pressure trend + window + dawn/dusk + moon - wind. Args: LAT LON TZ "TREND" WIND_MPH.
- `sensor.fishing_forecast` (command_line in configuration.yaml, every 5 min, uses zone.home lat/lon so it follows the camper) = Excellent/Good/Fair/Slow; attributes score, reasons, now_text, in_window, rows, tomorrow_majors, phase, moon_icon…
- Dashboard view `/lovelace-camper/fishing` (and phone): a Fishing badge (&b_fishing) on every page, a big rating card, a Today's Best Times table, the moon card, a 48 h pressure chart and a "what pressure means" guide. api.solunar.org is dead (no response), so don't use it.
- **New `sensor.barometric_pressure`** (template, under-camper Aqara first, over-bed as fallback; registry unit forced to hPa) now feeds the statistics `pressure_change_3h`/`pressure_range_6h` (both forced to hPa) → `pressure_trend` → the storm alert and fishing. Why: the two Aqaras read about 3 hPa apart, and the sensor swap made a fake "falling fast". GOTCHA: atmospheric_pressure device_class shows inHg under the US unit system; inHg samples got into the recorder and made a fake 975 hPa jump, fixed with recorder.purge_entities on those 3 entities.
- Backups `*.bak-preclaude-fishing-20261025-165629` (configuration.yaml, camper.yaml, camper_phone.yaml).
Ideas not built: add their favorite lakes' locations, water temperature, a notification when an Excellent window is coming.
