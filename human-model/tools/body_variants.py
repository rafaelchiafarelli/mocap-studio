"""Bodies for every silhouette, biotype and height, each built, walked and filmed apart, several at once (Rafael, 2026-11-12).

    python3 human-model/tools/body_variants.py OUT_DIR [--workers 8] [--silhouettes pera,oval] [--only NAME ...]

Each body: a recipe from the neutral woman, with the biotype's macros, fitted to the silhouette's waist/hip and shoulder/hip and the height (tools/fit_proportions.py);
then tools/animation_body.py with the medium wave only; then a plain video with front, side and back, in OUT_DIR/videos/<name>.mp4. OUT_DIR/indice.csv lists what each body reached.
Runs in WSL. The targets below are by eye: the silhouettes' waist/hip from data/silhouette_ratios.json, the shoulder/hip in the tape's terms, which read about 1.11 times the photos'.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
HEIGHTS = {"baixa": 155.0, "media": 165.0, "alta": 175.0}
SILHOUETTES = {  # waist/hip girth, shoulder/hip on the tape
    "ampulheta": (0.72, 1.42), "pera": (0.84, 1.31), "triangulo_invertido": (0.84, 1.54), "retangulo": (0.92, 1.42), "oval": (1.00, 1.42),
}
SILHOUETTE_WEIGHT = {"oval": 0.20, "retangulo": 0.10}  # added to the biotype's weight macro: with the sliders alone the oval stopped at a waist/hip of 0.82; the silhouette wins over the biotype where they disagree (Rafael, 2026-11-08)
LIMIT = 0.75  # the sliders' reach here; at 0.5 the pear, rectangle and oval came out alike
BIOTYPES = {"ectomorfo": {"weight": 0.30, "muscle": 0.35}, "mesomorfo": {"weight": 0.50, "muscle": 0.75}, "endomorfo": {"weight": 0.78, "muscle": 0.55}}
VIEWS = ("frente", "lado", "costas")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def run(command, log):
    with open(log, "a", encoding="utf-8") as f:
        done = subprocess.run(command, stdout=f, stderr=subprocess.STDOUT)
    return done.returncode == 0


def build(name, sil, bio, height, out):
    folder = out / name
    folder.mkdir(parents=True, exist_ok=True)
    log = folder / "log.txt"
    recipe = json.loads((HERE / "data" / "recipes" / "female.json").read_text(encoding="utf-8"))
    recipe["name"] = name
    recipe["macros"].update(BIOTYPES[bio])
    recipe["macros"]["weight"] = min(1.0, recipe["macros"]["weight"] + SILHOUETTE_WEIGHT.get(sil, 0.0))
    base = folder / "receita_base.json"
    base.write_text(json.dumps(recipe, indent=1), encoding="utf-8")
    fitted = folder / "receita.json"
    waist_hip, shoulder_hip = SILHOUETTES[sil]
    if not fitted.exists() and not run([sys.executable, str(HERE / "tools" / "fit_proportions.py"), str(base), str(fitted), str(folder / "ajuste"), f"height_cm={height}", f"waist_hip={waist_hip}", f"shoulder_hip={shoulder_hip}", f"limit={LIMIT}"], log):
        return name, "falhou no ajuste"
    if not (folder / "07_ondas" / "caminhada_final_ondas_media.blend").exists():
        if not run([sys.executable, str(HERE / "tools" / "animation_body.py"), str(fitted), str(folder), "--waves", "media"], log):
            return name, "falhou na cadeia"
    frames = folder / "quadros"
    blend = folder / "07_ondas" / "caminhada_final_ondas_media.blend"
    for view in VIEWS:
        if not (frames / view / "0144.png").exists():
            run([sys.executable, str(HERE / "blender_run.py"), "--blend", str(blend), str(HERE / "blender" / "simple_video.py"), str(frames / view), view], log)
    videos = out / "videos"
    videos.mkdir(exist_ok=True)
    label = lambda t: f"drawtext=fontfile={FONT}:text='{t}':x=12:y=12:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.5"
    inputs = sum([["-framerate", "24", "-i", str(frames / v / "%04d.png")] for v in VIEWS], [])
    graph = ";".join(f"[{i}]{label(v)}[v{i}]" for i, v in enumerate(VIEWS)) + ";" + "".join(f"[v{i}]" for i in range(len(VIEWS))) + f"hstack={len(VIEWS)},drawtext=fontfile={FONT}:text='{name}':x=(w-tw)/2:y=h-40:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.5"
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph, "-c:v", "libx264", "-crf", "25", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(videos / f"{name}.mp4")], log)
    return name, "ok"


def reached(folder):
    history = folder / "ajuste" / "historico.json"
    if not history.exists():
        return {}
    data = json.loads(history.read_text(encoding="utf-8"))
    last = data["rounds"][-1]
    return {"altura_cm": round(last["height"], 1), "cintura_quadril": round(last["waist_hip"], 3), "ombro_quadril": round(last["shoulder_hip"], 3),
            "meta_cintura_quadril": data["goals"]["waist_hip"], "meta_ombro_quadril": data["goals"]["shoulder_hip"]}


def main(args) -> int:
    if not args:
        print(__doc__)
        return 2
    out = Path(args[0])
    workers = int(args[args.index("--workers") + 1]) if "--workers" in args else 8
    only = set(args[args.index("--only") + 1:]) if "--only" in args else None
    jobs = [(f"{sil}_{bio}_{alt}", sil, bio, h) for sil in SILHOUETTES for bio in BIOTYPES for alt, h in HEIGHTS.items()]
    all_jobs = list(jobs)
    if "--silhouettes" in args:
        keep = set(args[args.index("--silhouettes") + 1].split(","))
        jobs = [j for j in jobs if j[1] in keep]
    if only:
        jobs = [j for j in jobs if j[0] in only]
    out.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(workers) as pool:
        results = list(pool.map(lambda j: build(*j, out), jobs))
    with open(out / "indice.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["corpo", "silhueta", "biotipo", "altura", "resultado", "altura_cm", "cintura_quadril", "meta_cintura_quadril", "ombro_quadril", "meta_ombro_quadril", "video"])
        for name, sil, bio, h in [j for j in all_jobs if j not in jobs and (out / j[0] / "ajuste" / "historico.json").exists()]:
            r = reached(out / name)
            w.writerow([name, sil, bio, h, "ok", r.get("altura_cm"), r.get("cintura_quadril"), r.get("meta_cintura_quadril"), r.get("ombro_quadril"), r.get("meta_ombro_quadril"), f"videos/{name}.mp4"])
        for (name, sil, bio, h), (_, status) in zip(jobs, results):
            r = reached(out / name)
            w.writerow([name, sil, bio, h, status, r.get("altura_cm"), r.get("cintura_quadril"), r.get("meta_cintura_quadril"), r.get("ombro_quadril"), r.get("meta_ombro_quadril"), f"videos/{name}.mp4"])
    print("\n".join(f"{n}: {s}" for n, s in results))
    return 0 if all(s == "ok" for _, s in results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
