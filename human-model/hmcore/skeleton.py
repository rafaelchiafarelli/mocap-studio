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
KNEE_TISSUE = 0.003  # declared, as for the patella in data/skin_over_bone_female.json, m
RIB_TISSUE = 0.002  # declared, the default of data/skin_over_bone_female.json, m
FOOT_TISSUE = 0.002  # declared, the default of data/skin_over_bone_female.json, m
LARYNX_TISSUE = 0.003  # declared, as in data/skin_over_bone_female.json, m
PELVIS_TISSUE = 0.006  # declared: least tissue over the sacrum and the hip bones' crests, as in data/skin_over_bone_female.json, m
AC_JOINT = 0.003  # declared: the gap between the clavicle's end and the acromion, m
ACROMION_TISSUE = 0.008  # declared: skin and fat over the acromion's top, m; it lies just under the skin
MOST_RAISE = 0.06  # the most the shoulder girdle may be raised, m
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
    # The talus sits under the shin, so it goes under the ankle joint. Centred by the whole foot's box, the forefoot's spread left the talus and heel 2 cm medial and through the skin (bug human-model/23).
    talus = turned[f"Talus{side}"]
    centre_x = (talus[:, 0].min() + talus[:, 0].max()) / 2 * s
    floor = skin[:, 2].min() + 0.008
    low = allv[:, 2].min() * s
    target_back_y = near[:, 1].max() - 0.008
    offset = np.array([ankle[0] - centre_x, target_back_y - back[1], floor - low])
    return lambda name, v: turned[name] * s + offset


def girdle_raise(ind, lib, side, trunk_map):
    """How far the girdle must go up for the acromion to lie ACROMION_TISSUE under the shoulder's skin, hung from the humeral head's
    centre on the rig's joint. The acromion is the scapula's highest point within 6 cm of the joint, seen from above."""
    s, skin = SIDE[side], ind["skin"]
    shoulder = head_tail(ind, f"upper_arm.{side}")[0]
    scap_v, hum_v = lib[f"scapula_{s}"][0], lib[f"humerus_{s}"][0]
    ends = end_centres(hum_v)
    c = scap_v.mean(axis=0)
    near = ends[0] if np.linalg.norm(ends[0] - c) < np.linalg.norm(ends[1] - c) else ends[1]
    placed = trunk_map(scap_v, "T3")
    placed = placed + (shoulder - trunk_map(humeral_head(hum_v, near)[None], "T3")[0])
    close = placed[np.linalg.norm((placed - shoulder)[:, :2], axis=1) < 0.06]
    acromion = close[np.argmax(close[:, 2])]
    above = skin[(np.abs(skin[:, 0] - acromion[0]) < 0.012) & (np.abs(skin[:, 1] - acromion[1]) < 0.012) & (skin[:, 2] > acromion[2])]
    return float(np.clip(above[:, 2].max() - ACROMION_TISSUE - acromion[2], 0.0, MOST_RAISE)) if len(above) else 0.0


def humeral_head(hum_v, near, reach=0.035):
    """Centre of the humeral head: a sphere fitted to the humerus's points within reach of its proximal end's centre."""
    p = hum_v[np.linalg.norm(hum_v - near, axis=1) < reach].astype(float)
    A = np.column_stack([2 * p, np.ones(len(p))])
    return np.linalg.lstsq(A, (p ** 2).sum(axis=1), rcond=None)[0][:3]


def glenoid_fossa(scapula, head, sign, reach=0.045):
    """Middle of the glenoid fossa: the scapula's points near the humeral head's centre that lie toward the body's middle from it."""
    d = scapula - head
    dist = np.linalg.norm(d, axis=1)
    m = (dist < reach) & ((d[:, 0] * -sign) > 0.6 * dist)
    return scapula[m].mean(axis=0) if m.any() else head + np.array([-sign * 0.025, 0.0, 0.0])


