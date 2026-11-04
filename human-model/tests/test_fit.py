import numpy as np
import pytest
from hmcore import fit


def test_rotation_between_is_a_rotation():
    R = fit.rotation_between([1, 0, 0], [0, 0, 1])
    assert R @ np.array([1, 0, 0]) == pytest.approx([0, 0, 1])
    assert np.linalg.det(R) == pytest.approx(1.0)
    R2 = fit.rotation_between([0, 0, 1], [0, 0, -1])
    assert R2 @ np.array([0, 0, 1]) == pytest.approx([0, 0, -1])


def test_segment_fit_lands_joints_on_targets():
    a, b = np.array([0, 0, 1.0]), np.array([0, 0, 0.0])
    v = np.array([a, b, [0.1, 0, 0.5]])
    out = fit.segment_fit(v, a, b, [1, 1, 1], [1, 1, 3])
    assert out[0] == pytest.approx([1, 1, 1]) and out[1] == pytest.approx([1, 1, 3])
    radial = np.linalg.norm(out[2] - np.array([1, 1, 2]))
    assert radial == pytest.approx(0.1 * 2 ** 0.7)


def test_frame_rotation_keeps_the_second_axis_near():
    R = fit.frame_rotation([1, 0, 0], [0, 1, 0], [0, 1, 0], [0, 0, 1])
    assert R @ np.array([1, 0, 0]) == pytest.approx([0, 1, 0])
    assert R @ np.array([0, 1, 0]) == pytest.approx([0, 0, 1])


def _cube():
    v = np.array([[x, y, z] for x in (0, 1) for y in (0, 1) for z in (0, 1)], float)
    q = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    starts = np.arange(0, 24, 4)
    return v, fit.triangles(starts, [4] * 6, np.array(q).ravel())


def test_winding_number_inside_and_outside():
    v, t = _cube()
    w = fit.winding_number([[0.5, 0.5, 0.5], [2, 2, 2]], v, t)
    assert w[0] == pytest.approx(1.0, abs=1e-6) and w[1] == pytest.approx(0.0, abs=1e-6)


def test_profiles_ignore_arms():
    skin = np.array([[0, -0.1, 1.0], [0, 0.1, 1.0], [0.01, 0, 1.0], [0.02, 0, 1.0], [0.5, 0, 1.0]])
    assert fit.body_profile(skin, 1.0) == (-0.1, 0.1)
    assert fit.body_half_width(skin, 1.0) == 0.02
