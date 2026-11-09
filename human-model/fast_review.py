"""One command from a recipe to a walked body in a Blender file, with no rendering, from WSL:
    python3 human-model/fast_review.py NICKNAME [--body female|male] [NAME=value ...]
With no --body, the woman and the man side by side, then both in <nickname>/mulher_e_homem.blend. If one fails the other finishes, the pair file isn't made, and the command says which stage failed and where its log is.
Stages, in order: build, tape, skin, layers, walk, dump, simulate, file. A NAME=value goes to the stage that knows it (VOXEL, fat.<zone> and
structure.<name> to layers; depth.<prefix> and MAX_PUSH_MM to skin; the tissue values, VOLUME_EVERY and BONE_TEST to simulate); one that no
stage knows stops the run before it starts. Results go to review/<today>/fast_review/<nickname>/<sex>/, with run.json and a log per stage.
A nickname already used that day is refused, so nothing is overwritten.
--render also makes the two videos of blender/body_walk_bake.py for each body, into its folder; off unless asked.
--from STAGE --base EARLIER starts at STAGE and reads the stages before it from the earlier run, not copied; run.json records where each part came from, through chains of reuse, and a base run that lacks a needed stage's output is refused before anything runs."""
import argparse, concurrent.futures, datetime, glob, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REVIEW = "/mnt/g/mocap-studio-downloads/review"
DATA = os.path.join(HERE, "data")
BODIES = ("female", "male")
PAIR_NAME = "mulher_e_homem.blend"
LABELS = {"female": "mulher", "male": "homem"}
STAGES = ("build", "tape", "skin", "layers", "walk", "dump", "simulate", "file")
SIMULATE_SETTINGS = ("VOLUME_EVERY", "BONE_TEST")
VIDEO_FPS = "24"  # as blender/walk.py's FPS
VIDEOS = ("compare", "inside")  # body_walk_bake.py's two views
WALK_CYCLES, WALK_STOP_STEPS = "4", "2"  # the 2 are the steps of the slow stop, as in docs/muscle-physics.md


class Refused(Exception):
    """The run can't start: the message says why."""


class StageFailed(Exception):
    def __init__(self, stage, log):
        super().__init__(f"stage {stage} failed; its log is {log}")
        self.stage, self.log = stage, log


def _json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def known_values(sex, data=DATA):
    """What each stage can be told, from the same files the stages read their defaults from."""
    body_fat = _json(os.path.join(data, f"body_fat_{sex}.json"))
    depth = _json(os.path.join(data, f"skin_over_bone_{sex}.json"))
    tissue = [k for k in _json(os.path.join(data, "body_tissue.json")) if not k.startswith("_")]
    return {"layers": {"VOXEL", *(f"fat.{z}" for z in body_fat["fat_mm"]), *(f"structure.{k}" for k in body_fat["structure"])},
            "skin": {"MAX_PUSH_MM", *(f"depth.{k}" for k in depth["least_depth_mm"])},
            "simulate": {*tissue, *SIMULATE_SETTINGS}}


def route(overrides, known):
    """{stage: [NAME=value, ...]} for the NAME=value strings given. Raises Refused for anything malformed or that no stage knows."""
    out = {}
    for item in overrides:
        name, eq, value = item.partition("=")
        if not eq:
            raise Refused(f"{item}: expected NAME=value")
        try:
            float(value)
        except ValueError:
            raise Refused(f"{item}: the value must be a number") from None
        stage = next((s for s, names in known.items() if name in names), None)
        if stage is None:
            raise Refused(f"{name}: no stage knows this value")
        out.setdefault(stage, []).append(item)
    return out


def check_nickname(nickname):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", nickname):
        raise Refused(f"{nickname}: a nickname may use only letters, numbers, - and _")


def run_folder(root, day, nickname):
    return os.path.join(root, day, "fast_review", nickname)


def refuse_used(root, day, nickname):
    if os.path.exists(run_folder(root, day, nickname)):
        raise Refused(f"the nickname {nickname} was already used on {day}: every attempt is kept, so choose another")


def outputs(stage, folder, name):
    """What a stage leaves behind, by name."""
    return {"build": {"blend": f"{folder}/build/{name}.blend", "bones": f"{folder}/build/{name}.bones.npz", "build_dir": f"{folder}/build"},
            "tape": {"tape": f"{folder}/tape.json"},
            "skin": {"skin_fit": f"{folder}/skin/{name}.skin_fit.npz"},
            "layers": {"layers": f"{folder}/layers/{name}.body_layers.npz"},
            "walk": {"walk": f"{folder}/walk/{name}_walk.blend"},
            "dump": {"dump": f"{folder}/dump.npz"},
            "simulate": {"walked": f"{folder}/simulate/body_walk.npz"},
            "file": {"body_blend": f"{folder}/body_walk.blend"}}[stage]


