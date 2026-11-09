import json, os, sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import fast_review as fr

KNOWN = fr.known_values("female")


def test_stages_run_in_the_agreed_order():
    assert fr.STAGES == ("build", "tape", "skin", "layers", "walk", "dump", "simulate", "file")


def test_overrides_go_to_the_stage_that_knows_them():
    routed = fr.route(["VOXEL=0.01", "fat.belly=40", "depth.patella=8", "FAT_YOUNG=3000", "VOLUME_EVERY=5", "BONE_TEST=1"], KNOWN)
    assert routed == {"layers": ["VOXEL=0.01", "fat.belly=40"], "skin": ["depth.patella=8"], "simulate": ["FAT_YOUNG=3000", "VOLUME_EVERY=5", "BONE_TEST=1"]}


@pytest.mark.parametrize("bad", ["NOPE=1", "fat.nowhere=3", "VOXEL", "VOXEL=fine"])
def test_an_override_no_stage_knows_stops_the_run(bad):
    with pytest.raises(fr.Refused):
        fr.route([bad], KNOWN)


def test_a_used_nickname_is_refused(tmp_path):
    root = str(tmp_path)
    fr.refuse_used(root, "2026-11-08", "first")
    os.makedirs(fr.run_folder(root, "2026-11-08", "first"))
    with pytest.raises(fr.Refused):
        fr.refuse_used(root, "2026-11-08", "first")
    fr.refuse_used(root, "2026-11-09", "first")  # another day is fine


@pytest.mark.parametrize("bad", ["a b", "a/b", "", "../x"])
def test_a_nickname_must_be_safe_for_a_folder(bad):
    with pytest.raises(fr.Refused):
        fr.check_nickname(bad)


def test_the_commands_chain_each_stage_to_the_one_before():
    d = "/mnt/g/run/female"
    made = {}
    seen = {}
    for stage in fr.STAGES:
        seen[stage] = fr.commands(stage, d, "female", "female", "/r/female.json", made, {"layers": ["VOXEL=0.01"]}, here="/h")[0]
        made.update(fr.outputs(stage, d, "female"))
    assert f"{d}/build" in seen["build"]
    assert f"SKIN={d}/skin/female.skin_fit.npz" in seen["layers"] and "VOXEL=0.01" in seen["layers"]
    assert seen["walk"][seen["walk"].index("--blend") + 1] == f"{d}/build/female.blend"
    assert seen["walk"][-2:] == ["4", "2"]
    assert seen["dump"][seen["dump"].index("--blend") + 1] == f"{d}/walk/female_walk.blend"
    assert "ABOVE_HIP=10" in seen["simulate"]
    assert seen["file"][-1] == "-"  # no frames, no rendering


def test_run_json_records_each_stage_and_stops_at_a_failure(tmp_path):
    recipe = tmp_path / "female.json"
    recipe.write_text(json.dumps({"name": "female"}))
    folder = str(tmp_path / "run" / "female")
    calls = []

    def execute(argv, log):
        calls.append(argv)
        return 1 if "skin_over_bone.py" in " ".join(argv) else 0

    with pytest.raises(fr.StageFailed) as e:
        fr.run_body("first", "female", str(recipe), ["FAT_YOUNG=3000"], folder, execute=execute)
    assert e.value.stage == "skin" and e.value.log.endswith("logs/skin.log")
    record = json.load(open(f"{folder}/run.json"))
    assert record["status"] == "failed" and record["failed_stage"] == "skin" and record["overrides"] == ["FAT_YOUNG=3000"]
    assert record["stages"]["build"]["status"] == "done" and "seconds" in record["stages"]["build"]
    assert "layers" not in record["stages"]  # nothing ran after the failure


def test_a_full_run_ends_done(tmp_path):
    recipe = tmp_path / "male.json"
    recipe.write_text(json.dumps({"name": "male"}))
    folder = str(tmp_path / "run" / "male")
    record = fr.run_body("first", "male", str(recipe), [], folder, execute=lambda argv, log: 0)
    assert record["status"] == "done" and list(record["stages"]) == list(fr.STAGES)
    assert record["stages"]["file"]["output"]["body_blend"] == f"{folder}/body_walk.blend"


