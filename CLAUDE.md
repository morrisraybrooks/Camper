# Notes for Claude working on this repo

This repo is a snapshot of Morris's camper smart-home setup. **It is PUBLIC.**

## Never commit
- Passwords, tokens, API keys, Wi-Fi details, or real `secrets.yaml` / `secrets.h`. Use `!secret` names and keep the `*.example` files up to date.
- The full VIN, the home address or home coordinates, email addresses, or the Tailscale IP.
- Photos of people, camera snapshots, or recordings.

## How the pieces fit
- The live system is on the home LAN (Pi running Home Assistant at 192.168.0.168, Jetson at .173). **Cloud sessions can't reach it.** Changes made here are proposals: open a PR, and Morris (or a local Claude session on the ODROID) applies them.
- `home-assistant/dashboards/camper.yaml` is the source of truth. `camper_phone.yaml` is GENERATED. After editing camper.yaml, run `python3 home-assistant/dashboards/make_phone_dashboard.py` (check the script for the paths it expects) and commit both files.
- ESP32 boards (`esphome/`) are on the bench, not installed. Their tank, battery and awning values are test values.
- `docs/notes/` explains what's set up, how and why. Read the matching note before changing a feature.

## User preferences
- Low vision: big pictures, big text, and pictures over text lists on dashboards.
- One glow color per device on every page; peach sections, white inner cards.
- No ad-supported audio sources, ever.
- Never change real thermostat setpoints or modes just to test.
- Keep explanations short and plain.
