"""Builds the data the faders work from: sounds from the recognizer, sounds from the known words aligned to the recognizer's
timing, the tracked lip opening and the loudness. Args: phones, table, channels JSON, pts, raw audio, poses, words JSON, output."""
import json, sys
import numpy as np
ph, table, chan, pts, raw, poses, words, out = sys.argv[1:9]
g = {p["code"]: p["group"] for p in json.load(open(table))["phonemes"]}
rec = [(float(l.split()[0]), g.get(l.split()[2], "E"), l.split()[2]) for l in open(ph, encoding="utf-8").read().splitlines()]
ch = json.load(open(chan)); n = ch["frames"]; fps = ch["fps"]
W = json.load(open(words)); until = W["until"]
# Align the expected mouth groups to what was heard (keeps the heard timing where they agree).
exp = [x for w in W["words"] for x in w.split()]
heard = [r for r in rec if r[0] < until]
A, B = len(exp), len(heard)
sim = lambda a, b: 2 if a == b else (1 if {a, b} <= set("AEIOU") else (0.5 if {a, b} <= {"T", "S", "SH", "K", "L", "F", "M"} else -1))
M = np.zeros((A + 1, B + 1)); M[:, 0] = -np.arange(A + 1) * 0.6; M[0, :] = -np.arange(B + 1) * 0.3
T = np.zeros((A + 1, B + 1), int)
for i in range(1, A + 1):
    for j in range(1, B + 1):
        o = (M[i - 1, j - 1] + sim(exp[i - 1], heard[j - 1][1]), M[i - 1, j] - 0.6, M[i, j - 1] - 0.3)
        T[i, j] = int(np.argmax(o)); M[i, j] = max(o)
i, j = A, B; match = [None] * A
while i > 0 and j > 0:
    if T[i, j] == 0: match[i - 1] = heard[j - 1][0]; i -= 1; j -= 1
    elif T[i, j] == 1: i -= 1
    else: j -= 1
for k, t in W.get("anchors", {}).items():  # sounds the recognizer missed, placed by hand
    match[int(k)] = t
known = [k for k, t in enumerate(match) if t is not None]
times = np.interp(np.arange(A), known, [match[k] for k in known])
script = [(float(t), e, "script") for t, e in zip(times, exp)] + [r for r in rec if r[0] >= until]
print("script tokens", A, "matched", len(known), "same group", sum(1 for k in known for h in heard if h[0] == match[k] and h[1] == exp[k]))
# Loudness at the frame rate, 0-1.
au = np.fromfile(raw, dtype=np.int16) / 32768.0; sr = 16000
env = np.array([np.sqrt((au[int(k / fps * sr):int((k + 1) / fps * sr)] ** 2).mean()) if int(k / fps * sr) < len(au) - 1 else 0 for k in range(n)])
env = np.clip(env / max(np.percentile(env, 99), 1e-5), 0, 1)
json.dump({"fps": fps, "frames": n, "recognizer": rec, "script": script, "tracked_jaw": ch["channels"]["jawOpen"], "loudness": [round(float(x), 3) for x in env], "poses": json.load(open(poses))}, open(out, "w"))
print("groups rec", {k: sum(1 for r in rec if r[1] == k) for k in "MF"}, "script", {k: sum(1 for r in script if r[1] == k) for k in "MF"})
print("M,F times script", [(round(t, 2), c) for t, c, _ in script if c in ("M", "F")])
