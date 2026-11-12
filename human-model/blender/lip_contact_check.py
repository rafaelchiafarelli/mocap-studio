"""How the lips meet on a face driven by the mouth faders, frame by frame (initiative animation-face, epic lip-contact). Run with --blend on a faders file. Args: out.json [sections_dir]
Per frame: the gap between the lips in 2 mm strips across the mouth (the lower lip's closest point to the upper lip's skin, negative when inside it), the share of the width that
touches and the gap at the centre; the lower lip against the upper teeth; the deepest lip point inside either set of teeth. With sections_dir, an SVG of the cut through the mouth's
middle (skin, teeth) at each M and F, in profile. Then, at each M (also P and B) and F in the script, the values near its time. Lips are the body's `lips` group, upper or lower by the lip.T and lip.B weights."""
import json, os, sys
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
import posed_mesh as pm

a = hb.args()
scene = bpy.context.scene
body, teeth = bpy.data.objects["HM_body"], bpy.data.objects["HM_teeth"]
STRIP_M, TOUCH_M = 0.002, 0.0005  # strips across the mouth; a strip touches when its gap is under this
NEAR_FRAMES = 2  # a sound's value is the best within this many frames of its time, since the faders' bells and the tracked opening shift it a little


def weights(obj, prefix):
    names = {g.index for g in obj.vertex_groups if g.name.startswith(prefix)}
    w = np.zeros(len(obj.data.vertices))
    for v in obj.data.vertices:
        for g in v.groups:
            if g.group in names:
                w[v.index] += g.weight
    return w


def group(obj, name):
    gi = obj.vertex_groups[name].index
    w = np.zeros(len(obj.data.vertices))
    for v in obj.data.vertices:
        for g in v.groups:
            if g.group == gi:
                w[v.index] = g.weight
    return w


lips = group(body, "lips")[: pm.N_BODY]
top, bottom = weights(body, "lip.T")[: pm.N_BODY], weights(body, "lip.B")[: pm.N_BODY]
upper_lip = np.nonzero((lips > 0.5) & (top > bottom))[0]
lower_lip = np.nonzero((lips > 0.5) & (bottom > top))[0]
tris = pm.triangles(body)
upper_tris = tris[np.isin(tris, upper_lip).all(axis=1)]
teeth_top = weights(teeth, "teeth.T") > 0.5
teeth_tris = [list(p.vertices) for p in teeth.data.polygons]
upper_teeth_tris = [t for t in teeth_tris if teeth_top[t].all()]
for o in (body, teeth):
    pm.set_display(o, False)


def teeth_now():
    ev = teeth.evaluated_get(bpy.context.evaluated_depsgraph_get())
    V = np.array([teeth.matrix_world @ v.co for v in ev.data.vertices])
    return V


rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")


def in_head(points):
    """World points in the head's frame at the rest frame's placement, so the head's turns and nods don't move the strips or the cut."""
    m = np.array(head_rest @ (rig.matrix_world @ rig.pose.bones["spine.006"].matrix).inverted())
    return points @ m[:3, :3].T + m[:3, 3]


def signed(tree, points):
    """Distance from each point to the tree's surface along its normal: negative inside."""
    out = []
    for p in points:
        loc, normal, _, _ = tree.find_nearest(Vector(p))
        out.append((Vector(p) - loc).dot(normal) if loc is not None else np.inf)
    return np.array(out)


scene.frame_set(scene.frame_start)
head_rest = (rig.matrix_world @ rig.pose.bones["spine.006"].matrix).copy()
rest = pm.read(body)[: pm.N_BODY]
centre_x = float(rest[np.concatenate([upper_lip, lower_lip]), 0].mean())
half_width = float(np.abs(rest[lower_lip, 0] - centre_x).max())
first, last = scene.frame_start, scene.frame_end
rows = []
for f in range(first, last + 1):
    scene.frame_set(f)
    V = in_head(pm.read(body)[: pm.N_BODY])
    T = in_head(teeth_now())
    lip_tree = BVHTree.FromPolygons([Vector(x) for x in V], upper_tris.tolist())
    all_teeth = BVHTree.FromPolygons([Vector(x) for x in T], teeth_tris)
    top_teeth = BVHTree.FromPolygons([Vector(x) for x in T], upper_teeth_tris)
    gap = signed(lip_tree, V[lower_lip])
    xs = V[lower_lip, 0] - centre_x
    strips = {}
    for x, g in zip(xs, gap):
        k = int(np.floor(x / STRIP_M))
        strips[k] = min(strips.get(k, np.inf), g)
    inner = [k for k in strips if abs(k * STRIP_M) < half_width - STRIP_M]  # leaves the corners out, where the lips always join
    touching = sum(strips[k] < TOUCH_M for k in inner) / max(1, len(inner))
    centre = min(strips.get(k, np.inf) for k in (-1, 0))
    to_top_teeth = signed(top_teeth, V[lower_lip])
    in_teeth = signed(all_teeth, V[np.concatenate([upper_lip, lower_lip])])
    rows.append({"frame": f, "lip_gap_mm": float(min(strips[k] for k in inner) * 1000), "centre_gap_mm": float(centre * 1000), "width_touching": float(touching), "strips_mm": [[round(k * STRIP_M * 1000), round(float(strips[k]) * 1000, 2)] for k in sorted(strips)], "lower_lip_to_upper_teeth_mm": float(to_top_teeth.min() * 1000),
                 "lip_into_teeth_mm": float(max(0.0, -in_teeth.min()) * 1000)})
