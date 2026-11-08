"""Two walked bodies of body_walk_bake.py in one file, without the current model's skin. Run with --blend FIRST.blend; args: SECOND.blend OUT.blend FIRST_NAME SECOND_NAME
Four columns along X, a metre apart: the first's skin, the second's skin, the first's section, the second's. They play without simulating."""
import sys
import bpy

second, out, first_name, second_name = sys.argv[sys.argv.index("--") + 1:][:4]
SPACING = 1.0  # m
scene = bpy.context.scene
with bpy.data.libraries.load(second, link=False) as (source, target):
    target.collections = [c for c in source.collections if c in ("walk_compare", "walk_inside")]
    target.scenes = []
for c in target.collections:
    scene.collection.children.link(c)


def column(collection, label, x):
    """Renames a collection and carries it to its column, leaving out the current model's skin."""
    for ob in list(collection.objects):
        if ob.name.startswith("skin_current"):
            bpy.data.objects.remove(ob, do_unlink=True)
    collection.name = label
    anchor = bpy.data.objects.new(f"{label}_anchor", None)
    anchor.location = (x, 0, 0)
    collection.objects.link(anchor)
    for ob in collection.objects:
        ob.hide_render = False
        ob.hide_viewport = False
        ob.hide_set(False)
        if ob is not anchor and ob.parent is None:
            ob.parent = anchor


first_compare = bpy.data.collections["walk_compare"]
first_inside = bpy.data.collections["walk_inside"]
second_compare = next(c for c in target.collections if "compare" in c.name)  # the library lists them in its own order
second_inside = next(c for c in target.collections if "inside" in c.name)
column(first_compare, f"{first_name} pele", 0 * SPACING)
column(second_compare, f"{second_name} pele", 1 * SPACING)
column(first_inside, f"{first_name} corte", 2 * SPACING)
column(second_inside, f"{second_name} corte", 3 * SPACING)
scene.frame_end = int(max(scene.frame_end, *(a.frame_range[1] for a in bpy.data.actions)))
bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
print("pair", [c.name for c in scene.collection.children], "frames", scene.frame_end)