def test_status_shows_recent_runs(tmp_path):
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
    import time
    import hm_status
    d = tmp_path / "a"
    d.mkdir()
    (d / "run.json").write_text(json.dumps({"nickname": "first", "sex": "female", "status": "running", "stages": {"build": {"status": "done"}, "tape": {"status": "running"}}}))
    lines = hm_status.fast_review_lines(str(tmp_path / "*" / "run.json"), time.time(), 1)
    assert len(lines) == 1 and "first/female" in lines[0] and "1/2" in lines[0] and "tape" in lines[0]
    assert hm_status.fast_review_lines(str(tmp_path / "*" / "run.json"), time.time() + 7200, 1) == []


def recipes(tmp_path):
    out = {}
    for sex in fr.BODIES:
        f = tmp_path / f"{sex}.json"
        f.write_text(json.dumps({"name": sex}))
        out[sex] = str(f)
    return out


def test_both_bodies_end_in_one_pair_file(tmp_path):
    run = str(tmp_path / "run")
    calls = []
    record, failures = fr.run_both("first", [], run, recipes(tmp_path), execute=lambda argv, log: calls.append(argv) or 0)
    assert not failures and record["status"] == "done"
    pair = [c for c in calls if any("body_walk_pair.py" in x for x in c)]
    assert len(pair) == 1 and f"{run}/female/body_walk.blend" in pair[0] and f"{run}/male/body_walk.blend" in pair[0] and f"{run}/mulher_e_homem.blend" in pair[0]
    written = json.load(open(f"{run}/run.json"))
    assert set(written["bodies"]) == set(fr.BODIES) and "seconds" in written


def test_if_one_body_fails_the_other_finishes_and_no_pair_is_made(tmp_path):
    run = str(tmp_path / "run")
    calls = []

    def execute(argv, log):
        calls.append(argv)
        return 1 if "/male/" in " ".join(argv) and "body_layers.py" in " ".join(argv) else 0

    record, failures = fr.run_both("first", [], run, recipes(tmp_path), execute=execute)
    assert set(failures) == {"male"} and failures["male"].stage == "layers" and failures["male"].log.endswith("male/logs/layers.log")
    assert record["status"] == "failed" and record["bodies"]["female"]["status"] == "done"
    assert not [c for c in calls if any("body_walk_pair.py" in x for x in c)]
    assert any("/female/body_walk.blend" in x for c in calls for x in c)  # the woman went all the way


def finished(tmp_path, sex="female"):
    """A finished run with its outputs on disk."""
    base = tmp_path / "2026-11-08" / "fast_review" / "early"
    recipe = tmp_path / f"{sex}.json"
    recipe.write_text(json.dumps({"name": sex}))
    fr.run_body("early", sex, str(recipe), [], str(base / sex), execute=lambda argv, log: 0)
    record = json.load(open(base / sex / "run.json"))
    for entry in record["stages"].values():
        for name, path in entry["output"].items():
            if name != "build_dir":
                open(path, "w").close()
    return str(base), str(recipe)


def test_restart_reads_earlier_stages_from_the_base_run(tmp_path):
    base, recipe = finished(tmp_path)
    assert fr.find_base(str(tmp_path), "early") == base
    reused = fr.reusable(base, "female", "simulate")
    calls = []
    folder = str(tmp_path / "next" / "female")
    record = fr.run_body("next", "female", recipe, ["FAT_YOUNG=3000"], folder, execute=lambda argv, log: calls.append(argv) or 0, reused=reused)
    assert len(calls) == 2  # simulate and file only
    assert f"{base}/female/layers/female.body_layers.npz" in calls[0] and f"{folder}/simulate" in calls[0]
    assert record["stages"]["layers"]["status"] == "reused" and record["stages"]["layers"]["origin"] == f"{base}/female"
    assert record["stages"]["simulate"]["status"] == "done"


def test_a_chain_of_reuse_names_the_first_run(tmp_path):
    base, recipe = finished(tmp_path)
    folder = tmp_path / "2026-11-09" / "fast_review" / "next" / "female"
    fr.run_body("next", "female", recipe, [], str(folder), execute=lambda argv, log: 0, reused=fr.reusable(base, "female", "simulate"))
    assert fr.reusable(str(folder.parent), "female", "simulate")["layers"]["origin"] == f"{base}/female"


def test_a_base_without_a_stages_output_is_refused(tmp_path):
    base, _ = finished(tmp_path)
    os.remove(f"{base}/female/layers/female.body_layers.npz")
    with pytest.raises(fr.Refused, match="layers"):
        fr.reusable(base, "female", "simulate")
    assert fr.reusable(base, "female", "layers")  # needing only what's left is fine
    with pytest.raises(fr.Refused):
        fr.find_base(str(tmp_path), "nobody")


