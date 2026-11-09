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
