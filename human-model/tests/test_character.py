import json, os, sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from hmcore import body, character as ch

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "characters")


def full():
    return {"sex": "female", "name": "x", "silhouette": "ampulheta", "biotype": {"type": "mesomorph", "others": {"ectomorph": 0.2, "endomorph": 0.1}}, "height_cm": 168, "body_fat_percent": 26,
            "distances": {"busto": 90, "cintura": 66, "manga": 58}, "bone_parameters": {"pelvis_width_cm": 26, "thigh_share_of_leg": 0.5, "humerus_share_of_arm": 0.56},
            "gluteus": {"shape": "coracao"}, "breast": {"shape": "gota", "espacados": 0.3, "assimetricos": {"L": 1.0, "R": 0.9}, "pendentes": 0.2},
            "underbust_cm": 70, "regions": {"breast": {"young_pa": 3000, "damping": 25}}}


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
    broken(regions={"breast": {"cor": 1}}), broken(extra=1)])
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
