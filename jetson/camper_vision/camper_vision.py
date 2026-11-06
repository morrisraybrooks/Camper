#!/usr/bin/env python3
"""Camper vision: webcam -> presence + hand gestures -> Home Assistant.

CPU only (MediaPipe/TFLite), so it never competes with the camper brain for GPU memory.
Frames are processed in memory and discarded; only events leave this process.

Home Assistant (REST API, token from $HA_TOKEN_FILE, default ~/camper_vision/ha_token):
  binary_sensor.camper_occupied   on/off  (device_class occupancy), re-posted every minute so it
                                  survives HA restarts
  sensor.camper_last_gesture      last gesture fired
  event  camper_gesture           {"gesture": "Thumb_Up", "score": 0.81}  <- trigger automations on this

Gestures (MediaPipe names): Thumb_Up, Thumb_Down, Open_Palm, Closed_Fist, Pointing_Up, Victory, ILoveYou
plus Middle_Finger, which MediaPipe doesn't know - worked out here from the hand landmarks.
"""
import argparse
import collections
import json
import logging
import math
import os
import signal
import time
import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

MODELS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
HA = os.environ.get("HA_HTTP", "http://192.168.0.168:8123")
TOKEN_FILE = os.environ.get("HA_TOKEN_FILE", os.path.expanduser("~/camper_vision/ha_token"))

PERSON_MIN_SCORE = 0.40      # dim camper -> real people often score 0.45-0.6
PRESENT_HITS = (3, 5)        # occupied after a person in 3 of the last 5 frames
EMPTY_AFTER_S = 120          # unoccupied after this long with nobody seen
GESTURE_MIN_SCORE = 0.55     # Open_Palm reads a steady 0.58-0.63 at bed distance
GESTURE_HOLD_FRAMES = 3      # same gesture this many processed frames in a row (~0.5 s)
GESTURE_COOLDOWN_S = 4       # after firing, ignore all gestures this long
BOX_HOLD_S = 3              # keep using the last person box this long after a missed detection
MAX_PEOPLE = 2              # gesture-check this many people per frame (~70 ms each)
STATE_REFRESH_S = 60

log = logging.getLogger("camper_vision")


class HomeAssistant:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.token = None if dry_run else open(TOKEN_FILE).read().strip()

    def _post(self, path, body):
        if self.dry_run:
            log.info("[dry-run] POST %s %s", path, body)
            return
        req = urllib.request.Request(
            HA + path, data=json.dumps(body).encode(), method="POST",
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=5).read()
        except Exception as e:  # HA down / network blip: log and keep watching
            log.warning("HA %s failed: %s", path, e)

    def occupied(self, on, people=0):
        self._post("/api/states/binary_sensor.camper_occupied", {
            "state": "on" if on else "off",
            "attributes": {"friendly_name": "Camper Occupied", "device_class": "occupancy",
                           "people_in_view": people, "source": "Jetson webcam"}})

    def gesture(self, name, score):
        self._post("/api/events/camper_gesture", {"gesture": name, "score": round(score, 2)})
        self._post("/api/states/sensor.camper_last_gesture", {
            "state": name, "attributes": {"friendly_name": "Camper Last Gesture",
                                          "icon": "mdi:hand-wave", "score": round(score, 2)}})


