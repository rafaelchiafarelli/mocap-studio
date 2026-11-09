"""The GPU solver's tests. Warp is only in the GPU image, so these run with hm.sh --gpu pytest and are skipped otherwise. They use Warp's CPU device."""
import numpy as np
import pytest
from hmcore import layers

wp = pytest.importorskip("warp")
from hmcore import xpbd  # noqa: E402


def _cube(cells, side=0.1, z=0.02):
    nodes, tets, tet_voxel, vox = layers.tetrahedra(np.ones((cells,) * 3, bool), np.array([-side / 2, -side / 2, z]), side / cells)
    return nodes, tets, tet_voxel, vox


def _shares_no_node(tets, colours):
    for c in np.unique(colours):
        nodes = tets[colours == c].ravel()
        if len(np.unique(nodes)) != len(nodes):
            return False
    return True


def test_voxel_colours_share_no_node():
    _, tets, tet_voxel, vox = _cube(5)
    c = xpbd.voxel_colours(vox, tet_voxel)
    assert len(np.unique(c)) == 48
    assert _shares_no_node(tets, c)


def test_greedy_colours_share_no_node():
    _, tets, _, _ = _cube(4)
    c = xpbd.colours(tets, tets.max() + 1)
    assert _shares_no_node(tets, c)


def test_lame():
    mu, lam = xpbd.lame(20000.0, 0.25)
    assert mu == pytest.approx(8000.0) and lam == pytest.approx(8000.0)


def test_a_dropped_cube_lands_and_keeps_its_volume():
    wp.init()
    nodes, tets, tet_voxel, vox = _cube(4)
    s = xpbd.Solver(nodes, tets, xpbd.voxel_colours(vox, tet_voxel), 1000.0, 20000.0, 0.45, damping=2.0, floor=0.0, device="cpu")
    for _ in range(24):
        s.step(1 / 24, 20)
    x = s.positions()
    assert np.isfinite(x).all()
    assert x[:, 2].min() == pytest.approx(0.0, abs=1e-6)
    assert s.volume() / s.rest_total > 0.95
    assert x[:, 2].max() > 0.09


def test_pinned_nodes_follow_set_pinned():
    wp.init()
    nodes, tets, tet_voxel, vox = _cube(3)
    top = np.flatnonzero(nodes[:, 2] > nodes[:, 2].max() - 1e-9)
    s = xpbd.Solver(nodes, tets, xpbd.voxel_colours(vox, tet_voxel), 1000.0, 20000.0, 0.45, pinned=top, device="cpu")
    s.set_pinned(top, nodes[top] + [0.01, 0.0, 0.0])
    s.step(1 / 24, 10)
    assert s.positions()[top] == pytest.approx(nodes[top] + [0.01, 0.0, 0.0], abs=1e-6)


def _carried(all_rest):
    """A block whose bottom layer is carried at 1 m/s along X for two seconds: how far its top trails where the carrying puts it, in mm."""
    wp.init()
    nodes, tets, tet_voxel, vox = _cube(3)
    bottom = np.flatnonzero(nodes[:, 2] < nodes[:, 2].min() + 1e-9)
    s = xpbd.Solver(nodes, tets, xpbd.voxel_colours(vox, tet_voxel), 1000.0, 20000.0, 0.45, damping=5.0, device="cpu")
    s.drive(bottom, nodes[bottom], all_rest=nodes if all_rest else None)
    s.gravity = wp.vec3(0.0, 0.0, 0.0)
    T = lambda f: np.array([[1, 0, 0, f / 24], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], float)
    for f in range(1, 49):
        s.set_drive(T(f - 1), T(f))
        s.step(1 / 24, 40)
    top = nodes[:, 2] > nodes[:, 2].max() - 1e-9
    return float(-(s.positions()[top, 0] - (nodes[top, 0] + 2.0)).mean() * 1000)


def test_driven_nodes_follow_the_transform():
    wp.init()
    nodes, tets, tet_voxel, vox = _cube(3)
    bottom = np.flatnonzero(nodes[:, 2] < nodes[:, 2].min() + 1e-9)
    s = xpbd.Solver(nodes, tets, xpbd.voxel_colours(vox, tet_voxel), 1000.0, 20000.0, 0.45, device="cpu")
    s.drive(bottom, nodes[bottom], all_rest=nodes)
    M = np.eye(4)
    M[:3, 3] = [0.0, 0.05, 0.0]
    s.set_drive(np.eye(4), M)
    s.step(1 / 24, 10)
    assert s.positions()[bottom] == pytest.approx(nodes[bottom] + [0.0, 0.05, 0.0], abs=1e-6)


def test_relative_damping_doesnt_hold_a_carried_body_back():
    relative, absolute = _carried(True), _carried(False)
    assert abs(relative) < 1.0
    assert absolute > 2.0


def test_mesh_queries_on_a_closed_tube():
    from hmcore import meshgpu
    from tests.test_layers import _tube
    wp.init()
    v, f = _tube(0.05, 0.0, 0.2, n=64, closed=True)
    m = meshgpu.Mesh(v, f, device="cpu")
    p = np.array([[0, 0, 0.1], [0.06, 0, 0.1], [0, 0, 0.3]])
    assert m.inside(p).tolist() == [True, False, False]
    assert m.closest(p)[0] == pytest.approx([0.05, 0.01, 0.1], abs=1e-3)


