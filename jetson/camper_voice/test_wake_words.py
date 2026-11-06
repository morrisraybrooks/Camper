#!/usr/bin/env python3
"""Feed Piper-spoken wake phrases to openWakeWord (:10400) in real time; print max score per model.
Needs the wake server started with --debug --debug-probability (scores are read from logs/oww.log).
Run: ~/camper_voice/venv-faster-whisper/bin/python ~/camper_voice/test_wake_words.py
"""
import asyncio, re
from wyoming.client import AsyncTcpClient
from wyoming.wake import Detect, Detection, NotDetected
from test_voice_servers import tts, stream, WAKE

CASES = {"hey_jarvis": "Hey Jarvis", "alexa": "Alexa", "hey_mycroft": "Hey Mycroft",
         "ok_nabu": "Okay Nabu", "hey_rhasspy": "Hey Rhasspy"}
LOG = "/home/morris/camper_voice/logs/oww.log"

async def run(model, phrase):
    pcm = await tts(phrase)
    start = len(open(LOG).read())
    async with AsyncTcpClient(*WAKE) as c:
        await c.write_event(Detect(names=[model]).event())
        await stream(c, b"\0" * 16000 + pcm + b"\0" * 32000, realtime=True)
        hit = None
        while True:
            ev = await asyncio.wait_for(c.read_event(), 10)
            if ev is None or NotDetected.is_type(ev.type):
                break
            if Detection.is_type(ev.type):
                hit = Detection.from_event(ev).name
                break
    await asyncio.sleep(0.5)
    probs = [float(p) for p in re.findall(r"probability=([0-9.e-]+)", open(LOG).read()[start:])]
    print(f"{model:12s} {phrase!r:16s} max={max(probs, default=0):.4f} detected={hit}")

async def main():
    for m, p in CASES.items():
        await run(m, p)

asyncio.run(main())
