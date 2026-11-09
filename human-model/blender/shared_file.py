"""The file with every fast_review run, linked, each in a strip of its own along X. Run with --blend SHARED.blend if it exists.
Args: add SHARED.blend NICKNAME PAIR.blend, or remove SHARED.blend NICKNAME. Each run keeps its own file, so deleting the shared one loses nothing."""
import json, os, sys
import bpy

STRIP = 6.0  # m along X between runs: a run's four columns take 3 m, and the bodies walk about 6 m along Y
KEY = "hm_runs"
action, shared, nickname, *rest = sys.argv[sys.argv.index("--") + 1:]
scene = bpy.context.scene
if not bpy.data.filepath:  # a new file: Blender's startup scene has a cube, a camera and a light
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
runs = json.loads(scene.get(KEY, "{}"))


def save():
    scene[KEY] = json.dumps(runs)
    bpy.ops.wm.save_as_mainfile(filepath=shared)


def look_at_the_runs():
    """Every saved view turns around the first strip: a view left at the origin zoomed into empty space (bug human-model/31)."""
    middle = STRIP * (max(r["strip"] for r in runs.values()) / 2 if runs else 0)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                r = area.spaces.active.region_3d
                r.view_location = (middle, -2.5, 0.9)
                r.view_distance = max(8.0, STRIP * len(runs) * 0.9)


def add(pair):
    if nickname in runs:
        raise SystemExit(f"{nickname} is already in the shared file")
    taken = {r["strip"] for r in runs.values()}
    strip = next(i for i in range(len(taken) + 1) if i not in taken)  # the first free one, so removing a run doesn't push the next ones away
    with bpy.data.libraries.load(pair, link=True) as (source, target):
        target.collections = [c for c in source.collections if c.endswith((" pele", " corte"))]
    holder = bpy.data.collections.new(f"run_{nickname}")
    scene.collection.children.link(holder)
    for col in target.collections:
        e = bpy.data.objects.new(f"{nickname}: {col.name}", None)
        e.instance_type, e.instance_collection = "COLLECTION", col
        e.location = (strip * STRIP, 0.0, 0.0)
        e.hide_viewport = col.name.endswith(" corte")  # the sections hold most of the triangles: off until asked for
        holder.objects.link(e)
    runs[nickname] = {"strip": strip, "file": pair}
    scene.frame_start, scene.frame_end = 1, max(int(a.frame_range[1]) for a in bpy.data.actions)
    look_at_the_runs()
    save()


def remove():
    if nickname not in runs:
        raise SystemExit(f"{nickname} isn't in the shared file")
    holder = bpy.data.collections[f"run_{nickname}"]
    libraries = {e.instance_collection.library for e in holder.objects if e.instance_collection}
    for ob in list(holder.objects):
        bpy.data.objects.remove(ob)
    bpy.data.collections.remove(holder)
    for library in libraries:
        bpy.data.libraries.remove(library)
    del runs[nickname]
    if runs:
        scene.frame_start, scene.frame_end = 1, max(int(a.frame_range[1]) for a in bpy.data.actions)
    look_at_the_runs()
    save()


if action == "add":
    add(rest[0])
elif action == "remove":
    remove()
else:
    raise SystemExit(f"unknown action {action}")
print("shared", list(runs))
