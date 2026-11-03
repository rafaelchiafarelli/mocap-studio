import json, sys
import cv2, numpy as np, mediapipe as mp
O, flm, out = sys.argv[1:4]
img0 = cv2.imread(f"{O}/neutral_front.png"); img = cv2.cvtColor(img0, cv2.COLOR_BGR2RGB)
opts = mp.tasks.vision.FaceLandmarkerOptions(base_options=mp.tasks.BaseOptions(model_asset_path=flm), running_mode=mp.tasks.vision.RunningMode.IMAGE, num_faces=1)
with mp.tasks.vision.FaceLandmarker.create_from_options(opts) as L:
    r = L.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=img))
ant = np.array([(p.x * 1024, p.y * 1024) for p in r.face_landmarks[0]])
Nz = np.load(f"{O}/neutral.npz"); co = Nz["co"]; skin = Nz["skin"]; W = Nz["world"]
cam = json.load(open(f"{O}/camera.json")); K = np.array(cam["K"]); Rt = np.array(cam["Rt"])
wco = (W @ np.c_[co, np.ones(len(co))].T).T[:, :3]; cc = (Rt @ np.c_[wco, np.ones(len(wco))].T).T; px = (K @ cc.T).T; px = px[:, :2] / px[:, 2:]
vis = img0.copy()
for p in px[skin][::3]:
    if 0 <= p[0] < 1024 and 0 <= p[1] < 1024: cv2.circle(vis, tuple(np.round(p).astype(int)), 1, (0, 255, 0), -1)
for p in px[~skin][::3]:
    if 0 <= p[0] < 1024 and 0 <= p[1] < 1024: cv2.circle(vis, tuple(np.round(p).astype(int)), 1, (255, 0, 255), -1)
for i in [13, 14, 82, 87, 312, 317, 78, 308, 1, 152, 33, 263, 10]:
    cv2.circle(vis, tuple(np.round(ant[i]).astype(int)), 5, (0, 0, 255), 1, cv2.LINE_AA)
cv2.imwrite(out, vis)
for i, nm in ((13, "upper lip inner"), (14, "lower lip inner"), (1, "nose tip"), (152, "chin"), (33, "eye corner")):
    a = np.linalg.norm(px[skin] - ant[i], axis=1); print(nm, "landmark", ant[i].round(0), "nearest skin vert px %.1f" % a.min(), "world z", round(float(wco[skin][a.argmin()][2]), 3), "y", round(float(wco[skin][a.argmin()][1]), 3))
print("skin z range in head", wco[skin][:, 2].max().round(3), "mouth region skin count within 40px of lip", int((np.linalg.norm(px[skin] - ant[13], axis=1) < 40).sum()), "non-skin", int((np.linalg.norm(px[~skin] - ant[13], axis=1) < 40).sum()))
