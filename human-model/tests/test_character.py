import json, os, sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from hmcore import body, character as ch

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "characters")


def full():
    return {"sex": "female", "name": "x", "silhouette": "ampulheta", "biotype": {"type": "mesomorph", "others": {"ectomorph": 0.2, "endomorph": 0.1}}, "height_cm": 168, "body_fat_percent": 26,
            "distances": {"busto": 90, "cintura": 66, "manga": 58}, "bone_parameters": {"pelvis_width_cm": 26, "thigh_share_of_leg": 0.5, "humerus_share_of_arm": 0.56},
            "gluteus": {"shape": "coracao"}, "breast": {"shape": "gota", "espacados": 0.3, "assimetricos": {"L": 1.0, "R": 0.9}, "pendentes": 0.2},
            "underbust_cm": 70, "regions": {"breast_L": {"young_pa": 3000, "damping": 25}}}


def test_a_full_character_has_no_problems():
    assert ch.problems(full()) == []


@pytest.mark.parametrize("path", ["female_neutral.json", "male_neutral.json"])
def test_the_neutral_fixtures_load(path):
    assert ch.load(os.path.join(FIXTURES, path))["sex"] == path.split("_")[0]


def test_zone_names_stay_in_step_with_the_body():
    assert ch.ZONE_NAMES == body.ZONES


def broken(**change):
    return {**full(), **change}


@pytest.mark.parametrize("bad", [
    broken(sex="other"), broken(silhouette="estrela"), broken(biotype={"type": "x"}),
    broken(biotype={"type": "mesomorph", "others": {"mesomorph": 0.1}}),
    broken(biotype={"type": "mesomorph", "others": {"ectomorph": 0.4}}),
    broken(biotype={"type": "mesomorph", "others": {"ectomorph": 0.35, "endomorph": 0.35}}),
    broken(height_cm=300), broken(body_fat_percent=1), broken(distances={"cintura": -2}), broken(distances={"cotovelo": 30}),
    broken(bone_parameters={"thigh_share_of_leg": 1.2}), broken(bone_parameters={"fêmur": 3}), broken(gluteus={"shape": "x"}),
    broken(breast={"shape": "pera"}), broken(breast={"voltas": 1}), broken(breast={"espacados": "x"}), broken(regions={"nowhere": {"damping": 1}}),
    broken(regions={"breast_L": {"cor": 1}}), broken(extra=1)])
def test_every_rule_is_checked(bad):
    assert ch.problems(bad)


def test_the_two_others_may_reach_their_limits():
    ok = broken(biotype={"type": "mesomorph", "others": {"ectomorph": 0.35, "endomorph": 0.30}})
    assert ch.problems(ok) == []


def test_breast_and_cup_are_for_the_female_body():
    male = {"sex": "male", "silhouette": "trapezio", "breast": {"shape": "gota"}}
    assert any("female body only" in p for p in ch.problems(male))
    assert ch.problems({"sex": "male", "silhouette": "trapezio"}) == []


def test_load_raises_with_every_problem(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"sex": "female", "silhouette": "x", "height_cm": 300}))
    with pytest.raises(ValueError, match="silhouette.*height"):
        ch.load(str(p))


BASE = {"height": 160.0, "bust": 84.0, "underbust": 68.0, "waist": 65.0, "hip": 90.0, "neck": 31.0, "upper_arm": 25.0, "wrist": 12.0, "thigh": 53.0, "knee": 34.0, "calf": 34.0, "ankle": 18.0,
        "shoulder_width": 36.0, "shoulder": 13.0, "bust_span": 20.0, "armhole_depth": 14.0, "back_length": 31.0, "bust_height": 25.0, "hip_height": 20.0, "rise": 29.0, "inseam": 74.0, "knee_height": 45.0, "arm_length": 46.0}
BIOTYPES = {"current_body_fat_percent": {"female": 28.0, "male": 17.0}, "fat_changes_girths": {"waist": 0.6, "hip": 0.4},
            "ectomorph": {"bone_thickness": 0.9, "limb_length": 1.03, "shoulders": 0.96, "waist": 0.96, "hips": 0.96, "muscle": 0.75, "body_fat_delta": -6.0},
            "mesomorph": {"bone_thickness": 1.0, "limb_length": 1.0, "shoulders": 1.04, "waist": 0.96, "hips": 1.0, "muscle": 1.25, "body_fat_delta": 0.0},
            "endomorph": {"bone_thickness": 1.1, "limb_length": 1.0, "shoulders": 1.0, "waist": 1.1, "hips": 1.08, "muscle": 1.1, "body_fat_delta": 8.0}}
RATIOS = ch.silhouette_ratios()


def sheet(c):
    return ch.resolve(c, BASE, BIOTYPES, RATIOS)["fields"]


