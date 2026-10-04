#!/usr/bin/env python3
"""Pick test resolutions from a device's /info: the largest size up to ~1080p (2.1 MP) and, if the
camera offers more, the largest up to 4K (8.3 MP). Only sizes the camera can deliver at the target fps.

usage: pick_sizes.py device.json [fps]   -> prints e.g. "1920x1080 3840x2160"
"""
import json
import sys


def main():
    with open(sys.argv[1]) as f:
        info = json.load(f)
    fps = float(sys.argv[2]) if len(sys.argv) > 2 else 30
    cams = info.get("cameras", [])
    cam = next((c for c in cams if c.get("facing") == "back"), cams[0] if cams else {})
    sizes = []
    for entry in cam.get("encoder_sizes", []):
        dims, _, max_fps = entry.partition("@")
        w, h = (int(x) for x in dims.split("x"))
        if not max_fps or float(max_fps) >= fps - 0.5:
            sizes.append((w * h, w, h))
    sizes.sort()
    picks = []
    hd = [s for s in sizes if s[0] <= 2_100_000]
    if hd:
        picks.append(hd[-1])
    big = [s for s in sizes if 2_100_000 < s[0] <= 8_300_000]
    if big:
        picks.append(big[-1])
    print(" ".join(f"{w}x{h}" for _, w, h in picks) or "1280x720")


if __name__ == "__main__":
    main()
