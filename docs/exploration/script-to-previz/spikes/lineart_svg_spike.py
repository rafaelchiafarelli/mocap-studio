"""Spike 1: Line Art (Grease Pencil v3) -> SVG, one layer per collection?"""
import bpy, sys, math
from mathutils import Vector

out = sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080

def coll(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c

def add(prim, coll_, name, **kw):
    getattr(bpy.ops.mesh, prim)(**kw)
    o = bpy.context.active_object
    o.name = name
    for c in o.users_collection:
        c.objects.unlink(o)
    coll_.objects.link(o)
    return o

cen, per, prop = coll("Cenario"), coll("Personagens"), coll("Props")
add("primitive_plane_add", cen, "chao", size=12)
add("primitive_cube_add", cen, "parede", size=1, location=(0, 4, 1.5)).scale = (12, 0.2, 3)

def mannequin(name, x, y):
    add("primitive_cylinder_add", per, name + "_corpo", radius=0.2, depth=1.0, location=(x, y, 1.0))
    add("primitive_uv_sphere_add", per, name + "_cabeca", radius=0.13, location=(x, y, 1.65))
    for s in (-1, 1):
        add("primitive_cylinder_add", per, f"{name}_perna{s}", radius=0.07, depth=0.8, location=(x + s * 0.1, y, 0.4))

mannequin("A", -1.0, 0.5)
mannequin("B", 1.2, 1.5)
add("primitive_cube_add", prop, "mesa", size=1, location=(0.2, 1.0, 0.4)).scale = (1.2, 0.7, 0.8)

cam_data = bpy.data.cameras.new("cam")
cam_data.lens = 35
cam = bpy.data.objects.new("cam_plano_01", cam_data)
scene.collection.objects.link(cam)
cam.location = (0.5, -5.5, 1.6)
d = Vector((0.1, 1.0, 1.1)) - cam.location
cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
scene.camera = cam

# Grease Pencil object with one layer per collection, each fed by a Line Art modifier
gp_data = bpy.data.grease_pencils.new("storyboard")
gp = bpy.data.objects.new("storyboard", gp_data)
scene.collection.objects.link(gp)
mat = bpy.data.materials.new("traco")
bpy.data.materials.create_gpencil_data(mat)
gp_data.materials.append(mat)

for c in (cen, per, prop):
    layer = gp_data.layers.new(c.name)
    m = gp.modifiers.new("LA_" + c.name, 'LINEART')
    m.source_type = 'COLLECTION'
    m.source_collection = c
    m.target_layer = c.name
    m.target_material = mat
    m.use_contour = m.use_crease = True
    m.use_intersection = False
    # occlusion must consider ALL geometry, not only the source collection
    m.radius = 0.01

bpy.context.view_layer.objects.active = gp
gp.select_set(True)
bpy.ops.object.lineart_bake_strokes()
for m in list(gp.modifiers):
    gp.modifiers.remove(m)
for l in gp_data.layers:
    n = sum(len(d.drawing.strokes) for d in l.frames) if len(l.frames) else 0
    print("layer", l.name, "strokes", n)

r = bpy.ops.wm.grease_pencil_export_svg(filepath=out, selected_object_type='VISIBLE',
                                        use_fill=False, use_clip_camera=True)
print("export", r)

# ---- own projection: GP stroke points (3D) -> camera -> SVG with Inkscape layers
from bpy_extras.object_utils import world_to_camera_view
W, H = scene.render.resolution_x, scene.render.resolution_y
mw = gp.matrix_world
lines = ['<?xml version="1.0" encoding="UTF-8"?>',
 f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
 '<metadata>{"scene":"spike","camera":"cam_plano_01","blender":"%s"}</metadata>' % bpy.app.version_string,
 f'<rect width="{W}" height="{H}" fill="white"/>']
for l in gp_data.layers:
    lines.append(f'<g inkscape:groupmode="layer" inkscape:label="{l.name}" id="{l.name}">')
    for fr in l.frames:
        for st in fr.drawing.strokes:
            pts = []
            for p in st.points:
                v = world_to_camera_view(scene, cam, mw @ p.position)
                pts.append(f"{v.x*W:.1f},{(1-v.y)*H:.1f}")
            if len(pts) > 1:
                lines.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="black" stroke-width="2" stroke-linecap="round"/>')
    lines.append('</g>')
lines.append('</svg>')
open(out.replace('.svg','_own.svg'),'w').write("\n".join(lines))
print("own svg written")
