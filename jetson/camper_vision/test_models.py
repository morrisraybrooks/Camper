#!/usr/bin/env python3
"""Benchmark + sanity-check the two vision models on images or live webcam frames.
  ~/camper_vision/venv/bin/python ~/camper_vision/test_models.py samples/*.jpg
  ~/camper_vision/venv/bin/python ~/camper_vision/test_models.py --live 20    # 20 webcam frames
"""
import argparse, time
import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

M = "/home/morris/camper_vision/models/"

def build(threads=None):
    det = vision.ObjectDetector.create_from_options(vision.ObjectDetectorOptions(
        base_options=BaseOptions(model_asset_path=M + "efficientdet_lite0.tflite"),
        category_allowlist=["person"], score_threshold=0.4, max_results=5))
    ges = vision.GestureRecognizer.create_from_options(vision.GestureRecognizerOptions(
        base_options=BaseOptions(model_asset_path=M + "gesture_recognizer.task"), num_hands=2))
    return det, ges

def run(det, ges, bgr):
    img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    t = time.time(); d = det.detect(img); td = time.time() - t
    t = time.time(); g = ges.recognize(img); tg = time.time() - t
    people = [round(x.categories[0].score, 2) for x in d.detections]
    gestures = [(h[0].category_name, round(h[0].score, 2)) for h in g.gestures]
    return people, gestures, td, tg

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("images", nargs="*"); ap.add_argument("--live", type=int)
    a = ap.parse_args()
    det, ges = build()
    frames = [(p, cv2.imread(p)) for p in a.images]
    if a.live:
        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640); cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
        for _ in range(15): cap.read()  # let auto-exposure settle
        for i in range(a.live):
            ok, f = cap.read()
            if ok: frames.append((f"live{i}", f))
        cap.release()
    for name, f in frames:
        people, gestures, td, tg = run(det, ges, f)
        print(f"{name:28s} {f.shape[1]}x{f.shape[0]} people={people} gestures={gestures} "
              f"det={td*1000:.0f}ms ges={tg*1000:.0f}ms")

if __name__ == "__main__":
    main()
