import numpy as np
import pytest
from hmcore import activation, retarget, tongue


def test_effort_nnls_recovers_a_nonnegative_mix():
    rng = np.random.default_rng(1)
    A = rng.normal(size=(30, 6))
    x = np.array([0.5, 0, 0.2, 0, 0, 0.7])
    got = activation.effort_nnls(A, A @ x)
    assert got == pytest.approx(x, abs=1e-3)


def test_effort_prefers_one_muscle_when_two_do_the_same_job():
    a = np.array([1.0, 0, 0])
    A = np.column_stack([a, a * 0.5])
    got = activation.effort_nnls(A, a * 0.5, effort=1e-3)
    assert got[1] == pytest.approx(0.0, abs=1e-6) and got[0] > 0.4


def test_bounds_hold():
    got = activation.effort_nnls(np.eye(2), np.array([5.0, -1.0]))
    assert got.tolist() == [1.0, 0.0]


def test_shape_fit_residual_is_zero_for_a_field_itself():
    F = np.random.default_rng(2).normal(size=(4, 20, 3))
    x, res = activation.shape_fit(F, F[2] * 0.6, effort=0.0)
    assert res < 1e-3 and x[2] == pytest.approx(0.6, abs=1e-3)


def test_align_removes_head_motion():
    rest = np.random.default_rng(3).normal(size=(68, 2)) * 50
    c, s = np.cos(0.2), np.sin(0.2)
    moved = 1.1 * rest @ np.array([[c, -s], [s, c]]).T + np.array([30.0, -12.0])
    assert activation.align(moved, rest) == pytest.approx(rest, abs=1e-6)


def test_tongue_track_rises_and_falls():
    c = tongue.track([(0.5, "T", ""), (0.8, "A", "")], 60, 30)
    tip = tongue.CONTROLS.index("tongue_tip_raise")
    assert c[14, tip] == 0.0 and c[22, tip] > 0.5 and c[40, tip] < 0.3


def test_every_mouth_group_has_a_tongue_pose():
    assert set(tongue.POSES) == {"rest", "M", "F", "S", "SH", "T", "L", "K", "A", "E", "I", "O", "U"}


def test_rigid_segment_has_no_variation():
    pts = np.zeros((10, 2, 3))
    pts[:, 1, 2] = 1.0
    assert retarget.bone_length_stats(pts, 0, 1) == (1.0, 0.0)


def test_facing_frame_is_a_rotation():
    R = retarget.facing_frame(np.array([0.1, 0, 0]), np.array([-0.1, 0, 0]), np.array([0.2, 0, 0.5]), np.array([-0.2, 0, 0.5]))
    assert np.linalg.det(R) == pytest.approx(1.0)
    assert (R @ np.array([1.0, 0, 0])).tolist() == pytest.approx([1, 0, 0])


def test_compression_is_exact_at_full_rank_and_zero_stays_zero():
    from hmcore import retire
    F = np.random.default_rng(4).normal(size=(5, 40, 3))
    basis, coeff = retire.compress(F, k=5)
    assert retire.error_mm(F, basis, coeff)[1] < 1e-6
    assert np.abs(retire.reconstruct(basis, coeff, np.zeros(5))).max() == 0.0


def test_compression_keeps_the_energy_asked():
    from hmcore import retire
    a = np.random.default_rng(5).normal(size=(1, 40, 3))
    F = np.concatenate([a, 2 * a, 3 * a])
    basis, coeff = retire.compress(F, keep_energy=0.999)
    assert basis.shape[0] == 1


def test_height_slider_inverts_the_sweep():
    from hmcore import morph
    assert morph.height_slider(1.73, "male") == pytest.approx(0.5)
    assert morph.height_slider(1.591, "female") == pytest.approx(0.5)
    assert 0.5 < morph.height_slider(1.80, "male") < 0.75


def test_height_outside_the_range_is_refused():
    from hmcore import morph
    with pytest.raises(ValueError):
        morph.height_slider(2.6, "male")
