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
    built = {"litres": {"bone": 3.0, "muscle": 17.0, "fat": 11.0, "skin": 11.0, "cavity": 7.0, "fat_deep": 0.0}, "enclosed_litres": 45.0, "skin_area_m2": 1.2}
    litres = body_report.inside_skin(built)
    assert litres["skin"] == pytest.approx(1.2 * body_report.REAL_SKIN_MM)
    assert litres["fat"] == pytest.approx(45.0 - 3.0 - 17.0 - 7.0 - 1.8)
    assert sum(litres.values()) == pytest.approx(45.0)


def test_head_vertices_follow_the_weights_border():
    rig = {"spine.005": {"parent": "spine.004"}, "spine.006": {"parent": "spine.005"}, "jaw": {"parent": "spine.006"}}
    groups = {"spine.005": [[0, 1.0], [1, 0.6], [2, 0.2]], "spine.006": [[2, 0.3]], "jaw": [[1, 0.3], [2, 0.5]],
              "joint-head": [[0, 5.0]], "DEF-neck": [[3, 1.0]]}
    assert body.head_vertices(4, rig, groups).tolist() == [False, False, True, False]


def test_near_a_cut_follows_the_cut_skins_border():
    # a tube from z=0 to z=1, open at both ends: two border loops
    n = 24
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    rings = [np.column_stack([np.cos(a), np.sin(a), np.full(n, z)]) for z in np.linspace(0, 1, 5)]
    skin = np.vstack(rings)
    tris = []
    for k in range(4):
        for i in range(n):
            p, q, r_, s = k * n + i, k * n + (i + 1) % n, (k + 1) * n + i, (k + 1) * n + (i + 1) % n
            tris += [(p, q, r_), (q, s, r_)]
    planes = body.cut_planes(skin, np.array(tris))
    assert len(planes) == 2
    pts = np.array([[0, 0, 1.2], [0, 0, 0.5], [0, 0, -0.3]])
    assert body.near_a_cut(pts, {}, planes).tolist() == [True, False, True]


def test_every_tetrahedron_knows_its_voxels_zone():
    shape = (3, 2, 2)
    included = np.zeros(12, bool)
    included[[0, 5, 7]] = True  # three voxels in the flat grid
    zone_of_included = np.array([4, 7, 2], np.int16)
    vox = np.array([[0, 0, 0], [1, 0, 1], [1, 1, 1]])  # flat indices 0, 5 and 7, in grid order
    tet_voxel = np.array([0, 0, 1, 2, 2])
    assert body.tet_zones(zone_of_included, included, shape, vox, tet_voxel).tolist() == [4, 4, 7, 2, 2]


def test_the_buttocks_divide_by_height_and_side():
    points = np.array([[0.01, 0, 0.9], [0.1, 0, 0.9], [0.01, 0, 0.8], [0.1, 0, 0.8], [0.05, 0, 0.85]])
    zone = np.array(["buttocks"] * 4 + ["hips"], object)
    out = body.divide_zones(points, zone)
    assert out.tolist() == ["buttocks_upper_center", "buttocks_upper_side", "buttocks_lower_center", "buttocks_lower_side", "hips"]


def test_the_breast_divides_by_side():
    assert body.divide_zones(np.array([[0.1, 0, 1.3], [-0.1, 0, 1.3]]), np.array(["breast", "breast"], object)).tolist() == ["breast_L", "breast_R"]


@pytest.mark.parametrize("sex,parent_breast,parent_buttocks", [("female", 15, 30), ("male", None, None)])
def test_the_new_zones_keep_todays_fat(sex, parent_breast, parent_buttocks):
    import json, os
    fat = json.load(open(os.path.join(os.path.dirname(__file__), "..", "data", f"body_fat_{sex}.json")))["fat_mm"]
    assert set(fat) == set(body.ZONES)
    breast = {fat[z] for z in body.BREAST_ZONES}
    buttocks = {fat[z] for z in body.GLUTEUS_ZONES}
    assert len(breast) == 1 and len(buttocks) == 1
    if parent_breast:
        assert breast == {parent_breast} and buttocks == {parent_buttocks}


def _voxels(n=4):
    return dict(d_bone=np.full(n, 0.05), inside=np.ones(n, bool), in_bone=np.zeros(n, bool), in_chest=np.zeros(n, bool), in_trunk=np.zeros(n, bool),
                front_of_spine=np.ones(n, bool), chest_bone=np.zeros(n, bool), breast=np.zeros(n, bool), h=0.005,
                s={"abdominal_wall_mm": 0.015, "cavity_bone_gap_mm": 0.005, "pectoral_mm": 0.015}, skin_band_voxels=1)


