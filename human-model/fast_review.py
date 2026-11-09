"""One command from a recipe to a walked body in a Blender file, with no rendering, from WSL:
    python3 human-model/fast_review.py NICKNAME [--body female|male] [NAME=value ...]
With no --body, the woman and the man side by side, then both in <nickname>/mulher_e_homem.blend. If one fails the other finishes, the pair file isn't made, and the command says which stage failed and where its log is.
Stages, in order: build, tape, skin, layers, walk, dump, simulate, file. A NAME=value goes to the stage that knows it (VOXEL, fat.<zone> and
structure.<name> to layers; depth.<prefix> and MAX_PUSH_MM to skin; the tissue values, VOLUME_EVERY and BONE_TEST to simulate); one that no
stage knows stops the run before it starts. Results go to review/<today>/fast_review/<nickname>/<sex>/, with run.json and a log per stage.
A nickname already used that day is refused, so nothing is overwritten.
After both bodies, the run is linked into review/fast_review_todas.blend, in a strip of its own along X, unless --no-shared; fast_review.py NICKNAME --remove-shared takes it out without touching its own folder.
--character SEX=FILE takes that character's file (hmcore.character) instead of the recipe, on the new path: shape, build, outward, layers, walk, dump, simulate, file. --to STAGE stops after it; --check runs tools/character_check.py at the end, and writes check.md.
--render also makes the two videos of blender/body_walk_bake.py for each body, into its folder; off unless asked.
--from STAGE --base EARLIER starts at STAGE and reads the stages before it from the earlier run, not copied; run.json records where each part came from, through chains of reuse, and a base run that lacks a needed stage's output is refused before anything runs."""
import argparse, concurrent.futures, datetime, fcntl, glob, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REVIEW = "/mnt/g/mocap-studio-downloads/review"
DATA = os.path.join(HERE, "data")
BODIES = ("female", "male")
PAIR_NAME = "mulher_e_homem.blend"
SHARED_NAME = "fast_review_todas.blend"
LABELS = {"female": "mulher", "male": "homem"}
STAGES = ("build", "tape", "skin", "layers", "walk", "dump", "simulate", "file")
CHARACTER_STAGES = ("shape", "build", "outward", "layers", "walk", "dump", "simulate", "file")
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
    tissue = [k for k, v in _json(os.path.join(data, "body_tissue.json")).items() if not k.startswith("_") and not isinstance(v, dict)]
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


def prepare_character(path, sex, folder, data=DATA):
    """The character's sheet and bone targets, written where the stages read them. Refuses a character that doesn't check out or isn't of this sex."""
    sys.path.insert(0, HERE)
    from hmcore import bone_targets, character as ch
    try:
        c = ch.load(path)
    except ValueError as e:
        raise Refused(str(e)) from None
    if c["sex"] != sex:
        raise Refused(f"{path} is a {c['sex']} character, not {sex}")
    resolved = ch.resolve(c, data=data)
    targets = bone_targets.targets(resolved, c.get("bone_parameters"), base_cm=ch.base_measures(sex, data))
    os.makedirs(folder, exist_ok=True)
    with open(f"{folder}/sheet.json", "w", encoding="utf-8") as f:
        json.dump({"resolved": resolved, "character": c}, f, indent=1, ensure_ascii=False)
    with open(f"{folder}/targets.json", "w", encoding="utf-8") as f:
        json.dump(targets, f, indent=1)
    return c.get("name") or sex


