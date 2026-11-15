"""Step 11d: the graded tissue moved by the captured skeleton, frame by frame, on the GPU.

    human-model/hm.sh --gpu python human-model/investigations/pose-capture/tissue_sim.py TECIDOS.npz OSSOS.npz OUT_DIR [frames=N] [substeps=S] [ramp=F] [hold=F] [stiff=K] [gravity=0] [uniforme=1] [contato=0] [cede_mm=5] [contato_cada=1]

TECIDOS.npz is tissue_mesh.py's, OSSOS.npz tissue_motion_dump.py's. A mesh built in the motion's first frame starts there
(ramp 1); otherwise the body starts at rest; over `ramp` frames (default 30) the
bones turn from rest to the dance's first frame (rotations slerped), it holds there `hold` frames (default 15) for the tissue to
settle under gravity, then the dance plays. Only the dance's frames are written:
- pele.pc2: the shown skin (tissue_mesh.py's subdivided skin), a Blender point cache, one sample per frame;
- relatorio.json: time per frame, steps, the volume kept, tetrahedra turned inside out, per group how far the skin moved
  from where its bone alone would carry it (the tissue's own motion); with contact, per frame how far the skeleton alone pushes
  one part into another (or a hand into the body) past the skin's yield, and how much overlap is left after the step, per pair.
Contact (on when the mesh has parts, tissue_mesh.py; contato=0 turns it off): parts and hands collide every `contato_cada`
substeps; the skin yields up to `cede_mm` (Rafael, 2026-11-14: 5 mm), past which the skeleton's overlap is left and measured.
"""
from __future__ import annotations

import json
import struct
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE))
import warp as wp  # noqa: E402
from scipy.spatial.transform import Rotation, Slerp  # noqa: E402
from hmcore import xpbd  # noqa: E402
from tissue_solver import ContactSolver, GradedSolver  # noqa: E402

GROUPS = ("braco", "antebraco", "tronco", "seio_E", "seio_D", "barriga", "cavidade", "bumbum", "coxa", "perna")
PARTS = ("tronco", "braco_E", "braco_D", "perna_E", "perna_D", "mao_E", "mao_D")
# (tested part, against part) pairs left out: a hand against its own arm (they join at the wrist); legs and trunk (2026-11-14:
# joined over most of the hip, split in patches, their surfaces at the groin and under the buttock tangled, and contact there
# resolved nothing and nearly blew up; buttock/thigh and belly/thigh are left open)
SKIP_PAIRS = [(1, 5), (2, 6), (0, 3), (0, 4), (3, 0), (4, 0)]


def lbs(points, weights, T):
    w = weights / np.maximum(weights.sum(axis=1, keepdims=True), 1e-9)
    out = np.zeros_like(points)
    for b in np.flatnonzero(w.any(axis=0)):
        sel = w[:, b] > 0
        out[sel] += w[sel, b, None] * (points[sel] @ T[b, :3, :3].T + T[b, :3, 3])
    return out


def ramp_transforms(T0, n):
    """n transforms per bone from identity to T0, rotation slerped, translation straight."""
    out = np.repeat(np.eye(4, dtype=np.float32)[None, None], n, axis=0).repeat(len(T0), axis=1)
    rots = Rotation.from_matrix(T0[:, :3, :3])
    for b in range(len(T0)):
        s = Slerp([0, 1], Rotation.concatenate([Rotation.identity(), rots[b]]))
        a = np.linspace(1 / n, 1, n)
        out[:, b, :3, :3] = s(a).as_matrix()
        out[:, b, :3, 3] = a[:, None] * T0[b, :3, 3]
    return out


def write_pc2(path, frames, fps):
    frames = np.asarray(frames, np.float32)
    with open(path, "wb") as fh:
        fh.write(struct.pack("<12siiffi", b"POINTCACHE2\0", 1, frames.shape[1], 1.0, 1.0, frames.shape[0]))
        fh.write(frames.tobytes())


