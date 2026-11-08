"""A walk file's root per frame and how its planted foot slides or leaves the floor (task muscle-physics/body-walk/2). Run with --blend WALK.blend; arg: OUT.json"""
import bpy, json, sys
import numpy as np
out = sys.argv[sys.argv.index("--") + 1]
rig = bpy.data.objects["HM_rig"]
sc = bpy.context.scene
rows = []
for f in range(sc.frame_start, sc.frame_end + 1):
    sc.frame_set(f)
    M = rig.matrix_world
    pts = []
    for s in "LR":
        pb = rig.pose.bones
        for name, p, off in ((f"heel.{s}", pb[f"foot.{s}"].head, 0.065), (f"ball.{s}", pb[f"toe.{s}"].head, 0.008), (f"toe.{s}", pb[f"toe.{s}"].tail, 0.0)):
            w = M @ p
            pts.append((name, w.x, w.y, w.z - off))
    rows.append({"frame": f, "root": list(rig.location), "pts": pts})
root = np.array([r["root"] for r in rows])
dz, dy = np.abs(np.diff(root[:, 2])), np.abs(np.diff(root[:, 1]))
low = [min(r["pts"], key=lambda p: p[3]) for r in rows]
floor = np.array([l[3] for l in low])
slide = []
for a, b, ra, rb in zip(low, low[1:], rows, rows[1:]):
    if a[0] == b[0]:
        slide.append(abs(b[2] - a[2]))
slide = np.array(slide)
# each foot's lowest point per frame: both down (within 3 mm) is double support
per_foot = np.array([[min(p[3] for p in r["pts"] if p[0].endswith(f".{s}")) for s in "LR"] for r in rows])
both = (per_foot < 0.003).all(axis=1)
res = {"frames": len(rows), "root_z_step_mm": {"max": dz.max() * 1000, "median": float(np.median(dz)) * 1000},
       "root_y_step_mm": {"max": dy.max() * 1000, "median": float(np.median(dy)) * 1000, "min": dy.min() * 1000},
       "bounce_cm": float(np.ptp(root[:, 2])) * 100, "lowest_point_height_mm": {"min": floor.min() * 1000, "max": floor.max() * 1000},
       "frames_both_feet_down": int(both.sum()), "lowest_by_foot_mm": (per_foot * 1000).round(1).tolist(), "double_support_share": float(both.mean()), "planted_slide_mm_per_frame": {"max": float(slide.max()) * 1000, "median": float(np.median(slide)) * 1000},
       "root_z_mm": (root[:, 2] * 1000).round(1).tolist(), "root_y_step_series_mm": (dy * 1000).round(1).tolist()}
json.dump(res, open(out, "w"), indent=1)
print({k: v for k, v in res.items() if not k.endswith("series_mm") and k != "root_z_mm"})