def outputs(stage, folder, name):
    """What a stage leaves behind, by name."""
    return {"shape": {"sheet": f"{folder}/sheet.json", "targets": f"{folder}/targets.json", "recipe": f"{folder}/{name}.recipe.json", "shape": f"{folder}/shape.json"},
            "outward": {"skin_fit": f"{folder}/skin/{name}.skin_fit.npz", "fat_table": f"{folder}/skin/{name}.fat_table.json", "regions": f"{folder}/skin/{name}.regions.json", "skin_report": f"{folder}/skin/{name}.skin_fit.json"},
            "build": {"blend": f"{folder}/build/{name}.blend", "bones": f"{folder}/build/{name}.bones.npz", "build_dir": f"{folder}/build"},
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
    if stage == "shape":
        return [[*blender, f"{here}/blender/character_shape.py", made["sheet"], recipe, made["recipe"], made["shape"], name]]
    if stage == "outward":
        voxel = [o for o in routed.get("layers", ()) if o.startswith("VOXEL=")]
        return [[*gpu, f"{tools}/outward_skin.py", made["build_dir"], name, made["sheet"], f"{folder}/skin", *voxel]]
    if stage == "build":
        if "targets" in made:  # the character path: the recipe is the shape stage's, the bones come from the sheet
            return [[sys.executable, f"{here}/build_model.py", made["recipe"], f"{folder}/build", "--targets", made["targets"]]]
        return [[sys.executable, f"{here}/build_model.py", recipe, f"{folder}/build"]]
    if stage == "tape":
        return [[*blender, f"{here}/blender/body_tape.py", recipe, f"{folder}/tape.json"]]
    if stage == "skin":
        return [[*gpu, f"{tools}/skin_over_bone.py", made["build_dir"], name, made["tape"], f"{folder}/skin", *extra]]
    if stage == "layers":
        table = [f"FAT_TABLE={made['fat_table']}"] if "fat_table" in made else []
        return [[*gpu, f"{tools}/body_layers.py", made["build_dir"], name, f"{folder}/layers", f"SKIN={made['skin_fit']}", *table, *extra]]
    if stage == "walk":
        return [[*blender, "--blend", made["blend"], f"{here}/blender/walk.py", f"{here}/data/gait_walk.json", sex, f"{folder}/walk/{name}_walk.blend", WALK_CYCLES, WALK_STOP_STEPS]]
    if stage == "dump":
        return [[*blender, "--blend", made["walk"], f"{here}/blender/body_walk_dump.py", f"{folder}/dump.npz"]]
    if stage == "simulate":
        table = [f"REGIONS={made['regions']}"] if "regions" in made else []
        return [[*gpu, f"{tools}/body_walk.py", made["layers"], made["bones"], made["dump"], f"{folder}/simulate", "ABOVE_HIP=10", *table, *extra]]
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


def reusable(base, sex, start, chain=STAGES):
    """{stage: entry} for the stages before start, read from the earlier run. Raises Refused if a stage or one of its outputs is missing."""
    path = f"{base}/{sex}/run.json"
    if not os.path.exists(path):
        raise Refused(f"{base} has no run of the {sex} body")
    stages, out = _json(path).get("stages", {}), {}
    for stage in chain[:chain.index(start)]:
        entry = stages.get(stage)
        if not entry or entry.get("status") not in ("done", "reused"):
            raise Refused(f"{base}/{sex} didn't finish the stage {stage}")
        missing = [p for p in entry["output"].values() if not os.path.exists(p)]
        if missing:
            raise Refused(f"{base}/{sex}: the stage {stage}'s output is gone: {missing[0]}")
        out[stage] = {"status": "reused", "output": entry["output"], "origin": entry.get("origin", f"{base}/{sex}")}
    return out


def check_start(routed, start, chain=STAGES):
    """An override for a stage that won't run would silently do nothing, so it stops the run."""
    skipped = [s for s in chain[:chain.index(start)] if s in routed]
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


def run_body(nickname, sex, recipe, overrides, folder, execute=run_stage, reused=None, render=False, chain=STAGES, to=None, name=None):
    """Runs every stage of one body in order, past the ones in reused ({stage: entry} of an earlier run). Writes run.json after each. Raises StageFailed at the first that fails."""
    name = name or _json(recipe)["name"]
    routed = route(overrides, known_values(sex))
    os.makedirs(f"{folder}/logs", exist_ok=True)
    for sub in ("walk", "skin", "layers", "simulate", "build"):
        os.makedirs(f"{folder}/{sub}", exist_ok=True)
    record = {"nickname": nickname, "sex": sex, "commit": commit(), "recipe": recipe, "overrides": list(overrides), "routed": routed,
              "status": "running", "stages": {}}
    save_record(folder, record)
    made = {}
    for stage in chain:
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
        if stage == to:
            break
    record["status"] = "done"
    save_record(folder, record)
    return record


def pair_command(run, here=HERE):
    """body_walk_pair.py on the two bodies' files: the woman's skin and section, then the man's."""
    return [sys.executable, f"{here}/blender_run.py", "--blend", f"{run}/female/body_walk.blend", f"{here}/blender/body_walk_pair.py",
            f"{run}/male/body_walk.blend", f"{run}/{PAIR_NAME}", LABELS["female"], LABELS["male"]]


def shared_command(action, shared, nickname, pair=None, here=HERE):
    """blender/shared_file.py on the file with every run; an existing file is opened, a new one starts empty."""
    opened = ["--blend", shared] if os.path.exists(shared) else []
    return [sys.executable, f"{here}/blender_run.py", *opened, f"{here}/blender/shared_file.py", action, shared, nickname, *([pair] if pair else [])]


def locked_shared(root, argv, log, execute=run_stage):
    """One writer at a time on the shared file."""
    with open(f"{root}/fast_review_todas.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return execute(argv, log)


def run_both(nickname, overrides, run, recipes, execute=run_stage, reused=None, render=False, chain=STAGES, to=None, names=None):
    """Both bodies side by side, each only waiting for its own previous stage. Returns (record, failures: {sex: StageFailed})."""
    t0 = time.time()
    record = {"nickname": nickname, "commit": commit(), "overrides": list(overrides), "status": "running", "bodies": {}}
    save_record(run, record)
    failures = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(BODIES)) as pool:
        running = {sex: pool.submit(run_body, nickname, sex, recipes[sex], overrides, f"{run}/{sex}", execute, (reused or {}).get(sex), render, chain, to, (names or {}).get(sex)) for sex in BODIES}
    for sex, future in running.items():
        try:
            future.result()
            record["bodies"][sex] = {"status": "done", "folder": f"{run}/{sex}"}
        except StageFailed as e:
            failures[sex] = e
            record["bodies"][sex] = {"status": "failed", "stage": e.stage, "log": e.log, "folder": f"{run}/{sex}"}
    if failures:
        record["status"] = "failed"
    elif to is not None and to != chain[-1]:
        record["status"] = "done"
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
    ap.add_argument("--from", dest="start", default=None, help="the stage to start from; the ones before it are read from --base")
    ap.add_argument("--base", help="the earlier run's nickname, with --from")
    ap.add_argument("--render", action="store_true", help="also make the two videos of each body")
    ap.add_argument("--character", action="append", default=[], metavar="SEX=FILE", help="a character file instead of the recipe: the new path")
    ap.add_argument("--to", help="stop after this stage")
    ap.add_argument("--check", action="store_true", help="after a character's run, write check.md (tools/character_check.py)")
    ap.add_argument("--no-shared", action="store_true", help="leave this run out of the file with every run")
    ap.add_argument("--remove-shared", action="store_true", help="take this nickname out of the file with every run, and stop")
    ap.add_argument("overrides", nargs="*", metavar="NAME=value")
    a = ap.parse_args(argv)
    shared = f"{REVIEW}/{SHARED_NAME}"
    if a.remove_shared:
        code = locked_shared(REVIEW, shared_command("remove", shared, a.nickname), f"{REVIEW}/fast_review_todas.log")
        sys.exit(code)
    day = datetime.date.today().isoformat()
    bodies = (a.body,) if a.body else BODIES
    reused, characters = {}, {}
    try:
        check_nickname(a.nickname)
        for item in a.character:
            sex, eq, path = item.partition("=")
            if not eq or sex not in BODIES:
                raise Refused(f"{item}: expected female=FILE or male=FILE")
            characters[sex] = path
        chain = CHARACTER_STAGES if characters else STAGES
        if characters and set(characters) != set(bodies):
            raise Refused(f"give a character for each body being run: {', '.join(bodies)}")
        start = a.start or chain[0]
        if start not in chain or (a.to and a.to not in chain):
            raise Refused(f"the stages of this path are: {', '.join(chain)}")
        if (start != chain[0]) != bool(a.base):
            raise Refused("--from and --base go together")
        for sex in bodies:
            known = known_values(sex)
            if characters:
                known = {k: v for k, v in known.items() if k != "skin"}  # the new path has no push of the skin over the bones
            check_start(route(a.overrides, known), start, chain)
        refuse_used(REVIEW, day, a.nickname)
        if a.base:
            base = find_base(REVIEW, a.base)
            reused = {sex: reusable(base, sex, start, chain) for sex in bodies}
        run = run_folder(REVIEW, day, a.nickname)
        names = {sex: prepare_character(path, sex, f"{run}/{sex}") for sex, path in characters.items()}
    except Refused as e:
        sys.exit(str(e))
    recipes = {sex: os.path.join(DATA, "recipes", f"{sex}.json") for sex in bodies}
    if a.body:
        try:
            run_body(a.nickname, a.body, recipes[a.body], a.overrides, f"{run}/{a.body}", reused=reused.get(a.body), render=a.render, chain=chain, to=a.to, name=names.get(a.body))
        except StageFailed as e:
            sys.exit(str(e))
        print("done:", f"{run}/{a.body}")
        return
    _, failures = run_both(a.nickname, a.overrides, run, recipes, reused=reused, render=a.render, chain=chain, to=a.to, names=names)
    if failures:
        sys.exit("\n".join(f"{sex}: {e}" for sex, e in failures.items()))
    if a.check:
        for sex in bodies:
            subprocess.call([sys.executable, f"{HERE}/tools/character_check.py", f"{run}/{sex}", names.get(sex, sex)])
    if a.to and a.to != chain[-1]:
        print("done up to", a.to, ":", run)
        return
    print("done:", f"{run}/{PAIR_NAME}")
    if not a.no_shared and locked_shared(REVIEW, shared_command("add", shared, a.nickname, f"{run}/{PAIR_NAME}"), f"{run}/logs/shared.log") != 0:
        sys.exit(f"the run is done, but it wasn't added to the shared file; the log is {run}/logs/shared.log")


if __name__ == "__main__":
    main()
