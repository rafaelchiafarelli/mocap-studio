"""Muscle volumes per muscle at rest and in test poses. Args: out.json. Run with --blend. Pose: jaw_open, mid-gait flex, face contractions."""
import json, math, os, sys
import bpy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
import posing as P
out = hb.args()[0]
rig = bpy.data.objects["HM_rig"]
ctrl = bpy.data.objects["HM_controls"]
ob = bpy.data.objects["HM_muscles"]
groups = {g.index: g.name for g in ob.vertex_groups}
owner = np.empty(len(ob.data.vertices), np.int64)
for v in ob.data.vertices:
    owner[v.index] = v.groups[0].group
polys = [tuple(p.vertices) for p in ob.data.polygons]


def eval_all():
    ctrl.update_tag()
    rig.update_tag()
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    return hb.evaluated_verts(ob)


def volumes(vs):
    res = {}
    for f in polys:
        g = owner[f[0]]
        a = vs[f[0]]
        tot = 0.0
        for i in range(1, len(f) - 1):
            tot += np.dot(a, np.cross(vs[f[i]], vs[f[i + 1]])) / 6
        res[g] = res.get(g, 0.0) + tot
    # absolute per segment, then per muscle
    per = {}
    for g, v in res.items():
        name = groups[g].rsplit(".", 1)[0]
        per[name] = per.get(name, 0.0) + abs(v)
    return per


rest = volumes(eval_all())
tests = {}


def run(label, setter):
    P.reset(rig)
    for k in list(ctrl.keys()):
        if isinstance(ctrl[k], float):
            ctrl[k] = 0.0
    setter()
    vol = volumes(eval_all())
    ratio = {k: vol[k] / rest[k] for k in rest if rest[k] > 1e-9}
    r = np.array(list(ratio.values()))
    worst = sorted(ratio.items(), key=lambda kv: abs(kv[1] - 1))[-5:]
    tests[label] = {"min": float(r.min()), "max": float(r.max()), "worst": worst}
    print(label, round(r.min(), 3), round(r.max(), 3), worst[-2:])


def jaw():
    ctrl["jaw_open"] = 1.0


def smile():
    for s in "LR":
        ctrl[f"m_zygomaticus_major_{s}"] = 1.0


def frown():
    for k in ctrl.keys():
        if k.startswith("m_frontalis"):
            ctrl[k] = 1.0


def hipknee():
    P.set_rotation(rig, "thigh.L", P.rx(-70))
    P.set_rotation(rig, "shin.L", P.rx(90))
    P.set_rotation(rig, "foot.L", P.rx(20))


def elbow():
    P.set_rotation(rig, "forearm.L", P.rx(-90))
    P.set_rotation(rig, "upper_arm.L", P.rx(-60))


run("jaw open", jaw)
run("smile", smile)
run("brows up", frown)
run("hip and knee flexed", hipknee)
run("arm and elbow", elbow)
total = {"rest_litres": float(sum(rest.values()) * 1000), "tests": tests, "rest": rest}
json.dump(total, open(out, "w"), indent=0)
