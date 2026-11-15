"""Synthetic check of the contact between parts (tissue_solver.ContactSolver), GPU image:

    human-model/hm.sh --gpu python human-model/investigations/pose-capture/test_tissue_contact.py

Two soft blocks (4 x 4 x 4 cm, 5 mm voxels, fat-like 4 kPa), each a part, side by side and touching. A's outer face is driven
towards B, whose outer face is held, so the skeleton alone carries A's surface that far into B. Checks:
1. without contact, driven 8 mm, the blocks pass through each other (overlap left near 8 mm);
2. driven 4 mm, within a 5 mm yield: contact keeps them apart (overlap left under 1 mm);
3. driven 8 mm with a 5 mm yield: about 3 mm (8 - 5) is left inside, which the report counts as skeleton past the yield.
Limit found (2026-11-14): driven 20 mm (80 mm of nearly incompressible tissue squeezed to 60), contact resolved only part of it:
the volume constraint, solved after the push, wins. In the body the yield is 5 mm, so that regime is not asked of it.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE))
import warp as wp  # noqa: E402
from hmcore import layers, xpbd  # noqa: E402
from tissue_solver import ContactSolver  # noqa: E402

H = 0.005
FRAMES = 30


def block(x0):
    mask = np.ones((8, 8, 8), bool)
    nodes, tets, tet_voxel, vox = layers.tetrahedra(mask, np.array([x0, -0.02, 0.0]), H)
    return nodes, tets, tet_voxel, vox


def run(contact, yield_m, push):
    na, ta, va, xa = block(-0.04)
    nb, tb, vb, xb = block(0.0)
    nodes = np.concatenate([na, nb])
    tets = np.concatenate([ta, tb + len(na)])
    colours = np.concatenate([xpbd.voxel_colours(xa, va), xpbd.voxel_colours(xb, vb)])
    part = np.r_[np.zeros(len(na), np.int8), np.ones(len(nb), np.int8)]
    n = len(nodes)
    # surfaces: each block's boundary, outward
    fa, fb = layers.boundary_faces(ta), layers.boundary_faces(tb) + len(na)
    coll_tris = np.concatenate([fa, fb])
    coll_part = np.r_[np.zeros(len(fa), np.int8), np.ones(len(fb), np.int8)]
    coll_nodes = np.unique(coll_tris)
    drive_a = np.flatnonzero(np.isclose(nodes[:, 0], -0.04))
    drive_b = np.flatnonzero(np.isclose(nodes[:, 0], 0.04))
    driven = np.r_[drive_a, drive_b]
    bone = np.r_[np.zeros(len(drive_a), int), np.ones(len(drive_b), int)]
    node_bone = part.astype(int)
    tet_n = len(tets)
    kw = dict(device="cuda:0")
    args = (nodes, tets, colours, np.full(tet_n, 900.0), np.full(tet_n, 4000.0), np.full(tet_n, 0.45), np.full(n, 20.0),
            np.zeros(0, np.int32), np.zeros((0, 4), np.int32), np.zeros((0, 4)))
    hand = np.zeros((3, 3), np.float32) + 10.0
    s = ContactSolver(*args, coll_tris=coll_tris, coll_part=coll_part, coll_nodes=coll_nodes, node_part=part,
                      hand_tris=np.array([[0, 1, 2]]), hand_part=np.array([5, 5, 5], np.int8), n_hand=3, yield_m=yield_m,
                      every=1 if contact else 10 ** 9, **kw)
    s.gravity = wp.vec3(0.0, 0.0, 0.0)
    s.drive(driven, nodes[driven], all_rest=nodes, bone=bone, all_bone=node_bone, n_bones=2)
    s.set_hands(hand, hand)
    left0, _, _, _ = s.overlap_now()
    s.set_base(left0)
    prev = np.repeat(np.eye(4, dtype=np.float32)[None], 2, 0)
    for f in range(FRAMES + 20):
        cur = prev.copy()
        cur[0, 0, 3] = push * min(1.0, (f + 1) / FRAMES)
        s.set_drive(prev, cur)
        s.step(1 / 30, 80)
        prev = cur
    left, _, skel, _ = s.overlap_now()
    x = s.positions()
    width_a = x[part == 0, 0].max() - x[drive_a, 0].mean()
    width_b = x[drive_b, 0].mean() - x[part == 1, 0].min()
    return float(np.percentile(left, 99)), float(skel.max()), float(width_a), float(width_b)


def main():
    wp.init()
    ok = True
    left, skel, wa, wb = run(False, 0.005, 0.008)
    print(f"no contact, driven 8 mm: overlap left (p99) {left*1000:.1f} mm, skeleton {skel*1000:.1f} mm")
    ok &= left > 0.006
    left, skel, wa, wb = run(True, 0.005, 0.004)
    print(f"contact, driven 4 mm, yield 5 mm: overlap left (p99) {left*1000:.1f} mm, widths A {wa*1000:.1f} B {wb*1000:.1f} mm (rest 40)")
    ok &= left < 0.001
    left, skel, wa, wb = run(True, 0.005, 0.008)
    print(f"contact, driven 8 mm, yield 5 mm: overlap left (p99) {left*1000:.1f} mm (expected ~3), skeleton {skel*1000:.1f} mm")
    ok &= abs(left - 0.003) < 0.0015
    print("OK" if ok else "FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
