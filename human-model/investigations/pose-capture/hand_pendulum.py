"""Hands as pendulums carried by the captured arm, with anatomical limits (Rafael, 2026-11-15: "give life" to hands and fingers,
pendulums that follow the armature's bones, the wrist mixed: a spring towards the captured hand; no non-anatomical motion).

    python3 human-model/blender_run.py --blend MOTION.blend human-model/investigations/pose-capture/hand_pendulum.py OUT.blend REPORT.json maos.json

MOTION.blend is drive_capture.py's. Its forearms stay as captured (their swing); everything else here is per side:
- Forearm rotation (pronation and supination). drive_capture.py turns the hand about its own length to match the captured index
  and little finger, which is a twist at the wrist, and a wrist doesn't twist. That twist is moved to the forearm, about its own
  length, limited to `antebraco_rotacao`; the wrist keeps none.
- Wrist, two angles: flexion/extension (towards the palm or the back of the hand) and radial/ulnar deviation (towards the thumb or
  the little finger). Each is a damped spring towards the captured hand's angle, plus the hand's weight and the wrist's
  acceleration acting on the hand's centre of mass; hard limits (`limites`), where the motion stops.
- Fingers: each joint (MCP, PIP, DIP; the thumb's MCP and IP) a damped pendulum towards a relaxed hand, bending only towards the
  palm, about the axis that moves the bone towards it (found as arm_pendulum.py does: the palm from the knuckle row and the
  fingernails); driven by gravity and the acceleration of its joint, acting on the segments beyond it. No sideways spread, no
  hyperextension. The thumb's base (thumb.01) and the palm bones stay at rest.
The arm's motion within a frame is a Catmull-Rom curve through the frames, so accelerations don't jump at frame boundaries.
`aquecimento_quadros` frames held at the first frame settle the hands before the dance. Writes OUT.blend (keys on forearm, hand
and finger bones) and REPORT.json (angles' ranges, share of time at a limit, how far the hand is from the captured one).
"""
import json, math, sys
import bpy
import numpy as np
from mathutils import Matrix, Quaternion

argv = sys.argv[sys.argv.index("--") + 1:]
out, report_path, params_path = argv[0], argv[1], argv[2]
P = json.load(open(params_path, encoding="utf-8"))
LIM, RELAX = P["limites"], P["repouso"]
rig, body, scene = bpy.data.objects["HM_rig"], bpy.data.objects["HM_body"], bpy.context.scene
Bn, PB = rig.data.bones, rig.pose.bones
first, last = scene.frame_start, scene.frame_end
fps = scene.render.fps / scene.render.fps_base
S = int(P["subpassos"])
dt = 1.0 / fps / S
G = np.array([0.0, 0.0, -9.81])
FINGERS = {"f_index": "palm.01", "f_middle": "palm.02", "f_ring": "palm.03", "f_pinky": "palm.04"}
Y = np.array([0.0, 1.0, 0.0])


def rot(axis, ang):
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * K @ K


def h4(R, t=(0.0, 0.0, 0.0)):
    M = np.eye(4)
    M[:3, :3], M[:3, 3] = R, t
    return M


def rest(b):
    return np.array(Bn[b].matrix_local)


def q_of(R):
    q = Matrix(R.tolist()).to_quaternion()
    return np.array([q.w, q.x, q.y, q.z])


def R_of(q):
    q = np.asarray(q, float) / np.linalg.norm(q)
    return np.array(Quaternion(q).to_matrix())


# ---------- rest geometry: the palm, each joint's bending axis, the wrist's axes ----------
rig.data.pose_position = "REST"
bpy.context.view_layer.update()
to_arm = np.array(rig.matrix_world.inverted() @ body.matrix_world)
nail_g = body.vertex_groups["fingernails"].index
nails = np.array([(to_arm @ np.array(list(v.co) + [1.0]))[:3] for v in body.data.vertices
                  if any(g.group == nail_g and g.weight > 0.5 for g in v.groups)])
