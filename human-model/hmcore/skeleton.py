"""Fits the bone library to one individual: the MPFB skin and rig exported by blender/export_human.py."""
import json
import numpy as np
from hmcore import bonelib, fit, parametric

TISSUE = {"top": 0.006, "back": 0.007, "side": 0.006, "chin": 0.010, "front": 0.005}  # skin over bone, m
PELVIS_MARGIN = 0.022
TRUNK_MARGIN = {"lateral": 0.018, "front": 0.012, "spinous": 0.012}
# Bones that lie just under the skin are moved rigidly until this much tissue covers them: the same least depths as
# data/skin_over_bone_female.json, so the pushed skin has nothing left to do for them.
SETTLE_TISSUE = 0.004  # m
VERTEBRAE = ["C1", "C2", "C3", "C4", "C5", "C6", "C7"] + [f"T{i}" for i in range(1, 13)] + ["L1", "L2", "L3", "L4", "L5"]
SIDE = {"L": "left", "R": "right"}
FINGER_BONES = {"index": "f_index", "middle": "f_middle", "ring": "f_ring", "little": "f_pinky"}
HAND_RIG = {"metacarpal1": "thumb.01", "thumb_proximal": "thumb.02", "thumb_distal": "thumb.03"}
for finger, palm in zip(("index", "middle", "ring", "little"), ("palm.01", "palm.02", "palm.03", "palm.04")):
    HAND_RIG[f"metacarpal{dict(index=2, middle=3, ring=4, little=5)[finger]}"] = palm
    HAND_RIG[f"{finger}_proximal"] = f"{FINGER_BONES[finger]}.01"
    HAND_RIG[f"{finger}_medial"] = f"{FINGER_BONES[finger]}.02"
    HAND_RIG[f"{finger}_distal"] = f"{FINGER_BONES[finger]}.03"


def load_individual(npz_path, json_path):
    d = np.load(npz_path)
    meta = json.load(open(json_path))
    return {"skin": d["verts"].astype(float), "tris": fit.triangles(d["starts"], d["sizes"], d["loops"]), "rig": meta["bones"], "groups": meta["groups"], "macros": meta["macros"]}


def head_tail(ind, bone):
    b = ind["rig"][bone]
    return np.array(b["head"]), np.array(b["tail"])


def end_centres(v, fraction=0.05):
    """Centres of the two ends of a long shape along its main axis; the first is the end with the larger z-value along the returned axis."""
    c = v.mean(axis=0)
    axis = np.linalg.svd(v - c, full_matrices=False)[2][0]
    d = (v - c) @ axis
    lo, hi = np.quantile(d, [fraction, 1 - fraction])
    return v[d >= hi].mean(axis=0), v[d <= lo].mean(axis=0)


def mandible_landmarks(md):
    """(condyle L, condyle R, chin): the chin is the front-most low point, and each condyle is the point of its half farthest from the chin, whatever the head's tilt."""
    mid = (md[:, 0].min() + md[:, 0].max()) / 2
    centre_band = md[np.abs(md[:, 0] - mid) < 0.008]
    chin = centre_band[np.argmin(centre_band[:, 1] + centre_band[:, 2])]
    out = []
    for sign in (1, -1):
        half = md[np.sign(md[:, 0] - mid) == sign]
        far = half[np.argmax(np.linalg.norm(half - chin, axis=1))]
        out.append(half[np.linalg.norm(half - far, axis=1) < 0.010].mean(axis=0))
    return out[0], out[1], chin


