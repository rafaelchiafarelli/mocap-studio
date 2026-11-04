"""Tongue from sounds: OpenSeeFace doesn't see the tongue, so it follows the known words' phonemes.
Group names are the mouth poses' groups (experiments/face-mouth/poses.json). Control values are declared from where each sound is articulated."""
import numpy as np

CONTROLS = ("tongue_tip_raise", "tongue_body_raise", "tongue_back_raise", "tongue_protrude")
POSES = {
    "rest": (0, 0, 0, 0),
    "M": (0, 0, 0, 0),
    "F": (0, 0, 0, 0),
    "S": (0.35, 0.4, 0, 0.1),
    "SH": (0.2, 0.7, 0, 0),
    "T": (1.0, 0.2, 0, 0.1),
    "L": (1.0, -0.1, 0, 0.1),
    "K": (-0.2, 0.1, 1.0, -0.2),
    "A": (-0.3, -0.5, 0, 0),
    "E": (0, 0.5, 0, 0.1),
    "I": (0.1, 0.9, 0, 0.2),
    "O": (-0.2, -0.2, 0.4, -0.2),
    "U": (-0.2, 0, 0.8, -0.3),
}


def track(events, frames, fps, attack=0.05, release=0.09):
    """Control curves from (time s, group, ...) events: each sound eases in, holds until the next and hands over."""
    curves = np.zeros((frames, len(CONTROLS)))
    times = np.arange(frames) / fps
    events = sorted(events, key=lambda e: e[0])
    if not events:
        return curves
    target = np.zeros((frames, len(CONTROLS)))
    for k, e in enumerate(events):
        start = e[0]
        end = events[k + 1][0] if k + 1 < len(events) else start + release
        pose = np.array(POSES.get(e[1], POSES["rest"]), float)
        mask = (times >= start) & (times < min(end, start + 0.35))
        target[mask] = pose
    value = np.zeros(len(CONTROLS))
    for t in range(frames):
        goal = target[t]
        rate = (1 / fps) / attack if np.linalg.norm(goal) >= np.linalg.norm(value) else (1 / fps) / release
        value = value + (goal - value) * min(rate, 1.0)
        curves[t] = value
    return curves
