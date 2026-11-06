#!/usr/bin/env python3
"""Run the "Camper Brain (Local)" pipeline from text (intent -> tts) through HA and
report each stage, proving HA <-> Jetson Piper and the brain work together.
  HA_TOKEN_FILE=... python3 ~/camper_ha/test_voice_pipeline.py ["question"]
"""
import json, sys, time
from ha_ws import HA

q = sys.argv[1] if len(sys.argv) > 1 else "What is the inside temperature?"
ha = HA()
pid = next(p["id"] for p in ha.call({"type": "assist_pipeline/pipeline/list"})["pipelines"]
           if p["name"] == "Camper Brain (Local)")
ha.n += 1
ha.ws.send(json.dumps({"id": ha.n, "type": "assist_pipeline/run", "pipeline": pid,
                       "start_stage": "intent", "end_stage": "tts", "input": {"text": q}}))
t0 = time.time()
while True:
    r = json.loads(ha.ws.recv())
    if r.get("type") != "event":
        continue
    ev = r["event"]; d = ev.get("data") or {}
    t = f"{time.time() - t0:5.2f}s"
    if ev["type"] == "intent-end":
        print(t, "answer:", d["intent_output"]["response"]["speech"]["plain"]["speech"])
    elif ev["type"] == "tts-end":
        print(t, "tts audio:", d["tts_output"].get("url"))
    elif ev["type"] == "error":
        print(t, "ERROR:", d); break
    elif ev["type"] == "run-end":
        print(t, "done"); break
