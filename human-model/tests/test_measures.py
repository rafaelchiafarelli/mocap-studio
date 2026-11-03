import numpy as np
import pytest
from hmcore import ctbones, measures, tsdata


def test_ansur_mm_to_metres_and_hectograms_to_kg():
    row = {"stature": "1755", "weightkg": "815"}
    assert measures.ansur_value(row, "stature") == pytest.approx(1.755)
    assert measures.ansur_value(row, "weightkg") == pytest.approx(81.5)


def test_model_frame_is_a_rotation_not_a_mirror():
    p = np.eye(3) * 1000.0
    out = ctbones.ras_to_model(p)
    assert np.linalg.det(out) == pytest.approx(1.0)
    assert out[2].tolist() == [0, 0, 1]  # superior stays up


def test_bbox_and_volume_use_spacing():
    m = np.zeros((10, 10, 10), bool)
    m[2:4, 2:6, 2:8] = True
    a = np.diag([1.5, 1.5, 1.5, 1.0])
    assert measures.bbox_extent_m(m, a).tolist() == pytest.approx([0.003, 0.006, 0.009])
    assert measures.label_volume_l(m, a) == pytest.approx(48 * 3.375e-6)


def test_cut_bone_has_no_length():
    m = np.zeros((6, 6, 20), bool)
    m[2:4, 2:4, 0:10] = True
    assert measures.long_bone_length_m(m, np.diag([1.5, 1.5, 1.5, 1.0])) is None
    m = np.zeros((6, 6, 20), bool)
    m[2:4, 2:4, 3:13] = True
    assert measures.long_bone_length_m(m, np.diag([1.5, 1.5, 1.5, 1.0])) == pytest.approx(0.0135, abs=0.002)


def test_cut_by_the_side_of_the_field_of_view_counts_as_cut():
    m = np.zeros((10, 10, 30), bool)
    m[0:3, 4:6, 10:20] = True
    assert ctbones.touches_scan_edge(m)
    assert measures.long_bone_length_m(m, np.diag([1.5, 1.5, 1.5, 1.0])) is None


def test_fragments_are_left_out():
    rows = [{"humerus_len_left": 0.33}, {"humerus_len_left": 0.10}, {}]
    assert measures.complete_values(rows, "humerus_len_left") == [0.33]


def test_z_score_and_summary():
    s = measures.summary([1.0, 2.0, 3.0, float("nan"), None])
    assert s["n"] == 3 and s["mean"] == 2.0
    assert measures.z_score(3.0, s) == pytest.approx(1.0)


def test_meta_with_bom_and_blank_age():
    rows = tsdata.read_meta("﻿image_id;age;gender;pathology\ns1;50.00;m;none\ns2;;f;x\n")
    assert rows[0]["age"] == 50.0 and rows[1]["age"] is None


def test_mesh_has_outward_normals_and_right_size():
    m = np.zeros((30, 30, 30), bool)
    m[8:22, 8:22, 8:22] = True
    v, f = ctbones.mask_to_mesh(m, np.diag([1.5, 1.5, 1.5, 1.0]))
    assert ctbones.signed_volume(v, f) > 0
    assert ctbones.signed_volume(v, f) == pytest.approx((14 * 0.0015) ** 3, rel=0.2)


def test_coverage_reads_the_index():
    class I:
        def __init__(s, f, n): s.filename, s.compress_size = f, n
    cov = tsdata.coverage([I("s1/segmentations/skull.nii.gz", 5), I("s1/ct.nii.gz", 9), I("meta.csv", 1)])
    assert cov == {"s1": {"skull": 5}}
