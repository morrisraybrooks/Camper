#!/usr/bin/env python3
"""Add a Ping (WiFi) home/away tracker for a phone and attach it to an HA person, alongside GPS.
Idempotent. Reserve the phone's IP in the TP-Link router or this breaks when DHCP changes it.

  HA_TOKEN_FILE=... python3 ~/camper_ha/setup_wifi_presence.py person.nadine 192.168.0.133

Caveat: a dead phone answers neither GPS nor ping. This only covers a live phone whose app's
GPS is stale/asleep. Android dozes and skips pings, so consider_home is long (10 min).
"""
import json, os, sys, time, urllib.request

from ha_ws import HA

HA_HTTP = os.environ.get("HA_HTTP", "http://192.168.0.168:8123")
TOKEN = open(os.environ["HA_TOKEN_FILE"]).read().strip()
CONSIDER_HOME_S = 600


def rest(path, body):
    req = urllib.request.Request(HA_HTTP + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {TOKEN}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def main(person_id, ip):
    ha = HA()
    entry = next((e for e in ha.call({"type": "config_entries/get", "domain": "ping"})
                  if e["title"] == ip), None)
    if entry:
        entry_id = entry["entry_id"]
        print("ping entry exists:", ip)
    else:
        flow = rest("/api/config/config_entries/flow", {"handler": "ping"})
        res = rest(f"/api/config/config_entries/flow/{flow['flow_id']}", {"host": ip})
        entry_id = res["result"]["entry_id"]
        print("ping entry created:", ip, res.get("type"))

    # consider_home: how long a phone may miss pings before it counts as away
    flow = rest(f"/api/config/config_entries/options/flow", {"handler": entry_id})
    fields = {f["name"] for f in flow.get("data_schema") or []}
    want = {"count": 5, "consider_home": CONSIDER_HOME_S}
    res = rest(f"/api/config/config_entries/options/flow/{flow['flow_id']}",
               {k: v for k, v in want.items() if k in fields})
    print("option fields offered:", sorted(fields))
    print("options:", res.get("type"), res.get("data"))

    time.sleep(3)
    reg = ha.call({"type": "config/entity_registry/list"})
    tracker = next(e for e in reg if e["config_entry_id"] == entry_id
                   and e["entity_id"].startswith("device_tracker."))
    if tracker.get("disabled_by"):
        ha.call({"type": "config/entity_registry/update", "entity_id": tracker["entity_id"],
                 "disabled_by": None})
        print("enabled", tracker["entity_id"], "(HA reloads the entry in ~30 s)")

    people = ha.call({"type": "person/list"})["storage"]
    p = next(x for x in people if f"person.{x['id']}" == person_id
             or f"person.{x['name'].lower()}" == person_id)
    trackers = list(p.get("device_trackers") or [])
    if tracker["entity_id"] not in trackers:
        trackers.append(tracker["entity_id"])
        ha.call({"type": "person/update", "person_id": p["id"], "name": p["name"],
                 "user_id": p.get("user_id"), "picture": p.get("picture"),
                 "device_trackers": trackers})
    print(person_id, "trackers ->", trackers)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
