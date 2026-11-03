"""Builds one individual from a recipe, from WSL: python3 build_model.py RECIPE.json OUT_DIR [--from STAGE]
Stages: export, bones, muscles, fields, assemble. Writes OUT_DIR/<name>.blend. Docker runs hmcore, Windows Blender runs blender/."""
import argparse, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
STAGES = ["export", "bones", "muscles", "fields", "assemble"]


def docker(*a):
    subprocess.check_call([os.path.join(HERE, "hm.sh"), "python", *a])


def blender(*a):
    subprocess.check_call([sys.executable, os.path.join(HERE, "blender_run.py"), *a], stdout=subprocess.DEVNULL)


def rel(p):
    return os.path.relpath(p, os.path.join(HERE, ".."))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("recipe")
    ap.add_argument("out")
    ap.add_argument("--from", dest="start", default="export", choices=STAGES)
    ap.add_argument("--to", default="assemble", choices=STAGES)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    r = json.load(open(a.recipe))
    name, sex = r["name"], r["sex"]
    out = os.path.abspath(a.out)
    recipe = os.path.abspath(a.recipe)
    base = os.path.join(out, name)
    tools = "human-model/tools"
    cache = "/mnt/g/mocap-studio-downloads/models/hm-cache"
    os.makedirs(cache, exist_ok=True)
    for stage in STAGES[STAGES.index(a.start):STAGES.index(a.to) + 1]:
        print("==", stage, flush=True)
        if stage == "export":
            blender(f"{HERE}/blender/export_human.py", recipe, f"{base}.export.npz", f"{base}.export.json")
        elif stage == "bones":
            docker(f"{tools}/build_bones.py", sex, f"{base}.export.npz", f"{base}.export.json", f"{base}.bones.npz", cache)
            docker(f"{tools}/spec.py", f"{base}.bones.npz", sex)
        elif stage == "muscles" and os.path.exists(f"{HERE}/tools/build_muscles.py"):
            docker(f"{tools}/build_muscles.py", f"{base}.export.npz", f"{base}.export.json", f"{base}.bones.npz", f"{base}.muscles.npz", sex)
        elif stage == "fields" and os.path.exists(f"{HERE}/tools/build_fields.py"):
            docker(f"{tools}/build_fields.py", f"{base}.export.npz", f"{base}.export.json", f"{base}.bones.npz", f"{base}.muscles.npz", f"{base}.fields.npz")
        elif stage == "assemble":
            args = [f"{HERE}/blender/assemble.py", recipe, f"{base}.bones.npz", f"{base}.blend"]
            if os.path.exists(f"{base}.muscles.npz"):
                args.append(f"{base}.muscles.npz")
            if os.path.exists(f"{base}.fields.npz"):
                args.append(f"{base}.fields.npz")
            blender(*args)
    print("built", f"{base}.blend")


if __name__ == "__main__":
    main()