def commands(stage, folder, name, sex, recipe, made, routed, here=HERE, render=False, nickname=None):
    """The commands of one stage. made: the outputs of the stages before it, as outputs() names them."""
    blender = [sys.executable, f"{here}/blender_run.py"]
    gpu = [f"{here}/hm.sh", "--gpu", "python"]
    tools = "human-model/tools"
    extra = list(routed.get(stage, ()))
    if stage == "build":
        return [[sys.executable, f"{here}/build_model.py", recipe, f"{folder}/build"]]
    if stage == "tape":
        return [[*blender, f"{here}/blender/body_tape.py", recipe, f"{folder}/tape.json"]]
    if stage == "skin":
        return [[*gpu, f"{tools}/skin_over_bone.py", made["build_dir"], name, made["tape"], f"{folder}/skin", *extra]]
    if stage == "layers":
        return [[*gpu, f"{tools}/body_layers.py", made["build_dir"], name, f"{folder}/layers", f"SKIN={made['skin_fit']}", *extra]]
    if stage == "walk":
        return [[*blender, "--blend", made["blend"], f"{here}/blender/walk.py", f"{here}/data/gait_walk.json", sex, f"{folder}/walk/{name}_walk.blend", WALK_CYCLES, WALK_STOP_STEPS]]
    if stage == "dump":
        return [[*blender, "--blend", made["walk"], f"{here}/blender/body_walk_dump.py", f"{folder}/dump.npz"]]
    if stage == "simulate":
        return [[*gpu, f"{tools}/body_walk.py", made["layers"], made["bones"], made["dump"], f"{folder}/simulate", "ABOVE_HIP=10", *extra]]
    if stage == "file":
        bake = [*blender, f"{here}/blender/body_walk_bake.py", made["walked"], made["layers"], made["bones"], made["dump"], f"{folder}/body_walk.blend", f"{folder}/frames" if render else "-", *([nickname] if nickname else [])]
        if not render:
            return [bake]
        return [bake, *[["ffmpeg", "-y", "-framerate", VIDEO_FPS, "-i", f"{folder}/frames/{v}/%04d.png", "-c:v", "libx264", "-pix_fmt", "yuv420p", f"{folder}/{v}.mp4"] for v in VIDEOS]]
    raise ValueError(stage)


def find_base(root, nickname):
    """The newest run with this nickname, whichever day it was."""
    found = sorted(glob.glob(os.path.join(root, "*", "fast_review", nickname)))
    if not found:
        raise Refused(f"no earlier run is called {nickname}")
    return found[-1]


def reusable(base, sex, start):
    """{stage: entry} for the stages before start, read from the earlier run. Raises Refused if a stage or one of its outputs is missing."""
    path = f"{base}/{sex}/run.json"
    if not os.path.exists(path):
        raise Refused(f"{base} has no run of the {sex} body")
    stages, out = _json(path).get("stages", {}), {}
    for stage in STAGES[:STAGES.index(start)]:
        entry = stages.get(stage)
        if not entry or entry.get("status") not in ("done", "reused"):
            raise Refused(f"{base}/{sex} didn't finish the stage {stage}")
        missing = [p for p in entry["output"].values() if not os.path.exists(p)]
        if missing:
            raise Refused(f"{base}/{sex}: the stage {stage}'s output is gone: {missing[0]}")
        out[stage] = {"status": "reused", "output": entry["output"], "origin": entry.get("origin", f"{base}/{sex}")}
    return out


def check_start(routed, start):
    """An override for a stage that won't run would silently do nothing, so it stops the run."""
    skipped = [s for s in STAGES[:STAGES.index(start)] if s in routed]
    if skipped:
        raise Refused(f"{', '.join(routed[skipped[0]])}: the stage {skipped[0]} comes before {start}, so it wouldn't run")


