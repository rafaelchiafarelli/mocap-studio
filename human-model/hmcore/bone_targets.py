"""From a resolved sheet (hmcore.character.resolve) to the bones' targets, in metres: biacromial width, pelvis width, trunk length, thigh and shin, humerus and forearm, and the bone thickness per region.
Bony measures (Modelagem_Plana-referencia.pdf 7 and 9) and near it (4, 5, 12, and 8, 14, 15 for thickness) are read as such; the rest aren't used for bones. A blank bone parameter comes from a proportion, recorded as such. A change of body fat alone changes nothing here: only those measures are read."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
BASE_THICKNESS = "bone_thickness"
THICKNESS_REGIONS = ("humerus", "forearm", "femur", "tibia")


def proportions(sex, data=DATA):
    with open(os.path.join(data, "bone_proportions.json"), encoding="utf-8") as fh:
        return json.load(fh)[sex]


def targets(resolved, parameters=None, table=None, base_cm=None, data=DATA):
    """{target: metres}, plus provenance: "measure", "proportion" or "parameter" for each."""
    sex = resolved["sex"]
    p = proportions(sex, data) if table is None else table
    field = resolved["fields"]
    cm = lambda k: field[k]["value"]
    parameters = parameters or {}
    origin, out = {}, {}

    def put(key, value, source):
        out[key], origin[key] = round(float(value), 5), source

    biacromial = cm("shoulder_width") / 100 * p["biacromial_over_tape"]
    put("biacromial_m", biacromial, "measure")
    put("trunk_length_m", (cm("back_length") + cm("hip_height")) / 100 * p["trunk_over_tape"], "measure")
    put("ribcage_width_m", biacromial * p["ribcage_width_over_biacromial"], "measure")
    put("ribcage_depth_m", biacromial * p["ribcage_depth_over_biacromial"], "measure")
    if parameters.get("pelvis_width_cm") is not None:
        put("pelvis_width_m", parameters["pelvis_width_cm"] / 100, "parameter")
    else:
        put("pelvis_width_m", cm("height") / 100 * p["pelvis_share_of_height"], "proportion")
    leg = cm("inseam") / 100 * p["leg_bone_over_inseam"]
    arm = cm("arm_length") / 100 * p["arm_bone_over_tape"]
    thigh_share, thigh_source = (parameters["thigh_share_of_leg"], "parameter") if parameters.get("thigh_share_of_leg") else (p["thigh_share_of_leg"], "proportion")
    arm_share, arm_source = (parameters["humerus_share_of_arm"], "parameter") if parameters.get("humerus_share_of_arm") else (p["humerus_share_of_arm"], "proportion")
    put("thigh_m", leg * thigh_share, thigh_source)
    put("shin_m", leg * (1 - thigh_share), thigh_source)
    put("humerus_m", arm * arm_share, arm_source)
    put("forearm_m", arm * (1 - arm_share), arm_source)
    put("acromion_beyond_joint_m", p["acromion_beyond_joint_m"], "proportion")
    # Thickness: the biotype's, and where the sheet gives a measure near the bone, that girth against the neutral body's at this height
    k = cm("height") / base_cm["height"] if base_cm else 1.0
    scale = (k ** 0.7)
    thick = cm(BASE_THICKNESS)
    ratio = lambda key: (cm(key) / (base_cm[key] * scale)) if base_cm and field[key]["source"] == "typed" else 1.0
    regions = {"humerus": thick, "forearm": thick * ratio("wrist"), "femur": thick * ratio("knee"), "tibia": thick * ratio("knee") * ratio("ankle") ** 0.5}
    out["thickness"] = {k: round(float(v), 4) for k, v in regions.items()}
    origin["thickness"] = "measure"
    out["provenance"] = origin
    return out
