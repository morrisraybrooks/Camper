#!/usr/bin/env python3
"""Register the Jetson's Wyoming voice services with Home Assistant and build a
local voice pipeline. Idempotent: skips entries/pipelines that already exist.

  HA_TOKEN_FILE=/path/to/token python3 ~/camper_ha/setup_voice_ha.py

- Wyoming entries: Whisper STT :10300, Piper TTS :10200, satellite :10700 on the Jetson.
- Pipeline "Camper Brain (Local)": conversation.camper_brain + local STT/TTS.
  The existing "Camper Brain" (HA Cloud STT/TTS) pipeline is left untouched.
- Points the satellite's pipeline select at the new pipeline.
"""
import json
import os
import time
import urllib.request

from ha_ws import HA

HA_HTTP = os.environ.get("HA_HTTP", "http://192.168.0.168:8123")
JETSON = os.environ.get("JETSON_IP", "192.168.0.173")
SERVICES = {10300: "Whisper", 10200: "Piper", 10700: "Satellite"}
PIPELINE = "Camper Brain (Local)"
TOKEN = open(os.environ["HA_TOKEN_FILE"]).read().strip()


def rest(path, body):
    req = urllib.request.Request(
        HA_HTTP + path, data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def main():
    ha = HA()
    have = {e.get("title") for e in ha.call({"type": "config_entries/get", "domain": "wyoming"})}
    print("existing wyoming entries:", have or "none")
    titles = {10300: "faster-whisper", 10200: "piper", 10700: "Camper Jetson"}

    for port, label in SERVICES.items():
        if titles[port] in have:
            print(f"{label:9s} :{port} -> already added")
            continue
        flow = rest("/api/config/config_entries/flow", {"handler": "wyoming", "show_advanced_options": False})
        res = rest(f"/api/config/config_entries/flow/{flow['flow_id']}", {"host": JETSON, "port": port})
        print(f"{label:9s} :{port} -> {res.get('type')} {res.get('title') or res.get('reason') or res.get('errors')}")

    time.sleep(5)  # let entities register
    states = ha.call({"type": "get_states"})
    ids = [s["entity_id"] for s in states]
    stt = next(e for e in ids if e.startswith("stt.") and "whisper" in e)
    tts = next(e for e in ids if e.startswith("tts.") and "piper" in e)
    print("stt:", stt, " tts:", tts)

    pl = ha.call({"type": "assist_pipeline/pipeline/list"})
    mine = next((p for p in pl["pipelines"] if p["name"] == PIPELINE), None)
    cfg = {
        "name": PIPELINE, "language": "en",
        "conversation_engine": "conversation.camper_brain", "conversation_language": "en",
        "prefer_local_intents": True,
        "stt_engine": stt, "stt_language": "en",
        "tts_engine": tts, "tts_language": "en_US", "tts_voice": "en_US-lessac-medium",
        "wake_word_entity": None, "wake_word_id": None,
    }
    if mine:
        print("pipeline exists:", mine["id"])
        pid = mine["id"]
    else:
        pid = ha.call(dict(cfg, type="assist_pipeline/pipeline/create"))["id"]
        print("created pipeline:", pid)

    sel = [s for s in states if s["entity_id"].startswith("select.") and s["entity_id"].endswith(("_assistant", "_pipeline"))
           and "camper_jetson" in s["entity_id"]]
    for s in sel:
        ha.call({"type": "call_service", "domain": "select", "service": "select_option",
                 "target": {"entity_id": s["entity_id"]}, "service_data": {"option": PIPELINE}})
        print("satellite pipeline select:", s["entity_id"], "->", PIPELINE)
    if not sel:
        print("no satellite pipeline select found yet; candidates:",
              [e for e in ids if e.startswith(("select.", "assist_satellite."))])


if __name__ == "__main__":
    main()