def main(tissue_npz, bones_npz, out_dir, opts):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    o = {"frames": 0, "substeps": 160, "ramp": 30, "hold": 15, "stiff": 1, "gravity": 1, "uniforme": 0, "contato": 1, "cede_mm": 5,
         "contato_cada": 1}
    if "pose_frame" in np.load(tissue_npz).files and int(np.load(tissue_npz)["pose_frame"]) == 1:
        o["ramp"] = 1  # already in the first frame
    for item in opts:
        k, v = item.split("=")
        o[k] = float(v) if k == "cede_mm" else int(v)
    m, mo = np.load(tissue_npz), np.load(bones_npz)
    assert list(m["bone_names"]) == list(mo["bone_names"]), "bones differ between mesh and motion"
    T, fps = mo["T"], float(mo["fps"])
    T_build = m["T_rest"].astype(float) if "T_rest" in m.files and int(m["pose_frame"]) > 0 else np.repeat(np.eye(4)[None], T.shape[1], 0)
    if "T_rest" in m.files and int(m["pose_frame"]) > 0:
        # the mesh was built in a frame of the motion: bones move it relative to that frame
        T = np.einsum("fbij,bjk->fbik", T, np.linalg.inv(m["T_rest"].astype(float))).astype(np.float32)
    if o["frames"]:
        T = T[: o["frames"]]
    nodes, tets = m["nodes"].astype(float), m["tets"]
    wp.init()
    t0 = time.time()
    young = np.where(m["label"] == 3, m["young"], m["young"] * o["stiff"])  # stiff=K: soft tissue K times stiffer, for diagnosis
    density, node_damping = m["density"], m["node_damping"]
    if o["uniforme"]:  # diagnosis: one density (900 kg/m3, times the overlap weight) and one damping (20/s) for all soft tissue
        density = np.where(m["label"] == 3, density, 900.0 * m["weight"])
        node_damping = np.full_like(node_damping, 20.0)
    contact = bool(o["contato"]) and "coll_tris" in m.files
    if contact:
        solver = ContactSolver(nodes, tets, m["colours"], density, young, m["poisson"], node_damping, m["emb_node"], m["emb_tets"], m["emb_w"],
                               coll_tris=m["coll_tris"], coll_part=m["coll_part"], coll_nodes=m["coll_nodes"], node_part=m["node_part"],
                               hand_tris=m["hand_tris"], hand_part=m["hand_part"], n_hand=len(m["hand_rest"]), yield_m=o["cede_mm"] / 1000,
                               every=o["contato_cada"], skip_pairs=SKIP_PAIRS)
        hand_rest, hand_w = m["hand_rest"].astype(float), m["hand_w"].astype(float)
        hands_at = lambda Trel: lbs(hand_rest, hand_w, np.einsum("bij,bjk->bik", Trel.astype(float), T_build))
        q_part = m["node_part"][m["coll_nodes"]]
    else:
        solver = GradedSolver(nodes, tets, m["colours"], density, young, m["poisson"], node_damping,
                              m["emb_node"], m["emb_tets"], m["emb_w"])
    if not o["gravity"]:
        solver.gravity = wp.vec3(0.0, 0.0, 0.0)
    solver.drive(m["driven"], nodes[m["driven"]], all_rest=nodes, bone=m["drive_bone"], all_bone=m["node_bone"], n_bones=T.shape[1])
    setup_s = time.time() - t0
    schedule = np.concatenate([ramp_transforms(T[0], o["ramp"]), np.repeat(T[:1], o["hold"], axis=0), T])
    first_dance = o["ramp"] + o["hold"]
    st, sb = m["sub_tet"], m["sub_bary"].astype(float)
    sub_nodes = tets[st]
    # each shown vertex's bone: the one its tetrahedron's first node follows, for "own motion" (tissue against bone)
    sub_bone = m["node_bone"][sub_nodes[:, 0]]
    sub_rest = m["sub_rest"].astype(float)
    sub_group = m["group"][st]
    rest_vol = solver.rest_total
    skins, times, report_frames = [], [], []
    prev = np.repeat(np.eye(4, dtype=np.float32)[None], T.shape[1], axis=0)
    contact_frames = []
    at_build = None
    if contact:
        # at the build pose, before any step: the parts only touch, so next to nothing should read as inside
        solver.set_hands(hands_at(prev), hands_at(prev))
        left0, lw0, _, _ = solver.overlap_now()
        mp0 = np.array(solver.mesh_parts)
        at_build = {"inside_over_1mm_nodes": int((left0 > 0.001).sum()), "inside_max_mm": round(float(left0.max() * 1000), 1),
                    "pairs": {}}
        for a, b in zip(q_part[left0 > 0.001], mp0[lw0[left0 > 0.001]]):
            key = "/".join(sorted((PARTS[a], PARTS[b])))
            at_build["pairs"][key] = at_build["pairs"].get(key, 0) + 1
        print("at build:", json.dumps(at_build), flush=True)
        np.save(out / "dentro_na_construcao.npy", np.column_stack([nodes[m["coll_nodes"]], left0]).astype(np.float32))
        solver.set_base(left0)
        base0 = left0
    hands_prev = hands_at(prev) if contact else None
    for f, cur in enumerate(schedule):
        solver.set_drive(prev, cur)
        if contact:
            hands_cur = hands_at(cur)
            solver.set_hands(hands_prev, hands_cur)
            hands_prev = hands_cur
        wp.synchronize()
        s = time.time()
        solver.step(1.0 / fps, o["substeps"])
        wp.synchronize()
        times.append(time.time() - s)
        prev = cur
        if f >= first_dance and contact:
            left, lw, skel, sw = solver.overlap_now()
            # what contact should have removed: inside past what is allowed (the build's reading, or the skeleton's past the yield)
            unresolved = left - np.maximum(base0, skel - o["cede_mm"] / 1000)
            tested = ~np.isin(np.char.add(np.char.add(q_part.astype(str), "-"), np.array(solver.mesh_parts)[lw].astype(str)),
                              [f"{a}-{b}" for a, b in SKIP_PAIRS])
            unresolved = np.where(tested, unresolved, 0.0)
            if (f - first_dance) % 10 == 0:
                bad = unresolved > 0.001
                np.save(out / f"nao_resolvidos_{f - first_dance + 1:03d}.npy",
                        np.column_stack([solver.positions()[m["coll_nodes"]][bad], unresolved[bad], left[bad], skel[bad], base0[bad],
                                         q_part[bad], np.array(solver.mesh_parts)[lw[bad]], m["coll_nodes"][bad]]).astype(np.float32))
            # measured from the build pose's own reading (the voxel staircase where parts meet)
            left, skel = np.maximum(0.0, left - base0), np.maximum(0.0, skel - base0)
            mp = np.array(solver.mesh_parts)
            over = skel > o["cede_mm"] / 1000

            def pairs(sel, which):
                out = {}
                for a, b in zip(q_part[sel], mp[which[sel]]):
                    key = "/".join(sorted((PARTS[a], PARTS[b])))
                    out[key] = out.get(key, 0) + 1
                return out
            st_push = solver.take_stats()
            near_cnt = int((solver.near.numpy() < solver.near_m).sum())
            contact_frames.append({"frame": f - first_dance + 1, "pushes": st_push["pushes"], "pushed_total_m": st_push["pushed_total_m"],
                                   "near_nodes": near_cnt,
                                   "skeleton_past_yield_nodes": int(over.sum()),
                                   "skeleton_past_yield_max_mm": round(float(skel.max() * 1000 - o["cede_mm"]), 1) if over.any() else 0.0,
                                   "skeleton_past_yield_pairs": pairs(over, sw),
                                   "unresolved_over_1mm_nodes": int((unresolved > 0.001).sum()),
                                   "unresolved_max_mm": round(float(max(unresolved.max(), 0.0) * 1000), 1),
                                   "left_inside_over_1mm_nodes": int((left > 0.001).sum()), "left_inside_max_mm": round(float(left.max() * 1000), 1),
                                   "left_inside_pairs": pairs(left > 0.001, lw)})
        if f >= first_dance:
            x = solver.positions().astype(float)
            skin = np.einsum("vk,vkd->vd", sb, x[sub_nodes])
            skins.append(skin.astype(np.float32))
            if (f - first_dance) % 10 == 0 or f == len(schedule) - 1:
                carried = np.einsum("vij,vj->vi", cur[sub_bone][:, :3, :3], sub_rest) + cur[sub_bone][:, :3, 3]
                own = np.linalg.norm(skin - carried, axis=1)
                v = xpbd.volumes(x, solver.tets_host)
                report_frames.append({"frame": f - first_dance + 1, "volume_kept_pct": round(float(v.sum() / rest_vol * 100), 2),
                                      "inverted_tets": int((v <= 0).sum()),
                                      "own_motion_mm_p95": {g: round(float(np.percentile(own[sub_group == i], 95) * 1000), 1)
                                                            for i, g in enumerate(GROUPS) if (sub_group == i).any()}})
                if contact:
                    report_frames[-1]["contact"] = contact_frames[-1]
                print(json.dumps(report_frames[-1]), f"{times[-1]*1000:.0f} ms", flush=True)
    write_pc2(out / "pele.pc2", skins, fps)
    np.save(out / "pele_faces.npy", m["sub_faces"])
    rep = {"setup_s": round(setup_s, 1), "substeps": o["substeps"], "ramp": o["ramp"], "hold": o["hold"], "dance_frames": len(skins), "fps": fps,
           "ms_per_frame_median": round(float(np.median(times[2:]) * 1000), 1), "ms_per_frame_max": round(float(np.max(times[2:]) * 1000), 1),
           "frames": report_frames}
    if contact:
        rep["contact"] = {"at_build": at_build, "yield_mm": o["cede_mm"], "every_substeps": o["contato_cada"],
                          "frames_with_skeleton_past_yield": sum(1 for c in contact_frames if c["skeleton_past_yield_nodes"]),
                          "skeleton_past_yield_max_mm": max(c["skeleton_past_yield_max_mm"] for c in contact_frames),
                          "left_inside_max_mm": max(c["left_inside_max_mm"] for c in contact_frames),
                          "unresolved_over_1mm_nodes_median": float(np.median([c["unresolved_over_1mm_nodes"] for c in contact_frames])),
                          "unresolved_max_mm": max(c["unresolved_max_mm"] for c in contact_frames)}
        (out / "contato_por_quadro.json").write_text(json.dumps(contact_frames, indent=0), encoding="utf-8")
    (out / "relatorio.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in rep.items() if k != "frames"}))


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
