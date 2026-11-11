"""The moment each foot touches the ground, and the pulse it sends up the body (initiative animation-body). The impact lasts less than a frame, so it's built from the event, not from the motion."""
from __future__ import annotations

import numpy as np

CONTACT_M = 0.012  # above the foot's lowest height, within this the heel counts as on the ground
LIFTED_M = 0.03  # it must have risen this far since the last touch


def touchdowns(heel_z, fps):
    """Frames, with a fraction, where the heel comes down to the ground. heel_z: one foot's heel height per frame."""
    ground = float(np.min(heel_z))
    contact, lifted, events = ground + CONTACT_M, ground + LIFTED_M, []
    up = heel_z[0] > lifted
    for f in range(1, len(heel_z)):
        if up and heel_z[f] <= contact:
            a, b = heel_z[f - 1], heel_z[f]
            events.append((f - 1 + (a - contact) / max(a - b, 1e-9)) / fps)
            up = False
        elif not up and heel_z[f] > lifted:
            up = True
    return events


def pulses(events, normals, distance, fps, height=None, size=90.0, width=0.012, speed=40.0, reach=0.9):
    """A function of (frame, substep, steps) giving, per vertex, the acceleration the impacts add along the normal.
    events: per foot, its touchdown times; distance: per foot, each vertex's distance from it along the skin; normals: frames x vertices x 3. The pulse goes up, as a heel strike does."""
    feet = [(np.asarray(t, float), np.where(np.isfinite(d), d, 1e9)) for t, d in zip(events, distance)]
    attenuations = [np.exp(-d / reach) for _, d in feet]
    delays = [d / speed for _, d in feet]

    def field(frame, step, steps):
        t = (frame + (step + 0.5) / steps) / fps
        total = np.zeros(normals.shape[1])
        for (times, _), attenuation, delay in zip(feet, attenuations, delays):
            for t0 in times[(times > t - 0.2) & (times < t + 0.05)]:
                total += attenuation * np.exp(-(((t - t0 - delay) / width) ** 2))
        return size * total * normals[min(frame, len(normals) - 1)][:, 2]

    return field