def along(head, tail, length):
    """The point this far from head, towards tail: where a bone of this length ends along the rig's own direction."""
    head, tail = np.asarray(head, float), np.asarray(tail, float)
    return head + (tail - head) / np.linalg.norm(tail - head) * length


def spine_line_y(ind, z):
    """The rig's spine line at this height: the y of the spine bones' heads, interpolated. Where the spine sits when it isn't read from the back's skin."""
    names = ("spine", "spine.001", "spine.002", "spine.003", "spine.004", "spine.005", "spine.006")
    heads = sorted((head_tail(ind, b)[0][2], head_tail(ind, b)[0][1]) for b in names if b in ind["rig"])
    return float(np.interp(z, [h[0] for h in heads], [h[1] for h in heads]))


def trunk_scales(ribs, sternum_v, pelvis, targets):
    """The trunk's scales from the targets: ribs' width and depth and the pelvis's width, against the bone library's."""
    return {"sx": targets["ribcage_width_m"] / float(np.ptp(ribs[:, 0])), "sy": targets["ribcage_depth_m"] / max(float(np.ptp(ribs[:, 1])), 1e-6),
            "s_p": targets["pelvis_width_m"] / float(np.ptp(pelvis[:, 0]))}


def pelvis_forward(sacrum, vertebra_l5_y, gap=0.003):
    """How far forward the pelvis moves so that the sacrum's top meets L5, as the CT has it, keeping gap between them."""
    top = sacrum[sacrum[:, 2] > np.quantile(sacrum[:, 2], 0.9)]
    return float(top[:, 1].max() - vertebra_l5_y - gap)


