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


def add(pair):
    if nickname in runs:
        raise SystemExit(f"{nickname} is already in the shared file")
    strip = 1 + max((r["strip"] for r in runs.values()), default=-1)
    with bpy.data.libraries.load(pair, link=True) as (source, target):
        target.collections = [c for c in source.collections if c.endswith((" pele", " corte"))]
    holder = bpy.data.collections.new(f"run_{nickname}")
    scene.collection.children.link(holder)
    for col in target.collections:
        e = bpy.data.objects.new(f"{nickname}: {col.name}", None)
        e.instance_type, e.instance_collection = "COLLECTION", col
        e.location = (strip * STRIP, 0.0, 0.0)
        holder.objects.link(e)
    scene.frame_end = max(scene.frame_end, max(int(a.frame_range[1]) for a in bpy.data.actions)) if bpy.data.actions else scene.frame_end
    runs[nickname] = {"strip": strip, "file": pair}
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
    save()


if action == "add":
    add(rest[0])
elif action == "remove":
    remove()
else:
    raise SystemExit(f"unknown action {action}")
print("shared", list(runs))