for o in (body, teeth):
    pm.set_display(o, True)

d = json.loads(bpy.data.texts["mouth_data.json"].as_string())
fps = d["fps"]
events = []
for t, g, _ in d["script"]:
    if g not in ("M", "F"):
        continue
    f0 = int(round(t * fps)) + first
    near = [r for r in rows if abs(r["frame"] - f0) <= NEAR_FRAMES]
    if g == "M":
        best = max(near, key=lambda r: r["width_touching"])
        events.append({"sound": g, "time_s": t, "frame": best["frame"], "width_touching": round(best["width_touching"], 2), "centre_gap_mm": round(best["centre_gap_mm"], 2), "narrowest_strip_gap_mm": round(best["lip_gap_mm"], 2)})
    else:
        best = min(near, key=lambda r: abs(r["lower_lip_to_upper_teeth_mm"]))
        events.append({"sound": g, "time_s": t, "frame": best["frame"], "lower_lip_to_upper_teeth_mm": round(best["lower_lip_to_upper_teeth_mm"], 2)})
def section(verts, polys, x0, centre, colour_of):
    """The cut of a mesh by the plane x = x0, as segments, one per face crossed, near `centre`, coloured per face."""
    out = []
    for k, poly in enumerate(polys):
        P = verts[poly]
        d = P[:, 0] - x0
        pts = []
        for i in range(len(poly)):
            j = (i + 1) % len(poly)
            if d[i] * d[j] < 0:
                pts.append(P[i] + d[i] / (d[i] - d[j]) * (P[j] - P[i]))
        if len(pts) == 2 and all(abs(q[1] - centre[1]) < 0.035 and abs(q[2] - centre[2]) < 0.035 for q in pts):
            out.append((pts[0], pts[1], colour_of(k)))
    return out


if len(a) > 1:
    os.makedirs(a[1], exist_ok=True)
    body_polys = [list(p.vertices) for p in body.data.polygons if max(p.vertices) < pm.N_BODY]
    teeth_colour = lambda k: "#3060c0" if teeth_top[teeth_tris[k]].all() else "#30a050"
    mouth = rest[np.concatenate([upper_lip, lower_lip])].mean(axis=0)
    for o in (body, teeth):
        pm.set_display(o, False)
    shots = [{"sound": "rest", "time_s": 0.0, "frame": first}] + events
    for e in shots:
        scene.frame_set(e["frame"])
        V, T = in_head(pm.read(body)[: pm.N_BODY]), in_head(teeth_now())
        scale = 10000  # px per metre: 1 mm is 10 px
        svg = []
        for x_off, dx in ((0.0, 0), (0.008, 700)):
            segs = section(V, body_polys, centre_x + x_off, mouth, lambda k: "#b04030") + section(T, teeth_tris, centre_x + x_off, mouth, teeth_colour)
            for p0, p1, c in segs:
                to = lambda q: (dx + 350 + (q[1] - mouth[1]) * scale, 350 - (q[2] - mouth[2]) * scale)
                (x0, y0), (x1, y1) = to(p0), to(p1)
                svg.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{c}" stroke-width="2"/>')
            svg.append(f'<text x="{dx + 10}" y="24" font-size="18">{"centre" if not x_off else "8 mm to the side"}</text>')
        label = f'{e["sound"]} at {e["time_s"]:.2f} s, frame {e["frame"]}. Skin red, upper teeth blue, lower teeth green. 1 mm = 10 px. Face to the left.'
        open(os.path.join(a[1], f'{e["frame"]:04d}_{e["sound"]}.svg'), "w").write(f'<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="740"><rect width="100%" height="100%" fill="#fff"/><text x="10" y="725" font-size="18">{label}</text>{"".join(svg)}</svg>')
    for o in (body, teeth):
        pm.set_display(o, True)
report = {"upper_lip_vertices": int(len(upper_lip)), "lower_lip_vertices": int(len(lower_lip)), "upper_teeth_faces": len(upper_teeth_tris),
          "frames_lips_crossing": sum(r["lip_gap_mm"] < -0.5 for r in rows), "deepest_crossing_mm": round(min(r["lip_gap_mm"] for r in rows), 2),
          "lower_lip_to_upper_teeth_mm_other_frames_median": round(float(np.median([r["lower_lip_to_upper_teeth_mm"] for r in rows])), 2),
          "frames_lip_in_teeth": sum(r["lip_into_teeth_mm"] > 0.5 for r in rows), "deepest_in_teeth_mm": round(max(r["lip_into_teeth_mm"] for r in rows), 2),
          "events": events, "frames": rows}
json.dump(report, open(a[0], "w"), indent=1)
print("RESULT", json.dumps({k: v for k, v in report.items() if k != "frames"}))
