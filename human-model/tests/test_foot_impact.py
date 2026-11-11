import numpy as np

from hmcore import foot_impact as fi


def walk_heel():
    t = np.arange(0.0, 3.0, 1 / 24)
    return t, 0.02 + 0.06 * np.maximum(np.sin(2 * np.pi * t / 1.1), 0.0)


def test_each_step_gives_one_touchdown():
    t, z = walk_heel()
    events = fi.touchdowns(z, 24)
    gaps = np.diff(events)
    assert len(events) >= 2
    assert np.all(np.abs(gaps - 1.1) < 0.06)


def test_touchdowns_on_flat_ground_are_none():
    assert fi.touchdowns(np.zeros(100), 24) == []


def test_a_pulse_arrives_later_and_smaller_further_up():
    n = 2
    normals = np.tile([0.0, 0.0, 1.0], (60, n, 1))
    distance = [np.array([0.05, 1.2])]
    field = fi.pulses([[1.0]], normals, distance, 24, speed=20.0)
    times = np.arange(0.9, 1.3, 0.002)
    series = np.array([field_at(field, x) for x in times])
    near, far = series[:, 0], series[:, 1]
    assert times[np.argmax(far)] > times[np.argmax(near)]
    assert far.max() < near.max()


def field_at(field, t, fps=24, steps=1000):
    frame = int(t * fps)
    step = int((t * fps - frame) * steps)
    return field(frame, step, steps)
