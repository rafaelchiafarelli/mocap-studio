"""The human being edited: a plain MPFB human whose sliders are live, and reading a recipe back from it or from a built model."""
import os
import bpy
import numpy as np
from . import recipe as rc, tape

N_BODY = 13380  # MakeHuman's body vertices come first; helpers follow, as in blender/export_blend.py
DENSITY_KG_PER_L = 1.01  # as in hmcore/morph.py
STATURE_TOLERANCE_M = 0.001
SLIDER_LIMIT = 0.8  # some targets break beyond it (docs/character-controls.md), and the panel's sliders stop there too


def _services():
    from bl_ext.user_default.mpfb.entities.objectproperties import HumanObjectProperties
    from bl_ext.user_default.mpfb.services.humanservice import HumanService
    from bl_ext.user_default.mpfb.services.locationservice import LocationService
    from bl_ext.user_default.mpfb.services.objectservice import ObjectService
    from bl_ext.user_default.mpfb.services.targetservice import TargetService
    return HumanObjectProperties, HumanService, LocationService, ObjectService, TargetService


def is_built():
    return "HM_controls" in bpy.data.objects


def find_body(scene):
    body = scene.hm_editor.body
    if body is not None:
        return body
    ObjectService = _services()[3]
    return next((o for o in scene.objects if o.type == "MESH" and o.data.shape_keys and ObjectService.object_is_basemesh(o)), None)


def built_skin():
    return next((o for o in bpy.data.objects if o.name.endswith(".skin")), None)


def assets_of(body):
    return [o for o in body.children_recursive if o.type == "MESH"]


# ---- making and removing a human

def create(r):
    """A plain MPFB human from a recipe: the same calls as blender/assemble.py, without the rig or inner layers."""
    _, HumanService, LocationService, ObjectService, TargetService = _services()
    body = HumanService.create_human(macro_detail_dict=r["macros"])
    body.name = r["name"] + ".skin"
    ObjectService.activate_blender_object(body)
    for name, value in r.get("targets", {}).items():
        path = TargetService.target_full_path(name)
        if not path:
            raise ValueError(f"MPFB has no target {name}")
        TargetService.load_target(body, path, weight=value, name=name)
    for kind, label in (("eyes", "Eyes"), ("teeth", "Teeth"), ("tongue", "Tongue")):
        rel = r.get("assets", {}).get(kind)
        if rel:
            HumanService.add_mhclo_asset(os.path.join(LocationService.get_user_data(), *rel.split("/")), body, asset_type=label, subdiv_levels=0, material_type="MAKESKIN")
    ObjectService.activate_blender_object(body)
    return body


def remove(body):
    for o in [*body.children_recursive, body]:
        bpy.data.objects.remove(o)


def remove_default_cube():
    """Only in a file never saved, which is where Blender's startup cube would sit inside the body."""
    cube = bpy.data.objects.get("Cube")
    if cube is not None and not bpy.data.filepath:
        bpy.data.objects.remove(cube)


# ---- sliders

def get_side(body, pair):
    keys = body.data.shape_keys
    if keys is None:
        return 0.0
    negative, positive = pair
    k = keys.key_blocks.get(positive)
    if k is not None and k.value > 0:
        return k.value
    k = keys.key_blocks.get(negative) if negative else None
    return -k.value if k is not None else 0.0


def _set_target(body, name, value):
    keys = body.data.shape_keys.key_blocks
    k = keys.get(name)
    if k is not None:
        k.value = value
    elif value > 0:
        _, _, _, ObjectService, TargetService = _services()
        ObjectService.activate_blender_object(body)
        TargetService.load_target(body, TargetService.target_full_path(name), weight=value, name=name)


def set_side(body, pair, value):
    """A slider sets one target of the pair, and clears its opposite."""
    negative, positive = pair
    _set_target(body, positive, max(value, 0.0))
    if negative:
        _set_target(body, negative, max(-value, 0.0))


def get_macro(body, name):
    return _services()[0].get_value(name, entity_reference=body)


def set_macro(body, name, value):
    props, _, _, ObjectService, TargetService = _services()
    props.set_value(name, value, entity_reference=body)
    ObjectService.activate_blender_object(body)
    TargetService.reapply_macro_details(body, remove_zero_weight_targets=False)


def set_ancestry(body, name, value):
    props, _, _, ObjectService, TargetService = _services()
    race = {k: props.get_value(k, entity_reference=body) for k in ("african", "asian", "caucasian")}
    for k, v in rc.rebalance(race, name, value).items():
        props.set_value(k, v, entity_reference=body)
    ObjectService.activate_blender_object(body)
    TargetService.reapply_macro_details(body, remove_zero_weight_targets=False)


# ---- real sizes

def _evaluated_body(body):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    c = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", c)
    ev.to_mesh_clear()
    M = np.array(body.matrix_world)
    return c.reshape(-1, 3)[:N_BODY] @ M[:3, :3].T + M[:3, 3]


def stature(body):
    z = _evaluated_body(body)[:, 2]
    return float(z.max() - z.min())


def measure(body):
    """Stature in metres, and mass from the skin's volume at a declared density, an estimate (docs/character-controls.md)."""
    c = _evaluated_body(body)
    tris = []
    for p in body.data.polygons:
        v = p.vertices
        if max(v) < N_BODY:
            tris += [(v[0], v[i], v[i + 1]) for i in range(1, len(v) - 1)]
    t = np.array(tris)
    volume = abs(np.einsum("ij,ij->i", c[t[:, 0]], np.cross(c[t[:, 1]], c[t[:, 2]])).sum() / 6)
    h = float(np.ptp(c[:, 2]))
    mass = float(volume * 1000 * DENSITY_KG_PER_L)
    return {"stature_m": h, "mass_kg": mass, "bmi": mass / h ** 2}


