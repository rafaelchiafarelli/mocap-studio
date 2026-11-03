"""video -> per-frame ARKit-style blendshapes (raw) with MediaPipe Face Landmarker, VIDEO mode."""
import csv, sys
import cv2, mediapipe as mp, numpy as np
video, model, out = sys.argv[1:4]
Opt = mp.tasks.vision.FaceLandmarkerOptions
opts = Opt(base_options=mp.tasks.BaseOptions(model_asset_path=model), running_mode=mp.tasks.vision.RunningMode.VIDEO,
           output_face_blendshapes=True, output_facial_transformation_matrixes=True, num_faces=1)
cap = cv2.VideoCapture(video); fps = cap.get(cv2.CAP_PROP_FPS)
names, rows, lost = None, [], []
with mp.tasks.vision.FaceLandmarker.create_from_options(opts) as lm:
    i = 0
    while True:
        ok, f = cap.read()
        if not ok: break
        im = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
        r = lm.detect_for_video(im, int(i * 1000 / fps))
        if r.face_blendshapes:
            b = r.face_blendshapes[0]
            names = names or [c.category_name for c in b]
            M = np.array(r.facial_transformation_matrixes[0])
            yaw = np.degrees(np.arctan2(M[0, 2], M[2, 2])); pitch = np.degrees(np.arcsin(np.clip(-M[1, 2], -1, 1)))
            rows.append([i, 1, round(float(yaw), 2), round(float(pitch), 2)] + [c.score for c in b])
        else:
            lost.append(i); rows.append([i, 0, "", ""] + [""] * (len(names) if names else 52))
        i += 1
with open(out, "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["frame", "detected", "yaw_deg", "pitch_deg"] + names); w.writerows(rows)
print("frames", i, "fps", round(fps, 3), "lost", len(lost), lost[:20], "n_names", len(names))
a = np.array([[float(x) for x in r[4:]] for r in rows if r[1] == 1]); yaw = np.array([r[2] for r in rows if r[1] == 1], dtype=float)
print("yaw range", yaw.min(), yaw.max(), "abs>45 frames", int((np.abs(yaw) > 45).sum()))
for n, c in sorted(zip(names, a.T), key=lambda z: -z[1].max())[:30]:
    print(f"{n:22s} max {c.max():.2f} mean {c.mean():.2f} jitter {np.abs(np.diff(c)).mean():.3f}")
print("low:", [n for n, c in zip(names, a.T) if c.max() < 0.02])
