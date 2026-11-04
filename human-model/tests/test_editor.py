import json, os, sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hm_editor"))
import catalog, recipe as rc  # the add-on's package needs bpy; these two modules don't

SECTIONS = {
    "nose": {"categories": [{"name": "nose-hump-decr-incr", "has_left_and_right": False, "opposites": {"negative-unsided": "nose-hump-decr", "positive-unsided": "nose-hump-incr"}},
                            {"name": "nose-trans-down-up", "has_left_and_right": False, "opposites": {"negative-unsided": "nose-trans-down", "positive-unsided": "nose-trans-up"}}]},
    "arms": {"categories": [{"name": "upperarm-muscle-decr-incr", "has_left_and_right": True, "opposites": {"negative-left": "l-upperarm-muscle-decr", "positive-left": "l-upperarm-muscle-incr", "negative-right": "r-upperarm-muscle-decr", "positive-right": "r-upperarm-muscle-incr"}}]},
    "head": {"categories": [{"name": "head-oval", "has_left_and_right": False}]},
    "torso": {"categories": [{"name": "measure-hips-circ-decr-incr", "has_left_and_right": False, "opposites": {"negative-unsided": "measure-hips-circ-decr", "positive-unsided": "measure-hips-circ-incr"}}]},
    "pelvis": {"categories": [{"name": "bulge-decr-incr", "has_left_and_right": False, "opposites": {"negative-unsided": "bulge-decr", "positive-unsided": "bulge-incr"}}]},
    "genitals": {"categories": [{"name": "penis-length-decr-incr", "has_left_and_right": False, "opposites": {"negative-unsided": "penis-length-decr", "positive-unsided": "penis-length-incr"}}]},
}


def by_name():
    return {s.name: s for s in catalog.sliders(SECTIONS)}


def test_genitals_are_left_out():
    assert not [n for n in by_name() if "penis" in n or "bulge" in n]


def test_a_slider_knows_its_targets_label_and_ends():
    s = by_name()["nose-trans-down-up"]
    assert s.sides == (("", ("nose-trans-down", "nose-trans-up")),)
    assert (s.low, s.high) == ("down", "up")
    assert s.label == "Position (down / up)"
    assert by_name()["nose-hump-decr-incr"].label == "Hump"


def test_a_sided_slider_has_both_sides_and_is_marked_skin_only():
    s = by_name()["upperarm-muscle-decr-incr"]
    assert s.sided and s.skin_only
    assert s.targets() == ["l-upperarm-muscle-decr", "l-upperarm-muscle-incr", "r-upperarm-muscle-decr", "r-upperarm-muscle-incr"]
    assert s.label == "Upper arm muscle"


def test_a_slider_that_only_goes_up():
    s = by_name()["head-oval"]
    assert s.sides == (("", (None, "head-oval")),)
    assert s.label == "Oval"


def test_moved_slider_goes_to_its_region():
    assert by_name()["measure-hips-circ-decr-incr"].region == "hip"
    assert by_name()["measure-hips-circ-decr-incr"].label == "Hips circumference"


def test_search_needs_every_word():
    found = catalog.search(catalog.sliders(SECTIONS), "nose hump")
    assert [s.name for s in found] == ["nose-hump-decr-incr"]
    assert catalog.search(catalog.sliders(SECTIONS), "  ") == []


TARGET_JSON = "/mnt/g/mocap-studio-downloads/apps/blender/5.2.2/blender-5.2.2-windows-x64/portable/extensions/user_default/mpfb/data/targets/target.json"


@pytest.mark.skipif(not os.path.exists(TARGET_JSON), reason="needs MPFB on G:")
def test_every_real_slider_has_a_region_and_a_unique_label():
    all_sliders = catalog.sliders(json.load(open(TARGET_JSON)))
    assert len(all_sliders) == 230  # MPFB's 234 less three genital sliders and bulge
    assert len({s.key for s in all_sliders}) == len(all_sliders)
    for region, _, _ in catalog.REGIONS:
        labels = [s.label for s in all_sliders if s.region == region]
        assert labels and len(set(labels)) == len(labels), region


def test_new_recipe_can_be_built():
    assert rc.problems(rc.new("anna", "female")) == []
    assert rc.new("anna", "female")["macros"]["gender"] == 0.0


@pytest.mark.parametrize("change, word", [
    (lambda r: r["macros"].update(age=0.3), "child"),
    (lambda r: r["macros"].update(gender=0.5), "Gender"),
    (lambda r: r.update(sex="other"), "Sex"),
    (lambda r: r.update(name="a b"), "name"),
    (lambda r: r["macros"]["race"].update(asian=0.9), "Race"),
    (lambda r: r["macros"].update(weight=1.5), "weight"),
    (lambda r: r["targets"].update({"penis-length-incr": 0.5}), "genitalia"),
    (lambda r: r["targets"].update({"nose-hump-incr": 1.5}), "nose-hump"),
])
def test_a_recipe_that_cant_be_built_says_why(change, word):
    r = rc.new("a", "male")
    change(r)
    assert any(word in p for p in rc.problems(r))


def test_neutral_recipes_are_valid():
    here = os.path.join(os.path.dirname(__file__), "..", "data", "recipes")
    for f in ("male.json", "female.json"):
        assert rc.problems(json.load(open(os.path.join(here, f)))) == [], f


def test_test_people_fail_only_on_age():
    """Four of the six are below the adult age: bug human-model/8. Anything else wrong with them would be new."""
    here = os.path.join(os.path.dirname(__file__), "..", "data", "recipes", "test_people")
    for f in os.listdir(here):
        wrong = rc.problems(json.load(open(os.path.join(here, f))))
        assert not [p for p in wrong if "child" not in p], f


def test_rebalance_keeps_the_sum_and_the_others_ratio():
    out = rc.rebalance({"african": 0.2, "asian": 0.2, "caucasian": 0.6}, "african", 0.5)
    assert out["african"] == 0.5
    assert sum(out.values()) == pytest.approx(1)
    assert out["caucasian"] == pytest.approx(3 * out["asian"])
    assert rc.rebalance({"african": 1.0, "asian": 0.0, "caucasian": 0.0}, "african", 0.0) == {"african": 0.0, "asian": 0.5, "caucasian": 0.5}


def test_identity_targets_keep_only_named_sliders():
    keys = [("Basis", 0.0), ("$md-x", 0.9), ("F_risorius_L", 0.4), ("B_breath", 0.2), ("nose-hump-incr", 0.61234), ("nose-hump-decr", 0.0), ("odd-key", 0.5)]
    assert rc.identity_targets(keys, lambda n: n.startswith("nose")) == {"nose-hump-incr": 0.6123}


def test_safe_name():
    assert rc.safe_name(" Old man! 2 ") == "Old_man_2"
