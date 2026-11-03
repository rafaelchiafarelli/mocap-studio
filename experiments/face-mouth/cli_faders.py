"""Command line: blender -b FILE.blend --python cli_faders.py -- preset=PATH offset_ms=-40 ... out=OUTPUT.blend"""
import json, sys
import bpy
import addon_utils
addon_utils.enable("bl_ext.user_default.mouth_faders", default_set=False)
import bl_ext.user_default.mouth_faders as mf
s = bpy.context.scene; p = s.mouth_faders
args = dict(a.split("=", 1) for a in sys.argv[sys.argv.index("--") + 1:])
out = args.pop("out", None); preset = args.pop("preset", None)
if preset:
    mf.apply_dict(p, json.load(open(preset)))
mf.apply_dict(p, {k: (v if k == "source" else float(v)) for k, v in args.items()})
mf.bake(s)
print("RESULT params", mf.params_dict(p))
if out:
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print("RESULT saved", out)