def test_fat_splits_in_two_layers_only_where_it_is_thick_enough():
    d_skin = np.array([0.012, 0.022, 0.012, 0.009])  # m under the skin
    t_fat = np.array([0.030, 0.030, 0.008, 0.009])   # thick, thick, thin, thin
    t_superficial = t_fat * 0.5
    lab = body.label_voxels(d_skin, t_fat, t_superficial, **_voxels())
    assert lab.tolist() == [body.FAT, body.FAT_DEEP, body.MUSCLE, body.MUSCLE]


def test_two_layers_only_change_the_label_not_where_the_fat_ends():
    d_skin = np.array([0.005, 0.02, 0.025])
    t_fat = np.full(3, 0.03)
    a = body.label_voxels(d_skin, t_fat, t_fat, **_voxels(3))
    b = body.label_voxels(d_skin, t_fat, t_fat * 0.4, **_voxels(3))
    assert ((a == body.FAT) == ((b == body.FAT) | (b == body.FAT_DEEP))).all()


def test_the_gland_is_the_breasts_fat_deep_under_the_skin():
    v = _voxels(3)
    v["breast"], v["s"] = np.ones(3, bool), {**v["s"], "gland_skin_mm": 0.012}
    d_skin = np.array([0.008, 0.02, 0.02])
    t_fat = np.full(3, 0.03)
    lab = body.label_voxels(d_skin, t_fat, t_fat, gland=True, **v)
    assert lab.tolist() == [body.FAT, body.GLAND, body.GLAND]
    assert body.GLAND not in body.label_voxels(d_skin, t_fat, t_fat, gland=False, **v)  # no gland for the man


def test_the_bellys_viscera_are_apart_from_the_chest():
    v = _voxels(3)
    v["in_trunk"] = np.ones(3, bool)
    v["in_chest"] = np.array([True, False, False])
    d_skin = np.array([0.06, 0.06, 0.01])
    t_fat = np.full(3, 0.02)
    lab = body.label_voxels(d_skin, t_fat, t_fat, **v)
    assert lab.tolist() == [body.CAVITY, body.VISCERA, body.FAT]


def test_place_balloons_are_spheres_of_the_exact_volume():
    h = 0.005
    axes = [np.arange(-30, 30) * h + h / 2, np.arange(-12, 12) * h + h / 2, np.arange(-12, 12) * h + h / 2]
    xs, ys, zs = np.meshgrid(*axes, indexing="ij")
    centres = np.column_stack([xs.ravel(), ys.ravel(), zs.ravel()])
    labels = np.full(len(centres), body.FAT, np.int8)
    spheres = {"L": np.array([0.08, 0.0, 0.0]), "R": np.array([-0.08, 0.0, 0.0])}
    placed = body.place_balloons(labels, centres, np.ones(len(centres), bool), h, 100.0, spheres)
    for side, on in (("L", centres[:, 0] > 0), ("R", centres[:, 0] < 0)):
        inside = on & (labels == body.BALLOON)
        assert inside.sum() * h ** 3 * 1e6 == pytest.approx(100.0, abs=h ** 3 * 1e6)
        assert placed[side]["farthest_cm"] <= placed[side]["radius_cm"] + 100 * h
        d = np.linalg.norm(centres - spheres[side], axis=1)
        assert d[inside].max() <= d[on & (labels != body.BALLOON)].min() + 1e-9


def test_place_balloons_takes_only_fat_and_refuses_too_little():
    h = 0.01
    centres = np.array([[0.05, 0.0, 0.0], [0.05, 0.01, 0.0], [-0.05, 0.0, 0.0], [-0.05, 0.01, 0.0]])
    spheres = {"L": centres[1], "R": centres[3]}
    labels = np.array([body.SKIN, body.GLAND, body.MUSCLE, body.FAT_DEEP], np.int8)
    body.place_balloons(labels, centres, np.ones(4, bool), h, 1.0, spheres)
    assert labels.tolist() == [body.SKIN, body.BALLOON, body.MUSCLE, body.BALLOON]
    with pytest.raises(ValueError):
        body.place_balloons(np.array([body.FAT, body.MUSCLE, body.FAT, body.MUSCLE], np.int8), centres, np.ones(4, bool), h, 2.0, spheres)