def set_stature(body, metres):
    """Finds the height slider by measuring this body, so its other sliders count. Raises when it can't reach that stature."""
    start = get_macro(body, "height")
    lo, hi = 0.0, 1.0
    set_macro(body, "height", lo)
    short = stature(body)
    set_macro(body, "height", hi)
    tall = stature(body)
    if not short <= metres <= tall:
        set_macro(body, "height", start)
        raise ValueError(f"This body can be from {short:.2f} to {tall:.2f} m")
    for _ in range(14):
        mid = (lo + hi) / 2
        set_macro(body, "height", mid)
        h = stature(body)
        if abs(h - metres) < STATURE_TOLERANCE_M:
            break
        lo, hi = (mid, hi) if h < metres else (lo, mid)
    return h


def settle(body):
    """After a change: refit eyes, teeth and tongue, stand the feet on the floor, and measure."""
    _, HumanService, _, _, _ = _services()
    if assets_of(body):
        HumanService.refit(body)
    z = _evaluated_body(body)[:, 2]
    body.location.z -= float(z.min())
    return measure(body)


# ---- the tape

def all_verts(body):
    """World positions with the helpers, whose joint cubes the tape uses as landmarks. They're mixed from the shape keys, because the evaluated mesh has the helpers masked away."""
    keys = body.data.shape_keys.key_blocks
    n = len(body.data.vertices)

    def read(key):
        c = np.empty(n * 3)
        key.data.foreach_get("co", c)
        return c

    basis = read(keys[0])
    mix = basis.copy()
    for k in keys[1:]:
        if k.value != 0:
            mix += k.value * (read(k) - basis)
    M = np.array(body.matrix_world)
    return mix.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]


def show_tape(lines, name="HM_tape"):
    """The tape's paths as a thin curve object, on top of the body. It's a view only: nothing reads it, and it isn't in the recipe."""
    curve = bpy.data.curves.get(name) or bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = 0.0015
    curve.splines.clear()
    for path in lines.values():
        if len(path) < 2:
            continue
        spline = curve.splines.new("POLY")
        spline.points.add(len(path) - 1)
        spline.points.foreach_set("co", np.column_stack([path, np.ones(len(path))]).ravel())
        spline.use_cyclic_u = len(path) > 3
    ob = bpy.data.objects.get(name)
    if ob is None:
        ob = bpy.data.objects.new(name, curve)
        bpy.context.scene.collection.objects.link(ob)
        material = bpy.data.materials.new(name)
        material.diffuse_color = (0.9, 0.05, 0.05, 1.0)
        material.use_nodes = True
        material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.9, 0.05, 0.05, 1.0)
        curve.materials.append(material)
    ob.show_in_front = True
    return ob


_topology = []


def measure_body(body):
    """Every measure in metres, and the tape's paths. The topology is built once: it's the same on every MPFB character."""
    if not _topology:
        _topology.append(tape_topology(body))
    values, lines, _ = tape.measure(_topology[0], all_verts(body))
    return values, lines


def fit_measures(body, targets, sliders_by_name):
    """Moves the sliders until the body has these measures, in metres. Measures move each other, so it goes round until they all hold.
    Returns {key: (reached, at_limit)}. The height macro goes first, because it scales everything."""
    results = {}
    keys = [k for k in tape.MEASURE_KEYS if k in targets and (k == "height" or k in tape.DRIVERS)]
    for _ in range(4):
        for key in keys:
            read = lambda: measure_body(body)[0][key]
            if key == "height":
                results[key] = tape.solve(read, lambda x: set_macro(body, "height", x), get_macro(body, "height"), targets[key], 0.0, 1.0)
                continue
            sides = [pair for name in tape.DRIVERS[key] for _, pair in sliders_by_name[name].sides]
            def write(x):
                for pair in sides:
                    set_side(body, pair, x)
            results[key] = tape.solve(read, write, get_side(body, sides[0]), targets[key], -SLIDER_LIMIT, SLIDER_LIMIT)
        now = measure_body(body)[0]
        if all(abs(now[k] - targets[k]) <= tape.TOLERANCE_M or results[k][1] for k in keys):
            break
    now = measure_body(body)[0]
    return {k: (now[k], results[k][1]) for k in keys}


def tape_topology(body):
    index = {g.index: g.name for g in body.vertex_groups}
    groups = {name: [] for name in index.values()}
    for v in body.data.vertices:
        for e in v.groups:
            if e.weight > 0:
                groups[index[e.group]].append(v.index)
    return tape.Topology([list(p.vertices) for p in body.data.polygons], groups)


# ---- reading a recipe back

def read_recipe(body, name, sex, assets=None):
    TargetService = _services()[4]
    macros = rc.rounded_macros(TargetService.get_macro_info_dict_from_basemesh(body))
    keys = body.data.shape_keys.key_blocks if body.data.shape_keys else []
    targets = rc.identity_targets([(k.name, k.value) for k in keys], lambda n: bool(TargetService.target_full_path(n)))
    return {"name": rc.safe_name(name), "sex": sex, "macros": macros, "targets": targets, "assets": dict(rc.ASSETS if assets is None else assets)}
