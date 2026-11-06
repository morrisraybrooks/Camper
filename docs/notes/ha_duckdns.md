# project-camper-ha-duckdns

> Exposing camper's Home Assistant via DuckDNS - setup status and findings

Goal: expose camper's Home Assistant (http://192.168.0.168:8123/lovelace-camper/camper, on LAN via WiFi) to the internet via DuckDNS. Was working before, broke after the camper moved (new location/network).

**Findings so far (2026-09-06):**
- HA reachable locally: `curl http://192.168.0.168:8123/` → 200 OK.
- Camper's current public IP: 172.58.250.142 — in T-Mobile's carrier range, strongly suggesting the camper is now on **cellular data (T-Mobile) behind CGNAT**.
- Router/gateway at 192.168.0.1 responds to HTTP (admin page reachable), needs login to inspect.
- If CGNAT is confirmed, port forwarding on the router CANNOT work — the router itself has no public-facing IP, so no forwarded port is reachable from the internet. This is the likely reason it stopped working after the move (probably was on a home ISP/WiFi before, with a real public IP).

**Next steps:**
1. Log into router at 192.168.0.1 to confirm WAN IP type and check/set port forwarding (8123 or 443 → 192.168.0.168).
2. If CGNAT confirmed: port forwarding won't work. Alternative: use a tunnel instead of port-forward + DuckDNS, e.g. Cloudflare Tunnel or Tailscale Funnel — no inbound ports needed, works over CGNAT/cellular.
3. If NOT CGNAT (real public IP available): proceed with DuckDNS add-on (if HAOS/Supervised) or manual cron update, port-forward 443→8123, and Let's Encrypt/NGINX proxy add-on for HTTPS.

**Backup encryption key (2026-09-06):** `YG7Z-GS66-WK6D-S4S3-NR06-OG26-VHIW` — needed to restore any HA backup created from this point forward. Keep this secure; without it, backups cannot be restored. An "emergency kit" file was also downloaded from the HA UI at backup setup time.

**HA config confirmed (2026-09-06):**
- HA is HAOS (has Supervisor, network interface config for eth0/wlan0) — not Core/Container as initially guessed.
- `configuration.yaml` has `http:` → `external_url: https://homeassistanthomesc.duckdns.org` and `internal_url: http://192.168.0.168:8123` already correctly set (confirmed via masked UI field pattern matching).
- These settings are manually specified in YAML (not editable via UI) — instance is heavily manually configured, user used AI to configure it, wants a full backup + bug audit.
- Existing manual backup: 1.14 MB, no automatic backups configured. In progress: creating a fresh full manual backup via Settings > Backups.

Related: [[project_jetson]] (other home network device, same LAN presumably).

**Update 2026-10-11:**
- CGNAT confirmed: TP-Link router (192.168.0.1) WAN is 192.168.12.141, so it's double-NATed behind a T-Mobile gateway. Public IP rotates (172.58/172.59.x). DuckDNS + port forwarding can't work here.
- **Tailscale add-on is installed and running on the Pi**: tailnet IP `100.x.x.x (Tailscale IP)` (hostname `homeassistant`). Remote access = connect phone to Tailscale, open http://100.x.x.x (Tailscale IP):8123. Phone `morriss-s22` was offline in the tailnet for 49 days.
- Funnel (`share_homeassistant`) is disabled; turn it on if a public URL without the Tailscale app is ever needed.
- Debug tip: the Tailscale CLI is `/opt/tailscale` inside the docker container `app_a0d7b954_tailscale` (needs sudo docker exec). For `ha` CLI over SSH, export SUPERVISOR_TOKEN from /run/s6/container_environment/SUPERVISOR_TOKEN.
- On 2026-10-11, HA was briefly unreachable even on the LAN during a core update (2026.10.0→.1): the image download took about 11 minutes over cellular, then core was down for about 4 minutes.