def fit_head(ind, lib):
    """Maps for cranium and mandible, from the rig's face landmarks. The mandible runs from the condyles to the chin. The cranium is a box in the head's skin, turned about X until the socket that holds the condyle lands on the rig's jaw hinge: the scanner's head rest tilts the head."""
    skin = ind["skin"]
    neck_z = head_tail(ind, "spine.006")[0][2]
    head = skin[(skin[:, 2] > neck_z) & (np.abs(skin[:, 0]) < 0.12)]
    skin_top = head[head[:, 2] > np.quantile(head[:, 2], 0.6)]
    cr0, md0 = lib["cranium"][0], lib["mandible"][0]
    c_l, c_r, chin = mandible_landmarks(md0)
    socket = (c_l + c_r) / 2
    hinge = head_tail(ind, "jaw_master")[0]
    chin_t = head_tail(ind, "chin")[0] + np.array([0, TISSUE["chin"], TISSUE["chin"]])
    centre = cr0.mean(axis=0)
    dst_x = (skin_top[:, 0].min() + TISSUE["side"], skin_top[:, 0].max() - TISSUE["side"])
    dst_y = (skin_top[:, 1].min() + TISSUE["front"], skin_top[:, 1].max() - TISSUE["back"])
    dst_top = skin_top[:, 2].max() - TISSUE["top"]

    def mapping(angle):
        c, sn = np.cos(angle), np.sin(angle)
        Rx = np.array([[1, 0, 0], [0, c, -sn], [0, sn, c]])
        tilt = lambda v: (np.asarray(v, float) - centre) @ Rx.T + centre
        cr = tilt(cr0)
        band = cr[cr[:, 2] > np.quantile(cr[:, 2], 0.6)]
        sock = tilt(socket[None])[0]
        lo = np.array([band[:, 0].min(), band[:, 1].min(), sock[2]])
        hi = np.array([band[:, 0].max(), band[:, 1].max(), cr[:, 2].max()])
        dst_lo = np.array([dst_x[0], dst_y[0], hinge[2]])
        dst_hi = np.array([dst_x[1], dst_y[1], dst_top])
        return lambda v: fit.box_map(tilt(v), lo, hi, dst_lo, dst_hi)

    best = min(np.radians(np.arange(-40, 40.1, 1.0)), key=lambda a: abs(mapping(a)(socket[None])[0, 1] - hinge[1]))
    unshrunk = mapping(best)
    # A head isn't a box: shrink until the cranium stays under the skin. The face stays where it is, or the eyes leave their sockets, so depth shrinks from the front and height from the jaw hinge.
    sample = unshrunk(cr0[:: max(1, len(cr0) // 2500)])
    front = sample[:, 1].min()
    mid_x = (sample[:, 0].min() + sample[:, 0].max()) / 2

    def shrunk(p, k):
        return np.column_stack([(p[:, 0] - mid_x) * k + mid_x, (p[:, 1] - front) * k + front, (p[:, 2] - hinge[2]) * k + hinge[2]])

    shrink = 1.0
    while shrink > 0.8 and (fit.winding_number(shrunk(sample, shrink), skin, ind["tris"]) < 0.5).mean() >= 0.01:
        shrink -= 0.01

    def cranium_map(v):
        return shrunk(unshrunk(v), shrink)

    # The jaw in a scan can sit turned; its hinge axis has to run left to right.
    level = fit.rotation_between(c_l - c_r, [1, 0, 0])
    levelled = lambda v: (np.asarray(v, float) - socket) @ level.T + socket
    chin_l = levelled(chin[None])[0]
    mid_x = (fit.similarity(levelled(md0), socket, chin_l, hinge, chin_t)[:, 0].min() + fit.similarity(levelled(md0), socket, chin_l, hinge, chin_t)[:, 0].max()) / 2

    def mandible_map(v):
        return fit.similarity(levelled(v), socket, chin_l, hinge, chin_t) - np.array([mid_x, 0, 0])

    return cranium_map, mandible_map, (c_l, c_r, chin)


FOOT_PARTS = ("Talus", "Calcaneus", "Navicular", "Cuboid", "Cuneiform", "Metatarsal", "Phalanx")


def fit_foot(ind, legs, side, ankle):
    """The foot stands on the floor. BMF's body lay in a scanner with its feet pointing down, so the sole is turned flat, then the toes on their own, and the length comes from the skin."""
    skin = ind["skin"]
    near = skin[(np.abs(skin[:, 0] - ankle[0]) < 0.09) & (skin[:, 2] < 0.12)]
    parts = {n: v for n, (v, _) in legs.items() if n.endswith(side) and any(k in n for k in FOOT_PARTS)}
    calc = parts[f"Calcaneus{side}"]
    heel = calc[np.argmin(calc[:, 2])]
    meta = parts[f"FirstMetatarsal{side}"]
    distal = meta[meta[:, 1] < np.quantile(meta[:, 1], 0.3)]
    ball = distal[np.argmin(distal[:, 2])]
    toe_t = head_tail(ind, f"toe.{side}")[1]
    forward = (toe_t - ankle) * np.array([1, 1, 0])
    R = fit.frame_rotation(ball - heel, [0, 0, 1], forward, [0, 0, 1])
    turned = {n: (v - heel) @ R.T for n, v in parts.items()}
    ball_t = (ball - heel) @ R.T
    # Toes: rotate about the line through the ball of the foot until they lie flat.
    phalanges = [n for n in turned if "Phalanx" in n]
    tips = np.vstack([turned[n] for n in phalanges if "Dist" in n])
    roots = np.vstack([turned[n] for n in phalanges if "Prox" in n])
    toe_dir = tips.mean(axis=0) - roots.mean(axis=0)
    fwd_unit = forward / np.linalg.norm(forward)
    toe_angle = np.arctan2(toe_dir[2], toe_dir @ fwd_unit)
    axis = np.cross(fwd_unit, [0, 0, 1])
    c, sn = np.cos(-toe_angle), np.sin(-toe_angle)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    R_toe = np.eye(3) + sn * K + (1 - c) * K @ K
    for n in phalanges:
        turned[n] = (turned[n] - ball_t) @ R_toe.T + ball_t
    allv = np.vstack(list(turned.values()))
    d = allv @ fwd_unit
    s = (near[:, 1].max() - near[:, 1].min() - 2 * 0.008) / (d.max() - d.min())
    back = allv[np.argmin(d)] * s
    centre_x = (allv[:, 0].min() + allv[:, 0].max()) / 2 * s
    floor = skin[:, 2].min() + 0.008
    low = allv[:, 2].min() * s
    target_back_y = near[:, 1].max() - 0.008
    offset = np.array([ankle[0] - centre_x, target_back_y - back[1], floor - low])
    return lambda name, v: turned[name] * s + offset


def build(ind, lib, legs, leg_anchors, arm_r, arm_l, hips_ct):
    """Returns {bone name: {"verts", "faces", "parent", "source"}} and the anchor points later steps need (jaw pivot and so on)."""
    skin = ind["skin"]
    out, anchors = {}, {}

    def put(name, verts, faces, parent, source):
        out[name] = {"verts": np.asarray(verts, np.float32), "faces": np.asarray(faces, np.int32), "parent": parent, "source": source}

    # Head
    head_map, jaw_map, (c_l, c_r, chin_src) = fit_head(ind, lib)
    cr_v, cr_f = lib["cranium"]
    md_v, md_f = lib["mandible"]
    put("cranium", head_map(cr_v), cr_f, "spine.006", "ct")
    put("mandible", jaw_map(md_v), md_f, "hm_jaw", "ct")
    for side, c in (("L", c_l), ("R", c_r)):
        anchors[f"condyle_{side}"] = jaw_map(c[None])[0]
    anchors["chin"] = jaw_map(chin_src[None])[0]
    anchors["lower_incisor"] = head_tail(ind, "teeth.B")[0]

    # Spine: scale between the hips and C1, then each vertebra sits so its spinous tip stays under the back's skin.
    hip_l, hip_r = head_tail(ind, "thigh.L")[0], head_tail(ind, "thigh.R")[0]
    hips = (hip_l + hip_r) / 2
    ct_hips = (hips_ct["left"] + hips_ct["right"]) / 2
    centres = {n: lib[f"vertebrae_{n}"][0].mean(axis=0) for n in VERTEBRAE}
    c1_target = head_map(centres["C1"][None])[0]
    s_v = (c1_target[2] - hips[2]) / (centres["C1"][2] - ct_hips[2])
    s_block = s_v
    spine_bones = [b for b in ("spine", "spine.001", "spine.002", "spine.003", "spine.004", "spine.005", "spine.006") if b in ind["rig"]]
    bone_low = [(head_tail(ind, b)[0][2], b) for b in spine_bones]
    shift_y = {}
    vertebra_t = {}
    for n in VERTEBRAE:
        v, f = lib[f"vertebrae_{n}"]
        c = centres[n]
        z_t = hips[2] + s_v * (c[2] - ct_hips[2])
        placed = (v - c) * s_block
        back = fit.body_profile(skin, z_t, half_width=0.04, band=0.02)
        tip = placed[np.abs(placed[:, 0]) < 0.012, 1].max() if (np.abs(placed[:, 0]) < 0.012).any() else placed[:, 1].max()
        y_t = (back[1] - TRUNK_MARGIN["spinous"] - tip) if back else c1_target[1]
        shift_y[n] = y_t
        vertebra_t[n] = np.array([0.0, y_t, z_t])
    # smooth the depth curve: a vertebra can't jump relative to its neighbours
    ys = np.array([shift_y[n] for n in VERTEBRAE])
    # the neck is free of back skin, so C1 is pinned to the skull and C2-C6 blend towards C7
    ys[0] = c1_target[1]
    ys[1:6] = np.linspace(ys[0], ys[6], 7)[1:6]
    ys[6:] = np.array([np.median(ys[max(6, i - 2):i + 3]) for i in range(6, len(ys))])
    kernel = np.array([1, 2, 3, 2, 1], float) / 9
    smooth = np.convolve(np.pad(ys, 2, mode="edge"), kernel, mode="valid")
    smooth[0] = c1_target[1]
    for i, n in enumerate(VERTEBRAE):
        vertebra_t[n][1] = smooth[i]
        v, f = lib[f"vertebrae_{n}"]
        parent = max([b for z, b in bone_low if z <= vertebra_t[n][2]] or spine_bones[:1], key=lambda b: spine_bones.index(b))
        placed = (v - centres[n]) * s_block + vertebra_t[n]
        put(f"vertebra_{n}", placed, f, parent, "ct")

    # Hyoid and larynx: no allowed mesh exists, so they're parametric. Level of C3, in front of the spine, behind the chin.
    c3 = vertebra_t["C3"]
    chin_pt = anchors["chin"]
    hy_c = np.array([0.0, chin_pt[1] + 0.55 * (c3[1] - chin_pt[1]) - 0.015, c3[2]])
    neck_front = fit.body_profile(skin, c3[2] - 0.02, half_width=0.02, band=0.015)
    if neck_front:
        hy_c[1] = max(hy_c[1], neck_front[0] + 0.012)  # a slim neck keeps it under the skin
    v, f = parametric.hyoid(hy_c)
    put("hyoid", v, f, "hm_hyoid", "parametric")
    anchors["hyoid"] = hy_c
    la_c = hy_c + np.array([0, 0.002, -0.034])
    v, f = parametric.thyroid_shield(la_c)
    put("larynx", v, f, "hm_larynx", "parametric")
    anchors["larynx"] = la_c

    # Rib cage: one map for ribs, sternum and cartilage, with each rib carried by its own vertebra's depth.
    ribs = np.vstack([lib[f"rib_{s}_{i}"][0] for s in ("left", "right") for i in range(1, 13)])
    # Measured low on the chest: higher up the arms join the trunk at the armpit and the width reads wrong.
    chest_z = vertebra_t["T10"][2]
    armpit_limit = head_tail(ind, "upper_arm.L")[0][0] - 0.03
    half = min(fit.body_half_width(skin, chest_z, band=0.02, gap=0.025) - TRUNK_MARGIN["lateral"], armpit_limit)
    x_ref = (ribs[:, 0].min() + ribs[:, 0].max()) / 2
    src_half = (ribs[:, 0].max() - ribs[:, 0].min()) / 2
    sx = half / src_half
    front_z = vertebra_t["T5"][2]
    front = fit.body_profile(skin, front_z, half_width=0.01)[0] + TRUNK_MARGIN["front"]
    sternum_v, sternum_f = lib["sternum"]
    src_front = sternum_v[:, 1].min()
    y_ref_ct = centres["T5"][1]
    sy = (vertebra_t["T5"][1] - front) / (y_ref_ct - src_front)

    def trunk_map(v, level):
        p = np.asarray(v, float) - centres[level]
        return np.column_stack([(np.asarray(v, float)[:, 0] - x_ref) * sx, p[:, 1] * sy + vertebra_t[level][1], p[:, 2] * s_v + vertebra_t[level][2]])

    breath_parent = {i: "spine.002" if i > 7 else "spine.003" for i in range(1, 13)}
    for i in range(1, 13):
        for s, side in (("left", "L"), ("right", "R")):
            v, f = lib[f"rib_{s}_{i}"]
            put(f"rib_{i}_{side}", trunk_map(v, f"T{i}"), f, f"hm_rib_{i}_{side}", "ct")
            mapped = out[f"rib_{i}_{side}"]["verts"]
            anchors[f"rib_head_{i}_{side}"] = mapped[np.argsort(np.abs(mapped[:, 0]))[:20]].mean(axis=0)
    put("sternum", trunk_map(sternum_v, "T5"), sternum_f, "hm_sternum", "ct")
    cart_v, cart_f = lib["costal_cartilages"]
    put("costal_cartilages", trunk_map(cart_v, "T5"), cart_f, "hm_sternum", "ct")
    # The highest point of the manubrium lies off the midline in the CT, so the clavicles' sternal ends came out 22 mm apart in x: on the midline instead
    st = out["sternum"]["verts"]
    anchors["sternum_top"] = np.array([(st[:, 0].min() + st[:, 0].max()) / 2, *st[np.argmax(st[:, 2]), 1:]])

    # Pelvis: its width comes from the hips' skin, so the sockets become the true hip joints and the rig's are moved to them.
    both_hips = np.vstack([lib["hip_left"][0], lib["hip_right"][0]])
    crest_half = fit.body_half_width(skin, hips[2] + 0.11, band=0.02, gap=0.04) - PELVIS_MARGIN
    s_p = 2 * crest_half / (both_hips[:, 0].max() - both_hips[:, 0].min())
    def pelvis_map(v):
        return (np.asarray(v, float) - ct_hips) * s_p + hips
    for name, label in (("hip_L", "hip_left"), ("hip_R", "hip_right"), ("sacrum", "sacrum")):
        v, f = lib[label]
        put(name, pelvis_map(v), f, "spine", "ct")
    sockets = {"L": pelvis_map(hips_ct["left"][None])[0], "R": pelvis_map(hips_ct["right"][None])[0]}
    anchors["rig_edits"] = {f"thigh.{k}": v.tolist() for k, v in sockets.items()}

    # Shoulder girdle and upper arm
    for side in ("L", "R"):
        s = SIDE[side]
        sign = 1 if side == "L" else -1
        shoulder = head_tail(ind, f"upper_arm.{side}")[0]
        scap_v, scap_f = lib[f"scapula_{s}"]
        hum_v, hum_f = lib[f"humerus_{s}"]
        ends = end_centres(hum_v)
        # the humeral head is the end nearer the scapula, wherever the arms were in the scanner
        scap_c = scap_v.mean(axis=0)
        near, far = (ends if np.linalg.norm(ends[0] - scap_c) < np.linalg.norm(ends[1] - scap_c) else (ends[1], ends[0]))
        glenoid = scap_v[np.argsort(np.linalg.norm(scap_v - near, axis=1))[:80]].mean(axis=0)
        placed = trunk_map(scap_v, "T3")
        g = trunk_map(glenoid[None], "T3")[0]
        placed = placed + (shoulder - g) + np.array([-sign * 0.012, 0.0, 0.0])
        put(f"scapula_{side}", placed, scap_f, f"shoulder.{side}", "ct")
        anchors[f"glenoid_{side}"] = shoulder + np.array([-sign * 0.012, 0.0, 0.0])
        ua_h, ua_t = head_tail(ind, f"upper_arm.{side}")
        fa_h, fa_t = head_tail(ind, f"forearm.{side}")
        hinge = np.cross(ua_t - ua_h, fa_t - fa_h)
        if np.linalg.norm(hinge) < 1e-6:
            hinge = np.array([0, -1.0, 0])
        if hinge[1] > 0:
            hinge = -hinge
        distal = hum_v[np.linalg.norm(hum_v - far, axis=1) < 0.035]
        wide = np.linalg.svd(distal - distal.mean(axis=0), full_matrices=False)[2][0]
        R = fit.frame_rotation(far - near, wide, ua_t - ua_h, np.cross(hinge, ua_t - ua_h))
        put(f"humerus_{side}", fit.segment_fit(hum_v, near, far, ua_h, ua_t, rotation=R), hum_f, f"upper_arm.{side}", "ct")
        clav_v, clav_f = lib[f"clavicula_{s}"]
        c_ends = sorted(end_centres(clav_v), key=lambda e: abs(e[0]))
        target_m = anchors["sternum_top"] + np.array([sign * 0.022, 0.0, 0.0])
        target_l = shoulder + np.array([-sign * 0.018, -0.002, 0.022])
        put(f"clavicle_{side}", fit.similarity(clav_v, c_ends[0], c_ends[1], target_m, target_l), clav_f, f"shoulder.{side}", "ct")
        anchors[f"clavicle_medial_{side}"], anchors[f"clavicle_lateral_{side}"] = target_m, target_l

    # Legs and feet: BMF, joint to joint.
    for side in ("L", "R"):
        knee = head_tail(ind, f"thigh.{side}")[1]
        hip = sockets[side]
        ankle = head_tail(ind, f"shin.{side}")[1]
        a_h, a_k, a_a = leg_anchors[f"hip_{side}"], leg_anchors[f"knee_{side}"], leg_anchors[f"ankle_{side}"]
        v, f = legs[f"Femur{side}"]
        put(f"femur_{side}", fit.segment_fit(v, a_h, a_k, hip, knee), f, f"thigh.{side}", "bmf")
        v, f = legs[f"Patella{side}"]
        put(f"patella_{side}", fit.segment_fit(v, a_h, a_k, hip, knee), f, f"shin.{side}", "bmf")
        for bone in ("Tibia", "Fibula"):
            v, f = legs[f"{bone}{side}"]
            put(f"{bone.lower()}_{side}", fit.segment_fit(v, a_k, a_a, knee, ankle), f, f"shin.{side}", "bmf")
        foot_map = fit_foot(ind, legs, side, ankle)
        for name, (v, f) in legs.items():
            if not name.endswith(side) or not any(k in name for k in FOOT_PARTS):
                continue
            put(f"{name[:-1].lower()}_{side}", foot_map(name, v), f, f"toe.{side}" if "Phalanx" in name else f"foot.{side}", "bmf")
        fib = out[f"fibula_{side}"]["verts"]
        anchors[f"fibula_head_{side}"] = fib[fib[:, 2] > np.quantile(fib[:, 2], 0.97)].mean(axis=0)

    # Forearm and hand: Rajagopal.
    for side, (arm, elbow, wrist) in (("R", arm_r), ("L", arm_l)):
        fa_h, fa_t = head_tail(ind, f"forearm.{side}")
        thumb = head_tail(ind, f"palm.01.{side}")[1] - head_tail(ind, f"palm.04.{side}")[1]
        suffix = "rv" if side == "R" else "lv"
        radial = arm[f"radius_{suffix}"][0].mean(axis=0) - arm[f"ulna_{suffix}"][0].mean(axis=0)
        R = fit.frame_rotation(wrist - elbow, radial, fa_t - fa_h, thumb)
        for n in ("ulna", "radius"):
            v, f = arm[f"{n}_{suffix}"]
            put(f"{n}_{side}", fit.segment_fit(v, elbow, wrist, fa_h, fa_t, rotation=R), f, f"forearm.{side}", "rajagopal")
        mid = arm[f"middle_distal_{suffix}s"][0].mean(axis=0)
        idx, lit = arm[f"metacarpal2_{suffix}s"][0].mean(axis=0), arm[f"metacarpal5_{suffix}s"][0].mean(axis=0)
        hand_h = head_tail(ind, f"hand.{side}")[0]
        rig_mid = head_tail(ind, f"f_middle.03.{side}")[1]
        R_h = fit.frame_rotation(mid - wrist, idx - lit, rig_mid - hand_h, thumb)
        s_h = np.linalg.norm(rig_mid - hand_h) / np.linalg.norm(mid - wrist)
        hand_map = lambda p: (np.asarray(p, float) - wrist) * s_h @ R_h.T + hand_h
        for key, (v, f) in arm.items():
            stem = key[:-(len(suffix) + 2)] if key.endswith(f"_{suffix}s") else None
            if stem is None:
                continue
            placed = hand_map(v)
            if stem in HAND_RIG:
                rig_bone = f"{HAND_RIG[stem]}.{side}"
                a, b = end_centres(placed)
                h, t = head_tail(ind, rig_bone)
                near, far = (a, b) if np.linalg.norm(a - h) < np.linalg.norm(b - h) else (b, a)
                ring = fit.ring_centre(skin, h, t, 0.03)
                shift = ring - (h + t) / 2 if ring is not None else 0.0
                put(f"{stem}_{side}", fit.segment_fit(placed, near, far, h + shift, t + shift, radial_power=1.0), f, rig_bone, "rajagopal")
            else:
                put(f"{stem}_{side}", placed, f, f"hand.{side}", "rajagopal")
    anchors["settled"] = settle_superficial(out, anchors, fit.SkinDepth(skin, ind["tris"]))
    return out, anchors


def settle_superficial(out, anchors, depth_of):
    """Moves the scapulae, clavicles and fibulae until SETTLE_TISSUE covers them (bug human-model/12): the scapula turns about the
    glenoid, the fibula about its head, the clavicle about its sternal end and back. Placed whole from the CT, the right scapula came
    27 mm through the back and the left 15, because the scanned person's shoulders weren't level; the fibulae came 15 mm out behind
    MPFB's slim ankle, and the clavicles' sternal ends lie as far forward as the sternum, which is under 1 mm deep.
    Returns {bone: {"moves": amounts (degrees, or mm for a shift), "short_before_mm", "short_after_mm"}}."""
    from scipy.spatial import cKDTree
    ribs = cKDTree(np.vstack([b["verts"] for n, b in out.items() if n.startswith(("rib_", "sternum", "costal"))]))
    report = {}
    for side in ("L", "R"):
        medial, lateral = anchors[f"clavicle_medial_{side}"], anchors[f"clavicle_lateral_{side}"]
        jobs = [
            (f"scapula_{side}", anchors[f"glenoid_{side}"], [("turn", [0, 0, 1], 24.0), ("turn", [1, 0, 0], 24.0), ("turn", [0, 1, 0], 24.0)], ribs),
            (f"clavicle_{side}", medial, [("turn", lateral - medial, 30.0), ("turn", [0, 0, 1], 10.0), ("shift", [0, 1, 0], 0.016)], ribs),
            (f"fibula_{side}", anchors[f"fibula_head_{side}"], [("turn", [1, 0, 0], 8.0), ("turn", [0, 1, 0], 8.0)], cKDTree(out[f"tibia_{side}"]["verts"])),
        ]
        for name, pivot, moves, avoid in jobs:
            move, before, after, amounts = fit.settle(out[name]["verts"], pivot, depth_of, SETTLE_TISSUE, moves, avoid=avoid)
            out[name]["verts"] = move(out[name]["verts"]).astype(np.float32)
            report[name] = {"moves": [round(float(a) * (1000 if m[0] == "shift" else 1), 1) for m, a in zip(moves, amounts)],
                            "short_before_mm": round(before * 1000, 1), "short_after_mm": round(after * 1000, 1)}
    return report


def containment(bones, ind, sample=1500, seed=0):
    """Winding number of a sample of bone vertices against the skin. Fraction outside per bone: the fit's main check."""
    rng = np.random.default_rng(seed)
    res = {}
    for name, b in bones.items():
        v = b["verts"]
        idx = rng.choice(len(v), min(sample // 10 + 30, len(v)), replace=False)
        w = fit.winding_number(v[idx], ind["skin"], ind["tris"])
        res[name] = float((w < 0.5).mean())
    return res


def save(path, bones, anchors):
    arrays = {}
    meta = {"bones": {}, "anchors": {k: (v if isinstance(v, dict) else np.asarray(v).tolist()) for k, v in anchors.items()}}
    for name, b in bones.items():
        arrays[f"{name}__v"] = b["verts"]
        arrays[f"{name}__f"] = b["faces"]
        meta["bones"][name] = {"parent": b["parent"], "source": b["source"]}
    np.savez_compressed(path, **arrays)
    json.dump(meta, open(path + ".json", "w"), indent=0)
