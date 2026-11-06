#!/usr/bin/env python3
"""Mic command for wyoming_satellite: runs arecord on the Brio and passes the
audio straight through to stdout (the satellite), and also sends a copy over
UDP to 127.0.0.1:10777 for sound_watch.py (smoke alarm / barking). The UDP copy
is fire-and-forget, so the voice assistant keeps working if sound_watch is
down. Added 2026-10-23."""
import signal, socket, subprocess, sys

ARECORD = ["arecord", "-D", "plughw:CARD=B100,DEV=0", "-r", "16000", "-c", "1",
           "-f", "S16_LE", "-t", "raw", "-q"]
proc = subprocess.Popen(ARECORD, stdout=subprocess.PIPE)
signal.signal(signal.SIGTERM, lambda *_: (proc.terminate(), sys.exit(0)))
udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp.setblocking(False)
out = sys.stdout.buffer
try:
    while True:
        chunk = proc.stdout.read1(2048)
        if not chunk:
            break
        out.write(chunk)
        out.flush()
        try:
            udp.sendto(chunk, ("127.0.0.1", 10777))
        except OSError:
            pass
except (BrokenPipeError, KeyboardInterrupt):
    pass
finally:
    proc.terminate()