def build(ind, lib, legs, leg_anchors, arm_r, arm_l, hips_ct, targets=None):
    """Returns {bone name: {"verts", "faces", "parent", "source"}} and the anchor points later steps need (jaw pivot and so on).
    With targets (hmcore.bone_targets), the trunk's bones take their sizes from them instead of reading the trunk's skin. The head's bones still follow the skin of the head."""
    skin = ind["skin"]
    depth = fit.SkinDepth(skin, ind["tris"])
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
    s_v = (c1_target[2] - hips[2]) / (centres["C1"][2] - ct_hips[2]) if targets is None else targets["trunk_length_m"] / (centres["C1"][2] - ct_hips[2])
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
        if targets is None:
            back = fit.body_profile(skin, z_t, half_width=0.04, band=0.02)
            tip = placed[np.abs(placed[:, 0]) < 0.012, 1].max() if (np.abs(placed[:, 0]) < 0.012).any() else placed[:, 1].max()
            y_t = (back[1] - TRUNK_MARGIN["spinous"] - tip) if back else c1_target[1]
        else:
            y_t = spine_line_y(ind, z_t)
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
    # sized from the skin, about the shield's back edge, since MPFB's neck is too thin for it and behind it lies the spine (bug human-model/20)
    back = la_c + np.array([0, v[:, 1].max() - la_c[1], 0])
    s_la = fit.largest_scale(lambda s: float((LARYNX_TISSUE - depth(back + (v - back) * s)).max()))
    put("larynx", back + (v - back) * s_la, f, "hm_larynx", "parametric")
    la_c = back + (la_c - back) * s_la
    anchors["larynx"] = la_c
    anchors["slimmed"] = {"larynx": round(s_la, 3)}

    # Rib cage: one map for ribs, sternum and cartilage, with each rib carried by its own vertebra's depth.
    ribs = np.vstack([lib[f"rib_{s}_{i}"][0] for s in ("left", "right") for i in range(1, 13)])
    x_ref = (ribs[:, 0].min() + ribs[:, 0].max()) / 2
    sternum_v, sternum_f = lib["sternum"]
    both_hips = np.vstack([lib["hip_left"][0], lib["hip_right"][0]])
    if targets is None:
        # Measured low on the chest: higher up the arms join the trunk at the armpit and the width reads wrong.
        chest_z = vertebra_t["T10"][2]
        armpit_limit = head_tail(ind, "upper_arm.L")[0][0] - 0.03
        half = min(fit.body_half_width(skin, chest_z, band=0.02, gap=0.025) - TRUNK_MARGIN["lateral"], armpit_limit)
        src_half = (ribs[:, 0].max() - ribs[:, 0].min()) / 2
        sx = half / src_half
        front_z = vertebra_t["T5"][2]
        front = fit.body_profile(skin, front_z, half_width=0.01)[0] + TRUNK_MARGIN["front"]
        src_front = sternum_v[:, 1].min()
        y_ref_ct = centres["T5"][1]
        sy = (vertebra_t["T5"][1] - front) / (y_ref_ct - src_front)
    else:
        scales = trunk_scales(ribs, sternum_v, both_hips, targets)
        sx, sy = scales["sx"], scales["sy"]

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
    # The cage's width comes from the skin at T10, but it is widest lower down, where a man's trunk already narrows, and his ribs 9 to 11 came
    # through his sides (bug human-model/22). Its lower half is narrowed sideways to the skin, only as far as that asks.
    cage = [n for n in out if n.startswith(("rib_", "sternum", "costal"))]
    if targets is None:
        placed, least = fit.slim_to_skin([out[n]["verts"] for n in cage], vertebra_t["T5"], vertebra_t["L1"], skin, depth, RIB_TISSUE, reach=0.4, only=np.array([1.0, 0.0, 0.0]))
        for n, p in zip(cage, placed):
            out[n]["verts"] = p.astype(np.float32)
        anchors["slimmed"]["ribs"] = round(least, 3)
    for n in cage:
        if n.startswith("rib_"):
            mapped = out[n]["verts"]
            anchors[f"rib_head_{n[4:]}"] = mapped[np.argsort(np.abs(mapped[:, 0]))[:20]].mean(axis=0)
    # The highest point of the manubrium lies off the midline in the CT, so the clavicles' sternal ends came out 22 mm apart in x: on the midline instead
    st = out["sternum"]["verts"]
    anchors["sternum_top"] = np.array([(st[:, 0].min() + st[:, 0].max()) / 2, *st[np.argmax(st[:, 2]), 1:]])

    # Pelvis: its width comes from the hips' skin, so the sockets become the true hip joints and the rig's are moved to them.
    if targets is None:
        crest_half = fit.body_half_width(skin, hips[2] + 0.11, band=0.02, gap=0.04) - PELVIS_MARGIN
        s_p = 2 * crest_half / (both_hips[:, 0].max() - both_hips[:, 0].min())
    else:
        s_p = scales["s_p"]
    def pelvis_map(v):
        return (np.asarray(v, float) - ct_hips) * s_p + hips
    for name, label in (("hip_L", "hip_left"), ("hip_R", "hip_right"), ("sacrum", "sacrum")):
        v, f = lib[label]
        put(name, pelvis_map(v), f, "spine", "ct")
    sockets = {"L": pelvis_map(hips_ct["left"][None])[0], "R": pelvis_map(hips_ct["right"][None])[0]}
    # Scaled from the hips alone, the pelvis sat 2 cm behind the spine: the sacrum stood 20 to 24 mm behind L5 and came up to 22 mm
    # through the skin (bug human-model/2). It moves forward, and may tilt about the sockets, until PELVIS_TISSUE covers it; the hip
    # joints go with it. L5 keeps its distance or 3 mm, whichever is less.
    middle = (sockets["L"] + sockets["R"]) / 2
    pelvis_names = ("hip_L", "hip_R", "sacrum")
    if targets is None:
        move, before, after, amounts = fit.settle(np.vstack([out[n]["verts"] for n in pelvis_names]), middle, depth, PELVIS_TISSUE,
                                                  [("shift", [0, -1, 0], 0.04), ("turn", [1, 0, 0], 10.0)], exact=True,
                                                  avoid=fit.solids([(out["vertebra_L5"]["verts"], out["vertebra_L5"]["faces"])]), sample=900)
    else:
        # The sacrum meets L5 as the CT has it, and the hip joints go with it; no skin to settle against
        forward = pelvis_forward(out["sacrum"]["verts"].astype(float), float(out["vertebra_L5"]["verts"].astype(float)[:, 1].max()))
        move, before, after, amounts = (lambda p: np.asarray(p, float) + np.array([0.0, -forward, 0.0])), 0.0, 0.0, (forward, 0.0)
    for n in pelvis_names:
        out[n]["verts"] = move(out[n]["verts"]).astype(np.float32)
    sockets = {k: move(v[None])[0] for k, v in sockets.items()}
    anchors["pelvis_move"] = {"forward_mm": round(float(amounts[0]) * 1000, 1), "tilt_deg": round(float(amounts[1]), 1),
                              "short_before_mm": round(before * 1000, 1), "short_after_mm": round(after * 1000, 1)}
    anchors["rig_edits"] = {f"thigh.{k}": v.tolist() for k, v in sockets.items()}

    # Shoulder girdle and upper arm
    # With targets the skin is the result, so the joint isn't raised to the skin; width comes from the biacromial target instead
    raises = {side: girdle_raise(ind, lib, side, trunk_map) for side in ("L", "R")} if targets is None else {"L": 0.0, "R": 0.0}
    raise_z = float(np.mean(list(raises.values())))  # both sides alike: the CT donor's shoulders weren't level, and the rig's are
    anchors["shoulder_raise_mm"] = {"each": {k: round(v * 1000, 1) for k, v in raises.items()}, "applied": round(raise_z * 1000, 1)}
    arm_joints = {}
    for side in ("L", "R"):
        s = SIDE[side]
        sign = 1 if side == "L" else -1
        shoulder = head_tail(ind, f"upper_arm.{side}")[0]
        if targets is not None:
            shoulder = shoulder.copy()
            shoulder[0] = sign * (targets["biacromial_m"] / 2 - targets["acromion_beyond_joint_m"])
        scap_v, scap_f = lib[f"scapula_{s}"]
        hum_v, hum_f = lib[f"humerus_{s}"]
        ends = end_centres(hum_v)
        # the humeral head is the end nearer the scapula, wherever the arms were in the scanner
        scap_c = scap_v.mean(axis=0)
        near, far = (ends if np.linalg.norm(ends[0] - scap_c) < np.linalg.norm(ends[1] - scap_c) else (ends[1], ends[0]))
        # The girdle hangs from the humeral head's centre, a sphere fitted to the CT humerus, placed on the rig's shoulder joint: the
        # scapula keeps the CT's own relation to the head. It used to hang from the scapula's points nearest the humerus's end, which are
        # the acromion's underside, 25 mm above the head, so the girdle sat 4 to 5 cm low and the clavicle fell to it (bug human-model/18).
        head = humeral_head(hum_v, near)
        placed = trunk_map(scap_v, "T3")
        placed = placed + (shoulder - trunk_map(head[None], "T3")[0])
        placed = placed + np.array([0.0, 0.0, raise_z])
        shoulder = shoulder + np.array([0.0, 0.0, raise_z])
        anchors["rig_edits"][f"upper_arm.{side}"] = shoulder.tolist()
        put(f"scapula_{side}", placed, scap_f, f"shoulder.{side}", "ct")
        anchors[f"glenoid_{side}"] = glenoid_fossa(placed, shoulder, sign)
        ua_h, ua_t = head_tail(ind, f"upper_arm.{side}")
        ua_h = shoulder  # the raised joint
        fa_h, fa_t = head_tail(ind, f"forearm.{side}")
        if targets is not None:
            ua_t = along(ua_h, ua_t, targets["humerus_m"])
            wrist_new = along(ua_t, fa_t, targets["forearm_m"])
            arm_joints[side] = (ua_t, wrist_new, wrist_new - fa_t)
            fa_h, fa_t = ua_t, wrist_new
            anchors["rig_edits"][f"forearm.{side}"] = ua_t.tolist()
            anchors["rig_edits"][f"hand.{side}"] = wrist_new.tolist()
        hinge = np.cross(ua_t - ua_h, fa_t - fa_h)
        if np.linalg.norm(hinge) < 1e-6:
            hinge = np.array([0, -1.0, 0])
        if hinge[1] > 0:
            hinge = -hinge
        distal = hum_v[np.linalg.norm(hum_v - far, axis=1) < 0.035]
        wide = np.linalg.svd(distal - distal.mean(axis=0), full_matrices=False)[2][0]
        R = fit.frame_rotation(far - head, wide, ua_t - ua_h, np.cross(hinge, ua_t - ua_h))
        # from the head's centre, so the head turns in place at the joint; from the end's centre, 19 mm off, it came through the shoulder
        put(f"humerus_{side}", fit.segment_fit(hum_v, head, far, ua_h, ua_t, rotation=R), hum_f, f"upper_arm.{side}", "ct")
        if targets is not None:
            out[f"humerus_{side}"]["verts"] = fit.thicken(out[f"humerus_{side}"]["verts"], ua_h, ua_t, targets["thickness"]["humerus"]).astype(np.float32)
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
        if targets is not None:
            knee = along(hip, knee, targets["thigh_m"])
            ankle = along(knee, ankle, targets["shin_m"])
            anchors["rig_edits"][f"shin.{side}"] = knee.tolist()
            anchors["rig_edits"][f"foot.{side}"] = ankle.tolist()
        a_h, a_k, a_a = leg_anchors[f"hip_{side}"], leg_anchors[f"knee_{side}"], leg_anchors[f"ankle_{side}"]
        v, f = legs[f"Femur{side}"]
        put(f"femur_{side}", fit.segment_fit(v, a_h, a_k, hip, knee), f, f"thigh.{side}", "bmf")
        if targets is not None:
            out[f"femur_{side}"]["verts"] = fit.thicken(out[f"femur_{side}"]["verts"], hip, knee, targets["thickness"]["femur"]).astype(np.float32)
        v, f = legs[f"Patella{side}"]
        put(f"patella_{side}", fit.segment_fit(v, a_h, a_k, hip, knee), f, f"hm_patella.{side}", "bmf")
        for bone in ("Tibia", "Fibula"):
            v, f = legs[f"{bone}{side}"]
            put(f"{bone.lower()}_{side}", fit.segment_fit(v, a_k, a_a, knee, ankle), f, f"shin.{side}", "bmf")
            if targets is not None:
                out[f"{bone.lower()}_{side}"]["verts"] = fit.thicken(out[f"{bone.lower()}_{side}"]["verts"], knee, ankle, targets["thickness"]["tibia"]).astype(np.float32)
        foot_map = fit_foot(ind, legs, side, ankle)
        for name, (v, f) in legs.items():
            if not name.endswith(side) or not any(k in name for k in FOOT_PARTS):
                continue
            put(f"{name[:-1].lower()}_{side}", foot_map(name, v), f, f"toe.{side}" if "Phalanx" in name else f"foot.{side}", "bmf")
        # The foot's width from the skin too: centred on the talus, the heel and forefoot still came through its sides. Sideways only, and to 70% at most, or the foot loses its shape.
        if targets is None:
            foot = [n for n in out if n.endswith(f"_{side}") and n[:-2].startswith(("talus", "calcaneus", "navicular", "cuboid")) or n.endswith(f"_{side}") and any(k in n for k in ("cuneiform", "metatarsal"))]
            toe = head_tail(ind, f"foot.{side}")[1]
            way = (toe - ankle) / np.linalg.norm(toe - ankle)
            sideways = np.cross(way, [0.0, 0.0, 1.0])
            placed, least = fit.slim_to_skin([out[n]["verts"] for n in foot], ankle, toe, skin, depth, FOOT_TISSUE, start=-10.0, least=0.7, only=sideways / np.linalg.norm(sideways))
            for n, p in zip(foot, placed):
                out[n]["verts"] = p.astype(np.float32)
            anchors["slimmed"][f"foot_{side}"] = round(least, 3)
            # MPFB's knee and ankle are thinner than these bones (bug human-model/20): narrowed where the skin leaves them too little tissue.
            for names, top, bottom, need, key in ((("femur", "patella"), hip, knee, KNEE_TISSUE, "knee"), (("tibia", "fibula"), knee, ankle, SETTLE_TISSUE, "ankle")):
                placed, least = fit.slim_to_skin([out[f"{n}_{side}"]["verts"] for n in names], top, bottom, skin, depth, need)
                for n, p in zip(names, placed):
                    out[f"{n}_{side}"]["verts"] = p.astype(np.float32)
                anchors["slimmed"][f"{key}_{side}"] = round(least, 3)
        fib = out[f"fibula_{side}"]["verts"]
        anchors[f"fibula_head_{side}"] = fib[fib[:, 2] > np.quantile(fib[:, 2], 0.97)].mean(axis=0)

    # Forearm and hand: Rajagopal.
    for side, (arm, elbow, wrist) in (("R", arm_r), ("L", arm_l)):
        fa_h, fa_t = head_tail(ind, f"forearm.{side}")
        delta = np.zeros(3)
        if targets is not None:
            fa_h, fa_t, delta = arm_joints[side]
        thumb = head_tail(ind, f"palm.01.{side}")[1] - head_tail(ind, f"palm.04.{side}")[1]
        suffix = "rv" if side == "R" else "lv"
        radial = arm[f"radius_{suffix}"][0].mean(axis=0) - arm[f"ulna_{suffix}"][0].mean(axis=0)
        R = fit.frame_rotation(wrist - elbow, radial, fa_t - fa_h, thumb)
        for n in ("ulna", "radius"):
            v, f = arm[f"{n}_{suffix}"]
            put(f"{n}_{side}", fit.segment_fit(v, elbow, wrist, fa_h, fa_t, rotation=R), f, f"forearm.{side}", "rajagopal")
            if targets is not None:
                out[f"{n}_{side}"]["verts"] = fit.thicken(out[f"{n}_{side}"]["verts"], fa_h, fa_t, targets["thickness"]["forearm"]).astype(np.float32)
        mid = arm[f"middle_distal_{suffix}s"][0].mean(axis=0)
        idx, lit = arm[f"metacarpal2_{suffix}s"][0].mean(axis=0), arm[f"metacarpal5_{suffix}s"][0].mean(axis=0)
        hand_h = head_tail(ind, f"hand.{side}")[0] + delta
        rig_mid = head_tail(ind, f"f_middle.03.{side}")[1] + delta
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
                h, t = (x + delta for x in head_tail(ind, rig_bone))
                near, far = (a, b) if np.linalg.norm(a - h) < np.linalg.norm(b - h) else (b, a)
                ring = fit.ring_centre(skin, h - delta, t - delta, 0.03)  # the hand's skin stays where the rig was
                shift = ring - (h + t - 2 * delta) / 2 if ring is not None else 0.0
                put(f"{stem}_{side}", fit.segment_fit(placed, near, far, h + shift, t + shift, radial_power=1.0), f, rig_bone, "rajagopal")
            else:
                put(f"{stem}_{side}", placed, f, f"hand.{side}", "rajagopal")
    anchors["settled"] = settle_superficial(out, anchors, depth) if targets is None else {}  # with targets the skin is the result, so there's nothing to settle against
    return out, anchors


