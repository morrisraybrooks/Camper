# jetson-ai-agent

> NVIDIA Jetson Orin running SD image generator and local AI agent on the local network

Jetson Orin Super device running JetPack 6 with CUDA 12.6. **Since 2026-10-23: wired to the router at 192.168.0.173 (static on enP8p1s0; Wi-Fi autoconnect off). 10.0.0.2 / the ODROID direct link is GONE — SSH morris@192.168.0.173 (or `ssh jetson`).** The old 192.168.55.1 USB address is gone too. Previously was at 10.0.0.2 via direct link on enp2s0 from the Odroid H3, but after JetPack downgrade it moved to main LAN.
**2026-10-28:** ODROID /etc/fstab sshfs mount (~/jetson) and /etc/hosts `jetson` entry switched from 10.0.0.2 to 192.168.0.173 (the old address made ~/jetson hang). Backups /etc/fstab.bak-preclaude-jetsonip-*, /etc/hosts.bak-preclaude-jetsonip. Use 192.168.0.173 for every 10.0.0.2 URL below.

**Why:** Local AI/image generation, no cloud required.

**How to apply:** When user references "the Jetson", this is what they mean. SSH as morris@10.0.0.2 (passwordless key set up). Use `sshpass -p [REDACTED]` if key ever fails.

## Network
- Main access: 10.0.0.2 (direct link via enp2s0 on Odroid H3, 10.0.0.1 on Odroid side)
- USB NIC (192.168.55.x) no longer present as of May 2026 network rework
- SSH: morris@10.0.0.2, password: [REDACTED], passwordless key installed
- sudo: passwordless sudo configured via /etc/sudoers.d/morris-nopasswd

## Services
- **LLM Chat Server:** http://10.0.0.2:5003 — served by `jetson-llm.service` (systemd)
  - Script: /home/morris/jetson_llm/llm_server.py (python process pid ~815 at boot)
  - Venv: /home/morris/jetson_ui/.venv
- SD image generator also runs on the Jetson (:5002), unrelated to the camper.

## Status as of 2026-10-01
- Jetson also on home WiFi (TP-Link_2.4) at 192.168.0.173 (wlP1p1s0); direct link 10.0.0.2 still works. ODROID LAN is 192.168.0.169.
- Running: jetson-ui (:5002), mosquitto (:1883, :9001), smbd (shares `morris`=/home/morris, `jetson-root`=/).
- jetson-llm.service (:5003) is disabled/inactive. Tailscale not installed on Jetson or ODROID.
- Phone-access guide written to ~/Desktop/jetson info.md on the ODROID.

## LLM services added 2026-10-02
- **granite-llm.service** (enabled, running): llama-server CUDA, Granite 4.0 h-micro Q4_K_M (~2.7 GB RAM), 127.0.0.1:8090 only (OpenAI-compatible + built-in web UI). Reach from ODROID via `ssh -N -L 8090:localhost:8090 morris@10.0.0.2`.
- **needle3.service** (installed, disabled/stopped): Cactus Needle3 tool-call model, CPU, `--serve --port 8091`, files in ~/needle3 (tools.json, ext.json, compare.py). User said keep all files; don't delete.
- Head-to-head 2026-10-02: Granite 9/9 tool calls (~2-4 s), Needle3 5/9 (~0.5 s). User prefers Granite.
- Gotcha: `pkill -f "llama-server.*granite"` inside an ssh command kills the ssh shell itself (pattern matches its own cmdline).

## HA voice brain (2026-10-04)
- llama-server on Jetson now serves model `camper-brain` at http://192.168.0.173:8090/v1 (LAN-reachable, not just localhost).
- HA (Pi) has core `llama_cpp` integration pointed there; agent entity `conversation.camper_brain`, Assist API ("Control Home Assistant") on. Both assist pipelines ("Home Assistant", "Home Assistant Cloud") use it with prefer_local_intents=true. Replies take ~12-26 s.
- Exposed entities got plain aliases (Thermostat, Water Pump, Water Heater, Power Strip, …); orphan `switch.tp_link_power_strip_63ce_light` unexposed. Backups `*.bak-preclaude-camperbrain-*` in /homeassistant/.storage.
- Router DHCP reservations done 2026-10-04 (see project_pi_haos).

