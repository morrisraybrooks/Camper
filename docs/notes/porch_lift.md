# project-porch-lift

> DIY porch lift for Nadine (walker user) - bolt-together screw-drive design, guide PDF on Desktop

Started 2026-10-24. Nadine uses a walker/cane; the camper moves sometimes, so the lift must come apart; budget goal was under $1,000 (the design costs ~$1,450-1,800 for the lift plus $350-450 for the porch; told the user).
Design: 4x8 porch + bolt-together steel platform lift. A 1"-5 single-start ACME rod hangs from the mast top, the platform rides a bronze nut with a steel backup nut and switch, 12 V gearmotor (not worm) on #40 chain, hardwired relay safety chain (no ESP in it). A winch was refused for carrying a person.
Generator: ~/Documents/porch-lift-build/build.py -> guide.html -> `python3.11 render.py <abs html> <abs pdf> x` -> ~/Desktop/Porch-Lift-Build-Guide.pdf (18 pages).
Porch height measured 2026-10-24: P = 30" (guide updated). HA monitoring ESP32 is only an idea.
Related: [[user-low-vision]]

Firewood lift (2026-10-24): separate simplified goods-only lift for the BACK porch (assumed 30" too), for a hand truck of firewood. Guide ~/Desktop/Firewood-Lift-Build-Guide.pdf, generator ~/Documents/firewood-lift-build (build.py + render.py, same as porch). User asked for a "winch": designed with a 120 V electric HOIST (440/880 lb, double-line pulley), not an ATV pulling winch. Platform 36x30, park pins at the top, lockout switch, NO RIDERS. About $800-1,050.
