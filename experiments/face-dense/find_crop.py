"""The square crop around the face over a whole video, and a query frame with the mouth shut before speech, for stage1_track.py.
Args: video, face_landmarker.task, last frame to look for the query frame in. Prints x0 y0 size q."""
import sys
import cv2, numpy as np, mediapipe as mp

video, flm, before = sys.argv[1], sys.argv[2], int(sys.argv[3])
opts = mp.tasks.vision.FaceLandmarkerOptions(base_options=mp.tasks.BaseOptions(model_asset_path=flm), running_mode=mp.tasks.vision.RunningMode.VIDEO, num_faces=1)
cap = cv2.VideoCapture(video)
boxes, gaps, i = [], [], 0
with mp.tasks.vision.FaceLandmarker.create_from_options(opts) as L:
    while True:
        ok, f = cap.read()
        if not ok:
            break
        h, w = f.shape[:2]
        r = L.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(f, cv2.COLOR_BGR2RGB)), int(i * 1000 / 30))
        if r.face_landmarks:
            p = np.array([(q.x * w, q.y * h) for q in r.face_landmarks[0]])
            boxes.append([*p.min(0), *p.max(0)])
            gaps.append(np.linalg.norm(p[13] - p[14]) / np.linalg.norm(p[10] - p[152]))
        else:
            gaps.append(np.inf)
        i += 1
b = np.array(boxes)
x_lo, y_lo, x_hi, y_hi = b[:, 0].min(), b[:, 1].min(), b[:, 2].max(), b[:, 3].max()
size = int(min(h, w, 1.25 * max(x_hi - x_lo, y_hi - y_lo)))
cx, cy = (x_lo + x_hi) / 2, (y_lo + y_hi) / 2
x0 = int(np.clip(cx - size / 2, 0, w - size)); y0 = int(np.clip(cy - size / 2, 0, h - size))
q = int(np.argmin(gaps[:before]))
print("frames", i, "face box", [round(x) for x in (x_lo, y_lo, x_hi, y_hi)])
print("CROP", x0, y0, size, q)
