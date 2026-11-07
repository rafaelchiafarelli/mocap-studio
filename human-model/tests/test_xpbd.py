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
