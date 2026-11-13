#!/usr/bin/env python3
"""Camper TTS front door on :10200 (added 2026-11-11).

- Voice "af_heart" (Kokoro, on the GPU) is spoken here.
- Every other voice (and no voice) is passed through to wyoming_piper on
  127.0.0.1:10202, so scripts/alerts that use the Piper default are unchanged.
Supports Wyoming streaming TTS (synthesize-start/chunk/stop) for both paths.
"""
import argparse, asyncio, logging, re, threading
import subprocess
import numpy as np
import onnxruntime as ort
from kokoro_onnx import Kokoro
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.client import AsyncTcpClient
from wyoming.event import Event
from wyoming.info import Attribution, Describe, Info, TtsVoice
from wyoming.server import AsyncEventHandler, AsyncServer
from wyoming.tts import (Synthesize, SynthesizeChunk, SynthesizeStart,
                         SynthesizeStop, SynthesizeStopped)

LOG = logging.getLogger("tts_proxy")
KOKORO_VOICES = {"af_heart": "Heart (Kokoro, natural female)"}
KOKORO_RATE = 24000
# 2026-11-12: Kokoro makes 24 kHz but the satellite now plays at 44100 Hz stereo (the Furrion sink rate) and its own converter
# (audioop, no filter) aliased the top end into crackle. Convert here with a proper
# low-pass (sox) so the satellite passes it through untouched.
RATE = 44100


def resample(x, src=KOKORO_RATE, dst=RATE):
    """High-quality rate change with sox (very-high quality, linear phase)."""
    x = np.asarray(x, dtype=np.float32)
    if src == dst or len(x) == 0:
        return x
    r = subprocess.run(["sox", "-q", "-t", "f32", "-r", str(src), "-c", "1", "-",
                        "-t", "f32", "-r", str(dst), "-c", "1", "-", "rate", "-v",
                        # 2026-11-12: trim hiss above 9 kHz; harsh Kokoro "s" sounds crackled over SBC Bluetooth
                        "sinc", "-9000"],
                       input=x.tobytes(), capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.float32)


SENT_END = re.compile(r"(.+?[.!?;:])(\s+|$)", re.S)

kokoro = None
gpu_lock = threading.Lock()


def load_kokoro(model, voices):
    global kokoro
    sess = ort.InferenceSession(model, providers=[
        ("CUDAExecutionProvider", {"arena_extend_strategy": "kSameAsRequested",
                                   "cudnn_conv_algo_search": "HEURISTIC"}),
        "CPUExecutionProvider"])
    kokoro = Kokoro.from_session(sess, voices)
    # 2026-11-12: warm up with a long sentence so the GPU memory arena is reserved at start-up
    # (a fresh start next to the LLM ran out of memory on the first real reply).
    kokoro.create("Good morning! The inside temperature is seventy three degrees, the humidity is "
                  "forty five percent, and it is sunny outside, so it should be a really nice day "
                  "for a walk with Daisy around the campground this afternoon.", voice="af_heart", lang="en-us")
    LOG.info("Kokoro ready on %s", sess.get_providers()[0])


