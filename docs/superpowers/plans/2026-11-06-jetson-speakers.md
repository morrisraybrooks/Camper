# Jetson Speakers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Jetson audio (Jarvis replies + VLC music) plays on the Furrion DV3100. It falls back to
the W-KING D8, and the W-KING is charged by a smart plug.
**Architecture:** The Jetson's BlueZ/PipeWire holds the speakers. `speaker-reconnect.sh` picks the
first connected speaker from a priority list and moves streams to it. An HA automation drives the
Kasa plug.
**Tech Stack:** BlueZ 5.64, WirePlumber 0.4.8 (Lua config), POSIX sh, Home Assistant automations.
**Spec:** docs/superpowers/specs/2026-11-06-jetson-speakers-design.md

## Global Constraints
- Furrion DV3100 00:13:04:02:45:EE: A2DP only, never HFP. Keep `bluez5.hfphsp-backend = "none"`
  unless the battery test proves HFP is safe for the Furrion.
- W-KING D8 F4:4E:FD:8C:1D:6F. ECOXGEAR 7C:96:D2:D1:C9:47 is removed from the rotation (keep its
  pairing for the user's outdoor use).
- Plug: switch.kasa_hs105_spare. Battery: on at 25%, off at 100%. Timer fallback: 2 h per day.
- Back up before editing: Jetson `*.bak-preclaude-furrion-20261106`; Pi /config/claude_backups.
- The user is physically limited, so ask for each pairing-button press only once, one speaker at a
  time.

## Review Focus
- Stereo turned off mid-song: the stream must move to the W-KING within about 60 s, and back when
  the stereo turns on.
- Both speakers off: no error loop, and the default sink falls back quietly.
- The Pi re-grabs the Furrion at power-on: it must be removed from the Pi before pairing.
- The Furrion tries hands-free: watch the journal for HFP errors and drops for 10 min after pairing.
- The Kasa plug is offline: the automation must not error-spam. Notify once.

---

### Task 1: Pair the Furrion to the Jetson (A2DP only)
**Files:** Pi bluetooth pairing (via hassio host `bluetoothctl remove`), Jetson BlueZ.
- [ ] Back up the Pi BT state, then `bluetoothctl remove 00:13:04:02:45:EE` on the Pi host.
- [ ] Ask the user to put the stereo in BT pairing mode. On the Jetson, run the interactive
  bluetoothctl with `pairable on` / `scan bredr` / `pair` / `trust` / `connect`.
- [ ] Verify: `pactl list short sinks` shows `bluez_output.00_13_04_02_45_EE.a2dp-sink`. Play a
  Piper test phrase and the user hears it.
- [ ] Verify: there are no HFP errors and no disconnect in `journalctl -u bluetooth` for 10 min.

### Task 2: Pair the W-KING and set the speaker priority
**Files:** Modify `~/camper_voice/speaker-reconnect.sh` (Jetson)
**Produces:** `SPEAKERS="00:13:04:02:45:EE F4:4E:FD:8C:1D:6F"` (priority order). The active sink is
derived from the MAC (`bluez_output.<MAC_with_underscores>.a2dp-sink`).
- [ ] Ask the user to put the W-KING in pairing mode. Pair, trust and connect it the same way.
- [ ] Rewrite the loop. If the Furrion isn't connected, try it, then try the W-KING. The target is
  the first speaker whose sink exists. While the W-KING is the target, it keeps retrying the
  Furrion. Only one speaker stays connected: when the Furrion connects, disconnect the W-KING.
  Keep the power-on, wake-from-suspend and move-streams logic.
- [ ] `systemctl --user restart speaker-reconnect`
- [ ] Verify the fallback: disconnect the Furrion from the Jetson side, play music, and within 60 s
  the stream is on the W-KING. Reconnect the Furrion, and the stream moves back.

### Task 3: W-KING battery reading
- [ ] With the W-KING connected, check `bluetoothctl info F4:4E:FD:8C:1D:6F` for "Battery Percentage".
- [ ] If it's absent: test the HFP native backend temporarily (enable BlueZ `Experimental = true` and
  `bluez5.hfphsp-backend = "native"` with the W-KING only) and check again. Revert if the Furrion
  shows any HFP attempt.
- [ ] Outcome A (battery readable): the reconnect loop writes the percentage to HA via a webhook ->
  `sensor.w_king_battery`. Outcome B: no sensor, so Task 4 uses the timer.

### Task 4: Charging automation in HA
**Files:** `/config/automations.yaml` (Pi), repo `home-assistant/automations.yaml`
- [ ] A: plug on when battery < 25, off at 100 (and off after 4 h max as a safety).
  B: plug on daily 13:00–15:00.
- [ ] If the plug is unavailable at trigger time, send one notification.
- [ ] Verify with `ha core check`, then trigger the automation manually and watch the plug state.
- [ ] Commit the repo changes (spec, plan, automation, script copy) and update the memory notes.
