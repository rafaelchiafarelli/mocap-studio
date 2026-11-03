"""Read-only inventory of a reference .blend: writes one JSON row per mesh with its collections and vertex count."""
import json, sys
import bpy
out = sys.argv[sys.argv.index("--") + 1]
rows, seen = [], set()
for o in bpy.data.objects:
    cols = sorted(c.name for c in o.users_collection)
    parents = []
    for c in bpy.data.collections:
        if any(k.name in cols for k in c.children):
            parents.append(c.name)
    rows.append({"name": o.name, "type": o.type, "verts": len(o.data.vertices) if o.type == "MESH" else 0, "collections": cols, "parents": parents, "mesh": o.data.name if o.data else None})
tree = {c.name: [k.name for k in c.children] for c in bpy.data.collections}
json.dump({"objects": rows, "tree": tree, "roots": [c.name for c in bpy.context.scene.collection.children]}, open(out, "w"))
print("objects", len(rows))