def reach_acromion(out, side, medial, lateral):
    """Stretches or shortens the clavicle about its sternal end, and turns it, until its lateral end meets the placed scapula's acromion
    with AC_JOINT between them (bug human-model/18: aimed at a fixed offset from the rig's shoulder, it stopped 17 to 20 mm short).
    The acromion is the scapula's point nearest the clavicle's end. Returns the new lateral end."""
    from scipy.spatial import cKDTree
    scap = cKDTree(out[f"scapula_{side}"]["verts"])
    v0 = out[f"clavicle_{side}"]["verts"].astype(float)
    acromion = out[f"scapula_{side}"]["verts"][scap.query(lateral)[1]].astype(float)
    inward = (medial - acromion) / np.linalg.norm(medial - acromion)

    def placed(back):
        target = acromion + inward * back
        return fit.similarity(v0, medial, lateral, medial, target), target

    lo, hi = 0.0, 0.04  # how far short of the acromion the lateral end's centre sits; the bone's tip reaches past it
    for _ in range(12):
        mid = (lo + hi) / 2
        gap = scap.query(placed(mid)[0])[0].min()
        lo, hi = (lo, mid) if gap > AC_JOINT else (mid, hi)
    v, target = placed(hi)
    out[f"clavicle_{side}"]["verts"] = v.astype(np.float32)
    return target


