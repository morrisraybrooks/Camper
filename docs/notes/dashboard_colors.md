# project-camper-dashboard-colors

> Camper dashboard visual rules - one "on" glow color per device on every page; peach section boxes; white inner cards

Consistency pass done 2026-10-25 (user: "make visually consistent throughout"). Rules in `camper.yaml`:
- Section boxes: `linear-gradient(160deg, #FDE9D9, #FBDFC4)`. Inner cards: `#FFFFFF`, border `#E3D9C7`. No blue section boxes.
- "On" glow is the same color for a device on every page: water pump blue `#4FA8D8`, lights (interior, porch) gold `#E8C563`, power-strip plugs pink `#DD6FA0`, water heater orange `#E8935A`, ceiling fan teal `#3FBCAE`.
- A blank white strip or missing beach photo for a second on page load is just card-mod templates loading slowly, not a bug in the YAML.

**How to apply:** when adding a card for a device that already appears elsewhere, copy that device's glow colors. Re-run the phone generator afterward ([[project-camper-phone-dashboard]]).
Backup: `claude_backups/dashboards__camper.yaml.bak-preclaude-unavailnote-*` (newest; the colormatch one is in /share/ha-cleanup-20261013/).

**Offline devices (2026-10-25):** don't let HA's yellow "Entity is currently unavailable" boxes show. Wrap the card in a `conditional` (`state_not: unavailable`) and add a matching conditional note card (`state: unavailable`). This is done for the Water tank gauges/Details rows and the Sequoia gauges, so they come back on their own once the hardware reports.
**Clutter:** the 16 old `*.bak-*` files that sat in `/homeassistant/dashboards/` were moved out (newest per file in `claude_backups`, older ones in `/share/ha-cleanup-20261013/` with a `dashboards__` prefix). Never leave a backup next to the original.
