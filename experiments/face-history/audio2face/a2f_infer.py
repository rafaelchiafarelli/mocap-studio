"""Audio -> Audio2Face-3D v3.0 geometry at 60 fps, running NVIDIA's network.onnx with ONNX Runtime.
Windowing as in the SDK (executor_diffusion_core.cpp): 1 s window, 0.5 s stride, centre 30 of 60 frames; GRU state carried."""
import json, sys, time, resource
import numpy as np, onnxruntime as ort, soundfile as sf
model, wav, out, identity, seed = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
info = json.load(open(model + "/network_info.json"))["params"]
audio, sr = sf.read(wav, dtype="float32")
assert sr == 16000 and audio.ndim == 1
ident = np.zeros((1, 3), dtype=np.float32); ident[0, info["identities"].index(identity)] = 1
emotion = np.zeros((1, 30, 10), dtype=np.float32)
latents = np.zeros((2, 2, 1, 256), dtype=np.float32)
rng = np.random.default_rng(seed)
so = ort.SessionOptions(); s = ort.InferenceSession(model + "/network.onnx", so, providers=["CPUExecutionProvider"])
t0 = time.time(); frames = []
start = -16000
pad = np.zeros(16000, dtype=np.float32)
buf = np.concatenate([pad, audio, pad, pad])
while start < len(audio):
    w = buf[start + 16000: start + 32000][None]
    noise = rng.standard_normal((1, 3, 60, 88831), dtype=np.float32)
    pred, latents = s.run(None, {"window": w, "identity": ident, "emotion": emotion, "input_latents": latents, "noise": noise})
    # centre frames only; frame i of this window sits at start/16000 + i/60 s
    for i in range(15, 45):
        t = start / 16000 + i / 60
        if 0 <= t <= len(audio) / 16000:
            frames.append(pred[0, i].copy())
    start += 8000
pred = np.stack(frames)
np.save(out, pred.astype(np.float32))
el = time.time() - t0
print(f"frames {len(pred)} shape {pred.shape} audio {len(audio)/16000:.2f}s infer {el:.1f}s = {el/(len(audio)/16000):.1f}s per audio second, peak RAM {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1e6:.1f} GB")
sk, to, ja, ey = pred[:, :72006], pred[:, 72006:88812], pred[:, 88812:88827], pred[:, 88827:]
print("skin abs max", float(np.abs(sk).max()), "rms", float(np.sqrt((sk**2).mean())), "tongue max", float(np.abs(to).max()), "jaw", float(np.abs(ja).max()), "eyes range", ey.min(0).round(2), ey.max(0).round(2))
