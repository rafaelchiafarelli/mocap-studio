"""Puts an Audio2Face-3D mouth on a faders file, for comparing the two on the same face (initiative animation-face, epic audio-to-face; Rafael, 2026-11-13).
Run in Blender on a faders .blend: -- A2F_ARKIT.json out.blend. The JSON is experiments/face-history/audio2face/a2f_solve.py's output (60 fps).
Every jaw, mouth, cheekPuff and tongue channel comes from Audio2Face, resampled to the scene's rate from the audio's start at the scene's first frame; the faders' own
lipBite and tongueUp, which move bones, are set to 0. Eyes, brows and head stay as tracked."""
import json, sys
import bpy
import numpy as np

src, out = sys.argv[sys.argv.index("--") + 1:][:2]
d = json.load(open(src))
rate = d["fps_num"] / d["fps_den"]
scene = bpy.context.scene
fps = scene.render.fps / scene.render.fps_base
frames = np.arange(scene.frame_start, scene.frame_end + 1)
t = (frames - scene.frame_start) / fps
MOUTH = ("jaw", "mouth", "cheekPuff", "tongue")
channels = {k: np.interp(t * rate, np.arange(len(v)), np.array(v)) for k, v in d["channels"].items() if k.startswith(MOUTH)}
ctrl = next(o for o in bpy.data.objects if o.type == "EMPTY" and "jawOpen" in o.keys())


# the faders' control: its channels become Audio2Face's, the rest 0; the drivers carry them to the shapes, so the mouth faders' panel no longer applies here
ad = ctrl.animation_data
if ad and ad.action:
    ad.action = None
done = []
for k in ctrl.keys():
    if k.startswith("_"):
        continue
    values = channels.get(k, np.zeros(len(frames)))
    for f, v in zip(frames, values):
        ctrl[k] = float(v)
        ctrl.keyframe_insert(f'["{k}"]', frame=int(f))
    done.append(k)
# channels the faders don't have: keyed on each mesh's shape of that name
direct = []
for o in bpy.data.objects:
    if o.type != "MESH" or not o.data.shape_keys:
        continue
    keys = o.data.shape_keys
    for k, values in channels.items():
        if k in done or k not in keys.key_blocks:
            continue
        kb = keys.key_blocks[k]
        path = f'key_blocks["{k}"].value'
        if keys.animation_data:
            for fc in list(keys.animation_data.drivers):
                if fc.data_path == path:
                    keys.animation_data.drivers.remove(fc)
            if keys.animation_data.action:
                for fc in list(getattr(keys.animation_data.action, "fcurves", [])):
                    if fc.data_path == path:
                        keys.animation_data.action.fcurves.remove(fc)
        for f, v in zip(frames, values):
            kb.value = float(v)
            kb.keyframe_insert("value", frame=int(f))
        direct.append(f"{o.name}:{k}")
bpy.ops.wm.save_as_mainfile(filepath=out)
print("RESULT control channels", done, "direct", direct)
