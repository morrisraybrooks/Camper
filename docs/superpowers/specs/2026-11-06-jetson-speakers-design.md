# Jetson speakers: Furrion stereo first, W-KING D8 fallback (short design)

**Intent:** Jarvis replies and camper music (Jetson VLC) should play on the camper's built-in
Furrion DV3100 stereo. When the stereo is off, use the W-KING D8 indoor speaker. The ECOXGEAR is
the user's outdoor speaker and must not be used by the Jetson any more. Keep the W-KING charged
automatically through a smart plug.

**Goals:** Furrion preferred whenever connected; automatic switch to the W-KING and back;
W-KING never runs flat; no new walking for the user beyond pairing each speaker once.
**Non-goals:** Changing the Pi's media setup, the outdoor ECOXGEAR, or the voice pipeline.
**Anti-goals:** Furrion hands-free (HFP) setup, which made it drop the Pi in Oct 2026; leaving the
W-KING on the charger 24/7; the Pi stealing the Furrion connection.

**Approaches considered:**
- Battery-driven plug (chosen first): read the W-KING battery over HFP (BlueZ battery provider);
  plug on at 25%, off at 100%.
- Timer plug (fallback, if the D8 doesn't report battery): plug on ~2 h per day.
- Always on the charger: rejected, wears the battery.

**Decided:** Furrion is paired to the Jetson with A2DP only and removed from the Pi.
speaker-reconnect.sh is priority Furrion > W-KING; ECOXGEAR is removed from the rotation.
The plug is the spare Kasa HS105 (switch.kasa_hs105_spare).
**Left to the builder:** how the battery reaches HA, and the exact thresholds and timer.
