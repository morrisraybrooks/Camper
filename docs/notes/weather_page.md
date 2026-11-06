# project-camper-weather-page

> Camper Weather page and badge built 2026-11-01 from three weather services; NWS location is fixed, not following the camper

Built 2026-11-01 at the user's request ("make an actual weather page", "add more weather services"). View `/lovelace-camper/weather` (and tablet), badge `&b_weather` on every page.

- **Services:** met.no (weather.forecast_home, follows Home), Open-Meteo (weather.open_meteo, zone.home), NWS (weather.nws, station KEHO). NWS `api_key` is just the free-form identifier "camper-home-assistant", not a real key.
- **GOTCHA:** NWS's "entity" setup step rejected zone.home (`entity_not_found`), so it was set with fixed coordinates. **If the camper moves, NWS must be reconfigured.** met.no and Open-Meteo follow Home.
- `sensor.camper_weather_forecast` (trigger template in configuration.yaml, every 30 min, on start and on template reload) trims forecasts into attributes `hourly` [t,c,f,r,p], `daily` [d,c,hi,lo,r,p], `met_hi`, `om_hi`, `nws_hi` (about 1.6 KB). Extra services use continue_on_error so met.no still works if they fail.
- Right Now and the badge prefer the measured NWS reading, falling back to met.no. Other dashboard cards still use met.no. Rain chance % comes from NWS (met.no only gives amounts).
- Backups `*.bak-preclaude-weatherpage-*`, `*.bak-preclaude-weather3-*`.

Related: [[user_low_vision]], [[project_camper_phone_dashboard]].

**Animated sky (2026-11-01):** the Right Now card's top is a CSS scene chosen from the current condition (sun, moon/stars, clouds, rain, snow, hail, lightning, fog, wind, heat shimmer at 85°+). CSS lives in the button-card's `extra_styles`, the scene in its JS. The user rejected the first sun (dashed ring of rays, clipped); it's now an SVG with tapered rays. No `prefers-reduced-motion` rule on purpose: the ODROID desktop's Chrome reports reduced motion, which froze everything, and the user asked for animation. Preview by overriding `el.hass` on the button-card in browser JS, never by changing real states. Backups `*.bak-preclaude-weatheranim-*`, `*.bak-preclaude-weathersun-*`.

**Santa (2026-11-01, user asked):** an SVG Santa, sleigh and 3 reindeer (lead has a glowing red nose) cross the Right Now sky every 20 s, Dec 1-26, in any weather; the sky gets taller (`.wx-xmas`) then so he clears the temperature. The date window was my choice. Preview by temporarily patching window.Date in browser JS. Backup `*.bak-preclaude-weathersanta-*`.
Santa redraw (2026-11-01): Nadine said the first Santa "looked like a hoodlum chasing three deer". He now has a round front-facing face (rosy cheeks, eyes, nose, moustache, smile, big beard), and the deer are hitched with gold reins, traces, red straps and bells. Keep faces friendly and front-on. Backup `*.bak-preclaude-santaface-*`.

**Sky fix (2026-11-01):** NWS said "sunny" under real overcast: KEHO reported CLR, and airport sensors generally only report clouds below 12,000 ft (met.no had 100% cloud). Right Now now uses the NWS temperature, but if NWS says sunny/clear/partly cloudy and met.no or Open-Meteo shows clouds or worse, it uses that sky.
