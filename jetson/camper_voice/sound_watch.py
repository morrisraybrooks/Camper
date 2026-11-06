#!/usr/bin/env python3
"""Listens to the Brio mic (a copy sent by mic_tee.py over UDP) with YAMNet and
tells Home Assistant when it hears a smoke/CO alarm or a lot of barking.
HA decides whether to alert (only while Daisy is home alone). Nothing is
recorded; only the sound labels and scores are logged, to logs/sound_watch.log,
for tuning. Added 2026-10-23."""
import collections, json, logging, os, socket, time, urllib.request
import numpy as np
from ai_edge_litert.interpreter import Interpreter

HA = "http://192.168.0.168:8123/api/webhook/"
# The two webhook IDs (they match automations.yaml's sound_*_webhook_id secrets) are kept
# out of the code, in a private file with two lines:  smoke=<id>  and  bark=<id>
HOOKS_FILE = os.environ.get("SOUND_HOOKS_FILE", os.path.expanduser("~/.config/camper-sound-hooks"))
_hooks = dict(line.strip().split("=", 1) for line in open(HOOKS_FILE) if "=" in line)
SMOKE_HOOK, BARK_HOOK = _hooks["smoke"], _hooks["bark"]
SMOKE_IDS = [393, 394]                 # Smoke detector / Fire alarm
BARK_IDS = [69, 70, 71, 72, 73, 74]    # Dog, Bark, Yip, Howl, Bow-wow, Growling
SMOKE_SCORE, SMOKE_HITS, SMOKE_WINDOW, SMOKE_COOLDOWN = 0.25, 8, 20, 600
BARK_SCORE, BARK_HITS, BARK_WINDOW, BARK_COOLDOWN = 0.40, 40, 300, 1800
HOP = 0.5                              # seconds between checks

logging.basicConfig(filename="/home/morris/camper_voice/logs/sound_watch.log",
                    format="%(asctime)s %(message)s", level=logging.INFO)
log = logging.getLogger()

interp = Interpreter("/home/morris/camper_voice/models/yamnet.tflite")
interp.allocate_tensors()
inp = interp.get_input_details()[0]["index"]
outp = interp.get_output_details()[0]["index"]


def post(hook, data):
    try:
        req = urllib.request.Request(HA + hook, data=json.dumps(data).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=10).read()
        log.info("SENT %s %s", hook, data)
    except Exception as e:
        log.info("SEND FAILED %s %s", hook, e)


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("127.0.0.1", 10777))
sock.settimeout(5)
buf = np.zeros(15600, np.float32)      # last 0.975 s at 16 kHz
new = 0
smoke_hits, bark_hits = collections.deque(), collections.deque()
last_smoke = last_bark = 0.0
log.info("started")
while True:
    try:
        data = sock.recv(8192)
    except socket.timeout:
        continue
    x = np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768.0
    buf = np.concatenate([buf, x])[-15600:]
    new += len(x)
    if new < 16000 * HOP:
        continue
    new = 0
    interp.set_tensor(inp, buf)
    interp.invoke()
    scores = interp.get_tensor(outp)[0]
    now = time.time()
    smoke, bark = float(scores[SMOKE_IDS].max()), float(scores[BARK_IDS].max())
    if smoke >= SMOKE_SCORE:
        smoke_hits.append(now)
        log.info("smoke %.2f", smoke)
    if bark >= BARK_SCORE:
        bark_hits.append(now)
        log.info("bark %.2f", bark)
    while smoke_hits and smoke_hits[0] < now - SMOKE_WINDOW:
        smoke_hits.popleft()
    while bark_hits and bark_hits[0] < now - BARK_WINDOW:
        bark_hits.popleft()
    if len(smoke_hits) >= SMOKE_HITS and now - last_smoke > SMOKE_COOLDOWN:
        last_smoke = now
        post(SMOKE_HOOK, {"hits": len(smoke_hits)})
    if len(bark_hits) >= BARK_HITS and now - last_bark > BARK_COOLDOWN:
        last_bark = now
        post(BARK_HOOK, {"seconds": int(len(bark_hits) * HOP)})
