"""What Rafael sees at the cuts: the simulated skin against the rig's skin next to it, per frame, in an assembled file.

    python3 human-model/blender_run.py --blend MONTADO.blend human-model/investigations/pose-capture/seam_gap.py TECIDOS.npz OUT.json [PASSO]

MONTADO.blend: one with `HM_pele_simulada` (tissue_assemble.py) and `HM_body`. The shown skin is MPFB's skin subdivided twice
(tissue_export.py); `sub_ids` gives each of its vertices the index of the same point in HM_body subdivided twice, so the
simulated and the skinned positions of one point are compared directly. Per cut (wrists, ankles, neck) and per ring from
the cut's border (ring 0 = the border itself, where the seam is): the distance between the two, median, p95 and max over
the frames; its part along the skin's normal (+ out) and the worst frames. Every PASSO-th frame (default 1).
"""
import json, sys
import bpy
import numpy as np

a = sys.argv[sys.argv.index("--") + 1:]
m = np.load(a[0])
out = a[1]
step = int(a[2]) if len(a) > 2 else 1
RINGS = 12

sub_ids, faces, rest = m["sub_ids"], m["sub_faces"], m["sub_rest"].astype(float)
n = len(rest)

# border: edges used by one face
edges = {}
for f in faces:
    for i in range(4):
        e = tuple(sorted((int(f[i]), int(f[(i + 1) % 4]))))
        edges[e] = edges.get(e, 0) + 1
border = np.unique([v for e, c in edges.items() if c == 1 for v in e])
nbr = [[] for _ in range(n)]
for (u, v) in edges:
    nbr[u].append(v)
    nbr[v].append(u)

# the cuts: border vertices joined by border edges, each loop one cut
bset = set(border.tolist())
badj = {v: [] for v in border.tolist()}
for (u, v), c in edges.items():
    if c == 1:
        badj[u].append(v)
        badj[v].append(u)
seen, loops = set(), []
for v in border.tolist():
    if v in seen:
        continue
    stack, comp = [v], []
    seen.add(v)
    while stack:
        u = stack.pop()
        comp.append(u)
        for w in badj[u]:
            if w not in seen:
                seen.add(w)
                stack.append(w)
    loops.append(np.array(comp))
loops = [l for l in loops if len(l) >= 8]


def name(loop):
    c = rest[loop].mean(axis=0)
    side = "esq" if c[0] > 0 else "dir"
    if c[2] > 1.25 and abs(c[0]) < 0.08:
        return "pescoco"
    if c[2] < 0.25:
        return "tornozelo_" + side
    return "punho_" + side


cuts = {}
for l in loops:
    k = name(l)
    while k in cuts:
        k += "+"
    cuts[k] = l

# rings from each cut, by walking edges
ring_of = np.full(n, -1)
cut_of = np.full(n, -1)
for ci, (k, l) in enumerate(cuts.items()):
    front = list(l)
    for v in front:
        ring_of[v], cut_of[v] = 0, ci
    for r in range(1, RINGS + 1):
        nxt = []
        for u in front:
            for w in nbr[u]:
                if ring_of[w] < 0:
                    ring_of[w], cut_of[w] = r, ci
                    nxt.append(w)
        front = nxt
sel = np.flatnonzero(ring_of >= 0)
# each ring's mean distance from the cut along the rest skin
ring_mm = {}
for ci, (k, l) in enumerate(cuts.items()):
    c0 = rest[l].mean(axis=0)
    ring_mm[k] = [float(np.median([np.min(np.linalg.norm(rest[l] - p, axis=1)) for p in rest[(ring_of == r) & (cut_of == ci)]]) * 1000)
                  for r in range(RINGS + 1)]

sim = bpy.data.objects["HM_pele_simulada"]
body = bpy.data.objects["HM_body"]
# as tissue_export.py read it: masks on (the helpers'), Subsurf and Geometry Nodes off, then Subsurf 2 last
for md in body.modifiers:
    if md.type in ("SUBSURF", "NODES"):
        md.show_viewport = False
    if md.type == "MASK" and md.name == "so_fora_da_simulacao":
        md.show_viewport = False
sub = body.modifiers.new("medida_sub", "SUBSURF")
sub.levels = 2
for md in sim.modifiers:
    if md.type == "SUBSURF":
        md.show_viewport = False


def world(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    c = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", c)
    ev.to_mesh_clear()
    M = np.array(ob.matrix_world)
    return c.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]


def normals(x):
    nr = np.zeros_like(x)
    q = x[faces]
    fn = np.cross(q[:, 2] - q[:, 0], q[:, 3] - q[:, 1])
    for i in range(4):
        np.add.at(nr, faces[:, i], fn)
    return nr / np.maximum(np.linalg.norm(nr, axis=1, keepdims=True), 1e-12)


sc = bpy.context.scene
frames = list(range(sc.frame_start, sc.frame_end + 1, step))
D = np.zeros((len(frames), len(sel)), np.float32)
Dn = np.zeros_like(D)
for fi, f in enumerate(frames):
    sc.frame_set(f)
    xs = world(sim)
    xb = world(body)
    if fi == 0:
        assert len(xs) == n, (len(xs), n)
        assert xb.shape[0] > sub_ids.max(), (xb.shape, sub_ids.max())
    xb = xb[sub_ids]
    d = xs[sel] - xb[sel]
    D[fi] = np.linalg.norm(d, axis=1)
    Dn[fi] = (d * normals(xb)[sel]).sum(axis=1)

rep = {"arquivo": bpy.data.filepath, "quadros": [frames[0], frames[-1], step], "cortes": {}}
for ci, k in enumerate(cuts):
    r = {"anel_mm_do_corte": [round(v, 1) for v in ring_mm[k]], "aneis": []}
    for ring in range(RINGS + 1):
        cols = (ring_of[sel] == ring) & (cut_of[sel] == ci)
        d, dn = D[:, cols] * 1000, Dn[:, cols] * 1000
        per_frame = d.max(axis=1)
        r["aneis"].append({"anel": ring, "vertices": int(cols.sum()), "mediana_mm": round(float(np.median(d)), 2),
                           "p95_mm": round(float(np.percentile(d, 95)), 2), "max_mm": round(float(d.max()), 2),
                           "normal_mediana_mm": round(float(np.median(dn)), 2), "normal_p5_mm": round(float(np.percentile(dn, 5)), 2),
                           "normal_p95_mm": round(float(np.percentile(dn, 95)), 2),
                           "piores_quadros": [int(frames[i]) for i in np.argsort(per_frame)[-5:][::-1]]})
    border_frame = (D[:, (ring_of[sel] == 0) & (cut_of[sel] == ci)] * 1000).max(axis=1)
    r["borda_max_por_quadro_mm"] = [round(float(v), 1) for v in border_frame]
    rep["cortes"][k] = r
    a0 = r["aneis"][0]
    print(k, "borda: mediana", a0["mediana_mm"], "p95", a0["p95_mm"], "max", a0["max_mm"], "| anel 4:", r["aneis"][4]["mediana_mm"],
          r["aneis"][4]["p95_mm"], "| anel 8:", r["aneis"][8]["mediana_mm"], r["aneis"][8]["p95_mm"], "| anel 12:",
          r["aneis"][12]["mediana_mm"], r["aneis"][12]["p95_mm"])
json.dump(rep, open(out, "w"), indent=1)