rig.data.pose_position = "POSE"
bpy.context.view_layer.update()
head = lambda b: rest(b)[:3, 3]
tail = lambda b: (rest(b) @ np.array([0.0, Bn[b].length, 0.0, 1.0]))[:3]
side_data = {}
for s in "LR":
    along = tail(f"hand.{s}") - head(f"hand.{s}")
    knuckles = head(f"f_index.01.{s}") - head(f"f_pinky.01.{s}")
    n = np.cross(knuckles, along)
    n /= np.linalg.norm(n)
    tip_mid = (head(f"f_middle.03.{s}") + tail(f"f_middle.03.{s}")) / 2
    nail = nails[np.argsort(np.linalg.norm(nails - tip_mid, axis=1))[:6]].mean(axis=0)
    palm = -n if np.dot(nail - tip_mid, n) > 0 else n
    # each finger joint: the local axis (X or Z) and way that moves the bone's tip towards the palm
    chains = {}
    for finger, palm_bone in list(FINGERS.items()) + [("thumb", f"palm.01")]:
        bones = [f"{finger}.0{i}.{s}" for i in (1, 2, 3)]
        axes = []
        for b in bones:
            R = rest(b)[:3, :3]
            tl = np.array([0.0, Bn[b].length, 0.0])
            best = None
            for ax in (np.array([1.0, 0, 0]), np.array([0, 0, 1.0])):
                for sg in (1.0, -1.0):
                    d = R @ (rot(ax, sg * 0.35) @ tl - tl)
                    sc = float(np.dot(d, palm))
                    if best is None or sc > best[0]:
                        best = (sc, sg * ax)
            axes.append(best[1])
        if finger == "thumb":
            kinds = [None, ("polegar_mcp"), ("polegar_ip")]  # thumb.01, the base, stays at rest
        else:
            kinds = ["mcp", "pip", "dip"]
        chains[finger] = {"parent": f"{palm_bone}.{s}", "bones": bones, "axes": axes, "kinds": kinds}
    Rh = rest(f"hand.{s}")[:3, :3]
    n_loc = Rh.T @ palm
    a_d = n_loc - np.dot(n_loc, Y) * Y
    a_d /= np.linalg.norm(a_d)
    a_f = np.cross(Y, a_d)
    a_f /= np.linalg.norm(a_f)
    if np.dot(rot(a_f, 0.2) @ Y - Y, n_loc) < 0:  # positive flexion takes the hand towards the palm
        a_f = -a_f
    thumb_dir = Rh.T @ (head(f"thumb.01.{s}") - head(f"hand.{s}"))
    thumb_dir -= np.dot(thumb_dir, Y) * Y
    if np.dot(rot(a_d, 0.2) @ Y - Y, thumb_dir) < 0:  # positive deviation takes it towards the thumb (radial)
        a_d = -a_d
    hand_reach = Bn[f"hand.{s}"].length + sum(Bn[f"f_middle.0{i}.{s}"].length for i in (1, 2, 3))
    side_data[s] = {"palm": palm, "chains": chains, "a_f": a_f, "a_d": a_d,
                    "Rrel": rest(f"forearm.{s}")[:3, :3].T @ Rh, "fore_len": Bn[f"forearm.{s}"].length,
                    "com": np.array([0.0, P["punho"]["centro_de_massa_da_mao"] * hand_reach, 0.0])}

# ---------- the captured arm and hand per frame ----------
frames = list(range(first, last + 1))
cap = {s: {"pf": [], "qf": [], "qf_local": [], "tf": [], "td": [], "tw": [], "Hw": [], "Fr": [], "bend": [], "tf_raw": [], "td_raw": []} for s in "LR"}
for f in frames:
    scene.frame_set(f)
    W = np.array(rig.matrix_world)
    for s in "LR":
        d = side_data[s]
        Fw = W @ np.array(PB[f"forearm.{s}"].matrix)
        Hw = W @ np.array(PB[f"hand.{s}"].matrix)
        Fr, Hr = Fw[:3, :3], Hw[:3, :3]
        Q = d["Rrel"].T @ Fr.T @ Hr  # the captured hand, in its rest frame relative to the forearm
        q = q_of(Q)
        # Q = T(twist about the forearm's length, seen in the hand's rest frame) then the swing, the order step() rebuilds it in:
        # Fr @ rot(Y, twist) @ Rrel = Fr @ Rrel @ rot(Rrel^T Y, twist). Split the other way round, or about the hand's own length,
        # the hand ended 32 to 49 degrees (median) from the captured one
        a = d["Rrel"].T @ Y
        proj = np.dot(q[1:], a)
        tw = np.array([q[0], *(proj * a)])
        tw /= np.linalg.norm(tw)
        twist = 2 * math.atan2(np.dot(tw[1:], a), tw[0])
        twist = (twist + math.pi) % (2 * math.pi) - math.pi
        swing = Quaternion(tw).inverted() @ Quaternion(q)
        rv = np.array(swing.axis) * swing.angle
        c = cap[s]
        c["pf"].append(Fw[:3, 3].copy())
        c["qf"].append(q_of(Fr))
        c["qf_local"].append(np.array(PB[f"forearm.{s}"].rotation_quaternion))
        c["tf"].append(float(np.dot(rv, d["a_f"])))
        c["td"].append(float(np.dot(rv, d["a_d"])))
        c["tw"].append(twist)
        c["Hw"].append(Hr.copy())
        c["Fr"].append(Fr.copy())
        c["bend"].append(math.degrees(Quaternion(q).angle))
        c["tf_raw"].append(float(np.dot(rv, d["a_f"])))
        c["td_raw"].append(float(np.dot(rv, d["a_d"])))
