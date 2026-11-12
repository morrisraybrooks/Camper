-- 2026-10-21: never suspend the Bluetooth speaker output. Waking it took ~1 s,
-- so the voice satellite's short "listening" beep was lost.
table.insert(bluez_monitor.rules, {
  matches = { { { "node.name", "matches", "bluez_output.*" } } },
  apply_properties = { ["session.suspend-timeout-seconds"] = 0 },
})
