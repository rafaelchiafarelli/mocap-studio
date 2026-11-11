"""Adds pose_corrections.py's corrections to another file of the same body, with its volume-preserving skinning. Run with --blend. Args: corrections.npz out.blend"""
import json, os, sys
import bpy
import numpy as np
HERE = os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1]))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
import corrections_common as cc
import hmblender as hb
import posed_mesh as pm

a = hb.args()
data = np.load(a[0], allow_pickle=False)
definitions = json.loads(str(data["definitions"]))
rig, body = bpy.data.objects["HM_rig"], bpy.data.objects["HM_body"]
cc.preserve_volume(body, rig)
deltas = {k[len("delta_"):]: data[k] for k in data.files if k.startswith("delta_")}
pm.set_display(body, False)
bpy.context.scene.frame_set(1)
x = pm.read(body)[: pm.N_BODY, 0]
cc.apply(body, rig, deltas, definitions, x)
pm.set_display(body, True)
bpy.ops.wm.save_as_mainfile(filepath=a[1])
print("applied", sorted(deltas))
