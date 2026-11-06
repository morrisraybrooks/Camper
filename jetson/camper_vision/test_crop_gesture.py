#!/usr/bin/env python3
"""Does cropping to the detected person (and upscaling) let the gesture model see distant hands?
  ~/camper_vision/venv/bin/python ~/camper_vision/test_crop_gesture.py samples/thumbs_up_bed.jpg
"""
import sys
import cv2
from test_models import build, run
import mediapipe as mp

det, ges = build()
for p in sys.argv[1:]:
    f = cv2.imread(p)
    img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
    for d in det.detect(img).detections:
        b = d.bounding_box
        pad = int(0.15 * max(b.width, b.height))
        x0, y0 = max(0, b.origin_x - pad), max(0, b.origin_y - pad)
        crop = f[y0:b.origin_y + b.height + pad, x0:b.origin_x + b.width + pad]
        for scale in (1.0, 1.5, 2.0):
            c = cv2.resize(crop, None, fx=scale, fy=scale) if scale != 1 else crop
            _, g, _, tg = run(det, ges, c)
            print(f"{p} person={d.categories[0].score:.2f} box={b.width}x{b.height} scale={scale} -> {g} {tg*1000:.0f}ms")
        cv2.imwrite(p.replace(".jpg", "_crop.jpg"), crop)
