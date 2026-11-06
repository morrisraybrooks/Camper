# project-camper-safety-features

> Features the user picked on 2026-10-23 (ideas 1,2,4-9): battery/weather in work reminder, 1 PM summary, Daisy heat fix, safe-drive check, find my phone, smoke/bark listener (Jetson part blocked)

On 2026-10-23 the user asked for new ideas, then picked 1, 2, 4, 5, 6, 7, 8 and 9. All changes are in /config/automations.yaml. Backups are `claude_backups/{automations,scripts}.yaml.bak-preclaude-ideas-20261023-175920`.

Original alerts edited, per the "fix the original code" rule:
- **schedule_work_reminder (2:30 PM):** gets an hourly forecast first. Adds "Your phone is at X%. Plug it in" when the battery is under 50% and not charging, and "Drive home at 4 AM: N°" using the min temp for 2–6 AM tomorrow, plus rain, a frost warning at ≤34, a coat under 45 and a jacket under 60. A preview rendered OK.
- **camper_morning_summary:** Morris now gets it at 13:00 (he sleeps 6 AM–1 PM). Nadine stays at 08:00 with the same text camper_notify_both sent her. Both are trigger ids in one automation. The thermostat text in Auto shows "67-73°F" instead of "None".
- **camper_inside_too_hot:** if binary_sensor.daisy_home_alone is on, it sets the ceiling fan mode to Stay On, and if the climate isn't cool/auto it sets Cool at input_number.camper_smart_cool_to (direct climate calls, so there's no duplicate Smart Auto alert). The message says what it did. Never tested live (HVAC rule).

New automations (no original existed):
- **safety_drive_home_check:** device_tracker.sm_s906u leaves zone.work between 00:00 and 09:00. If it isn't home within 75 min (real drives are 30–55 min, he left work at 3:24–3:36), Morris gets "Are you OK?" with an I'm OK button (SAFE_DRIVE_OK). After 10 min without an answer, Nadine gets a spoken + visible high-priority alert with a Google Maps URI button. The user chose this, including telling Nadine.
  - **2026-11-05 fix:** the user tapped the alert, it just opened the app, and they never saw the button (Nadine was alerted at 4:52 AM). Now the alert has clickAction /lovelace-camper/safe-drive, a page with an "Are you OK?" heading and a normal-size green "I'm OK" button, 90 px tall (view safe-drive; the user called the first full-screen button ridiculous, so don't go huge) that runs script.safe_drive_ok, which fires event safe_drive_ok. The wait is 20 min and an answer replaces the alert with "Got it". Nadine alert kept. Backups `*.bak-preclaude-safedrive-20261105-063142`. Practice passed 2026-11-05: script.safe_drive_practice (phone only, never tells Nadine, 1 min delay) sent the alert at 6:41:52 and the I'm OK page tap ended the wait at 6:42:06. The script is kept for future practice. The real automation hasn't fired since the fix. HA API without copying the token out: pipe a script to `sudo docker exec -i app_core_configurator sh` and use its own $SUPERVISOR_TOKEN.
- **voice_find_my_phone:** conversation sentence trigger ("find/ring my phone", "where is/where's my phone", "I can't find my phone"...). It sends a TTS "Here I am" 4× with `media_stream: alarm_stream_max`. Matching was verified with `conversation/agent/homeassistant/debug`, so nothing rang. Morris's phone only.
- **camper_smoke_alarm_heard** (webhook !secret sound_smoke_webhook_id) and **camper_daisy_barking** (webhook !secret sound_bark_webhook_id): both local_only and only while daisy_home_alone is on. Smoke goes to both phones (urgent). Barking goes to Morris only.

**Jetson listener: installed 2026-10-23, after the user said "yes, set up the listener".** An earlier try was blocked by the permission classifier until the user OK'd it.
- `~/camper_voice/mic_tee.py` is now voice-satellite's `--mic-command`. It runs the same arecord and also copies the audio over UDP to 127.0.0.1:10777. Unit backup: `~/voice-satellite.service.bak-preclaude-soundwatch-20261023`.
- `~/camper_voice/sound_watch.py` runs as the user unit `sound-watch.service` (enabled). It uses YAMNet tflite in venv-sound with ai-edge-litert, at 3 ms per frame and about 2% CPU.
  - Smoke: ids 393/394 at ≥0.25, 8 hits in 20 s.
  - Bark: ids 69–74 at ≥0.40, 40 hits in 5 min.
  - Labels and scores are logged to `logs/sound_watch.log`. No audio is saved.
- pip on the Jetson needs `PIP_CONFIG_FILE=/dev/null --index-url https://pypi.org/simple`, because the NVIDIA index doesn't resolve.
- Verified: a webhook POST from the Jetson reached HA, and the trace showed failed_conditions because both were home.
- Not verified yet: a real "Hey Jarvis" after the mic change, and real smoke or bark detection. Tune the thresholds from the log if there are false alerts. TV audio, including Dog TV, could set off the bark alert.

Also 2026-10-23: sent `command_persistent_connection` persistent=always to Morris's phone, so alerts go over the websocket when connected. "Last notification" sensor doesn't exist on his app build. Related: [[user-morris-schedule]], [[project-jetson-voice-satellite]].
