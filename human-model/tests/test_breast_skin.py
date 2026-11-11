import numpy as np
import pytest
from hmcore import breast_skin as bs

TABLE = {"redondos": {"base_cm": 8.0, "upper": 1.0, "lower": 1.0, "power": 2.0}, "gota": {"base_cm": 8.0, "upper": 1.25, "lower": 0.85, "power": 2.0},
         "adjustments": {"projection_per_cm": 0.35, "espacados_m": 0.03, "pendentes_m": 0.04}}


def plate(n=61, half=0.2):
    a = np.linspace(-half, half, n)
    v = np.array([[x, 0.0, z] for z in a for x in a])
    f = []
    for j in range(n - 1):
        for i in range(n - 1):
            p, q = j * n + i, j * n + i + 1
            f += [(p, q, q + n), (p, q + n, p + n)]
    return v, np.array(f)


def outline(project=0.06, **w):
    return bs.params(np.zeros(3), 1, project * 100 / TABLE["adjustments"]["projection_per_cm"], 16.0, {"base_cm": 8.0, **w}, TABLE)


def test_the_skin_rises_to_the_outline_and_stays_put_outside():
    v, f = plate()
    out = bs.inflate(v, f, [outline()])
    assert out[:, 1].min() == pytest.approx(-0.06, abs=0.003)
    far = np.linalg.norm(v[:, [0, 2]], axis=1) > 0.11
    assert out[far, 1] == pytest.approx(v[far, 1], abs=1e-6)


def test_the_nipple_keeps_its_height_over_the_skin():
    v, f = plate()
    tip = np.argmin(np.linalg.norm(v[:, [0, 2]], axis=1))
    v[tip, 1] = -0.008  # a small detail in front of the form
    out = bs.inflate(v, f, [outline()])
    neighbours = np.linalg.norm(v[:, [0, 2]] - v[tip, [0, 2]], axis=1)
    ring = (neighbours > 0.005) & (neighbours < 0.012)
    assert out[tip, 1] < out[ring, 1].min() - 0.005


def test_it_doesnt_fold():
    v, f = plate()
    out = bs.inflate(v, f, [outline(0.09)])
    n0 = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    n1 = np.cross(out[f[:, 1]] - out[f[:, 0]], out[f[:, 2]] - out[f[:, 0]])
    assert (np.einsum("ij,ij->i", n0, n1) > 0).all()


def test_gota_reaches_higher_than_it_hangs():
    p = bs.params(np.zeros(3), 1, 16.0, 16.0, {"shape": "gota"}, TABLE)
    pts = np.array([[0, 0, 0.09], [0, 0, -0.09]], float)
    r = bs.rho(pts, p)
    assert r[0] < r[1]


def test_faders_override_the_shape():
    p = bs.params(np.zeros(3), 1, 16.0, 16.0, {"shape": "gota", "projection_cm": 9.0, "base_cm": 10.0, "upper": 2.0, "lower": 1.5, "power": 3.0}, TABLE)
    assert (p["project"], p["radius"], p["upper"], p["lower"], p["power"]) == pytest.approx((0.09, 0.10, 2.0, 1.5, 3.0))


def test_the_adjustments_move_the_outline():
    p = bs.params(np.zeros(3), -1, 16.0, 16.0, {"espacados": 1.0, "pendentes": 1.0}, TABLE)
    assert p["cx"] == pytest.approx(-0.03) and p["cz"] == pytest.approx(-0.04)


def test_asymmetry_is_per_side():
    wish = {"assimetricos": {"L": 1.0, "R": 0.7}}
    assert bs.params(np.zeros(3), -1, 16.0, 16.0, wish, TABLE)["project"] < bs.params(np.zeros(3), 1, 16.0, 16.0, wish, TABLE)["project"]


def test_the_footprint_is_the_base():
    assert bs.footprint(np.array([[0.0, 0, 0], [0.5, 0, 0]]), outline()).tolist() == [True, False]


def test_the_back_of_the_body_doesnt_move():
    v, f = plate()
    back = v.copy()
    back[:, 1] = 0.20  # the same x and z, behind the chest
    both = np.vstack([v, back])
    tris = np.vstack([f, f + len(v)])
    out = bs.inflate(both, tris, [outline()])
    assert out[len(v):, 1] == pytest.approx(back[:, 1])
    assert not bs.footprint(np.array([[0.0, 0.2, 0.0]]), outline())[0]


def test_ripples_of_the_first_shape_dont_reach_the_slopes():
    v, f = plate()
    v[:, 1] = 0.01 * np.sin(v[:, 0] * 60)
    p = outline()
    out = bs.inflate(v, f, [p])
    r = bs.rho(v, p)
    slope = (r > 0.75) & (r < 0.85)
    want = bs.wall_y(v, p) - p["project"] * (1 - r[slope] ** 2) ** (bs.PROFILE * p["power"])
    assert np.abs(out[slope, 1] - want).max() < 0.006


def test_the_edge_has_no_wall():
    v, f = plate(121)
    p = outline()
    out = bs.inflate(v, f, [p])
    r = bs.rho(v, p)
    assert np.abs(out[(r > 0.92) & (r < 1.0), 1] - bs.wall_y(v, p)).max() < 0.012


def test_the_move_fades_towards_the_back():
    v, f = plate(41)
    p = {**outline(), "front_y": bs.FRONT_FADE / 2}  # the plate lies halfway through the fade
    out = bs.inflate(v, f, [p])
    assert out[:, 1].min() == pytest.approx(-p["project"] / 2, abs=0.004)


def test_onto_sphere_puts_the_disc_on_the_sphere_and_keeps_the_rim():
    a = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    rings = [np.column_stack([r * np.cos(a), np.zeros(48), r * np.sin(a)]) for r in np.linspace(0.005, 0.2, 40)]
    flat = np.concatenate(rings)
    centre, radius = np.array([0.0, -0.02, 0.0]), 0.06
    out = bs.onto_sphere(flat, centre, radius, 0.0)
    rim = radius * np.sqrt(1 - (0.02 / radius) ** 2)
    inside = np.hypot(flat[:, 0], flat[:, 2]) < rim
    assert np.linalg.norm(out[inside] - centre, axis=1) == pytest.approx(radius, abs=1e-9)
    assert out[inside, 1].min() == pytest.approx(centre[1] - radius, abs=1e-3)  # the pole, towards the front
    assert np.array_equal(out[~inside], flat[~inside])
    near_rim = inside & (np.hypot(flat[:, 0], flat[:, 2]) > rim - 0.006)
    assert np.abs(out[near_rim, 1]).max() < 0.012  # arrives at the chest's plane


def test_onto_sphere_brings_the_pole_skin_to_the_front_and_keeps_the_rim():
    a = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    flat = np.concatenate([np.column_stack([r * np.cos(a), np.zeros(48), r * np.sin(a)]) for r in np.linspace(0.005, 0.2, 40)] + [np.array([[0.015, 0.0, 0.0]])])
    centre, radius = np.array([0.0, -0.02, 0.0]), 0.06
    out = bs.onto_sphere(flat, centre, radius, 0.0, pole=(0.015, 0.0))
    assert out[-1, 1] < centre[1] - radius * 0.99  # the nipple's point is at the front
    rim = radius * np.sqrt(1 - (0.02 / radius) ** 2)
    assert np.array_equal(out[np.hypot(flat[:, 0], flat[:, 2]) >= rim], flat[np.hypot(flat[:, 0], flat[:, 2]) >= rim])
