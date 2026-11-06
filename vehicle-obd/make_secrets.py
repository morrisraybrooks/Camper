# Writes src/secrets.h from the ESPHome secrets (Wi-Fi) and the cloudhook URL - never printed.
import os, re, sys
base = os.path.dirname(os.path.abspath(__file__))
# Where secrets.yaml and .sequoia_cloudhook_url live: $SECRETS_DIR, else ../esphome
# (this repo's layout), else .. (the old Pi layout, /config/esphome/sequoia_obd_fw).
sd = os.environ.get("SECRETS_DIR") or next(
    (d for d in (os.path.join(base, "..", "esphome"), os.path.join(base, ".."))
     if os.path.exists(os.path.join(d, "secrets.yaml"))), os.path.join(base, "..", "esphome"))
sec = open(os.path.join(sd, "secrets.yaml")).read()
def get(key):
    m = re.search(r"^%s:\s*\"?(.*?)\"?\s*$" % re.escape(key), sec, re.M)
    if not m: sys.exit("missing secret " + key)
    return m.group(1)
url = open(os.path.join(sd, ".sequoia_cloudhook_url")).read().strip()
esc = lambda s: s.replace("\\", "\\\\").replace('"', '\\"')
p = os.path.join(base, "src", "secrets.h")
open(p, "w").write(f'#pragma once\n#define WIFI_SSID "{esc(get("wifi_ssid"))}"\n#define WIFI_PASS "{esc(get("wifi_password"))}"\n#define HOOK_URL "{esc(url)}"\n')
os.chmod(p, 0o600)
print("secrets.h written")