def test_an_override_for_a_skipped_stage_is_refused():
    with pytest.raises(fr.Refused, match="VOXEL"):
        fr.check_start({"layers": ["VOXEL=0.01"]}, "simulate")
    fr.check_start({"simulate": ["FAT_YOUNG=3000"]}, "simulate")


def test_videos_only_when_asked():
    made = {"walked": "w", "layers": "l", "bones": "b", "dump": "d"}
    plain = fr.commands("file", "/f", "n", "female", "r", made, {}, here="/h")
    assert len(plain) == 1 and plain[0][-1] == "-"
    asked = fr.commands("file", "/f", "n", "female", "r", made, {}, here="/h", render=True)
    assert asked[0][-1] == "/f/frames" and [c[0] for c in asked[1:]] == ["ffmpeg", "ffmpeg"]
    assert asked[1][-1] == "/f/compare.mp4" and asked[2][-1] == "/f/inside.mp4" and "/f/frames/inside/%04d.png" in asked[2]


def test_the_nickname_reaches_the_file_stage():
    made = {"walked": "w", "layers": "l", "bones": "b", "dump": "d"}
    assert fr.commands("file", "/f", "n", "female", "r", made, {}, here="/h", nickname="first")[0][-2:] == ["-", "first"]


def test_a_run_is_added_to_the_shared_file_and_can_leave_it(tmp_path):
    shared = str(tmp_path / "todas.blend")
    add = fr.shared_command("add", shared, "first", "/run/pair.blend", here="/h")
    assert "--blend" not in add and add[-4:] == ["add", shared, "first", "/run/pair.blend"]  # a new file is started empty
    open(shared, "w").close()
    again = fr.shared_command("add", shared, "next", "/run/pair.blend", here="/h")
    assert again[again.index("--blend") + 1] == shared  # an existing one is opened
    assert fr.shared_command("remove", shared, "first", here="/h")[-3:] == ["remove", shared, "first"]


def test_the_shared_file_has_one_writer(tmp_path):
    assert fr.locked_shared(str(tmp_path), ["x"], "log", execute=lambda argv, log: 0) == 0
    assert (tmp_path / "fast_review_todas.lock").exists()


CHARACTER_MADE = {"sheet": "/f/sheet.json", "recipe": "/f/n.recipe.json", "shape": "/f/shape.json", "targets": "/f/targets.json", "build_dir": "/f/build", "skin_fit": "/f/skin/n.skin_fit.npz", "fat_table": "/f/skin/n.fat_table.json", "regions": "/f/skin/n.regions.json", "tissue": "/f/skin/n.tissue.npz", "layers": "/f/layers/n.body_layers.npz", "bones": "/f/build/n.bones.npz", "dump": "/f/dump.npz"}


def test_the_character_path_has_its_own_stages():
    assert fr.CHARACTER_STAGES == ("shape", "build", "outward", "layers", "walk", "dump", "simulate", "file")
    build = fr.commands("build", "/f", "n", "female", "/r", CHARACTER_MADE, {}, here="/h")[0]
    assert "/f/n.recipe.json" in build and build[-2:] == ["--targets", "/f/targets.json"]
    layers = fr.commands("layers", "/f", "n", "female", "/r", CHARACTER_MADE, {"layers": ["VOXEL=0.01"]}, here="/h")[0]
    assert "FAT_TABLE=/f/skin/n.fat_table.json" in layers and "TISSUE=/f/skin/n.tissue.npz" in layers and "VOXEL=0.01" in layers
    simulate = fr.commands("simulate", "/f", "n", "female", "/r", {**CHARACTER_MADE, "walked": "x"}, {}, here="/h")[0]
    assert "REGIONS=/f/skin/n.regions.json" in simulate
    outward = fr.commands("outward", "/f", "n", "female", "/r", CHARACTER_MADE, {"layers": ["VOXEL=0.01", "fat.belly=3"]}, here="/h")[0]
    assert "VOXEL=0.01" in outward and "fat.belly=3" not in outward


def test_the_recipe_path_keeps_its_commands():
    assert fr.commands("build", "/f", "n", "female", "/r", {}, {}, here="/h")[0][-2:] == ["/r", "/f/build"]


