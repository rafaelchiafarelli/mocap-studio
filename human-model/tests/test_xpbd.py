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
