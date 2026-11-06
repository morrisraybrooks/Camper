#!/usr/bin/env python3
"""Create/update "Keurig: Start on Wake-Up Motion" in HA (idempotent: fixed id).
  HA_TOKEN_FILE=... python3 ~/camper_ha/setup_keurig_morning.py

Morris works nights (Sun-Wed, Thu if overtime), gets home ~4 AM, alarm 2 PM, but is usually up
earlier: bathroom first, then coffee. First Aqara motion between 11:00 and 14:30 on a work day
turns the Keurig ("Coffee pot" plug) on. Mon-Fri only after Nadine has left (so it is Morris
up, not her); Sunday any motion. Once per day; skipped if the Keurig is already on.
The existing "Keurig: Auto-Off After 30 Minutes" still turns it off.
"""
import json, os, urllib.request

HA = os.environ.get("HA_HTTP", "http://192.168.0.168:8123")
TOKEN = open(os.environ["HA_TOKEN_FILE"]).read().strip()
AID = "keurig_wake_up_motion"

CONFIG = {
    "id": AID,
    "alias": "Keurig: Start on Wake-Up Motion",
    "description": "First motion between 11:00 AM and 2:30 PM on a work day turns the Keurig on "
                   "(Morris gets up before his 2 PM alarm: bathroom, then coffee). Weekdays only after Nadine "
                   "has left for child care; Sundays any motion. Once a day.",
    "mode": "single",
    "triggers": [{"trigger": "state", "entity_id": "binary_sensor.lumi_lumi_sensor_motion_aq2",
                  "to": "on"}],
    "conditions": [
        {"condition": "time", "after": "11:00:00", "before": "14:30:00"},
        {"condition": "or", "conditions": [
            {"condition": "time", "weekday": ["sun", "mon", "tue", "wed"]},
            {"condition": "and", "conditions": [
                {"condition": "time", "weekday": ["thu"]},
                {"condition": "state", "entity_id": "input_boolean.camper_overtime_thursday",
                 "state": "on"}]}]},
        # Only Morris's motion: on Nadine's work days (Mon-Fri, leaves ~noon) wait until she's gone.
        # She's off on Sunday and may be home all day, so any motion counts then.
        {"condition": "or", "conditions": [
            {"condition": "not", "conditions": [
                {"condition": "state", "entity_id": "person.nadine", "state": "home"}]},
            {"condition": "time", "weekday": ["sat", "sun"]}]},
        {"condition": "state", "entity_id": "switch.smart_switch_1", "state": "off"},
        # once per day: this automation hasn't already run today
        {"condition": "template", "value_template":
            "{% set t = state_attr(this.entity_id, 'last_triggered') %}"
            "{{ t is none or as_local(t).date() < now().date() }}"},
    ],
    "actions": [{"action": "switch.turn_on", "target": {"entity_id": "switch.smart_switch_1"}}],
}

req = urllib.request.Request(f"{HA}/api/config/automation/config/{AID}",
                             data=json.dumps(CONFIG).encode(), method="POST",
                             headers={"Authorization": f"Bearer {TOKEN}",
                                      "Content-Type": "application/json"})
print(CONFIG["alias"], "->", urllib.request.urlopen(req, timeout=30).read().decode())
