"""Per-frame 3D landmarks (crop pixels, z in same scale) for rigid head estimation. Args: video, face model, stage1.npz, output npy."""
import sys
import cv2, numpy as np, mediapipe as mp
video, flm, s1, out = sys.argv[1:5]
d = np.load(s1); x0, y0, size = d["crop"]; RES = int(d["res"])
opts = mp.tasks.vision.FaceLandmarkerOptions(base_options=mp.tasks.BaseOptions(model_asset_path=flm), running_mode=mp.tasks.vision.RunningMode.VIDEO, num_faces=1)
cap = cv2.VideoCapture(video); out_l = []; i = 0
with mp.tasks.vision.FaceLandmarker.create_from_options(opts) as L:
    while True:
        ok, f = cap.read()
        if not ok: break
        c = cv2.cvtColor(cv2.resize(f[y0:y0 + size, x0:x0 + size], (RES, RES), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
        r = L.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=c), int(i * 1000 / 24))
        out_l.append([(p.x * RES, p.y * RES, p.z * RES) for p in r.face_landmarks[0]] if r.face_landmarks else [(np.nan,) * 3] * 478); i += 1
np.save(out, np.array(out_l, dtype=np.float32)); print("frames", i)
