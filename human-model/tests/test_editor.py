import json, os, sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hm_editor"))
import numpy as np
import catalog, recipe as rc, sheet, tape  # the add-on's package needs bpy; these modules don't

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


def box_topology():
    """A closed box 0.2 wide and 0.1 deep, up to 1 high, without tape.Topology's landmarks."""
    verts = np.array([(x, y, z) for z in (0.0, 1.0) for x, y in ((-0.1, -0.05), (0.1, -0.05), (0.1, 0.05), (-0.1, 0.05))])
    faces = [[0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    top = tape.Topology.__new__(tape.Topology)
    edges = {}
    top.face_edges = np.full((len(faces), 4), -1, dtype=np.int32)
    for i, f in enumerate(faces):
        for k, a in enumerate(f):
            b = f[(k + 1) % 4]
            top.face_edges[i, k] = edges.setdefault((min(a, b), max(a, b)), len(edges))
    top.edges = np.array(list(edges), dtype=np.int32)
    return top, verts


def test_a_section_finds_the_loop_and_a_tape_goes_around_it():
    top, verts = box_topology()
    loops = tape.section(top, verts, np.array((0, 0, 0.5)), tape.UP)
    assert len(loops) == 1
    assert tape.length_of(tape.hull_loop(loops[0], tape.UP)) == pytest.approx(0.6)


def test_a_tape_bridges_a_hollow():
    star = np.array([(1, 0, 0), (0, 1, 0), (-1, 0, 0), (0, -1, 0), (0.1, 0.1, 0), (-0.1, 0.1, 0)], float)
    assert tape.length_of(tape.hull_loop(star, tape.UP)) == pytest.approx(4 * 2 ** 0.5)


def test_solve_reaches_a_target_on_a_curve():
    state = [0.0]
    read = lambda: 1.0 + 0.3 * state[0] + 0.1 * state[0] ** 3
    write = lambda x: state.__setitem__(0, x)
    reached, limit = tape.solve(read, write, 0.0, 1.2, -0.8, 0.8, tolerance=0.001)
    assert reached == pytest.approx(1.2, abs=0.001)
    assert not limit


def test_solve_stops_at_the_slider_limit_and_says_so():
    state = [0.0]
    reached, limit = tape.solve(lambda: 1.0 + state[0], lambda x: state.__setitem__(0, x), 0.0, 5.0, -0.8, 0.8)
    assert reached == pytest.approx(1.8)
    assert limit


def test_solve_gives_up_on_a_control_that_does_nothing():
    reached, limit = tape.solve(lambda: 1.0, lambda x: None, 0.0, 2.0, -0.8, 0.8)
    assert reached == 1.0
    assert limit


def test_every_driver_names_a_measure():
    assert set(tape.DRIVERS) <= set(tape.MEASURE_KEYS)
    assert {"armhole_depth", "shoulder", "height"}.isdisjoint(tape.DRIVERS)


def test_a_recipe_may_carry_measures():
    r = rc.new("a", "female")
    r["measures_cm"] = {"bust": 92.0}
    assert rc.problems(r) == []


def test_blank_panel_values_stay_unset():
    v = {"sex": "female", "name": "", "silhouette": "NONE", "height_cm": 0.0, "biotype": "NONE", "others": {}, "distances": {"busto": 0.0}, "bone_parameters": {"pelvis_width_cm": 0.0}, "gluteus": "NONE", "breast": "NONE", "cup": "NONE"}
    assert sheet.character_from_values(v) == {"sex": "female"}


def test_panel_values_make_a_character():
    v = {"sex": "female", "name": "a", "silhouette": "pera", "height_cm": 168.0, "body_fat_percent": 26.0, "biotype": "mesomorph", "others": {"ectomorph": 0.2, "endomorph": 0.0},
         "distances": {"cintura": 66.0, "busto": 0.0}, "gluteus": "coracao", "breast": "gota", "espacados": 0.3, "pendentes": 0.0, "assimetrico_R": 0.9}
    c = sheet.character_from_values(v)
    assert c["biotype"] == {"type": "mesomorph", "others": {"ectomorph": 0.2}} and c["distances"] == {"cintura": 66.0}
    assert c["gluteus"] == {"shape": "coracao"} and c["breast"] == {"shape": "gota", "espacados": 0.3, "assimetricos": {"L": 1.0, "R": 0.9}}
    assert "pendentes" not in c["breast"]


def test_the_sheet_rows_say_where_each_value_came_from():
    resolved = {"fields": {"height": {"value": 168.0, "source": "typed"}, "waist": {"value": 70.2, "source": "silhouette"}, "cup": {"value": "C", "source": "current"}}}
    assert sheet.rows(resolved) == [("Altura", "168.0", "digitado"), ("Copa", "C", "atual"), ("Cintura", "70.2", "silhueta")]


def test_sheet_labels_every_distance_and_biotype():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from hmcore import character as ch
    assert {k for k, _ in sheet.DISTANCE_LABELS} == set(ch.DISTANCES)
    assert {k for k, _ in sheet.BIOTYPE_LABELS} == set(ch.BIOTYPES)


def test_breast_faders_reach_the_character_when_set():
    v = {"sex": "female", "breast": "gota", "projection_cm": 9.0, "base_cm": 0.0, "upper": 1.2, "lower": 0.0, "power": 2.5, "others": {}, "distances": {}, "bone_parameters": {}}
    c = sheet.character_from_values(v)
    assert c["breast"] == {"shape": "gota", "projection_cm": 9.0, "upper": 1.2, "power": 2.5}


def test_a_runs_progress_line():
    assert sheet.stage_line({"status": "running", "stages": {"shape": {"status": "done"}, "build": {"status": "running"}}}) == "Etapa 2 de 8: build"
    assert sheet.stage_line({"status": "done", "stages": {}}) == "Pronto"
    assert sheet.stage_line({"status": "failed", "failed_stage": "outward", "stages": {}}) == "Falhou na etapa outward"


def test_a_built_file_and_a_running_generation_come_before_the_stored_stage():
    assert sheet.current_stage("choices", False, False) == "choices"
    assert sheet.current_stage("fine", False, True) == "generating"
    assert sheet.current_stage("fine", True, True) == "built"


def test_the_choices_close_and_reopen():
    assert sheet.next_stage("choices", "close") == "fine"
    assert sheet.next_stage("fine", "reopen") == "choices"


@pytest.mark.parametrize("stage, action", [("choices", "reopen"), ("fine", "close"), ("built", "reopen"), ("generating", "close")])
def test_a_move_from_the_wrong_stage_is_refused(stage, action):
    with pytest.raises(ValueError):
        sheet.next_stage(stage, action)


def test_only_the_fine_adjustments_that_are_set_are_reported():
    assert sheet.fine_moved({k: 0.0 for k in sheet.FINE_FIELDS}) == []
    assert sheet.fine_moved({"b_base": 12.0, "other_mesomorph": 0.2, "pendentes": 0.0}) == ["b_base", "other_mesomorph"]


def test_the_fine_fields_all_enter_the_character_file():
    """A fader the panel shows in stage 2 must reach the file, or what is seen isn't what is generated."""
    base = {"sex": "female", "biotype": "ectomorph", "others": {"mesomorph": 0.0, "endomorph": 0.0}}
    for key, set_it in (("projection_cm", {"projection_cm": 9.0}), ("base_cm", {"base_cm": 9.0}), ("espacados", {"espacados": 0.5}), ("pendentes", {"pendentes": 0.5})):
        assert key in sheet.character_from_values({**base, **set_it})["breast"]
    assert sheet.character_from_values({**base, "others": {"mesomorph": 0.2}})["biotype"]["others"] == {"mesomorph": 0.2}
    assert sheet.character_from_values({**base, "bone_parameters": {"pelvis_width_cm": 25.0}})["bone_parameters"] == {"pelvis_width_cm": 25.0}