def commit(here=HERE):
    try:
        return subprocess.run(["git", "-C", here, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except OSError:  # no git here: the tests' image has none
        return ""


def save_record(folder, record):
    os.makedirs(folder, exist_ok=True)
    tmp = f"{folder}/run.json.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=1, ensure_ascii=False)
    os.replace(tmp, f"{folder}/run.json")


def run_stage(argv, log, cwd=HERE):
    """Runs one command, its output going to the stage's log. Returns its exit code."""
    with open(log, "a", encoding="utf-8") as fh:
        fh.write("$ " + " ".join(argv) + "\n")
        fh.flush()
        return subprocess.call(argv, stdout=fh, stderr=subprocess.STDOUT, cwd=cwd)


def run_body(nickname, sex, recipe, overrides, folder, execute=run_stage, reused=None, render=False):
    """Runs every stage of one body in order, past the ones in reused ({stage: entry} of an earlier run). Writes run.json after each. Raises StageFailed at the first that fails."""
    name = _json(recipe)["name"]
    routed = route(overrides, known_values(sex))
    os.makedirs(f"{folder}/logs", exist_ok=True)
    for sub in ("walk", "skin", "layers", "simulate", "build"):
        os.makedirs(f"{folder}/{sub}", exist_ok=True)
    record = {"nickname": nickname, "sex": sex, "commit": commit(), "recipe": recipe, "overrides": list(overrides), "routed": routed,
              "status": "running", "stages": {}}
    save_record(folder, record)
    made = {}
    for stage in STAGES:
        if reused and stage in reused:
            record["stages"][stage] = dict(reused[stage])
            made.update(reused[stage]["output"])
            save_record(folder, record)
            continue
        log = f"{folder}/logs/{stage}.log"
        entry = {"status": "running", "log": log, "output": outputs(stage, folder, name)}
        record["stages"][stage] = entry
        save_record(folder, record)
        t0 = time.time()
        for argv in commands(stage, folder, name, sex, recipe, made, routed, render=render, nickname=nickname):
            code = execute(argv, log)
            if code != 0:
                entry.update(status="failed", seconds=round(time.time() - t0, 1), exit_code=code)
                record.update(status="failed", failed_stage=stage)
                save_record(folder, record)
                raise StageFailed(stage, log)
        entry.update(status="done", seconds=round(time.time() - t0, 1))
        made.update(entry["output"])
        if render and stage == "file":
            entry["output"].update({v: f"{folder}/{v}.mp4" for v in VIDEOS})
        save_record(folder, record)
    record["status"] = "done"
    save_record(folder, record)
    return record


def pair_command(run, here=HERE):
    """body_walk_pair.py on the two bodies' files: the woman's skin and section, then the man's."""
    return [sys.executable, f"{here}/blender_run.py", "--blend", f"{run}/female/body_walk.blend", f"{here}/blender/body_walk_pair.py",
            f"{run}/male/body_walk.blend", f"{run}/{PAIR_NAME}", LABELS["female"], LABELS["male"]]


def run_both(nickname, overrides, run, recipes, execute=run_stage, reused=None, render=False):
    """Both bodies side by side, each only waiting for its own previous stage. Returns (record, failures: {sex: StageFailed})."""
    t0 = time.time()
    record = {"nickname": nickname, "commit": commit(), "overrides": list(overrides), "status": "running", "bodies": {}}
    save_record(run, record)
    failures = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(BODIES)) as pool:
        running = {sex: pool.submit(run_body, nickname, sex, recipes[sex], overrides, f"{run}/{sex}", execute, (reused or {}).get(sex), render) for sex in BODIES}
    for sex, future in running.items():
        try:
            future.result()
            record["bodies"][sex] = {"status": "done", "folder": f"{run}/{sex}"}
        except StageFailed as e:
            failures[sex] = e
            record["bodies"][sex] = {"status": "failed", "stage": e.stage, "log": e.log, "folder": f"{run}/{sex}"}
    if failures:
        record["status"] = "failed"
    else:
        os.makedirs(f"{run}/logs", exist_ok=True)
        log = f"{run}/logs/pair.log"
        if execute(pair_command(run), log) != 0:
            failures["pair"] = StageFailed("pair", log)
            record.update(status="failed", pair={"status": "failed", "log": log})
        else:
            record.update(status="done", pair={"status": "done", "output": f"{run}/{PAIR_NAME}"})
    record["seconds"] = round(time.time() - t0, 1)
    save_record(run, record)
    return record, failures


def main(argv=None):
    ap = argparse.ArgumentParser(description="From recipes to walked bodies in a Blender file, no rendering")
    ap.add_argument("nickname")
    ap.add_argument("--body", choices=BODIES)
    ap.add_argument("--from", dest="start", choices=STAGES, default=STAGES[0], help="the stage to start from; the ones before it are read from --base")
    ap.add_argument("--base", help="the earlier run's nickname, with --from")
    ap.add_argument("--render", action="store_true", help="also make the two videos of each body")
    ap.add_argument("overrides", nargs="*", metavar="NAME=value")
    a = ap.parse_args(argv)
    day = datetime.date.today().isoformat()
    bodies = (a.body,) if a.body else BODIES
    reused = {}
    try:
        check_nickname(a.nickname)
        if (a.start != STAGES[0]) != bool(a.base):
            raise Refused("--from and --base go together")
        for sex in bodies:
            check_start(route(a.overrides, known_values(sex)), a.start)
        refuse_used(REVIEW, day, a.nickname)
        if a.base:
            base = find_base(REVIEW, a.base)
            reused = {sex: reusable(base, sex, a.start) for sex in bodies}
    except Refused as e:
        sys.exit(str(e))
    run = run_folder(REVIEW, day, a.nickname)
    recipes = {sex: os.path.join(DATA, "recipes", f"{sex}.json") for sex in bodies}
    if a.body:
        try:
            run_body(a.nickname, a.body, recipes[a.body], a.overrides, f"{run}/{a.body}", reused=reused.get(a.body), render=a.render)
        except StageFailed as e:
            sys.exit(str(e))
        print("done:", f"{run}/{a.body}")
        return
    _, failures = run_both(a.nickname, a.overrides, run, recipes, reused=reused, render=a.render)
    if failures:
        sys.exit("\n".join(f"{sex}: {e}" for sex, e in failures.items()))
    print("done:", f"{run}/{PAIR_NAME}")


if __name__ == "__main__":
    main()