def test_skinfit_covers_a_rod_that_pokes_through_a_tube():
    """A rod of radius 2 cm inside a tube of skin 2.5 cm, pushed 1 cm off centre, so it comes 5 mm out. Asked for 3 mm, with 15 mm the most."""
    from hmcore import meshgpu, skinfit
    from tests.test_layers import _tube
    wp.init()
    skin, tris = _tube(0.025, 0.0, 0.3, n=48, rings=31)
    rod, rod_tris = _tube(0.02, 0.05, 0.25, n=24, rings=11, closed=True)
    rod[:, 0] += 0.01
    mesh = lambda v, f: meshgpu.Mesh(v, f, device="cpu")
    rig = {"spine.006": {"head": [9, 9, 9]}, "spine.005": {"head": [9, 9, 8], "tail": [9, 9, 9]}}
    for side in ("L", "R"):
        rig[f"hand.{side}"] = rig[f"foot.{side}"] = {"head": [9, 9, 9]}
        rig[f"forearm.{side}"] = rig[f"shin.{side}"] = {"head": [9, 9, 8], "tail": [9, 9, 9]}
    after, push, rec = skinfit.fit(skin, tris, tris, {"rod": (rod, rod_tris)}, rig, {"default": 3}, 0.015, mesh)
    assert rec["misplaced"] == []
    assert rec["depth_after"].min() > 0.0025
    assert push.max() < 0.015


def test_two_bones_carry_their_own_tissue():
    """Two blocks side by side, each held at its bottom by its own bone; one bone moves up 2 cm, the other stays."""
    wp.init()
    nodes, tets, tet_voxel, vox = _cube(4)
    left = nodes[:, 0] < 0
    bottom = np.flatnonzero(nodes[:, 2] < nodes[:, 2].min() + 1e-9)
    bone_of = np.where(left, 0, 1).astype(np.int32)
    s = xpbd.Solver(nodes, tets, xpbd.voxel_colours(vox, tet_voxel), 1000.0, 20000.0, 0.45, damping=5.0, device="cpu")
    s.gravity = wp.vec3(0.0, 0.0, 0.0)
    s.drive(bottom, nodes[bottom], all_rest=nodes, bone=bone_of[bottom], all_bone=bone_of, n_bones=2)
    up = np.eye(4)
    up[2, 3] = 0.02
    s.set_drive(np.stack([np.eye(4), np.eye(4)]), np.stack([up, np.eye(4)]))
    s.step(1 / 24, 10)
    x = s.positions()
    moved = x[bottom, 2] - nodes[bottom, 2]
    assert moved[left[bottom]] == pytest.approx(0.02, abs=1e-6)
    assert moved[~left[bottom]] == pytest.approx(0.0, abs=1e-6)


def test_walk_region_keeps_whole_voxels_and_one_piece():
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
    import body_walk
    from hmcore import layers
    grid = np.zeros((6, 2, 6), bool)
    grid[0:2, :, :] = True  # a column
    grid[4:6, :, 0:2] = True  # a small piece apart, low down
    nodes, tets, _, _ = layers.tetrahedra(grid, np.zeros(3), 0.01)
    keep, used, t = body_walk.region(nodes, tets, 0.035)
    assert len(keep) % 6 == 0
    z = nodes[used][t].mean(axis=1)[:, 2]
    assert z.max() < 0.04
    assert nodes[used][:, 0].max() <= 0.02 + 1e-9  # the piece apart is dropped


def test_cut_zones_face_away_and_catch_what_lies_past_them():
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
    import body_walk
    a = np.linspace(0, 2 * np.pi, 12, endpoint=False)
    ring = np.column_stack([0.05 * np.cos(a), 0.05 * np.sin(a), np.zeros(12)])
    skin = np.vstack([ring, ring + [0, 0, 1.0]])
    zones = body_walk.cut_zones(skin, [np.arange(12), np.arange(12, 24)], np.array([0, 0, 0.5]))
    assert zones[0][1] @ [0, 0, 1] < -0.99 and zones[1][1] @ [0, 0, 1] > 0.99
    p = np.array([[0, 0, -0.01], [0, 0, 0.5], [0, 0, 1.02], [0.5, 0, 1.02]])
    assert body_walk.near_cuts(p, zones, 0.0).tolist() == [True, False, True, False]


def test_bone_summary_counts_frames_and_keeps_the_deepest():
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
    import body_walk
    a = {"bone_points_out": 3, "bone_out_depth_mm": 2.5, "bones_out": "patella_L;tibia_L", "current_bone_points_out": 0, "current_bone_out_depth_mm": 0.0, "current_bones_out": ""}
    b = {"bone_points_out": 0, "bone_out_depth_mm": 0.0, "bones_out": "", "current_bone_points_out": 7, "current_bone_out_depth_mm": 4.0, "current_bones_out": "rib_1_R"}
    got = body_walk.bone_summary([a, b], [a, b])
    assert (got["measured"], got["ours_frames_with_any"], got["ours_max_depth_mm"], got["ours_bones"]) == (True, 1, 2.5, ["patella_L", "tibia_L"])
    assert (got["current_frames_with_any"], got["current_bones"]) == (1, ["rib_1_R"])


def test_volumes_are_measured_every_so_many_frames_and_on_the_last():
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
    import body_walk
    measured = [f for f in range(25) if body_walk.measures_volume(f, 24, 10)]
    assert measured == [0, 10, 20, 24]
    assert all(body_walk.measures_volume(f, 24, 1) for f in range(25))


def test_damping_per_node_matches_the_same_damping_for_all():
    nodes, tets, tet_voxel, vox = _cube(4)
    c = xpbd.voxel_colours(vox, tet_voxel)
    a = xpbd.Solver(nodes, tets, c, 1000.0, 20000.0, 0.45, damping=5.0, floor=0.0, device="cpu")
    b = xpbd.Solver(nodes, tets, c, 1000.0, 20000.0, 0.45, damping=np.full(len(nodes), 5.0), floor=0.0, device="cpu")
    for s in (a, b):
        for _ in range(4):
            s.step(1 / 24, 10)
    assert np.allclose(a.positions(), b.positions())