class Vision:
    def __init__(self):
        self.det = vision.ObjectDetector.create_from_options(vision.ObjectDetectorOptions(
            base_options=BaseOptions(model_asset_path=f"{MODELS}/efficientdet_lite0.tflite"),
            category_allowlist=["person"], score_threshold=PERSON_MIN_SCORE, max_results=4))
        self.ges = vision.GestureRecognizer.create_from_options(vision.GestureRecognizerOptions(
            base_options=BaseOptions(model_asset_path=f"{MODELS}/gesture_recognizer.task"),
            num_hands=2))

    @staticmethod
    def _img(bgr):
        return mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))

    def people(self, frame):
        return self.det.detect(self._img(frame)).detections

    @staticmethod
    def boxes(people):
        """(x, y, w, h) of the MAX_PEOPLE largest people. Every one gets a gesture check:
        two people in bed are near-equal in size, so 'largest only' flipped between them
        frame to frame and broke held gestures."""
        big = sorted(people, key=lambda d: d.bounding_box.width * d.bounding_box.height,
                     reverse=True)[:MAX_PEOPLE]
        return [(d.bounding_box.origin_x, d.bounding_box.origin_y,
                 d.bounding_box.width, d.bounding_box.height) for d in big]

    @staticmethod
    def middle_finger(landmarks, w, h):
        """True when the middle finger is up and clearly sticks out past the other three:
        its tip is well past its middle joint (measured from the wrist) and reaches at
        least 1.3x as far as the index, ring and pinky tips. Thumb ignored. A strict
        "others fully folded" test missed real ones - a half-bent index read as
        Pointing_Up (2026-10-10). Landmarks are 0-1 of the crop, so scale to pixels."""
        pts = [(p.x * w, p.y * h) for p in landmarks]
        reach = lambda i: math.dist(pts[0], pts[i])
        mid = reach(12)
        return mid > reach(10) * 1.15 and all(mid > reach(t) * 1.3 for t in (8, 16, 20))

    def gesture(self, frame, boxes):
        """Best (name, score) across all hands of all given people. Runs on person crops:
        hands at camper distances are too small for the model in the full frame."""
        best = ("None", 0.0)
        for x, y, w, h in boxes:
            pad = int(0.15 * max(w, h))
            x0, y0 = max(0, x - pad), max(0, y - pad)
            crop = frame[y0:y + h + pad, x0:x + w + pad]
            if crop.size == 0 or crop.shape[0] < 8 or crop.shape[1] < 8:
                continue  # box at/over the frame edge: nothing to look at
            res = self.ges.recognize(self._img(crop))
            for i, hand in enumerate(res.gestures):
                c = hand[0]
                name, score = c.category_name, c.score
                # Middle finger isn't a MediaPipe gesture (it reads as None or Pointing_Up);
                # score it by how sure the model is that it's looking at a hand.
                if i < len(res.hand_landmarks) and self.middle_finger(
                        res.hand_landmarks[i], crop.shape[1], crop.shape[0]):
                    name, score = "Middle_Finger", res.handedness[i][0].score
                if name != "None" and score > best[1]:
                    best = (name, score)
        return best


def open_camera(dev, width, height):
    cap = cv2.VideoCapture(dev, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not cap.isOpened():
        raise SystemExit(f"cannot open camera {dev}")
    return cap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="/dev/video0")
    ap.add_argument("--fps", type=float, default=4.0, help="frames processed per second")
    ap.add_argument("--dry-run", action="store_true", help="log HA calls instead of sending")
    ap.add_argument("--debug", action="store_true", help="log every frame's results")
    a = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if a.debug else logging.INFO,
                        format="%(levelname)s:%(name)s:%(message)s")

    ha, vis = HomeAssistant(a.dry_run), Vision()
    cap = open_camera(a.device, 1280, 720)
    running = True

    def stop(*_):
        nonlocal running
        running = False
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    hits = collections.deque(maxlen=PRESENT_HITS[1])
    occupied, last_seen, last_post, last_boxes = False, 0.0, 0.0, []
    streak_name, streak_n, cooldown_until = None, 0, 0.0
    period = 1.0 / a.fps
    log.info("watching %s at %.1f fps", a.device, a.fps)
    ha.occupied(False); last_post = time.time()

    while running:
        t0 = time.time()
        cap.grab()                      # drop the stale buffered frame
        ok, frame = cap.read()
        if not ok:
            log.warning("camera read failed; reopening in 5 s")
            cap.release(); time.sleep(5)
            cap = open_camera(a.device, 1280, 720)
            continue

        people = vis.people(frame)
        now = time.time()
        hits.append(bool(people))
        if people:
            last_seen, last_boxes = now, vis.boxes(people)

        # --- presence ---
        if not occupied and sum(hits) >= PRESENT_HITS[0]:
            occupied = True
            log.info("occupied (people=%d)", len(people))
            ha.occupied(True, len(people)); last_post = now
        elif occupied and now - last_seen > EMPTY_AFTER_S:
            occupied = False
            log.info("empty (nobody seen for %d s)", EMPTY_AFTER_S)
            ha.occupied(False); last_post = now
        elif now - last_post > STATE_REFRESH_S:
            ha.occupied(occupied, len(people)); last_post = now

        # --- gestures ---
        # The person detector misses ~1 in 3 frames in a dim camper; reuse the last boxes
        # briefly so a dropout doesn't break a held gesture.
        recent = now - last_seen < BOX_HOLD_S
        name, score = vis.gesture(frame, last_boxes) if recent else ("None", 0.0)
        if a.debug:
            log.debug("people=%s gesture=%s %.2f",
                      [round(p.categories[0].score, 2) for p in people], name, score)
        if now < cooldown_until or score < GESTURE_MIN_SCORE or name == "None":
            streak_name, streak_n = None, 0
        elif name == streak_name:
            streak_n += 1
        else:
            streak_name, streak_n = name, 1
        if streak_n >= GESTURE_HOLD_FRAMES:
            log.info("gesture %s (%.2f)", name, score)
            ha.gesture(name, score)
            streak_name, streak_n, cooldown_until = None, 0, now + GESTURE_COOLDOWN_S

        time.sleep(max(0.0, period - (time.time() - t0)))

    cap.release()
    log.info("stopped")


if __name__ == "__main__":
    main()
