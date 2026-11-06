#!/usr/bin/env python3
"""Generate the satellite's chimes: sounds/awake.wav (rising) and sounds/done.wav (falling)."""
import math, struct, wave

def chime(path, freqs, note=0.12, rate=22050, vol=0.4):
    frames = b""
    for f in freqs:
        n = int(note * rate)
        for i in range(n):
            env = min(1, i / 200) * (1 - i / n) ** 1.5   # quick attack, soft decay
            frames += struct.pack("<h", int(32767 * vol * env * math.sin(2 * math.pi * f * i / rate)))
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(frames)

chime("sounds/awake.wav", [660, 880])
chime("sounds/done.wav", [880, 660])
print("wrote sounds/awake.wav sounds/done.wav")
