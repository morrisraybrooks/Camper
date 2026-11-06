#!/bin/bash
# Test launcher for the Wyoming voice servers (systemd units replace this later).
cd /home/morris/camper_voice || exit 1
mkdir -p data logs
pkill -f '[w]yoming_(openwakeword|faster_whisper|piper)' ; sleep 1
setsid ./venv-openwakeword/bin/python -m wyoming_openwakeword --uri tcp://127.0.0.1:10400 \
  --preload-model hey_jarvis --preload-model ok_nabu --debug --debug-probability > logs/oww.log 2>&1 < /dev/null &
setsid ./venv-faster-whisper/bin/python -m wyoming_faster_whisper --uri tcp://0.0.0.0:10300 \
  --model base-int8 --language en --device cpu --compute-type int8 --cpu-threads 4 \
  --data-dir data --download-dir data \
  --initial-prompt "Camper commands: awning, water pump, water heater, thermostat, power strip plug, Daisy, Nadine." > logs/whisper.log 2>&1 < /dev/null &
setsid ./venv-piper/bin/python -m wyoming_piper --uri tcp://0.0.0.0:10200 \
  --voice en_US-lessac-medium --data-dir data --download-dir data > logs/piper.log 2>&1 < /dev/null &
