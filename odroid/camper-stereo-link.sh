#!/bin/bash
# Spotify (official app on this ODROID) -> the Jetson's ECOXGEAR Bluetooth speaker (2026-10-25).
# latency_msec=300 added 2026-10-25 for drop-outs; raised to 1000 on 2026-11-06 (still glitching).
# Sound goes through an SSH-forwarded socket to the Jetson's PulseAudio, so nothing new is
# opened on the network. Every 5 s: keep the tunnel + "camper_stereo" sink up, and move
# Spotify's sound onto it.
SOCK=$XDG_RUNTIME_DIR/jetson-pulse.sock
TUNNEL="$SOCK:/run/user/1000/pulse/native"
while true; do
  if ! pgrep -f -- "-L $TUNNEL" >/dev/null; then
    pactl list modules short | awk '/module-tunnel-sink.*camper_stereo/{print $1}' | xargs -r -n1 pactl unload-module
    rm -f "$SOCK"
    ssh -f -N -o BatchMode=yes -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=3 \
      -L "$TUNNEL" morris@192.168.0.173 || { sleep 10; continue; }
  fi
  pactl list sinks short | grep -q "camper_stereo" || \
    pactl load-module module-tunnel-sink server="unix:$SOCK" sink_name=camper_stereo latency_msec=1000 \
      sink_properties=device.description=Camper_Stereo_Jetson >/dev/null
  pactl -f json list sink-inputs 2>/dev/null | python3 -c '
import json, subprocess, sys
sinks = {s["index"]: s["name"] for s in json.loads(subprocess.run(["pactl", "-f", "json", "list", "sinks"], capture_output=True, text=True).stdout or "[]")}
for i in json.loads(sys.stdin.read() or "[]"):
    if i["properties"].get("application.name") == "Spotify" and sinks.get(i["sink"]) != "camper_stereo":
        subprocess.run(["pactl", "move-sink-input", str(i["index"]), "camper_stereo"])
'
  sleep 5
done
