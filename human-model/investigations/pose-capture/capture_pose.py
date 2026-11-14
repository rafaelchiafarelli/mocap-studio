"""Step 1 of the pose-capture investigation: MediaPipe Pose on every frame of one clip, and a video to check it by eye.

    human-model/hm.sh --ref python human-model/investigations/pose-capture/capture_pose.py CLIP.mp4 OUT.npz OVERLAY.mp4

OUT.npz holds, per frame t: `image` (T, 33, 4) pixel x, y, z (MediaPipe's relative depth, in pixels) and visibility;
`world` (T, 33, 3) MediaPipe's world landmarks in metres, origin between the hips, x to the person's left in the image,
y down, z away from the camera; `found` (T,) whether a person was found; `fps`, `width`, `height`.
A frame with no person has NaN.

OVERLAY.mp4 is the clip with the 2D skeleton drawn on it and, on the right, the world landmarks seen from the front and
from the side, so the depth MediaPipe guessed can be judged. It is written with OpenCV's mp4v; transcode it to H.264 for Windows.
MediaPipe Pose is Apache-2.0, its models inside the wheel.
"""
from __future__ import annotations

import os
import sys

import numpy as np

os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import cv2  # noqa: E402
from mediapipe.python.solutions import pose as mp_pose  # noqa: E402

EDGES = [(a, b) for a, b in mp_pose.POSE_CONNECTIONS]
LEFT = {11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31}  # the person's left
PANEL = 540  # side of each 3D view, in pixels
SCALE = 230  # pixels per metre in the 3D views
COMPLEXITY = 1  # MediaPipe's 'full' model, inside the wheel; 2 (heavy) is downloaded at run time and the image's site-packages is read-only


def colour(a, b):
    if a in LEFT and b in LEFT:
        return (255, 160, 40)
    if a in LEFT or b in LEFT:
        return (200, 200, 200)
    return (40, 120, 255)


def draw_2d(frame, lm):
    for a, b in EDGES:
        if np.isfinite(lm[[a, b], :2]).all():
            cv2.line(frame, tuple(lm[a, :2].astype(int)), tuple(lm[b, :2].astype(int)), colour(a, b), 3, cv2.LINE_AA)
    for p in lm:
        if np.isfinite(p[:2]).all():
            cv2.circle(frame, tuple(p[:2].astype(int)), 5, (255, 255, 255) if p[3] > 0.5 else (0, 0, 255), -1, cv2.LINE_AA)


def draw_3d(world, axes, title):
    """One view of the world landmarks: axes picks (horizontal, vertical) from x, y, z; y is down in MediaPipe."""
    img = np.full((PANEL, PANEL, 3), 30, np.uint8)
    cv2.line(img, (PANEL // 2, 0), (PANEL // 2, PANEL), (70, 70, 70), 1)
    cv2.line(img, (0, PANEL // 2), (PANEL, PANEL // 2), (70, 70, 70), 1)
    cv2.putText(img, title, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (230, 230, 230), 2, cv2.LINE_AA)
    if not np.isfinite(world).all():
        return img
    pts = np.stack([world[:, axes[0]], world[:, axes[1]]], 1) * SCALE + PANEL / 2
    for a, b in EDGES:
        cv2.line(img, tuple(pts[a].astype(int)), tuple(pts[b].astype(int)), colour(a, b), 3, cv2.LINE_AA)
    return img


def main(clip, out_npz, overlay):
    cap = cv2.VideoCapture(clip)
    fps = cap.get(cv2.CAP_PROP_FPS)
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out_w = w * PANEL * 2 // h + PANEL  # the clip scaled to 2 panels tall, then the two views stacked
    writer = cv2.VideoWriter(overlay, cv2.VideoWriter_fourcc(*"mp4v"), fps, (out_w, PANEL * 2))
    images, worlds, found = [], [], []
    with mp_pose.Pose(static_image_mode=False, model_complexity=COMPLEXITY, smooth_landmarks=True, enable_segmentation=False) as pose:
        while True:
            ok, bgr = cap.read()
            if not ok:
                break
            r = pose.process(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            if r.pose_landmarks is None:
                lm, world = np.full((33, 4), np.nan), np.full((33, 3), np.nan)
            else:
                lm = np.array([[p.x * w, p.y * h, p.z * w, p.visibility] for p in r.pose_landmarks.landmark])
                world = np.array([[p.x, p.y, p.z] for p in r.pose_world_landmarks.landmark])
            images.append(lm)
            worlds.append(world)
            found.append(r.pose_landmarks is not None)
            draw_2d(bgr, lm)
            cv2.putText(bgr, f"quadro {len(found)}", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (255, 255, 255), 3, cv2.LINE_AA)
            left = cv2.resize(bgr, (w * PANEL * 2 // h, PANEL * 2), interpolation=cv2.INTER_AREA)
            right = np.vstack([draw_3d(world, (0, 1), "3D frente"), draw_3d(world, (2, 1), "3D lado (camera a esquerda)")])
            writer.write(np.hstack([left, right]))
    writer.release()
    np.savez_compressed(out_npz, image=np.array(images), world=np.array(worlds), found=np.array(found), fps=fps, width=w, height=h)
    print(f"frames {len(found)}, with person {int(np.sum(found))}, fps {fps:.3f}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(2)
    main(*sys.argv[1:])
