#!/usr/bin/env python3
"""Check camper_vision.Vision gesture-checks every person (not just the largest) and time it.
  ~/camper_vision/venv/bin/python ~/camper_vision/test_two_people.py samples/two_people_bed.jpg
"""
import sys, time
import cv2
from camper_vision import Vision

vis = Vision()
for p in sys.argv[1:]:
    f = cv2.imread(p)
    people = vis.people(f)
    boxes = vis.boxes(people)
    for i, b in enumerate(boxes):
        print(f"{p} person{i} box={b} -> {vis.gesture(f, [b])}")
    t = time.time()
    for _ in range(5):
        vis.people(f); vis.gesture(f, boxes)
    print(f"{p} people={len(people)} all-people gesture={vis.gesture(f, boxes)} "
          f"frame time={(time.time() - t) / 5 * 1000:.0f} ms")