def test_prepare_character_writes_sheet_and_targets(tmp_path):
    c = tmp_path / "c.json"
    c.write_text(json.dumps({"sex": "female", "name": "ana", "silhouette": "pera", "height_cm": 168}))
    folder = str(tmp_path / "run" / "female")
    assert fr.prepare_character(str(c), "female", folder) == "ana"
    sheet = json.load(open(f"{folder}/sheet.json"))
    assert sheet["resolved"]["fields"]["height"]["value"] == 168.0 and sheet["character"]["silhouette"] == "pera"
    assert "biacromial_m" in json.load(open(f"{folder}/targets.json"))


def test_a_character_of_the_other_sex_is_refused(tmp_path):
    c = tmp_path / "c.json"
    c.write_text(json.dumps({"sex": "male"}))
    with pytest.raises(fr.Refused, match="male character"):
        fr.prepare_character(str(c), "female", str(tmp_path / "r"))


def test_a_bad_character_is_refused(tmp_path):
    c = tmp_path / "c.json"
    c.write_text(json.dumps({"sex": "female", "silhouette": "x"}))
    with pytest.raises(fr.Refused, match="silhouette"):
        fr.prepare_character(str(c), "female", str(tmp_path / "r"))


def test_a_run_stops_at_to(tmp_path):
    recipe = tmp_path / "female.json"
    recipe.write_text(json.dumps({"name": "female"}))
    record = fr.run_body("first", "female", str(recipe), [], str(tmp_path / "run"), execute=lambda argv, log: 0, to="layers")
    assert list(record["stages"]) == ["build", "tape", "skin", "layers"] and record["status"] == "done"


def test_warnings_of_the_check():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
    import character_check as cc
    from hmcore import character as ch
    ratios = ch.silhouette_ratios()
    measures = {"waist": 80.0, "hip": 90.0, "bust": 90.0, "shoulder_width": 37.0}
    clean_layers = {"bones_with_points_outside_skin": {}}
    clean_skin = {"reached_within_0_5": True, "percent": 28.0, "target_percent": 28.0, "triangles_turned_over": 0}
    assert cc.warnings({"sex": "female", "silhouette": "pera"}, {"waist": 75.0, "hip": 90.0, "bust": 78.0, "shoulder_width": 30.0}, ratios, clean_layers, clean_skin) == []
    bad = cc.warnings({"sex": "female", "silhouette": "ampulheta"}, measures, ratios, {"bones_with_points_outside_skin": {"femur_L": {}}}, {**clean_skin, "reached_within_0_5": False, "triangles_turned_over": 3})
    assert any("femur_L" in w for w in bad) and any("tolerância" in w for w in bad) and any("viraram" in w for w in bad)
    assert any("waist_hip" in w for w in bad)
    assert cc.warnings({"sex": "female"}, measures, ratios, clean_layers, clean_skin) == []


def test_overrides_may_come_after_the_options():
    a = fr.parser().parse_intermixed_args(["first", "--character", "female=a.json", "--character", "male=b.json", "BONE_TEST=1", "VOXEL=0.01"])
    assert a.nickname == "first" and a.overrides == ["BONE_TEST=1", "VOXEL=0.01"] and a.character == ["female=a.json", "male=b.json"]


def test_a_character_run_goes_through_every_stage(tmp_path):
    recipe = tmp_path / "female.json"
    recipe.write_text(json.dumps({"name": "female"}))
    calls = []
    record = fr.run_body("first", "female", str(recipe), [], str(tmp_path / "run"), execute=lambda argv, log: calls.append(argv) or 0, chain=fr.CHARACTER_STAGES, name="ana")
    assert list(record["stages"]) == list(fr.CHARACTER_STAGES) and record["status"] == "done"
    assert any("character_shape.py" in x for x in calls[0]) and any("--targets" == x for c in calls for x in c)


def test_the_heavy_stage_takes_a_lock(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(fr, "REVIEW", str(tmp_path))
    monkeypatch.setattr(fr, "_call", lambda argv, log, cwd: calls.append(argv) or 0)
    fr.run_stage(["python3", "x/outward_skin.py"], "log")
    assert (tmp_path / "fast_review_heavy.lock").exists() and len(calls) == 1
    fr.run_stage(["python3", "x/body_layers.py"], "log")  # others run freely
    assert len(calls) == 2
