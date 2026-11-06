# project-camper-inverter

> User owns a Traveller 3000 W modified-sine inverter (model 1072569) and wants to add it to the camper; not installed as of 2026-11-01

Traveller "digital power inverter" 3000 W, model 1072569 (photos 2026-11-01). From the label: input 12.8 V DC 300 A; output 115 V AC 60 Hz, 3000 W continuous; USB 5 V 2.1 A; ETL to UL 458. Modified sine (label: "not sinusoidal", 30% THD). Neutral floating. Two +/- DC terminal pairs, chassis ground lug, two fans. Label bans rain exposure, zero-clearance mounting and compartments containing batteries.

Front panel: 3 household outlets, each next to a push-to-reset breaker (rating not visible); no hardwire AC terminals seen; displays for input V and output; USB; power button; RJ11-style "Remote On/Off" jack (pinout unknown, measure before connecting anything).

Manual read 2026-11-01, saved at ~/Documents/inverter/Traveller-1072569-3000W-Manual.pdf (source: Tractor Supply media.tractorsupply.com .../1072569_Man1.pdf). It says: both DC cable sets are REQUIRED; 1500 W max per outlet; 6000 W surge; input 11-15 V (alarm 11, cutoff 10.5, over-voltage cutoff above 15, damage above 16); operate only 32-104°F; 2 in. clearance; case can reach 140°F; no utility or branch-circuit connection; not in a compartment with batteries. It gives no fuse size, no remote jack pinout (switch not included), no idle draw. Its cable chart (6 AWG x2 at 3 ft) looks undersized for about 150 A per set; don't rely on it.

Not installed as of 2026-11-01. Still unknown: battery chemistry, intended loads.

**Why:** the single 100 Ah bank ([[project-camper-esp32-not-installed]]) can't supply 300 A, so the battery limits this inverter, not its 3000 W rating.

**How to apply:** plan around about 1000 W at most on the current bank unless it is upgraded. The inverter goes on the load side of the wall panel's 300 A shunt so HA sees its draw. Never feed the camper shore inlet or panel from it.

**Goal and plan (2026-11-01):** the user wants backup for grid hiccups at the current site (there since about Aug 2026). Battery is 100 Ah lead-acid (one battery, so about 50 Ah usable). Two DC cable sets came with the inverter; gauge not yet known. Recommended: UPS on Pi/router/gateway for blips (the inverter has no auto-switch), inverter by hand with cords for longer outages, stop at about 12.0 V. Roof A/C can't run on it. Still needed: cable gauge photo, inverter/battery location, whether a UPS was bought, whether the fridge needs AC.

**Outage evidence:** ODROID boot gaps since Sept show about 10 gaps of 3-57 min plus 9/27 (about 9 h) and 10/21 (about 4 h). These are unconfirmed as outages: logs can lose up to about 5 min, and the machine may not auto-restart. Only 10/24 ~13:20 and 10/31 ~20:18 also line up with a Pi restart (Pi data only goes back to 10/22).

**Install details (2026-11-01):** battery is on the camper tongue. Inverter location is the under-bed storage, which needs venting and clear space (2 in. minimum; label bans zero-clearance compartments). The included 3 ft cables were thin, so the user replaced them with thick 5 ft cables; gauge and number of sets not yet confirmed. Fuse size depends on that gauge.

**Guide built (2026-11-01):** cables are 2 AWG, two red and two black. ~/Desktop/Inverter-Install-Guide.pdf (15 landscape large-print pages); generator ~/Documents/inverter/build.py + render.py (python3.11). Design: 200 A ANL fuse on each red at the battery (Blue Sea 5005 holders), Blue Sea 6006 300 A switch under the bed, 6 AWG ground to frame. Not installed yet. Pure-copper check, UPS purchase and fridge type still unconfirmed.
