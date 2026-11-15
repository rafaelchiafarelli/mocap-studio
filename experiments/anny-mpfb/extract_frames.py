"""Frames of one runway model for the fit: per kept frame, the image, the body's mask and MediaPipe Pose's landmarks.
    human-model/hm.sh --ref python experiments/anny-mpfb/extract_frames.py OUT_DIR CLIP:VIEW [CLIP:VIEW ...] [step=3]
VIEW is front or back (the yaw the fit starts from). A frame is kept when every landmark the fit uses is seen (visibility >= 0.8),
the whole body is inside the picture, and the mask is one solid figure. MediaPipe Pose (Apache-2.0, model inside the wheel), complexity 1 (the heavy model isn't in the wheel).
Writes OUT_DIR/frames/<clip>_<n>.jpg, .mask.png, and OUT_DIR/frames.json."""
import json, os, sys
import cv2
import numpy as np
from mediapipe.python.solutions import pose as mp_pose

USED = {"shoulder.L": 11, "shoulder.R": 12, "elbow.L": 13, "elbow.R": 14, "wrist.L": 15, "wrist.R": 16,
        "hip.L": 23, "hip.R": 24, "knee.L": 25, "knee.R": 26, "ankle.L": 27, "ankle.R": 28, "heel.L": 29, "heel.R": 30, "nose": 0}
MIN_VIS = 0.8
MASK_THRESHOLD = 0.5
MARGIN = 10  # px from the picture's edge


def main():
    out = sys.argv[1]
    args = [a for a in sys.argv[2:] if "=" not in a]
    opts = dict(a.split("=", 1) for a in sys.argv[2:] if "=" in a)
    step = int(opts.get("step", 3))
    os.makedirs(os.path.join(out, "frames"), exist_ok=True)
    kept, seen = [], 0
    for spec in args:
        clip, view = spec.rsplit(":", 1)
        name = os.path.splitext(os.path.basename(clip))[0]
        cap = cv2.VideoCapture(clip)
        fps = cap.get(cv2.CAP_PROP_FPS)
        with mp_pose.Pose(static_image_mode=False, model_complexity=1, enable_segmentation=True, smooth_segmentation=True) as pose:
            n = -1
            while True:
                ok, img = cap.read()
                if not ok:
                    break
                n += 1
                res = pose.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))  # every frame, so tracking stays smooth
                if n % step:
                    continue
                seen += 1
                if res.pose_landmarks is None or res.segmentation_mask is None:
                    continue
                H, W = img.shape[:2]
                lm = res.pose_landmarks.landmark
                pts = {k: (lm[i].x * W, lm[i].y * H, lm[i].visibility) for k, i in USED.items()}
                if min(p[2] for p in pts.values()) < MIN_VIS:
                    continue
                mask = res.segmentation_mask > MASK_THRESHOLD
                count, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8))
                if count < 2:
                    continue
                big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
                mask = labels == big
                x, y, w, h = stats[big, :4]
                if x < MARGIN or y < MARGIN or x + w > W - MARGIN or y + h > H - MARGIN:
                    continue  # the body touches the edge: cut off
                stem = f"{name}_{n:05d}"
                cv2.imwrite(os.path.join(out, "frames", stem + ".jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
                cv2.imwrite(os.path.join(out, "frames", stem + ".mask.png"), mask.astype(np.uint8) * 255)
                world = res.pose_world_landmarks.landmark
                kept.append({"stem": stem, "clip": name, "frame": n, "time_s": round(n / fps, 3), "view": view, "size": [W, H],
                             "bbox": [int(x), int(y), int(w), int(h)], "mask_px": int(mask.sum()),
                             "joints": {k: [round(p[0], 2), round(p[1], 2), round(p[2], 3)] for k, p in pts.items()},
                             "world": {k: [round(world[i].x, 4), round(world[i].y, 4), round(world[i].z, 4)] for k, i in USED.items()}})
        print(name, view, "kept so far", len(kept))
    json.dump({"seen": seen, "kept": kept, "min_visibility": MIN_VIS}, open(os.path.join(out, "frames.json"), "w"), indent=1)
    print("seen", seen, "kept", len(kept))


if __name__ == "__main__":
    main()
