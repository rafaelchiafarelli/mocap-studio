"""Opened on a fader .blend, never saved. Args: presets folder, stills prefix, metrics JSON.
Measures each preset, proves a fader reaches the mesh, saves preset C's curves and renders fixed moments."""
import glob, json, os, sys, time
import bpy
import numpy as np
import addon_utils
addon_utils.enable("bl_ext.user_default.mouth_faders", default_set=False)
import bl_ext.user_default.mouth_faders as mf
folder, prefix, out = sys.argv[sys.argv.index("--") + 1:][:3]
s = bpy.context.scene; p = s.mouth_faders; d = mf.data()
fps = d["fps"]; T = np.arange(d["frames"]) / fps; tr = np.array(d["tracked_jaw"]); sp = T < 15.2
MF = [(t, g) for t, g, _ in d["script"] if g in ("M", "F")]
idx = lambda t: int(t * fps)
def reset():
    for k in mf._fields:
        if k != "preset_path":
            p.property_unset(k)
result = {"presets": {}, "frames": d["frames"]}
for f in sorted(glob.glob(os.path.join(folder, "*.json"))):
    reset(); mf.apply_dict(p, json.load(open(f)))
    r = mf.compute(d, p); j = r["jawOpen"]
    result["presets"][os.path.basename(f)] = {
        "corr_jaw_video": float(np.corrcoef(j[sp], tr[sp])[0, 1]),
        "jaw_at_M": float(np.mean([j[idx(t)] for t, g in MF if g == "M"])),
        "jaw_at_F": float(np.mean([j[idx(t)] for t, g in MF if g == "F"])),
        "lip_tuck_at_F": float(np.mean([r["lipBite"][idx(t)] for t, g in MF if g == "F"])),
        "press_at_M": float(np.mean([r["mouthPressLeft"][idx(t)] for t, g in MF if g == "M"])),
        "jaw_max": float(j.max()),
    }
    if os.path.basename(f).startswith("C_"):
        result["curves_C"] = {k: [round(float(x), 4) for x in v] for k, v in r.items()}
body = max((o for o in bpy.data.objects if o.type == "MESH" and o.data.shape_keys), key=lambda o: len(o.data.shape_keys.key_blocks)).data.shape_keys.key_blocks
c = os.path.join(folder, "C_roteiro_video.json")
reset(); mf.apply_dict(p, json.load(open(c))); mf.bake(s)
f = int(9.3 * fps) + 1
s.frame_set(f); a = body["jawOpen"].value
p.jaw_gain = 0.5; p.tracked_mix = 0.0; p.tracked_close = 0.0; mf.bake(s); s.frame_set(f); b = body["jawOpen"].value
result["fader_reaches_mesh"] = [round(a, 3), round(b, 3)]
reset(); mf.apply_dict(p, json.load(open(c))); mf.bake(s)
result["missing_images"] = sorted(i.name for i in bpy.data.images if i.source == "FILE" and not os.path.exists(bpy.path.abspath(i.filepath)))
s.cycles.samples = 24; s.cycles.seed = 0; s.render.resolution_percentage = 60
cp = bpy.context.preferences.addons["cycles"].preferences; cp.compute_device_type = "OPTIX"; cp.get_devices()
for dv in cp.devices:
    dv.use = dv.type == "OPTIX"
s.cycles.device = "GPU"; s.render.image_settings.file_format = "JPEG"
for name, t in (("rest", 0.5), ("P", 3.6), ("O", 3.72), ("F1", 4.8), ("F2", 9.21), ("A", 9.3), ("L", 9.39), ("F3", 14.46)):
    s.frame_set(int(t * fps) + 1); s.render.filepath = f"{prefix}{name}.jpg"; bpy.ops.render.render(write_still=True)
json.dump(result, open(out, "w"))
print("RESULT", {k: {m: round(v, 3) for m, v in x.items()} for k, x in result["presets"].items()}, "fader", result["fader_reaches_mesh"], "missing", result["missing_images"])
