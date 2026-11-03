import struct, numpy as np, sys
f = open(sys.argv[1], "rb"); h = f.read(32); _, _, nv, _, _, ns = struct.unpack("<12siiffi", h); p = np.frombuffer(f.read(), "<f4").reshape(ns, nv, 3)
d = np.linalg.norm(np.diff(p, axis=0), axis=2) * 1000; print("frames", ns, "per-frame vertex move mm: p95 %.2f p99.9 %.2f max %.2f" % (np.percentile(d, 95), np.percentile(d, 99.9), d.max()))
worst = d.max(1); print("largest frame-to-frame jumps at frames", (np.argsort(-worst)[:6] + 1).tolist(), np.round(np.sort(worst)[::-1][:6], 1).tolist())