## Chat web UI tuned (2026-10-05)
- camper-brain.service now runs `-c 16384 --parallel 2`: two 8k slots, one for HA and one for the web UI chat, so they don't block each other. Free memory went up to about 1.85 GB.
- `--ui-config-file /home/morris/camper-brain-ui.json` sets server-side defaults for every browser on the web UI at http://192.168.0.173:8090. It includes a system message about Morris, Nadine, Daisy and their schedules, with step-by-step and honesty guidance. `custom` = chat_template_kwargs enable_thinking=true, so thinking is on for the web UI only. Sampling: temp 0.6, top_p 0.95, top_k 20, min_p 0, presence 1.0, max_tokens 6000, show thoughts.
- `--reasoning-budget 400` plus a wrap-up message keeps thinking chats around 30 s instead of 2+ min. Qwen3.5 4B overthinks badly without it. HA is unaffected because its requests have thinking off (`--reasoning off` default).
- Web UI settings keys live in the bundle's `St` map (systemMessage, custom, temperature, …). A user's own localStorage settings may override the server defaults.
- Unit backup: /etc/systemd/system/camper-brain.service.bak-preclaude-chatui-*

## Sampling fix (2026-10-08)
- Chrome on ODROID had `LlamaUi.userOverrides` listing every sampler with blank values, so server ui-config defaults were ignored and llama.cpp stock values (temp 0.8/top_k 40/min_p 0.05) were used. Cleared it to `[]` (backup in localStorage `*.bak-claude`).
- camper-brain.service now also has `--temp 0.6 --top-k 20 --top-p 0.95 --min-p 0` (server-wide, HA included; presence left 0 server-side). Unit backup `*.bak-preclaude-sampling-*`.
- Restarts used to fail ~10x with `cudaMalloc failed` (495 MiB compute buffer): --no-mmap load filled ~2.7 GB page cache that nvmap couldn't reclaim. Fixed by adding `--direct-io` (unit backup `*.bak-preclaude-frag-*`): 4/4 restarts in 13-17 s, 0 failures. Fallback if it returns: `-ub 256`.
- Gen speed ~14.8 tok/s (Qwen3.5 4B Q4_K_M, llama.cpp b9282); Jetson already MAXN_SUPER + jetson_clocks.

## Scrypted removed (2026-10-08)
- At the user's request ("fuck scrypted"; they don't want Scrypted anywhere). It was installed 2026-06-13 (`npx scrypted serve`, scrypted.service) with plugins arlo, core, mqtt, prebuffer-mixin, snapshot, webrtc and scrypted-kasa.
- Stopped and disabled. The unit file, ~/.scrypted and the npx cache were deleted. About 400 MB RAM freed (available went 1.5 to 1.9 GB).
- Settings DB kept at ~/backups/scrypted-settings-20261008.tar.gz (12 MB).
- Don't suggest Scrypted again. Arlo cameras are to go into HA via the aarlo HACS integration (direct to Arlo cloud).

