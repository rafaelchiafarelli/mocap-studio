import numpy as np

from hmcore import deltamush as dm


def tube(rings=24, around=16, length=0.3, radius=0.05):
    z = np.linspace(0.0, length, rings)
    a = np.linspace(0.0, 2 * np.pi, around, endpoint=False)
    verts = np.array([[radius * np.cos(t), radius * np.sin(t), h] for h in z for t in a])
    tris = []
    for i in range(rings - 1):
        for j in range(around):
            k = (j + 1) % around
            p, q, r, s = i * around + j, i * around + k, (i + 1) * around + k, (i + 1) * around + j
            tris += [[p, q, r], [p, r, s]]
    return verts, np.array(tris)


def bend(verts, angle, weights):
    """A linear-blend bend of the upper half of a tube about the x axis at its middle, which pinches the inside as a skinned elbow does."""
    middle = np.array([0.0, 0.0, 0.15])
    c, s = np.cos(angle), np.sin(angle)
    r = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    turned = (verts - middle) @ r.T + middle
    return verts * (1 - weights[:, None]) + turned * weights[:, None]


def weights_of(verts):
    return np.clip((verts[:, 2] - 0.12) / 0.06, 0.0, 1.0)


def areas(v, tris):
    return 0.5 * np.linalg.norm(np.cross(v[tris[:, 1]] - v[tris[:, 0]], v[tris[:, 2]] - v[tris[:, 0]]), axis=1)


def test_no_pose_needs_no_correction():
    v, t = tube()
    in_pose, in_rest = dm.correction(v, v.copy(), t)
    assert np.abs(in_pose).max() < 1e-9
    assert np.abs(in_rest).max() < 1e-9


def test_a_rigid_turn_needs_almost_no_correction():
    v, t = tube()
    a = 1.0
    c, s = np.cos(a), np.sin(a)
    posed = v @ np.array([[1, 0, 0], [0, c, -s], [0, s, c]]).T
    in_pose, _ = dm.correction(v, posed, t)
    assert np.abs(in_pose).max() < 1e-6


def test_a_bend_is_corrected_near_the_bend_and_not_far_from_it():
    v, t = tube()
    posed = bend(v, np.radians(60), weights_of(v))
    in_pose, _ = dm.correction(v, posed, t)
    size = np.linalg.norm(in_pose, axis=1)
    near, far = np.abs(v[:, 2] - 0.15) < 0.04, v[:, 2] < 0.04
    assert size[near].max() > 5 * size[far].max()


def test_falloff_is_one_near_and_zero_far():
    p = np.array([[0.0, 0, 0], [0.15, 0, 0], [0.5, 0, 0]])
    f = dm.falloff(p, [np.zeros(3)], 0.1)
    assert f[0] == 1.0 and 0.0 < f[1] < 1.0 and f[2] == 0.0
