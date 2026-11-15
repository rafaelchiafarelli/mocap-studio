"""Step 11d: the graded tissue moved by the captured skeleton, frame by frame, on the GPU.

    human-model/hm.sh --gpu python human-model/investigations/pose-capture/tissue_sim.py TECIDOS.npz OSSOS.npz OUT_DIR [frames=N] [substeps=S] [ramp=F] [hold=F] [stiff=K] [gravity=0]

TECIDOS.npz is tissue_mesh.py's, OSSOS.npz tissue_motion_dump.py's. A mesh built in the motion's first frame starts there
(ramp 1); otherwise the body starts at rest; over `ramp` frames (default 30) the
bones turn from rest to the dance's first frame (rotations slerped), it holds there `hold` frames (default 15) for the tissue to
settle under gravity, then the dance plays. Only the dance's frames are written:
- pele.pc2: the shown skin (tissue_mesh.py's subdivided skin), a Blender point cache, one sample per frame;
- relatorio.json: time per frame, steps, the volume kept, tetrahedra turned inside out, per group how far the skin moved
  from where its bone alone would carry it (the tissue's own motion).
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
from tissue_solver import GradedSolver  # noqa: E402

GROUPS = ("braco", "antebraco", "tronco", "seio_E", "seio_D", "barriga", "cavidade", "bumbum", "coxa", "perna")


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
    o = {"frames": 0, "substeps": 160, "ramp": 30, "hold": 15, "stiff": 1, "gravity": 1}
    if "pose_frame" in np.load(tissue_npz).files and int(np.load(tissue_npz)["pose_frame"]) == 1:
        o["ramp"] = 1  # already in the first frame
    for item in opts:
        k, v = item.split("=")
        o[k] = int(v)
    m, mo = np.load(tissue_npz), np.load(bones_npz)
    assert list(m["bone_names"]) == list(mo["bone_names"]), "bones differ between mesh and motion"
    T, fps = mo["T"], float(mo["fps"])
    if "T_rest" in m.files and int(m["pose_frame"]) > 0:
        # the mesh was built in a frame of the motion: bones move it relative to that frame
        T = np.einsum("fbij,bjk->fbik", T, np.linalg.inv(m["T_rest"].astype(float))).astype(np.float32)
    if o["frames"]:
        T = T[: o["frames"]]
    nodes, tets = m["nodes"].astype(float), m["tets"]
    wp.init()
    t0 = time.time()
    young = np.where(m["label"] == 3, m["young"], m["young"] * o["stiff"])  # stiff=K: soft tissue K times stiffer, for diagnosis
    solver = GradedSolver(nodes, tets, m["colours"], m["density"], young, m["poisson"], m["node_damping"],
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
    for f, cur in enumerate(schedule):
        solver.set_drive(prev, cur)
        wp.synchronize()
        s = time.time()
        solver.step(1.0 / fps, o["substeps"])
        wp.synchronize()
        times.append(time.time() - s)
        prev = cur
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
                print(json.dumps(report_frames[-1]), f"{times[-1]*1000:.0f} ms", flush=True)
    write_pc2(out / "pele.pc2", skins, fps)
    np.save(out / "pele_faces.npy", m["sub_faces"])
    rep = {"setup_s": round(setup_s, 1), "substeps": o["substeps"], "ramp": o["ramp"], "hold": o["hold"], "dance_frames": len(skins), "fps": fps,
           "ms_per_frame_median": round(float(np.median(times[2:]) * 1000), 1), "ms_per_frame_max": round(float(np.max(times[2:]) * 1000), 1),
           "frames": report_frames}
    (out / "relatorio.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in rep.items() if k != "frames"}))


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