for s in "LR":
    c = cap[s]
    for k in c:
        c[k] = np.array(c[k])
    for t in range(1, len(frames)):  # one hemisphere, so quaternions interpolate the short way
        if np.dot(c["qf"][t], c["qf"][t - 1]) < 0:
            c["qf"][t] = -c["qf"][t]
    c["tw"] = np.unwrap(c["tw"])
    rl = math.radians(LIM["antebraco_rotacao"])
    c["tw"] = np.clip(c["tw"], -rl, rl)
    c["tf"] = np.clip(c["tf"], -math.radians(LIM["punho_extensao"]), math.radians(LIM["punho_flexao"]))
    c["td"] = np.clip(c["td"], -math.radians(LIM["punho_ulnar"]), math.radians(LIM["punho_radial"]))


def catmull(P_, i, u):
    n = len(P_)
    p0, p1, p2, p3 = P_[max(i - 1, 0)], P_[i], P_[min(i + 1, n - 1)], P_[min(i + 2, n - 1)]
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)


def lerp(a, i, u):
    return a[i] * (1 - u) + a[min(i + 1, len(a) - 1)] * u


def angle_between(Ra, Rb):
    return math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(Ra.T @ Rb) - 1) / 2))))


# diagnosis: the captured hand against the targets alone (no dynamics), before and after the limits
diag = {}
for s in "LR":
    c, d = cap[s], side_data[s]
    raw, lim = [], []
    tw_raw = np.unwrap(np.array(c["tw"]))
    for t in range(len(frames)):
        for out_, tf, td, tw in ((raw, c["tf_raw"][t], c["td_raw"][t], c["tw"][t]), (lim, c["tf"][t], c["td"][t], c["tw"][t])):
            Rt = c["Fr"][t] @ rot(Y, tw) @ d["Rrel"] @ rot(d["a_f"], tf) @ rot(d["a_d"], td)
            out_.append(angle_between(Rt, c["Hw"][t]))
    pct = lambda a: {"mediana": round(float(np.median(a)), 1), "p95": round(float(np.percentile(a, 95)), 1)}
    diag[s] = {"mao_capturada_dobrada_no_antebraco_deg": pct(c["bend"]), "alvo_sem_limites_vs_captura_deg": pct(raw),
               "alvo_com_limites_vs_captura_deg": pct(lim),
               "flexao_capturada_deg": [round(math.degrees(min(c["tf_raw"])), 1), round(math.degrees(max(c["tf_raw"])), 1)],
               "desvio_capturado_deg": [round(math.degrees(min(c["td_raw"])), 1), round(math.degrees(max(c["td_raw"])), 1)]}
print("DIAG", json.dumps(diag))

# ---------- simulation ----------
wl, wz = 2 * math.pi * P["punho"]["frequencia_hz"], P["punho"]["amortecimento"]
fl, fz = 2 * math.pi * P["dedos"]["frequencia_hz"], P["dedos"]["amortecimento"]
seg_m = np.array(P["dedos"]["massas_g"], float) / 1000
limits = {k: (math.radians(LIM[k][0]), math.radians(LIM[k][1])) for k in ("mcp", "pip", "dip", "polegar_mcp", "polegar_ip")}
lim_w = {"tf": (-math.radians(LIM["punho_extensao"]), math.radians(LIM["punho_flexao"])),
         "td": (-math.radians(LIM["punho_ulnar"]), math.radians(LIM["punho_radial"]))}
