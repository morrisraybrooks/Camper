#!/bin/sh
# Keep the ECOXGEAR-BP Bluetooth speaker connected to the Jetson (2026-10-21).
# Every 30 s: if it isn't connected, connect it; once its sink exists, make it
# the default and move any playing audio (VLC music, voice replies) onto it.
SPEAKER=7C:96:D2:D1:C9:47
SINK=bluez_output.7C_96_D2_D1_C9_47.a2dp-sink
while true; do
  # The radio came up powered off after the 2026-10-21 reboot, so turn it on first.
  if ! bluetoothctl show </dev/null 2>/dev/null | grep -q "Powered: yes"; then
    timeout 10 bluetoothctl power on </dev/null >/dev/null 2>&1 && echo "powered on bluetooth"
  fi
  if ! bluetoothctl info $SPEAKER </dev/null 2>/dev/null | grep -q "Connected: yes"; then
    timeout 25 bluetoothctl connect $SPEAKER </dev/null >/dev/null 2>&1 && echo "reconnected speaker"
    sleep 5
  fi
  if pactl list short sinks 2>/dev/null | grep -q "$SINK"; then
    if ! pactl info 2>/dev/null | grep -q "Default Sink: $SINK"; then
      pactl set-default-sink $SINK && echo "speaker set as default sink"
    fi
    # Wake the output if it is asleep (it then stays awake; see
    # ~/.config/wireplumber/bluetooth.lua.d/51-bluez-no-suspend.lua) so short
    # beeps are not lost while the Bluetooth link starts up.
    if pactl list short sinks 2>/dev/null | grep "$SINK" | grep -q SUSPENDED; then
      head -c 8820 /dev/zero | paplay --raw --rate=22050 --channels=1 --format=s16le && echo "woke speaker output"
    fi
    for i in $(pactl list short sink-inputs 2>/dev/null | awk -v s="$(pactl list short sinks | awk -v n=$SINK '$2==n{print $1}')" '$2!=s{print $1}'); do
      pactl move-sink-input "$i" $SINK && echo "moved stream $i to speaker"
    done
  fi
  sleep 30
done
