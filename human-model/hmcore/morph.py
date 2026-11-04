"""From a character's real sizes to MPFB's sliders. Measured by blender/macro_sweep.py, adults only: age at or above 0.5."""
import numpy as np

# stature in metres at height slider 0, 0.25, 0.5, 0.75, 1, age 0.5
HEIGHT_SLIDER = (0.0, 0.25, 0.5, 0.75, 1.0)
STATURE_M = {"male": (1.374, 1.556, 1.730, 2.074, 2.432), "female": (1.235, 1.416, 1.591, 1.934, 2.292)}
DENSITY_KG_PER_L = 1.01  # whole-body density; declared, general knowledge


def height_slider(stature_m, sex):
    """The slider value for a stature. Outside the slider's range it raises: a body can't be asked for silently."""
    s = STATURE_M[sex]
    if not s[0] <= stature_m <= s[-1]:
        raise ValueError(f"{stature_m} m is outside {s[0]} to {s[-1]} m for {sex}")
    return float(np.interp(stature_m, s, HEIGHT_SLIDER))


def mass_kg(volume_l):
    return volume_l * DENSITY_KG_PER_L