def synth(text, voice, speed):
    with gpu_lock:
        audio, _sr = kokoro.create(text, voice=voice, speed=speed, lang="en-us")
    audio = resample(audio)
    return (np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes()


class Handler(AsyncEventHandler):
    def __init__(self, args, *a, **kw):
        super().__init__(*a, **kw)
        self.args = args
        self.piper = None
        self.relay = None
        self.mode = None          # None / "kokoro" / "piper" while streaming
        self.buf = ""
        self.started = False

    # ---------- piper pass-through ----------
    async def _piper(self):
        if self.piper is None:
            self.piper = AsyncTcpClient(self.args.piper_host, self.args.piper_port)
            await self.piper.connect()
            self.relay = asyncio.create_task(self._relay())
        return self.piper

    async def _relay(self):
        try:
            while True:
                ev = await self.piper.read_event()
                if ev is None:
                    break
                await self.write_event(ev)
        except Exception as e:  # noqa
            LOG.debug("relay ended: %s", e)
        finally:
            self.piper = None

    async def _to_piper(self, event):
        c = await self._piper()
        await c.write_event(event)

    # ---------- kokoro ----------
    async def _speak(self, text, voice):
        text = text.strip()
        if not text:
            return
        if not self.started:
            await self.write_event(AudioStart(rate=RATE, width=2, channels=1).event())
            self.started = True
        loop = asyncio.get_running_loop()
        pcm = None
        for attempt in (1, 2):
            try:
                pcm = await loop.run_in_executor(None, synth, text, voice, self.args.speed)
                break
            except Exception as e:  # GPU out of memory etc.
                LOG.error("Kokoro failed (try %d): %s", attempt, str(e)[:200])
                await asyncio.sleep(0.3)
        if pcm is None:
            pcm = await self._piper_pcm(text)
        step = 2048 * 2
        for i in range(0, len(pcm), step):
            await self.write_event(AudioChunk(rate=RATE, width=2, channels=1,
                                              audio=pcm[i:i + step]).event())

    async def _piper_pcm(self, text):
        """Backup: speak this sentence with the Piper voice, converted to RATE mono."""
        from wyoming.tts import Synthesize
        c = AsyncTcpClient(self.args.piper_host, self.args.piper_port)
        await c.connect()
        try:
            await c.write_event(Synthesize(text=text).event())
            buf, rate = b"", 22050
            while True:
                ev = await c.read_event()
                if ev is None or AudioStop.is_type(ev.type):
                    break
                if AudioChunk.is_type(ev.type):
                    ch = AudioChunk.from_event(ev)
                    rate, buf = ch.rate, buf + ch.audio
        finally:
            await c.disconnect()
        x = np.frombuffer(buf, "<i2").astype(np.float32) / 32767
        x = resample(x, src=rate, dst=RATE)
        LOG.info("spoke with Piper backup voice")
        return (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()

    async def _finish(self):
        if not self.started:
            await self.write_event(AudioStart(rate=RATE, width=2, channels=1).event())
        await self.write_event(AudioStop().event())
        self.started = False

    async def _flush_sentences(self, voice):
        while True:
            m = SENT_END.match(self.buf)
            # only cut when whitespace follows the punctuation (sentence surely ended)
            if not m or not m.group(2):
                return
            sent = m.group(1)
            self.buf = self.buf[m.end():]
            await self._speak(sent, voice)

    # ---------- events ----------
    async def handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            info = await self._piper_info()
            await self.write_event(info.event())
            return True

        if SynthesizeStart.is_type(event.type):
            s = SynthesizeStart.from_event(event)
            name = s.voice.name if s.voice else None
            if name in KOKORO_VOICES:
                self.mode, self.voice, self.buf = "kokoro", name, ""
            else:
                self.mode = "piper"
                await self._to_piper(event)
            return True
        if SynthesizeChunk.is_type(event.type):
            if self.mode == "kokoro":
                self.buf += SynthesizeChunk.from_event(event).text
                await self._flush_sentences(self.voice)
            else:
                await self._to_piper(event)
            return True
        if SynthesizeStop.is_type(event.type):
            if self.mode == "kokoro":
                await self._speak(self.buf, self.voice)
                self.buf = ""
                await self._finish()
                await self.write_event(SynthesizeStopped().event())
            else:
                await self._to_piper(event)
            self.mode = None
            return True

        if Synthesize.is_type(event.type):
            if self.mode == "kokoro":
                return True       # compatibility copy sent during streaming
            s = Synthesize.from_event(event)
            name = s.voice.name if s.voice else None
            if self.mode is None and name in KOKORO_VOICES:
                parts = [m.group(1) for m in SENT_END.finditer(s.text)]
                rest = SENT_END.sub("", s.text)
                for p in parts + [rest]:
                    await self._speak(p, name)
                await self._finish()
            else:
                await self._to_piper(event)
            return True

        if self.mode == "piper" or self.piper is not None:
            await self._to_piper(event)
        return True

    async def _piper_info(self):
        c = AsyncTcpClient(self.args.piper_host, self.args.piper_port)
        await c.connect()
        try:
            await c.write_event(Describe().event())
            while True:
                ev = await c.read_event()
                if ev is None or Info.is_type(ev.type):
                    break
        finally:
            await c.disconnect()
        info = Info.from_event(ev)
        attr = Attribution(name="hexgrad / thewh1teagle", url="https://github.com/thewh1teagle/kokoro-onnx")
        for prog in info.tts:
            for vid, desc in KOKORO_VOICES.items():
                prog.voices.append(TtsVoice(name=vid, description=desc, attribution=attr,
                                            installed=True, version="1.0", languages=["en_US"]))
        return info

    async def disconnect(self):
        if self.relay:
            self.relay.cancel()
        if self.piper:
            try:
                await self.piper.disconnect()
            except Exception:
                pass


async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--uri", default="tcp://0.0.0.0:10200")
    p.add_argument("--piper-host", default="127.0.0.1")
    p.add_argument("--piper-port", type=int, default=10202)
    p.add_argument("--model", default="data/kokoro/kokoro-v1.0.fp16.onnx")
    p.add_argument("--voices", default="data/kokoro/voices-v1.0.bin")
    p.add_argument("--speed", type=float, default=1.0)
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO)
    load_kokoro(args.model, args.voices)
    server = AsyncServer.from_uri(args.uri)
    LOG.info("listening on %s", args.uri)
    await server.run(lambda *a, **kw: Handler(args, *a, **kw))


if __name__ == "__main__":
    asyncio.run(main())
