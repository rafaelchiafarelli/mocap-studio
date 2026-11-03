"""Puts each joint at its limits and checks that bones don't pass through each other. Args: out.json. Run with --blend."""
import json, os, sys
import bpy
import numpy as np
from mathutils import Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
import posing as P

out = hb.args()[0]
rig = bpy.data.objects["HM_rig"]
bones = [o for o in bpy.data.collections["HM_bones"].objects]
GROUPS = {"femur": "thigh", "patella": "shin", "tibia": "shin", "fibula": "shin"}
sex = rig.get("hm_sex", "male")


def bvh(o):
    M = o.matrix_world
    return BVHTree.FromPolygons([M @ v.co for v in o.data.vertices], [p.vertices[:] for p in o.data.polygons], all_triangles=False)


def overlaps(names_a, names_b, trees):
    hits = []
    for a in names_a:
        for b in names_b:
            if a != b and trees[a].overlap(trees[b]):
                hits.append((a, b))
    return hits


def limb(side, stems):
    return [o.name for o in bones if o.name.endswith(f"_{side}") and o.name.rsplit("_", 1)[0].rstrip("0123456789") in stems]


# (label, bone, rotation, moving bones, static bones it could hit)
UPPER = {"humerus", "ulna", "radius"}
LEG = {"femur", "patella", "tibia", "fibula", "talus", "calcaneus", "navicular", "cuboid"}
TRUNK = [o.name for o in bones if o.name.startswith(("rib_", "vertebra_", "hip_", "sacrum", "sternum", "cranium", "mandible", "scapula", "clavicle", "costal"))]
L = rig.data.bones["thigh.L"]
limits = {k[:-2]: rig.pose.bones[k].get("hm_limit_deg") for k in ("thigh.L", "shin.L", "foot.L", "upper_arm.L")}
lim = {k: list(v) for k, v in limits.items()}
results = []


def trial(label, setter, moving, static):
    P.reset(rig)
    setter()
    bpy.context.view_layer.update()
    trees = {o.name: bvh(o) for o in bones if o.name in moving or o.name in static}
    hits = overlaps(moving, static, trees)
    results.append({"pose": label, "hits": hits})
    print(label, len(hits), hits[:4])


for side, sgn in (("L", 1), ("R", -1)):
    leg = limb(side, LEG)
    arm = limb(side, UPPER)
    for name, d in (("flexion", lim["thigh"][0]), ("extension", lim["thigh"][1])):
        trial(f"hip {name} {side} {d}", lambda d=d, side=side: P.set_rotation(rig, f"thigh.{side}", P.rx(d)), leg, TRUNK)
    # the knee and ankle at limits, against their own limb's other segment
    femur = [f"femur_{side}"]
    shin = [f"tibia_{side}", f"fibula_{side}"]
    foot = [o.name for o in bones if o.name.endswith(f"_{side}") and o.parent_bone in (f"foot.{side}", f"toe.{side}")]
    trial(f"knee flexion {side} {lim['shin'][1]}", lambda side=side: P.set_rotation(rig, f"shin.{side}", P.rx(lim["shin"][1])), shin, femur)
    trial(f"ankle dorsiflexion {side} {lim['foot'][0]}", lambda side=side: P.set_rotation(rig, f"foot.{side}", P.rx(lim["foot"][0])), foot, shin)
    trial(f"ankle plantarflexion {side} {lim['foot'][1]}", lambda side=side: P.set_rotation(rig, f"foot.{side}", P.rx(lim["foot"][1])), foot, shin)
    for name, d in (("flexion", lim["upper_arm"][0] * 0.5), ("extension", lim["upper_arm"][1])):
        trial(f"shoulder {name} {side} {d}", lambda d=d, side=side: P.set_rotation(rig, f"upper_arm.{side}", P.rx(d)), [f"humerus_{side}"], TRUNK)
P.reset(rig)
json.dump(results, open(out, "w"), indent=0)
print("poses", len(results), "with hits", sum(1 for r in results if r["hits"]))
