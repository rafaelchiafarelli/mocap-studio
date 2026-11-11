import numpy as np

from hmcore import skin_waves as sw
from tests.test_folds import grid


def plate(gain=1.0, hz=4.0, damping=0.15, speed=1.5, n=41):
    v, t = grid(n=n, spacing=0.02)
    m = len(v)
    return v, t, sw.Values(np.full(m, gain), np.full(m, hz), np.full(m, damping), np.full(m, speed))


def kick(frames, n, vertex, size):
    drive = np.zeros((frames, n))
    drive[1, vertex] = size
    return drive


def test_a_pulse_travels_outwards():
    v, t, values = plate()
    middle = 20 * 41 + 20
    far = 20 * 41 + 36  # 32 cm along
    out, _ = sw.simulate(v, t, values, kick(24, len(v), middle, 400.0), 24)
    peak_middle = int(np.argmax(np.abs(out[:, middle])))
    peak_far = int(np.argmax(np.abs(out[:, far])))
    assert abs(out[:, far]).max() > 1e-6
    assert peak_far > peak_middle


def test_it_dies_out():
    v, t, values = plate()
    out, _ = sw.simulate(v, t, values, kick(72, len(v), 20 * 41 + 20, 400.0), 24)
    assert np.abs(out[-1]).max() < 0.05 * np.abs(out).max()


def test_the_offset_is_bounded():
    v, t, values = plate(hz=1.0, damping=0.05)
    drive = np.full((24, len(v)), 5000.0)
    out, _ = sw.simulate(v, t, values, drive, 24, limit=0.01)
    assert np.abs(out).max() <= 0.01 + 1e-9


def test_a_vertex_with_no_gain_stays_at_rest():
    v, t, values = plate(gain=0.0)
    out, _ = sw.simulate(v, t, values, kick(12, len(v), 0, 1000.0), 24)
    assert np.abs(out).max() == 0.0


def test_inertia_of_steady_motion_is_zero():
    p = np.zeros((5, 1, 3))
    p[:, 0, 2] = np.arange(5) * 0.1
    n = np.tile([0.0, 0.0, 1.0], (5, 1, 1))
    assert np.abs(sw.inertia(p, n, 24)).max() < 1e-9
