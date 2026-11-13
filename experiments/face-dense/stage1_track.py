"""Stage 1: track face points in one video with BootsTAPIR. Args: video, checkpoint, face model, output npz, query frame, x0,y0,size crop [grid step in px].
Query points are MediaPipe's 478 landmarks on the query frame plus a grid every GRID_PX inside the face outline. All points go in one call, so the video's
features are computed once (the archived version sent 800 at a time and recomputed them for each batch); the round trip checks the landmarks only."""
import sys, time
import cv2, numpy as np, torch
import mediapipe as mp
sys.path.insert(0, sys.argv[1])
from tapnet.torch import tapir_model
_, _, video, ckpt, flm, out, q, x0, y0, size = sys.argv[:10]
q, x0, y0, size = int(q), int(x0), int(y0), int(size)
RES = 512
GRID_PX = int(sys.argv[10]) if len(sys.argv) > 10 else 6  # the grid's step in the 512 crop; 4 in the archived version
QUERY_CHUNK = 256  # queries per cost volume inside TAPIR, which bounds the memory
cap = cv2.VideoCapture(video); fr = []
while True:
    ok, f = cap.read()
    if not ok: break
    fr.append(cv2.cvtColor(cv2.resize(f[y0:y0 + size, x0:x0 + size], (RES, RES), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB))
fr = np.stack(fr); n = len(fr)
opts = mp.tasks.vision.FaceLandmarkerOptions(base_options=mp.tasks.BaseOptions(model_asset_path=flm), running_mode=mp.tasks.vision.RunningMode.VIDEO, num_faces=1)
lmk = np.full((n, 478, 2), np.nan, dtype=np.float32)
with mp.tasks.vision.FaceLandmarker.create_from_options(opts) as lm:
    for i in range(n):
        r = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=fr[i].copy()), int(i * 1000 / 30))
        if r.face_landmarks:
            lmk[i] = [(p.x * RES, p.y * RES) for p in r.face_landmarks[0]]
outline = [10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,400,377,152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109]
mask = np.zeros((RES, RES), np.uint8); cv2.fillPoly(mask, [lmk[q, outline].astype(np.int32)], 1)
ys, xs = np.nonzero(mask[::GRID_PX, ::GRID_PX]); grid = np.stack([xs * GRID_PX, ys * GRID_PX], 1).astype(np.float32)
pts = np.concatenate([lmk[q], grid])
print("frames", n, "points", len(pts), "landmarks 478 grid", len(grid))
dev = "cuda"; model = tapir_model.TAPIR(pyramid_level=1); model.load_state_dict(torch.load(ckpt, map_location="cpu")); model = model.to(dev).eval()
def track(frames, query_xy, query_t):
    qp = np.concatenate([np.full((len(query_xy), 1), query_t), query_xy[:, ::-1]], 1).astype(np.float32)
    v = torch.tensor(frames).float().to(dev) / 255 * 2 - 1
    tr, vis = [], []
    with torch.inference_mode(), torch.autocast("cuda", dtype=torch.float16):
        o = model(v[None], torch.tensor(qp).to(dev)[None], query_chunk_size=QUERY_CHUNK)
        tr.append(o["tracks"][0].float().cpu().numpy())
        vis.append(((1 - torch.sigmoid(o["occlusion"][0])) * (1 - torch.sigmoid(o["expected_dist"][0]))).float().cpu().numpy())
    del v, o
    torch.cuda.empty_cache()
    return np.concatenate(tr), np.concatenate(vis)
print("tracking...", flush=True)
t0 = time.time(); tracks, vis = track(fr, pts, q); dt = time.time() - t0
print(f"tracking {dt:.1f}s for {n} frames, {dt / n:.2f}s per frame, peak VRAM {torch.cuda.max_memory_allocated() / 1e9:.1f} GB")
# Round trip: start again from where the points ended up on a far frame and track back to the query frame.
far = int(np.argmax(np.abs(np.arange(n) - q)))
back, _ = track(fr, tracks[:478, far], far)
rt = np.linalg.norm(back[:, q] - pts[:478], axis=1)
np.savez_compressed(out, tracks=tracks.transpose(1, 0, 2), vis=vis.transpose(1, 0), lmk=lmk, q=q, far=far, roundtrip=rt, res=RES, crop=[x0, y0, size], n_lmk=478)
print("round trip error px (512 crop), landmarks: p50 %.2f p95 %.2f; far frame %d" % (np.median(rt), np.percentile(rt, 95), far))
