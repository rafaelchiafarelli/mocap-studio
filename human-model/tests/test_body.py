import numpy as np
import pytest
from hmcore import body
from scipy.spatial import ConvexHull


def test_smoothing_spreads_a_step_but_keeps_flat_values():
    # A strip of triangles: vertices 0..9 along a line, values 0 then 1
    tris = np.array([[i, i + 1, i + 10] for i in range(9)] + [[i + 1, i + 11, i + 10] for i in range(9)])
    v = np.r_[np.zeros(5), np.ones(5), np.zeros(5), np.ones(5)]
    s = body.smooth_on_surface(v, tris, 20, 5)
    assert s[0] == pytest.approx(0, abs=0.05) and s[9] == pytest.approx(1, abs=0.05)
    assert 0.1 < s[4] < 0.9 and 0.1 < s[5] < 0.9


def test_inside_hull():
    hull = ConvexHull(np.array([[x, y, z] for x in (0, 1) for y in (0, 1) for z in (0, 1)], float))
    assert body.inside_hull(np.array([[0.5, 0.5, 0.5], [1.5, 0.5, 0.5]]), hull).tolist() == [True, False]


def test_segment_distance():
    d, c = body.segment_distance(np.array([[0.5, 1.0, 0.0], [2.0, 0.0, 0.0]]), np.zeros(3), np.array([1.0, 0, 0]))
    assert d == pytest.approx([1.0, 1.0]) and c[0] == pytest.approx([0.5, 0, 0])


def test_island_cleanup_moves_only_small_pieces():
    g = np.full((10, 10, 10), body.FAT, np.int8)
    g[1:6, 1:6, 1:6] = body.MUSCLE
    g[8, 8, 8] = body.MUSCLE
    assert body.island_cleanup(g, body.MUSCLE, body.FAT, 27) == 1
    assert g[8, 8, 8] == body.FAT and g[3, 3, 3] == body.MUSCLE


def test_outward_turns_an_inside_out_mesh_round():
    v = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], float)
    good = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
    assert (body.outward(v, good) == good).all()
    assert (body.outward(v, good[:, [0, 2, 1]]) == good).all()


def test_report_picture_keeps_the_slice_and_adds_a_frame():
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
    import body_report
    labels = np.full((20, 30), -1, np.int8)
    labels[5:10, 5:10] = body.FAT
    img = body_report.picture(labels, "Cintura: 65.2 cm", "corte")
    assert img.width >= 30 * body_report.SCALE and img.height == 20 * body_report.SCALE + 110
    assert img.getpixel((20 + 6 * body_report.SCALE, 70 + 6 * body_report.SCALE)) == body_report.COLORS[body.FAT]


def test_report_masses_come_from_inside_the_skin():
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
    import body_report
    built = {"litres": {"bone": 3.0, "muscle": 17.0, "fat": 11.0, "skin": 11.0, "cavity": 7.0}, "enclosed_litres": 45.0, "skin_area_m2": 1.2}
    litres = body_report.inside_skin(built)
    assert litres["skin"] == pytest.approx(1.2 * body_report.REAL_SKIN_MM)
    assert litres["fat"] == pytest.approx(45.0 - 3.0 - 17.0 - 7.0 - 1.8)
    assert sum(litres.values()) == pytest.approx(45.0)


def test_head_vertices_follow_the_weights_border():
    rig = {"spine.005": {"parent": "spine.004"}, "spine.006": {"parent": "spine.005"}, "jaw": {"parent": "spine.006"}}
    groups = {"spine.005": [[0, 1.0], [1, 0.6], [2, 0.2]], "spine.006": [[2, 0.3]], "jaw": [[1, 0.3], [2, 0.5]],
              "joint-head": [[0, 5.0]], "DEF-neck": [[3, 1.0]]}
    assert body.head_vertices(4, rig, groups).tolist() == [False, False, True, False]