state = {}
for s in "LR":
    st = {"th": np.array([cap[s]["tf"][0], cap[s]["td"][0]]), "thd": np.zeros(2), "hist": {}, "phi": {}, "phid": {}}
    for finger, ch in side_data[s]["chains"].items():
        for b, kind in zip(ch["bones"], ch["kinds"]):
            st["phi"][b] = math.radians(RELAX[kind]) if kind else 0.0
            st["phid"][b] = 0.0
    state[s] = st
rec = {s: {"th": [], "tw": [], "phi": {}, "at_limit": 0, "off_capture_deg": [], "steps": 0} for s in "LR"}


def accel(st, key, p):
    """Second difference of a point over the last substeps; zero until there are three."""
    h = st["hist"].setdefault(key, [])
    h.append(p.copy())
    if len(h) > 3:
        h.pop(0)
    if len(h) < 3:
        return np.zeros(3)
    return (h[2] - 2 * h[1] + h[0]) / (dt * dt)


def step(s, i, u, keep):
    d, c, st = side_data[s], cap[s], state[s]
    pf = catmull(c["pf"], i, u)
    qf = catmull(c["qf"], i, u)
    tw = lerp(c["tw"], i, u)
    target = np.array([lerp(c["tf"], i, u), lerp(c["td"], i, u)])
    Fw = h4(R_of(qf) @ rot(Y, tw), pf)  # the forearm, turned about its own length by the captured twist
    wrist = (Fw @ np.array([0.0, d["fore_len"], 0.0, 1.0]))[:3]
    a_w = accel(st, "wrist", wrist)
    if keep:
        rec[s].setdefault("a_wrist", []).append(float(np.linalg.norm(a_w)))
        rec[s].setdefault("lag", []).append([math.degrees(st["th"][0] - target[0]), math.degrees(st["th"][1] - target[1])])
    g_eff = G - a_w
    Rh = Fw[:3, :3] @ d["Rrel"] @ rot(d["a_f"], st["th"][0]) @ rot(d["a_d"], st["th"][1])
    r = Rh @ d["com"]
    for k, (ax, key) in enumerate(((d["a_f"], "tf"), (d["a_d"], "td"))):
        torque = float(np.dot(np.cross(r, g_eff), Rh @ ax)) / (1.2 * float(np.dot(r, r)))
        acc = wl * wl * (target[k] - st["th"][k]) - 2 * wz * wl * st["thd"][k] + torque
        st["thd"][k] += acc * dt
        st["th"][k] += st["thd"][k] * dt
        lo, hi = lim_w[key]
        if st["th"][k] < lo or st["th"][k] > hi:
            st["th"][k] = min(max(st["th"][k], lo), hi)
            st["thd"][k] = 0.0  # the joint stops at its limit
            if keep:
                rec[s]["at_limit"] += 1
    hand_w = Fw @ np.linalg.inv(rest(f"forearm.{s}")) @ rest(f"hand.{s}") @ h4(rot(d["a_f"], st["th"][0]) @ rot(d["a_d"], st["th"][1]))
    for finger, ch in d["chains"].items():
        parent_w = hand_w @ np.linalg.inv(rest(f"hand.{s}")) @ rest(ch["parent"])
        pname = ch["parent"]
        worlds = []
        for b, ax in zip(ch["bones"], ch["axes"]):
            Wb = parent_w @ np.linalg.inv(rest(pname)) @ rest(b) @ h4(rot(ax, st["phi"][b]))
            worlds.append(Wb)
            parent_w, pname = Wb, b
        centres = [(Wb @ np.array([0.0, Bn[b].length / 2, 0.0, 1.0]))[:3] for Wb, b in zip(worlds, ch["bones"])]
        for j, (b, ax, kind) in enumerate(zip(ch["bones"], ch["axes"], ch["kinds"])):
            if kind is None:
                continue
            joint = worlds[j][:3, 3]
            ge = G - accel(st, b, joint)
            ax_w = worlds[j][:3, :3] @ ax
            tq, inertia = 0.0, 0.0
            for k in range(j, 3):
                rr = centres[k] - joint
                tq += seg_m[k] * float(np.dot(np.cross(rr, ge), ax_w))
                inertia += seg_m[k] * float(np.dot(rr, rr))
            acc = fl * fl * (math.radians(RELAX[kind]) - st["phi"][b]) - 2 * fz * fl * st["phid"][b] + tq / max(inertia, 1e-9)
            st["phid"][b] += acc * dt
            st["phi"][b] += st["phid"][b] * dt
            lo, hi = limits[kind]
            if st["phi"][b] < lo or st["phi"][b] > hi:
                st["phi"][b] = min(max(st["phi"][b], lo), hi)
                st["phid"][b] = 0.0


