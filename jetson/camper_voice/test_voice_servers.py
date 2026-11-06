#!/usr/bin/env python3
"""Self-test for the camper voice servers (no human needed).

1. Piper (:10200) speaks test phrases.
2. Whisper (:10300) transcribes them back -> compare text.
3. openWakeWord (:10400) must fire on a synthesized "okay nabu"
   (Piper's voice never scores on hey_jarvis; that one needs a real voice) and stay
   quiet on a non-wake phrase.

Run with the faster-whisper venv (it has the newest `wyoming` lib):
    ~/camper_voice/venv-faster-whisper/bin/python ~/camper_voice/test_voice_servers.py
Optional: --wav FILE  transcribe a recorded 16 kHz mono wav instead.
"""
import argparse
import asyncio
import audioop
import time
import wave

from wyoming.asr import Transcribe, Transcript
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.client import AsyncTcpClient
from wyoming.tts import Synthesize
from wyoming.wake import Detect, Detection, NotDetected

PIPER = ("127.0.0.1", 10200)
WHISPER = ("127.0.0.1", 10300)
WAKE = ("127.0.0.1", 10400)

PHRASES = [
    "What is the inside temperature?",
    "Turn on the water pump.",
    "Pull the awning in.",
]


async def tts(text):
    """Return (pcm16 mono bytes, rate)."""
    async with AsyncTcpClient(*PIPER) as c:
        await c.write_event(Synthesize(text=text).event())
        audio, rate, width, ch = b"", 22050, 2, 1
        while True:
            ev = await c.read_event()
            if ev is None:
                break
            if AudioStart.is_type(ev.type):
                s = AudioStart.from_event(ev)
                rate, width, ch = s.rate, s.width, s.channels
            elif AudioChunk.is_type(ev.type):
                audio += AudioChunk.from_event(ev).audio
            elif AudioStop.is_type(ev.type):
                break
    if ch == 2:
        audio = audioop.tomono(audio, width, 0.5, 0.5)
    if rate != 16000:
        audio, _ = audioop.ratecv(audio, width, 1, rate, 16000, None)
    return audio


async def stream(client, pcm, chunk=2048, realtime=False):
    # openWakeWord scores a rolling buffer in background threads, so audio
    # flooded faster than real time overwrites itself unscored -> realtime=True.
    await client.write_event(AudioStart(rate=16000, width=2, channels=1).event())
    for i in range(0, len(pcm), chunk):
        await client.write_event(
            AudioChunk(rate=16000, width=2, channels=1, audio=pcm[i:i + chunk]).event())
        if realtime:
            await asyncio.sleep(chunk / 2 / 16000)
    await client.write_event(AudioStop().event())


async def stt(pcm):
    async with AsyncTcpClient(*WHISPER) as c:
        await c.write_event(Transcribe(language="en").event())
        await stream(c, pcm)
        while True:
            ev = await c.read_event()
            if ev is None:
                return None
            if Transcript.is_type(ev.type):
                return Transcript.from_event(ev).text


async def wake(pcm):
    silence = b"\x00" * 16000  # 0.5 s padding each side
    async with AsyncTcpClient(*WAKE) as c:
        await c.write_event(Detect(names=["ok_nabu"]).event())
        await stream(c, silence + pcm + silence * 2, realtime=True)
        while True:
            ev = await asyncio.wait_for(c.read_event(), 10)
            if ev is None:
                return None
            if Detection.is_type(ev.type):
                return Detection.from_event(ev).name
            if NotDetected.is_type(ev.type):
                return None


def norm(s):
    return "".join(ch for ch in s.lower() if ch.isalnum() or ch == " ").split()


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wav")
    args = ap.parse_args()

    if args.wav:
        w = wave.open(args.wav)
        pcm = w.readframes(w.getnframes())
        t = time.time()
        print(f"transcript: {await stt(pcm)!r}  ({time.time() - t:.2f}s)")
        return

    ok = 0
    for p in PHRASES:
        pcm = await tts(p)
        t = time.time()
        text = await stt(pcm)
        dt = time.time() - t
        good = norm(text or "") == norm(p)
        ok += good
        print(f"[{'PASS' if good else 'FAIL'}] STT {dt:.2f}s  said={p!r} heard={text!r}")

    hit = await wake(await tts("Okay Nabu"))
    print(f"[{'PASS' if hit else 'FAIL'}] wake on 'Okay Nabu' -> {hit}")
    miss = await wake(await tts("Hello there, how are you doing today?"))
    print(f"[{'PASS' if not miss else 'FAIL'}] no wake on other speech -> {miss}")
    total = len(PHRASES) + 2
    print(f"\n{ok + bool(hit) + (not miss)}/{total} passed")


if __name__ == "__main__":
    asyncio.run(main())
