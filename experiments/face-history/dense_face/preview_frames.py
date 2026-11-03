"""Opened on a test .blend. Args: output prefix, samples, frames ('all' or numbers). Renders frames for a preview."""
import sys, bpy
a = sys.argv[sys.argv.index("--") + 1:]
s = bpy.context.scene
prefs = bpy.context.preferences.addons["cycles"].preferences; prefs.compute_device_type = "OPTIX"; prefs.get_devices()
for d in prefs.devices: d.use = d.type == "OPTIX"
s.cycles.device = "GPU"; s.cycles.samples = int(a[1]); s.cycles.use_denoising = True; s.cycles.denoiser = "OPTIX"; s.render.use_sequencer = False
frames = range(s.frame_start, s.frame_end + 1) if a[2] == "all" else [int(x) for x in a[2:]]
for f in frames:
    s.frame_set(f); s.render.filepath = f"{a[0]}{f:04d}.png"; bpy.ops.render.render(write_still=True); print("RESULT frame", f, flush=True)