def test_neutral_keeps_the_current_values():
    s = sheet({"sex": "female"})
    assert s["waist"] == {"value": 65.0, "source": "current"} and s["body_fat_percent"]["value"] == 28.0 and s["muscle"]["value"] == 1.0


def test_the_biotype_changes_only_its_own_fields():
    s = sheet({"sex": "female", "biotype": {"type": "ectomorph"}})
    assert s["bone_thickness"] == {"value": 0.9, "source": "biotype"}
    assert s["shoulder_width"]["value"] == pytest.approx(36 * 0.96) and s["inseam"]["value"] == pytest.approx(74 * 1.03) and s["body_fat_percent"]["value"] == 22.0
    assert s["bust"]["source"] == "current"


def test_a_mix_is_the_weighted_mean():
    m = ch.biotype_mix({"type": "mesomorph", "others": {"ectomorph": 0.2, "endomorph": 0.1}}, BIOTYPES)
    assert m["muscle"] == pytest.approx(0.7 * 1.25 + 0.2 * 0.75 + 0.1 * 1.1)


def test_body_fat_moves_waist_and_hip():
    s = sheet({"sex": "female", "body_fat_percent": 38})
    assert s["waist"]["value"] == pytest.approx(65 * 1.06) and s["waist"]["source"] == "body_fat" and s["hip"]["value"] == pytest.approx(90 * 1.04)
    assert s["body_fat_percent"] == {"value": 38.0, "source": "typed"}


def test_height_widens_slower_than_it_lengthens():
    s = sheet({"sex": "female", "height_cm": 176})
    k = 176 / 160
    assert s["inseam"]["value"] == pytest.approx(74 * k) and s["inseam"]["source"] == "height"
    assert s["hip"]["value"] == pytest.approx(90 * k ** 0.7) and s["height"] == {"value": 176.0, "source": "typed"}


def test_the_silhouette_wins_over_the_biotype_on_proportions():
    s = sheet({"sex": "female", "silhouette": "retangulo", "biotype": {"type": "ectomorph"}, "body_fat_percent": 28})
    assert s["waist"]["source"] == "silhouette" and s["waist"]["value"] / s["hip"]["value"] >= 0.88


def test_a_silhouette_already_met_changes_nothing():
    s = sheet({"sex": "female", "silhouette": "oval", "distances": {"cintura": 95, "quadril": 100}})
    assert s["waist"]["source"] == "typed"


def test_what_is_typed_always_wins():
    s = sheet({"sex": "female", "silhouette": "ampulheta", "biotype": {"type": "endomorph"}, "distances": {"cintura": 70, "cava": 40}})
    assert s["waist"] == {"value": 70.0, "source": "typed"}
    assert "armhole" not in s  # cava isn't a measure the tape has


def test_shoulder_hip_ratio_reaches_the_range():
    s = sheet({"sex": "male", "silhouette": "trapezio"})
    p = RATIOS["ansur_proxies"]["male"]
    assert s["shoulder_width"]["value"] * p["bideltoid_over_biacromial"] / (s["hip"]["value"] * p["hip_breadth_over_hip_girth"]) >= 1.53


CUPS = {"letters": ["A", "B", "C", "D"], "first_difference_cm": 13.0, "step_cm": 2.0}


def cup_sheet(**c):
    return ch.resolve({"sex": "female", **c}, BASE, BIOTYPES, RATIOS, cups=CUPS)["fields"]


def test_the_cup_comes_from_the_bust_minus_the_underbust():
    s = cup_sheet(bust_cm=85)  # 85 - 68 = 17: A 13, B 15, C 17
    assert s["cup"]["value"] == "C"


def test_setting_the_cup_holds_the_thorax_and_raises_the_bust():
    s = cup_sheet(cup="D")
    assert s["underbust"]["value"] == 68.0 and s["bust"] == {"value": 87.0, "source": "typed"} and s["cup"] == {"value": "D", "source": "typed"}


def test_a_changed_underbust_with_the_cup_set_moves_the_bust():
    assert cup_sheet(cup="D", underbust_cm=72)["bust"]["value"] == 91.0


def test_setting_the_bust_recalculates_the_cup():
    assert cup_sheet(bust_cm=81)["cup"]["value"] == "A"
    assert cup_sheet(bust_cm=200)["cup"]["value"] == "D"  # past the last letter


def test_cup_and_bust_together_are_refused():
    assert any("cup or the bust" in p for p in ch.problems({"sex": "female", "cup": "B", "bust_cm": 90}))
    assert any("letter" in p for p in ch.problems({"sex": "female", "cup": "Z"}))


def test_the_sixteen_test_bodies_are_valid():
    d = os.path.join(os.path.dirname(__file__), "..", "data", "characters", "test")
    names = sorted(os.listdir(d))
    assert len(names) == 16 and sum(n.startswith("female") for n in names) == 8
    for n in names:
        assert ch.problems(json.load(open(os.path.join(d, n)))) == []
