#!/usr/bin/env python3
"""Create/update the camper gesture -> device automations in HA (idempotent: fixed ids).
  HA_TOKEN_FILE=... python3 ~/camper_ha/setup_gesture_automations.py
Gestures come from ~/camper_vision (event type camper_gesture, data.gesture = MediaPipe name).
"""
import json, os, urllib.error, urllib.request

HA = os.environ.get("HA_HTTP", "http://192.168.0.168:8123")
TOKEN = open(os.environ["HA_TOKEN_FILE"]).read().strip()

def gesture_auto(aid, alias, gesture, action, entity):
    return aid, {
        "id": aid, "alias": alias, "mode": "single",
        "description": f"Webcam gesture {gesture} (camper_vision on the Jetson) -> {action} {entity}",
        "triggers": [{"trigger": "event", "event_type": "camper_gesture",
                      "event_data": {"gesture": gesture}}],
        "conditions": [],
        "actions": [{"action": action, "target": {"entity_id": entity}}],
    }

AUTOMATIONS = [
    gesture_auto("camper_gesture_fan_on_point", "Gesture: Pointing Up -> Ceiling Fan On",
                 "Pointing_Up", "switch.turn_on", "switch.ceiling_fan"),
    gesture_auto("camper_gesture_fan_off_fist", "Gesture: Closed Fist -> Ceiling Fan Off",
                 "Closed_Fist", "switch.turn_off", "switch.ceiling_fan"),
    # Keurig is on the "Coffee pot" smart plug; its own automations turn it off after 30 min.
    gesture_auto("camper_gesture_keurig_on", "Gesture: Thumbs Up -> Keurig On",
                 "Thumb_Up", "switch.turn_on", "switch.smart_switch_1"),
    gesture_auto("camper_gesture_keurig_off", "Gesture: Thumbs Down -> Keurig Off",
                 "Thumb_Down", "switch.turn_off", "switch.smart_switch_1"),
]

# Removed at the user's request 2026-10-08 (thumbs up/down no longer control the fan).
REMOVED = ["camper_gesture_fan_on", "camper_gesture_fan_off"]

def call(method, aid, body=None):
    req = urllib.request.Request(f"{HA}/api/config/automation/config/{aid}",
                                 data=json.dumps(body).encode() if body else None, method=method,
                                 headers={"Authorization": f"Bearer {TOKEN}",
                                          "Content-Type": "application/json"})
    try:
        return urllib.request.urlopen(req, timeout=30).read().decode()
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}"

for aid in REMOVED:
    print("delete", aid, "->", call("DELETE", aid))

for aid, cfg in AUTOMATIONS:
    print(cfg["alias"], "->", call("POST", aid, cfg))
