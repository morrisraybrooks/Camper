"""Tiny Home Assistant websocket client.
Token is read from $HA_TOKEN_FILE (never hard-coded). Usage as a module:
    from ha_ws import HA; ha = HA(); ha.call({'type': 'config_entries/subentries/list', 'entry_id': ...})
or from the shell:  python3 ha_ws.py '{"type":"assist_pipeline/pipeline/list"}'"""
import json, os, sys, websocket
URL = os.environ.get('HA_URL', 'ws://192.168.0.168:8123/api/websocket')
class HA:
    def __init__(self):
        tok = open(os.environ['HA_TOKEN_FILE']).read().strip()
        self.ws = websocket.create_connection(URL, timeout=60); self.ws.recv()
        self.ws.send(json.dumps({'type': 'auth', 'access_token': tok}))
        r = json.loads(self.ws.recv())
        if r.get('type') != 'auth_ok': raise SystemExit(f'auth failed: {r}')
        self.n = 0
    def call(self, msg):
        self.n += 1; msg = dict(msg, id=self.n); self.ws.send(json.dumps(msg))
        while True:
            r = json.loads(self.ws.recv())
            if r.get('id') == self.n and r.get('type') == 'result':
                if not r.get('success'): raise RuntimeError(f"{msg['type']}: {r.get('error')}")
                return r.get('result')
if __name__ == '__main__':
    print(json.dumps(HA().call(json.loads(sys.argv[1])), indent=1))
