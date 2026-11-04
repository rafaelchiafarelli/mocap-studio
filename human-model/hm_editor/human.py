"""The human being edited: a plain MPFB human whose sliders are live, and reading a recipe back from it or from a built model."""
import os
import bpy
import numpy as np
from . import recipe as rc

N_BODY = 13380  # MakeHuman's body vertices come first; helpers follow, as in blender/export_blend.py
DENSITY_KG_PER_L = 1.01  # as in hmcore/morph.py
STATURE_TOLERANCE_M = 0.001


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


# ---- reading a recipe back

def read_recipe(body, name, sex, assets=None):
    TargetService = _services()[4]
    macros = rc.rounded_macros(TargetService.get_macro_info_dict_from_basemesh(body))
    keys = body.data.shape_keys.key_blocks if body.data.shape_keys else []
    targets = rc.identity_targets([(k.name, k.value) for k in keys], lambda n: bool(TargetService.target_full_path(n)))
    return {"name": rc.safe_name(name), "sex": sex, "macros": macros, "targets": targets, "assets": dict(rc.ASSETS if assets is None else assets)}