def settle_superficial(out, anchors, depth_of):
    """Moves the scapulae, clavicles and fibulae until SETTLE_TISSUE covers them (bug human-model/12): the scapula turns about the
    glenoid, the fibula about its head, the clavicle about its sternal end and back. Placed whole from the CT, the right scapula came
    27 mm through the back and the left 15, because the scanned person's shoulders weren't level; the fibulae came 15 mm out behind
    MPFB's slim ankle, and the clavicles' sternal ends lie as far forward as the sternum, which is under 1 mm deep.
    Returns {bone: {"moves": amounts (degrees, or mm for a shift), "short_before_mm", "short_after_mm"}}."""
    mesh = lambda n: (out[n]["verts"], out[n]["faces"])
    chest = [mesh(n) for n in out if n.startswith(("rib_", "sternum", "costal"))]
    ribs = fit.solids(chest)
    report = {}
    for side in ("L", "R"):
        medial, lateral = anchors[f"clavicle_medial_{side}"], anchors[f"clavicle_lateral_{side}"]
        jobs = [
            (f"scapula_{side}", anchors[f"glenoid_{side}"], [("turn", [0, 0, 1], 24.0), ("turn", [1, 0, 0], 24.0), ("turn", [0, 1, 0], 24.0)], ribs),
            (f"clavicle_{side}", medial, [("turn", lateral - medial, 30.0), ("turn", [0, 0, 1], 10.0), ("shift", [0, 1, 0], 0.016)], None),
            (f"fibula_{side}", anchors[f"fibula_head_{side}"], [("turn", [1, 0, 0], 8.0), ("turn", [0, 1, 0], 8.0)], fit.solids([mesh(f"tibia_{side}")])),
        ]
        for name, pivot, moves, avoid in jobs:
            keep = ()
            if name.startswith("clavicle"):
                avoid = fit.solids(chest + [mesh(f"scapula_{side}")])  # the scapula as it has just settled
                lateral = reach_acromion(out, side, medial, lateral)
                anchors[f"clavicle_lateral_{side}"] = lateral
                moves = [("turn", lateral - medial, 30.0), ("turn", [0, 0, 1], 10.0), ("shift", [0, 1, 0], 0.016)]
                keep = ((lateral, 0.004),)  # the joint with the acromion holds
            # the fibula and the clavicle are jointed to the bones they avoid, so they may touch them, not enter them; with any clearance they can't move
            clearance = 0.003 if name.startswith("scapula") else 0.0
            move, before, after, amounts = fit.settle(out[name]["verts"], pivot, depth_of, SETTLE_TISSUE, moves, avoid=avoid, clearance=clearance, keep=keep)
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
