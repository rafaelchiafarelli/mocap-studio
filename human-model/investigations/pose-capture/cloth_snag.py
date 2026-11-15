"""How much of a piece the arms carry off: the cloth caught on a forearm (Rafael, 2026-11-15: "a roupa continua enroscando no punho").

    human-model/hm.sh --gpu python human-model/investigations/pose-capture/cloth_snag.py TECIDOS.npz ROUPA.npz SIM_DIR [PECA] [OUT.json]

TECIDOS.npz: tissue_mesh.py's (rest); ROUPA.npz: dress_rest.py's; SIM_DIR: tissue_cloth_sim.py's (pele.pc2, <PECA>.pc2; PECA
blusinha by default). Per frame, the piece's vertices lying within `PERTO_MM` of an arm's skin that were further than
`LONGE_EM_REPOUSO_MM` from that arm at rest (the hem, not the sleeve): how many, and how far around the arm they reach (the
angle they cover about the forearm's axis, 360 = a bracelet). Arm skin: the groups `braco` and `antebraco`, left at +x.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from tissue_sim import GROUPS  # noqa: E402

PERTO_MM = 6.0
LONGE_EM_REPOUSO_MM = 60.0


def read_pc2(path):
    with open(path, "rb") as f:
        head = f.read(32)
        n = int(np.frombuffer(head[16:20], np.int32)[0])
        frames = int(np.frombuffer(head[28:32], np.int32)[0])
        return np.frombuffer(f.read(), np.float32).reshape(frames, n, 3)


def main(tissue, cloth, sim_dir, piece="blusinha", out=None):
    m, cl = np.load(tissue), np.load(cloth)
    groups = np.array(GROUPS)[m["group"][m["sub_tet"]]]
    rest = m["sub_rest"].astype(float)
    arm = np.isin(groups, ("braco", "antebraco"))
    fore = groups == "antebraco"
    left = rest[:, 0] > 0
    sides = {"esq": arm & left, "dir": arm & ~left}
    c_rest = cl[f"{piece}_verts"].astype(float)
    far = {s: cKDTree(rest[sel]).query(c_rest)[0] > LONGE_EM_REPOUSO_MM / 1000 for s, sel in sides.items()}
    skin, cx = read_pc2(Path(sim_dir) / "pele.pc2"), read_pc2(Path(sim_dir) / f"{piece}.pc2")
    rows = []
    for f in range(len(cx)):
        row = {"quadro": f + 1}
        for s, sel in sides.items():
            ids = np.flatnonzero(sel)
            d, j = cKDTree(skin[f, ids]).query(cx[f], distance_upper_bound=0.05)
            caught = far[s] & (d < PERTO_MM / 1000)
            ang = 0.0
            if caught.sum() >= 3:
                # the forearm's axis: its skin's principal direction this frame; angles of the caught vertices about it
                fs = skin[f, np.flatnonzero(sel & fore)]
                c0 = fs.mean(axis=0)
                ax = np.linalg.svd(fs - c0, full_matrices=False)[2][0]
                r = cx[f, caught] - c0
                r -= np.outer(r @ ax, ax)
                e1 = np.linalg.svd(r, full_matrices=False)[2][0]
                e1 -= ax * (e1 @ ax)
                e1 /= np.linalg.norm(e1)
                e2 = np.cross(ax, e1)
                a = np.sort(np.degrees(np.arctan2(r @ e2, r @ e1)) % 360)
                gaps = np.diff(np.concatenate([a, [a[0] + 360]]))
                ang = float(360 - gaps.max())
            row[s] = {"vertices": int(caught.sum()), "volta_graus": round(ang)}
        rows.append(row)
    worst = {s: max(rows, key=lambda r: (r[s]["volta_graus"], r[s]["vertices"])) for s in sides}
    summary = {s: {"quadros_com_pano_preso": int(sum(r[s]["vertices"] > 0 for r in rows)),
                   "quadros_volta_maior_que_180": int(sum(r[s]["volta_graus"] > 180 for r in rows)),
                   "vertices_max": int(max(r[s]["vertices"] for r in rows)),
                   "pior_quadro": worst[s]["quadro"], "pior_volta_graus": worst[s][s]["volta_graus"]} for s in sides}
    print(json.dumps(summary))
    if out:
        Path(out).write_text(json.dumps({"resumo": summary, "quadros": rows}, indent=1), encoding="utf-8")
    return summary


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(2)
    main(*sys.argv[1:])