warm = int(P["aquecimento_quadros"])
for _ in range(warm * S):
    for s in "LR":
        step(s, 0, 0.0, False)
for t, f in enumerate(frames):
    for k in range(S):
        u = (k + 1) / S
        i = t - 1 if t > 0 else 0
        uu = u if t > 0 else 0.0
        for s in "LR":
            step(s, i, uu, True)
            rec[s]["steps"] += 1
    for s in "LR":
        d, st = side_data[s], state[s]
        R_loc = rot(d["a_f"], st["th"][0]) @ rot(d["a_d"], st["th"][1])
        fq = Quaternion(cap[s]["qf_local"][t]) @ Quaternion((0.0, 1.0, 0.0), float(cap[s]["tw"][t]))
        PB[f"forearm.{s}"].rotation_quaternion = fq
        PB[f"forearm.{s}"].keyframe_insert("rotation_quaternion", frame=f)
        PB[f"hand.{s}"].rotation_quaternion = Quaternion(q_of(R_loc))
        PB[f"hand.{s}"].keyframe_insert("rotation_quaternion", frame=f)
        for finger, ch in d["chains"].items():
            for b, ax, kind in zip(ch["bones"], ch["axes"], ch["kinds"]):
                PB[b].rotation_mode = "QUATERNION"
                PB[b].rotation_quaternion = Quaternion(ax.tolist(), st["phi"][b]) if kind else Quaternion()
                PB[b].keyframe_insert("rotation_quaternion", frame=f)
                rec[s]["phi"].setdefault(kind or b, []).append(math.degrees(st["phi"][b]))
        rec[s]["th"].append([math.degrees(v) for v in st["th"]])
        rec[s]["tw"].append(math.degrees(cap[s]["tw"][t]))
    for s in "LR":
        rec[s]["th_frames"] = rec[s].get("th_frames", []) + [state[s]["th"].copy()]

# with the keys written, every frame evaluated: the hand against the captured one, and against what the model meant to put there
# (measured while writing, the arm above and the root were still those of the last frame: 32 to 49 degrees off, all of it false)
for t, f in enumerate(frames):
    scene.frame_set(f)
    W = np.array(rig.matrix_world)
    for s in "LR":
        Hn = (W @ np.array(PB[f"hand.{s}"].matrix))[:3, :3]
        d_, th = side_data[s], rec[s]["th_frames"][t]
        Rm = cap[s]["Fr"][t] @ rot(Y, cap[s]["tw"][t]) @ d_["Rrel"] @ rot(d_["a_f"], th[0]) @ rot(d_["a_d"], th[1])
        rec[s].setdefault("model_vs_blender", []).append(angle_between(Rm, Hn))
        rec[s]["off_capture_deg"].append(angle_between(cap[s]["Hw"][t], Hn))

bpy.ops.wm.save_as_mainfile(filepath=out)
rng = lambda a: [round(float(np.min(a)), 1), round(float(np.max(a)), 1)]
report = {"frames": len(frames), "substeps": S, "params": params_path, "diagnostico": diag}
for s in "LR":
    r = rec[s]
    th = np.array(r["th"])
    report[s] = {"punho_flexao_deg": rng(th[:, 0]), "punho_desvio_deg": rng(th[:, 1]), "antebraco_rotacao_deg": rng(r["tw"]),
                 "punho_no_limite_pct_dos_subpassos": round(100 * r["at_limit"] / max(1, 2 * r["steps"]), 2),
                 "mao_longe_da_captura_deg": {"mediana": round(float(np.median(r["off_capture_deg"])), 1),
                                              "p95": round(float(np.percentile(r["off_capture_deg"], 95)), 1)},
                 "dedos_deg": {k: rng(v) for k, v in r["phi"].items() if not k.startswith("thumb.01")},
                 "aceleracao_do_punho_m_s2": {"mediana": round(float(np.median(r["a_wrist"])), 1), "p95": round(float(np.percentile(r["a_wrist"], 95)), 1)},
                 "modelo_vs_blender_mao_deg_p95": round(float(np.percentile(r["model_vs_blender"], 95)), 2),
                 "punho_atras_do_alvo_deg_p95": [round(float(np.percentile(np.abs(np.array(r["lag"])[:, k]), 95)), 1) for k in (0, 1)]}
json.dump(report, open(report_path, "w"), indent=1)
print(json.dumps(report))
