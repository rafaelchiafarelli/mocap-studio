"""A plain stage for judging motion: a floor in 0.5 m squares and a gridded wall behind the body, a fixed camera, frames
for a video. Rafael (2026-11-14): the body needs a background as a reference for its motion.

    python3 human-model/blender_run.py --blend IN.blend human-model/investigations/pose-capture/stage_video.py FRAMES_DIR [OUT.blend] [--view frente|lado|costas] [--no-frames]

The camera stands 3.6 m from where the hips are on average, at their mean height, and doesn't move, so travel, sway and
bounce show against the grid. Workbench, as blender/simple_video.py. OUT.blend, if given, keeps the stage for Blender;
--no-frames saves it without rendering (FRAMES_DIR is then ignored).
Lines every 0.5 m, a darker one every metre; the wall stands 1.5 m behind the hips' mean position.
"""
import os, sys
import bpy
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])), "..", "..", "blender"))
import hmblender as hb

argv = sys.argv[sys.argv.index("--") + 1:]
view = "frente"
NO_FRAMES = "--no-frames" in argv
argv = [a for a in argv if a != "--no-frames"]
if "--view" in argv:
    i = argv.index("--view")
    view = argv[i + 1]
    argv = argv[:i] + argv[i + 2:]
frames_dir = argv[0]
out_blend = argv[1] if len(argv) > 1 else None

rig = bpy.data.objects["HM_rig"]
scene = bpy.context.scene
hips = []
for f in range(scene.frame_start, scene.frame_end + 1):
    scene.frame_set(f)
    hips.append(np.array(rig.matrix_world @ rig.pose.bones["spine"].head))
hips = np.array(hips)
centre = hips.mean(0)
DIRS = {"frente": np.array([0.0, -1.0, 0.0]), "costas": np.array([0.0, 1.0, 0.0]), "lado": np.array([1.0, 0.0, 0.0])}
look = DIRS[view]  # from the hips towards the camera


def material(name, rgb):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1.0)
    return m


def box(name, centre_xyz, size, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=centre_xyz)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = size
    ob.data.materials.append(mat)
    ob.users_collection[0].objects.unlink(ob)
    stage.objects.link(ob)
    return ob


stage = bpy.data.collections.new("HM_stage")
scene.collection.children.link(stage)
floor_m, line_m, metre_m, wall_m = material("stage_floor", (0.78, 0.78, 0.76)), material("stage_line", (0.45, 0.45, 0.45)), \
    material("stage_metre", (0.2, 0.2, 0.2)), material("stage_wall", (0.88, 0.88, 0.9))
HALF, STEP, T = 3.0, 0.5, 0.008  # stage half-size, line spacing, line width (m)
cx, cy = round(centre[0] / STEP) * STEP, round(centre[1] / STEP) * STEP
box("stage_floor", (cx, cy, -0.006), (2 * HALF, 2 * HALF, 0.01), floor_m)
ticks = np.arange(-HALF, HALF + 1e-6, STEP)
for k in ticks:
    m = metre_m if abs(k - round(k)) < 1e-6 else line_m
    box("stage_x", (cx + k, cy, 0.0005), (T, 2 * HALF, 0.002), m)
    box("stage_y", (cx, cy + k, 0.0005), (2 * HALF, T, 0.002), m)
# the wall: behind the body as the camera sees it, facing the camera
side = np.array([-look[1], look[0], 0.0])  # along the wall
w0 = np.array([cx, cy, 0.0]) - look * 1.5
thick = np.abs(look) * 0.01 + np.abs(side) * 2 * HALF
box("stage_wall", tuple(w0 + np.array([0, 0, 1.25]) - look * 0.01), tuple(thick + np.array([0, 0, 2.5])), wall_m)
for k in ticks:
    m = metre_m if abs(k - round(k)) < 1e-6 else line_m
    box("stage_wall_v", tuple(w0 + side * k + np.array([0, 0, 1.25])), tuple(np.abs(look) * 0.004 + np.abs(side) * T + np.array([0, 0, 2.5])), m)
for z in np.arange(0.0, 2.5 + 1e-6, STEP):
    m = metre_m if abs(z - round(z)) < 1e-6 else line_m
    box("stage_wall_h", tuple(w0 + np.array([0, 0, z])), tuple(np.abs(look) * 0.004 + np.abs(side) * 2 * HALF + np.array([0, 0, T])), m)

scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light, scene.display.shading.color_type = "STUDIO", "MATERIAL"
scene.render.resolution_x, scene.render.resolution_y = 540, 960
target = np.array([centre[0], centre[1], 0.95])
cam = hb.camera_look("HM_stage_cam", tuple(target + look * 3.6), tuple(target), lens=40)
scene.camera = cam
if out_blend:
    bpy.ops.wm.save_as_mainfile(filepath=out_blend, compress=True)
if NO_FRAMES:
    print("hips travel (m)", np.round(hips.max(0) - hips.min(0), 3).tolist())
    sys.exit(0)
os.makedirs(frames_dir, exist_ok=True)
for f in range(scene.frame_start, scene.frame_end + 1):
    scene.frame_set(f)
    scene.render.filepath = os.path.join(frames_dir, f"{f:04d}.png")
    bpy.ops.render.render(write_still=True)
print("frames", scene.frame_end - scene.frame_start + 1, "hips travel (m)", np.round(hips.max(0) - hips.min(0), 3).tolist())
