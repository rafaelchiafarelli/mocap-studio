"""Builds the whole animation body in order, each stage from the last one's file, keeping every stage's result: a clean body, its range of motion, joint corrections, a walk, folds.

    python3 human-model/tools/animation_body.py RECIPE.json OUT_DIR [--stop-after STAGE]

Stages (in OUT_DIR): 01_corpo, 02_amplitude, 03_correcoes, 04_caminhada, 05_dobras, 06_malha_fina, 07_ondas (with a soft, medium and strong step impact). Runs in WSL, calling Blender through blender_run.py. data/folds.json is rewritten from the clean body."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
BLENDER = HERE / "blender"
CYCLES, STOP_STEPS = "4", "2"


def run(*args, blend=None):
    command = [sys.executable, str(HERE / "blender_run.py")] + (["--blend", str(blend)] if blend else []) + [str(a) for a in args]
    done = subprocess.run(command, capture_output=True, text=True)
    useful = [l for l in done.stdout.splitlines() if not l.startswith(("[INFO", "Blender", "OBJ import", "Info:")) and l.strip()]
    if done.returncode:
        print("\n".join(useful[-20:]), done.stderr[-2000:])
        raise SystemExit(f"failed: {args[0]}")
    print("\n".join(useful[-16:]))


def main(args) -> int:
    if len(args) < 2:
        print(__doc__)
        return 2
    recipe, out = Path(args[0]).resolve(), Path(args[1])
    stop = args[args.index("--stop-after") + 1] if "--stop-after" in args else None
    names = ["01_corpo", "02_amplitude", "03_correcoes", "04_caminhada", "05_dobras", "06_malha_fina", "07_ondas"]
    d = {n: out / n for n in names}
    for p in d.values():
        p.mkdir(parents=True, exist_ok=True)
    body, rom, rom_json = d["01_corpo"] / "corpo.blend", d["02_amplitude"] / "amplitude.blend", d["02_amplitude"] / "amplitude.json"
    corrected, npz = d["03_correcoes"] / "amplitude_corrigida.blend", d["03_correcoes"] / "correcoes.npz"
    walk, fixed_walk = d["04_caminhada"] / "caminhada.blend", d["04_caminhada"] / "caminhada_corrigida.blend"
    run(BLENDER / "clean_body.py", recipe, body, d["01_corpo"] / "corpo.json")
    if stop == "01_corpo":
        return 0
    run(BLENDER / "range_of_motion.py", rom, rom_json, blend=body)
    run(BLENDER / "pose_corrections.py", rom_json, corrected, d["03_correcoes"] / "correcoes.json", npz, blend=rom)
    run(BLENDER / "walk.py", HERE / "data" / "gait_walk.json", "female", walk, CYCLES, STOP_STEPS, "smooth_stop", blend=body)
    relaxed = d["04_caminhada"] / "caminhada_maos_relaxadas.blend"
    run(BLENDER / "hands.py", relaxed, d["04_caminhada"] / "maos.json", blend=walk)
    clear_walk = d["04_caminhada"] / "caminhada_contato.blend"
    run(BLENDER / "arm_clearance.py", clear_walk, d["04_caminhada"] / "contato.json", blend=relaxed)
    run(BLENDER / "apply_corrections.py", npz, fixed_walk, blend=clear_walk)
    if stop == "04_caminhada":
        return 0
    folds = HERE / "data" / "folds.json"
    run(BLENDER / "fold_lines.py", folds, blend=body)
    run(BLENDER / "fold_apply.py", folds, d["05_dobras"] / "amplitude_com_dobras.blend", blend=corrected)
    run(BLENDER / "fold_apply.py", folds, d["05_dobras"] / "caminhada_com_dobras.blend", blend=fixed_walk)
    run(BLENDER / "fold_fine.py", folds, d["06_malha_fina"] / "amplitude_malha_fina.blend", blend=d["05_dobras"] / "amplitude_com_dobras.blend")
    run(BLENDER / "fold_fine.py", folds, d["06_malha_fina"] / "caminhada_malha_fina.blend", blend=d["05_dobras"] / "caminhada_com_dobras.blend")
    waves = d["07_ondas"]
    final = d["06_malha_fina"] / "caminhada_malha_fina.blend"
    run(BLENDER / "skin_dump.py", waves / "pele.npz", blend=final)
    for label, size in (("suave", 90), ("media", 300), ("forte", 800)):
        offsets = waves / f"ondas_{label}.npz"
        done = subprocess.run([str(HERE / "hm.sh"), "python", "human-model/tools/skin_waves.py", str(waves / "pele.npz"), str(offsets), f"impact.size={size}"], capture_output=True, text=True)
        print(label, "\n".join(line for line in done.stdout.splitlines() if "pico" in line))
        if done.returncode:
            print(done.stderr[-1500:])
            raise SystemExit("failed: skin_waves")
        run(BLENDER / "wave_bake.py", offsets, waves / f"caminhada_final_ondas_{label}.blend", blend=final)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