## Image generator vs Camper Brain (confirmed 2026-10-16)
- jetson-ui.service has `Conflicts=camper-brain.service` + `ExecStopPost` that restarts the brain, so only one runs at a time (GPU/RAM). While the image generator is on, HA's voice/Camper Brain is offline and `sensor.camper_brain_status` goes unavailable.
- 2026-10-16: the user started image gen at 4:22 AM, a 50-image batch finished 6:00 AM, then it sat idle until they stopped it at 2:25 PM; the brain was down ~10 h. Fixed with an idle auto-stop (below).
- Jetson journal times are local (UTC-4); reach it via `ssh morris@10.0.0.2` (192.168.0.173 host key isn't in known_hosts from the ODROID).
- **Idle auto-stop (2026-10-16):** `/usr/local/bin/sd-idle-stop` run by `sd-idle-stop.timer` (every 5 min, enabled). If jetson-ui has been up 30+ min, no batch is running (`GET :5002/api/sd/batch` running:true), and the last 30 min of its journal has no POST/PUT/DELETE or Generating/Saved/Batch/Starting sd-server/PhotoMaker/ESRGAN lines, it stops jetson-ui (ExecStopPost brings camper-brain back) and logs via `logger -t sd-idle-stop`. The page's 3-s GET polling doesn't count as activity. The user restarts image gen from the Jetson Monitor app (~/Desktop/jetson-monitor, ServicePanel for jetson-ui.service).

## Chat page date + quick answers (2026-10-16)
- camper-brain.service now has `--chat-template-file /home/morris/camper-brain-template.jinja`: the model's own Qwen3.5 template (from /props) with two changes, both ONLY when no tools are sent (HA always sends tools, so HA voice is unchanged):
  - The live date/time is stamped at the end of the system message via `strftime_now` (llama.cpp's jinja sets current_time per render; the Jetson's TZ is America/New_York).
  - Quick-answer rule: if the system message contains "You are Camper Brain" and the last user message is <60 chars with no digits, the template emits an empty `<think></think>`, so no thinking. Greeting went 32 s → 2 s; math still thinks.
- Gotchas: this jinja engine can't loop over a string (use a list). llama.cpp test-renders the template at startup to build its parser; a bad template means the server never comes up (`common_chat_verify_template` error), so keep v1 handy. The rule is gated on the Camper Brain system text so startup test renders aren't affected.
- camper-brain-ui.json systemMessage: "today's date is given at the end" and "keep thinking to 1-2 lines for greetings". Backups: `~/camper-brain-ui.json.bak-preclaude-date-*`, `/etc/systemd/system/camper-brain.service.bak-preclaude-date-*`; date-only template at ~/camper-brain-template.jinja.bak-v1-dateonly.
- Seen while testing (2026-10-16, not fixed): HA voice answers for camper temperature vary (68/70/72 while the thermostat read 72). This is the small model picking the wrong number, and it's unrelated to the template change.

## Chat page → HA control via MCP (2026-10-16)
- HA: `mcp_server` integration added (entry 01M531FXJPQCAHXF62EW9CAYTK, "All LLM APIs" = only Assist exists; require_admin on). Endpoint http://192.168.0.168:8123/api/mcp (Streamable HTTP), 401 without a token.
- Jetson: camper-brain.service now has `--ui-mcp-proxy` (/cors-proxy?url=…; forwards headers). camper-brain-ui.json presets `mcpServers` (id camper-ha, name "Camper (Home Assistant)", useProxy true, no headers); the user adds header `Authorization: Bearer <long-lived token>` themselves in the chat page's MCP Servers → edit → Custom Headers, then toggles it on.
- Template rebuilt (mk_tmpl3): chat page detected by "You are Camper Brain, a friendly" in the system message (HA's prompt is "…, the voice assistant…"), NOT by absence of tools, so the date + quick answers also work with MCP tools. The quick rule uses messages[ns.last_query_index].
- The systemMessage now tells it to use the HA tools (GetLiveContext once, inside temp = Thermostat Temperature sensor, don't change the thermostat/water heater/gas/awning unless clearly asked).
- ODROID Chrome localStorage had `systemMessage: ""` in userOverrides (cleared by someone after 10-08), so the persona was off there. Restored from /props ui_settings; backups `LlamaUi.config.bak-claude-mcp`, `LlamaUi.userOverrides.bak-claude-mcp`.
- Backups: `*.bak-preclaude-mcp-*` (ui json, template, unit).
- **Key relay (2026-10-16, replaces pasting the key):** the user couldn't get the key pasted into Custom Headers, and I may not enter keys into web pages. So `ha-mcp-relay.service` (enabled) runs `/home/morris/ha_mcp_relay.py` on **127.0.0.1:8124 only**. It forwards only `/api/mcp` to HA (others → 404) and adds `Authorization: Bearer` from `~/.config/ha-mcp-token` (600). That token is "Camper Brain chat", created by the user 2026-10-16. The chat page's server URL is now `http://127.0.0.1:8124/api/mcp` with "Use llama-server proxy" on and no headers, both in ODROID Chrome and in the ui-config default. Verified in Chrome: 26 tools; "Is the ceiling fan on?" → correct answer.
- Note: anyone on the LAN who opens the chat page can now use the Assist tools (no key needed). The chat page asks "Allow once / Always allow" before each tool. The MCP GetLiveContext takes a `domain` filter; the model sometimes guesses the wrong domain (fan vs switch) and retries.

## Moved to wired LAN (2026-10-23)
- Why: Jetson Wi-Fi stalled (associated, 0 packets) right after its BT adapter was powered on; HA lost VLC/voice. The user moved the Jetson's cable from the ODROID's enp2s0 to the router.
- "Wired connection 1" = manual 192.168.0.173/24, gw/DNS 192.168.0.1 (+8.8.8.8), metric 100. TP-Link_2.4 Wi-Fi: autoconnect no (still configured; router DHCP reservation for .173 is the Wi-Fi MAC). NM backup /root/nm-backup-20261023.
- HA needed no address changes (all used .173); reloaded vlc_telnet + wyoming entries. ODROID ~/.ssh/config `Host jetson` → 192.168.0.173 (backup .bak-preclaude-jetsonwired-20261023); ~/.config/jetson-monitor.conf host=morris@192.168.0.173.

2026-10-23 speed-up: camper-brain (Qwen3.5 hybrid) was fully re-reading its ~5.5k-token prompt on every new question (11–15 s), because checkpoints were made only every 8192 tokens. Changed /etc/systemd/system/camper-brain.service to `--ctx-checkpoints 12 --checkpoint-every-n-tokens 1024` (was `--ctx-checkpoints 4`). Backup: ~/camper-brain.service.bak-preclaude-checkpoints-20261023. Questions now take about 5–7 s once warm. Each of the 2 slots is cold on its first use after a restart (about 17–25 s). Memory: about 600 MB available, zram barely used; watch for OOM.

