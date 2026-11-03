"""Jaw opening as rotation, then rotation with the condyle sliding forward and down (Posselt's envelope).
Targets: Travers et al. 2000, incisor 46.6 mm and condyle 11.9 mm straight-line at maximum opening."""
import math
import numpy as np

MAX_INCISOR_M = 0.0466
MAX_CONDYLE_M = 0.0119
HINGE_DROP_M = 0.020  # pure rotation ends between 10 and 25 mm depending on the source; 20 is our choice
EMINENCE_DEG = 35.0  # the slide runs forward and down along the articular eminence; declared, not from a measured source


def slide_direction():
    a = math.radians(EMINENCE_DEG)
    return np.array([0.0, -math.cos(a), -math.sin(a)])  # body faces -Y


def incisor_position(theta, slide, condyle, incisor):
    """Incisor after rotating theta about the condyle's left-right axis (opening: the front goes down), plus the slide."""
    c, s = math.cos(theta), math.sin(theta)
    r = np.asarray(incisor, float) - np.asarray(condyle, float)
    # Rx(theta) with y forward as -Y: rotating +X moves -Y towards -Z
    rotated = np.array([r[0], c * r[1] - s * r[2], s * r[1] + c * r[2]])
    return np.asarray(condyle, float) + rotated + slide_direction() * slide


def drop(theta, slide, condyle, incisor):
    return float(np.linalg.norm(incisor_position(theta, slide, condyle, incisor) - np.asarray(incisor, float)))


def solve_angles(condyle, incisor, scale=1.0):
    """(hinge angle, final angle) in radians so that the incisor travels HINGE_DROP then MAX_INCISOR, scaled to the individual."""
    def find(target, slide):
        lo, hi = 0.0, math.radians(70)
        for _ in range(60):
            mid = (lo + hi) / 2
            if drop(mid, slide, condyle, incisor) < target:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2
    return find(HINGE_DROP_M * scale, 0.0), find(MAX_INCISOR_M * scale, MAX_CONDYLE_M * scale)


def table(condyle, incisor, scale=1.0):
    """What a driver needs: opening o in 0..1, break point in o, angles and slide at the end of the range."""
    hinge, final = solve_angles(condyle, incisor, scale)
    return {"hinge_rad": hinge, "final_rad": final, "break_o": hinge / final, "slide_m": MAX_CONDYLE_M * scale, "slide_dir": slide_direction().tolist()}


def pose(o, t):
    """(rotation, slide) at opening o. Rotation is linear in o; the slide starts at the break."""
    o = min(max(o, 0.0), 1.0)
    theta = o * t["final_rad"]
    slide = max(0.0, (o - t["break_o"]) / (1 - t["break_o"])) * t["slide_m"]
    return theta, slide


def incisor_back_motion(t, condyle, incisor):
    """How far the incisor ends behind where it started: the proof of concept's fault (36 mm) with pure rotation."""
    end = incisor_position(*pose(1.0, t), condyle, incisor)
    return float(end[1] - incisor[1])
