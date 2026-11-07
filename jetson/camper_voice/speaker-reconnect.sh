#!/bin/sh
# Keep the Jetson's speakers connected (2026-11-06).
# Speaker: the Furrion DV3100 camper stereo. (The W-KING D8 fallback was removed
# 2026-11-06 at the user's request; to add a speaker back, append its MAC to SPEAKERS.)
# The ECOXGEAR is the user's outdoor speaker and is deliberately not used here.
# Every 30 s: power the radio on, connect any speaker that is missing, pick the
# first one in SPEAKERS whose sink exists, make it the default and move all
# playing audio (VLC music, voice replies) onto it.
SPEAKERS="00:13:04:02:45:EE"
sink_of() { echo "bluez_output.$(echo "$1" | tr : _).a2dp-sink"; }
while true; do
  if ! bluetoothctl show </dev/null 2>/dev/null | grep -q "Powered: yes"; then
    timeout 10 bluetoothctl power on </dev/null >/dev/null 2>&1 && echo "powered on bluetooth"
  fi
  for MAC in $SPEAKERS; do
    if ! bluetoothctl info "$MAC" </dev/null 2>/dev/null | grep -q "Connected: yes"; then
      timeout 15 bluetoothctl connect "$MAC" </dev/null >/dev/null 2>&1 && echo "connected $MAC"
    elif ! pactl list short sinks 2>/dev/null | grep -q "$(sink_of "$MAC")"; then
      # Connected but no sound output (happens after a sound-system restart):
      # count how long, and reconnect it after about a minute.
      eval "N=\${MISS_$(echo "$MAC" | tr -d :):-0}"; N=$((N+1))
      if [ "$N" -ge 2 ]; then
        timeout 10 bluetoothctl disconnect "$MAC" </dev/null >/dev/null 2>&1; sleep 3
        timeout 15 bluetoothctl connect "$MAC" </dev/null >/dev/null 2>&1 && echo "reconnected $MAC (no sink)"
        N=0
      fi
      eval "MISS_$(echo "$MAC" | tr -d :)=$N"
    fi
  done
  TARGET=""
  for MAC in $SPEAKERS; do
    S=$(sink_of "$MAC")
    if pactl list short sinks 2>/dev/null | grep -q "$S"; then TARGET=$S; break; fi
  done
  if [ -n "$TARGET" ]; then
    if ! pactl info 2>/dev/null | grep -q "Default Sink: $TARGET"; then
      pactl set-default-sink "$TARGET" && echo "default sink is now $TARGET"
    fi
    # Wake the output if it is asleep, so short beeps aren't lost while the
    # Bluetooth link starts (see wireplumber 51-bluez-no-suspend.lua).
    if pactl list short sinks 2>/dev/null | grep "$TARGET" | grep -q SUSPENDED; then
      head -c 8820 /dev/zero | paplay --raw --rate=22050 --channels=1 --format=s16le && echo "woke $TARGET"
    fi
    ID=$(pactl list short sinks | awk -v n="$TARGET" '$2==n{print $1}')
    for i in $(pactl list short sink-inputs 2>/dev/null | awk -v s="$ID" '$2!=s{print $1}'); do
      pactl move-sink-input "$i" "$TARGET" && echo "moved stream $i to $TARGET"
    done
  fi
  sleep 30
done
