"""Runs the variations in variacoes.json, one .blend each, for Rafael to open (Rafael, 2026-11-15: experiments on a new body and
on the parameters; one .blend per variation, some variations his own).

    python3 human-model/investigations/pose-capture/experimentos.py [NOME ...] [--refazer] [--lista]

Runs in WSL with the system Python (no numpy): every step is a subprocess, Blender through blender_run.py, the GPU steps
through hm.sh --gpu. With no NOME, every variation whose .blend doesn't exist yet. --refazer runs them again; --lista prints
them with their state.

A variation changes only what it names; everything else is the base (tet_v11i). The steps, each kept in its own folder under
OUT/trabalho/ keyed by a hash of what it depends on, so variations that share a step share its result:
- corpo (only with "corpo"): rig_body.py, tissue_export.py, dress_rest.py on the given MPFB body;
- movimento: drive_capture.py (the levelled capture with contacts, --no-head), hand_pendulum.py, tissue_motion_dump.py;
- malha: tissue_mesh.py at rest, with the group, anatomy and mesh overrides;
- sim: tissue_cloth_sim.py with roupas.json overridden and its options;
- montagem: tissue_assemble.py, stage_video.py --no-frames, dress_assemble.py (2 mm Solidify) -> OUT/exp_<nome>.blend and
  abrir_exp_<nome>.bat;
- medidas: cloth_snag.py and the sim's report -> OUT/medidas/<nome>.json; OUT/resumo.txt has every variation's line.
A step that fails is recorded (which step, the log's last lines) in the variation's medidas and the next variation runs: for a
new body (experiment 1) that is where the process breaks.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
HM = REPO / "human-model"
R14 = Path("/mnt/g/mocap-studio-downloads/review/2026-11-14/pose_capture")
OUT = Path("/mnt/g/mocap-studio-downloads/review/2026-11-15/experimentos")
WORK = OUT / "trabalho"
CLOTHES = Path("/mnt/g/mocap-studio-downloads/apps/blender/5.2.2/blender-5.2.2-windows-x64/portable/extensions/.user/user_default/mpfb/data/clothes")
BLENDER_EXE = r"G:\mocap-studio-downloads\apps\blender\5.2.2\blender-5.2.2-windows-x64\blender.exe"
BASE = {
    "rig": R14 / "02_corpo_com_rig.blend",
    "rest": R14 / "11_tecidos/corpo_repouso.npz",
    "dressed": R14 / "17_vestida_repouso.blend",
    "cloth": R14 / "17_roupa/roupa_repouso.npz",
    "mesh": R14 / "11_tecidos/malha_v10_repouso_para_desenho/tecidos.npz",
    "mov_blend": R14 / "tet_v9_movimento/movimento_ganho_1_maos.blend",
    "bones": R14 / "tet_v9_movimento/ossos_ganho_1_maos.npz",
}
CONTACTS = R14 / "15_chao_e_contatos/contatos.npz"
PIECES = "blusinha,jeans"


class Falhou(Exception):
    def __init__(self, etapa, log):
        self.etapa, self.log = etapa, log


def key(*parts):
    return hashlib.sha1(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:10]


def run(cmd, log, etapa):
    """One step; its output to log; raises Falhou with the log's tail."""
    log.parent.mkdir(parents=True, exist_ok=True)
    t = time.time()
    with open(log, "a", encoding="utf-8") as f:
        f.write(f"\n$ {' '.join(map(str, cmd))}\n")
        f.flush()
        r = subprocess.run([str(c) for c in cmd], cwd=REPO, stdout=f, stderr=subprocess.STDOUT)
        f.write(f"[{etapa}: exit {r.returncode}, {time.time() - t:.0f} s]\n")
    if r.returncode != 0:  # blender_run.py passes --python-exit-code 1, so a script that raised fails here too
        raise Falhou(etapa, "\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-25:]))


def blender(blend, script, *args, log, etapa):
    cmd = [sys.executable, HM / "blender_run.py"]
    if blend:
        cmd += ["--blend", blend]
    run(cmd + [HERE / script, *args], log, etapa)


def gpu(script, *args, log, etapa):
    # inside the image the repository is /repo and the working folder: the script by its path relative to it
    run([HM / "hm.sh", "--gpu", "python", (HERE / script).relative_to(REPO), *args], log, etapa)


def done(folder):
    return (folder / "pronto").exists()


def mark(folder):
    (folder / "pronto").write_text(time.strftime("%Y-%m-%d %H:%M:%S"))


def set_dotted(d, path, value):
    """'pecas.*.atrito' -> every piece's atrito; 'punho.frequencia_hz' -> d['punho']['frequencia_hz']."""
    head, _, rest = path.partition(".")
    if not rest:
        d[head] = value
        return
    targets = [v for k, v in d.items() if isinstance(v, dict) and not k.startswith("_")] if head == "*" else [d[head]]
    for t in targets:
        set_dotted(t, rest, value)


def stage_body(v):
    if not v.get("corpo"):
        return {k: BASE[k] for k in ("rig", "rest", "dressed", "cloth")}, False
    src = Path(v["corpo"])
    f = WORK / f"corpo_{key(str(src), src.stat().st_mtime)}"
    log = f / "log.txt"
    out = {"rig": f / "corpo_com_rig.blend", "rest": f / "corpo_repouso.npz", "dressed": f / "vestida_repouso.blend",
           "cloth": f / "roupa_repouso.npz"}
    if not done(f):
        f.mkdir(parents=True, exist_ok=True)
        blender(src, "rig_body.py", out["rig"], f / "verificacao_rig", log=log, etapa="corpo: rig (rig_body.py)")
        blender(out["rig"], "tissue_export.py", out["rest"], log=log, etapa="corpo: exportar repouso (tissue_export.py)")
        blender(out["rig"], "dress_rest.py", CLOTHES, out["dressed"], out["cloth"], 3, HERE / "roupas.json", log=log,
                etapa="corpo: vestir em repouso (dress_rest.py)")
        mark(f)
    return out, True


def stage_motion(v, body, custom_body):
    m = v.get("movimento", {})
    if not m and not custom_body:
        return BASE["mov_blend"], BASE["bones"]
    sigma = m.get("suavizacao_quadros", 2)
    f = WORK / f"movimento_{key(str(body['rig']), m)}"
    log = f / "log.txt"
    final = f / ("movimento.blend" if m.get("maos") == "capturadas" else "movimento_maos.blend")
    bones = f / "ossos.npz"
    if not done(f):
        f.mkdir(parents=True, exist_ok=True)
        args = [CONTACTS, f / "movimento.blend", f / "relatorio_retarget.json", sigma, "--no-head"]
        if m.get("sem_pes_presos"):
            args.append("--no-pin")
        blender(body["rig"], "drive_capture.py", *args, log=log, etapa="movimento: captura no corpo (drive_capture.py)")
        if m.get("maos") != "capturadas":
            hands = json.loads((HERE / "maos.json").read_text(encoding="utf-8"))
            for p, val in m.get("maos_json", {}).items():
                set_dotted(hands, p, val)
            (f / "maos.json").write_text(json.dumps(hands, indent=1, ensure_ascii=False), encoding="utf-8")
            blender(f / "movimento.blend", "hand_pendulum.py", final, f / "relatorio_maos.json", f / "maos.json", log=log,
                    etapa="movimento: mãos pêndulo (hand_pendulum.py)")
        blender(final, "tissue_motion_dump.py", bones, log=log, etapa="movimento: ossos por quadro (tissue_motion_dump.py)")
        mark(f)
    return final, bones


def stage_mesh(v, body, custom_body):
    over = v.get("malha", {})
    if not over and not custom_body:
        return BASE["mesh"]
    f = WORK / f"malha_{key(str(body['rest']), over)}"
    if not done(f):
        f.mkdir(parents=True, exist_ok=True)
        gpu("tissue_mesh.py", body["rest"], f, *[f"{k}={json.dumps(val) if isinstance(val, list) else val}" for k, val in over.items()],
            log=f / "log.txt", etapa="malha de tetraedros (tissue_mesh.py)")
        mark(f)
    return f / "tecidos.npz"


def stage_sim(v, body, mesh, bones):
    roupa = v.get("roupa", {})
    opts = {"pano_pano": 0, **v.get("sim", {})}
    if v.get("quadros"):
        opts["frames"] = v["quadros"]
    params = json.loads((HERE / "roupas.json").read_text(encoding="utf-8"))
    for p, val in roupa.items():
        set_dotted(params["solver_tetraedros"], p, val)
    f = WORK / f"sim_{key(str(mesh), str(bones), str(body['cloth']), params, opts)}"
    if not done(f):
        f.mkdir(parents=True, exist_ok=True)
        (f / "roupas.json").write_text(json.dumps(params, indent=1, ensure_ascii=False), encoding="utf-8")
        gpu("tissue_cloth_sim.py", mesh, bones, body["cloth"], f / "roupas.json", f / "sim", *[f"{k}={val}" for k, val in opts.items()],
            f"corpo={body['rest']}", log=f / "log.txt", etapa="simulação de tecido e roupa (tissue_cloth_sim.py)")
        mark(f)
    return f


def stage_assembly(v, body, mesh, mov_blend, sim):
    name = "exp_" + v["nome"]
    f = WORK / f"montagem_{v['nome']}"
    log = f / "log.txt"
    if f.exists():
        shutil.rmtree(f)
    f.mkdir(parents=True)
    blender(mov_blend, "tissue_assemble.py", mesh, sim / "sim/pele.pc2", f / "pele.blend", log=log, etapa="montagem: pele (tissue_assemble.py)")
    blender(f / "pele.blend", "stage_video.py", f / "x", f / "cenario.blend", "--no-frames", log=log, etapa="montagem: cenário (stage_video.py)")
    blender(f / "cenario.blend", "dress_assemble.py", body["dressed"], sim / "sim", PIECES, OUT / f"{name}.blend", sim / "roupas.json", log=log,
            etapa="montagem: roupa (dress_assemble.py)")
    (OUT / f"{name}.blend1").unlink(missing_ok=True)
    (OUT / f"abrir_{name}.bat").write_bytes(f'@echo off\r\nstart "" "{BLENDER_EXE}" "%~dp0{name}.blend"\r\n'.encode())


def measure(v, body, mesh, sim):
    f = sim / "sim"
    rep = json.loads((f / "relatorio.json").read_text(encoding="utf-8"))
    frames = [x for x in rep["frames"] if isinstance(x["quadro"], int)]

    def med(get):
        vals = sorted(get(x) for x in frames)
        return vals[len(vals) // 2] if vals else None

    out = {"ms_por_quadro": rep["ms_per_frame_median"], "quadros": rep["dance_frames"],
           "blusa_esticado_p95_pct": med(lambda x: x["blusinha"]["esticado_p95_pct"]),
           "blusa_esticado_max_pct": med(lambda x: x["blusinha"]["esticado_max_pct"]),
           "jeans_esticado_p95_pct": med(lambda x: x["jeans"]["esticado_p95_pct"]),
           "blusa_dentro_da_pele": med(lambda x: x["blusinha"]["dentro_da_pele"]),
           "pele_dentro_de_outra_parte": med(lambda x: x["pele_dentro_de_outra_parte"]),
           "tetraedros_invertidos": med(lambda x: x["inverted_tets"]),
           "volume_minimo_pct": min(x["volume_kept_pct"] for x in frames)}
    snag = WORK / f"enrosco_{sim.name}.json"
    if not snag.exists():
        gpu("cloth_snag.py", mesh, body["cloth"], f, "blusinha", snag, log=sim / "log.txt", etapa="medida: enrosco (cloth_snag.py)")
    s = json.loads(snag.read_text(encoding="utf-8"))["resumo"]
    out["meia_volta_antebraco_E_D"] = [s["esq"]["quadros_volta_maior_que_180"], s["dir"]["quadros_volta_maior_que_180"]]
    return out


def run_variation(v):
    t0 = time.time()
    res = {"nome": v["nome"], "area": v.get("area", ""), "o_que": v.get("o_que", ""), "inicio": time.strftime("%H:%M:%S")}
    try:
        body, custom = stage_body(v)
        mov_blend, bones = stage_motion(v, body, custom)
        mesh = stage_mesh(v, body, custom)
        sim = stage_sim(v, body, mesh, bones)
        stage_assembly(v, body, mesh, mov_blend, sim)
        res["medidas"] = measure(v, body, mesh, sim)
        res["blend"] = f"exp_{v['nome']}.blend"
    except Falhou as e:
        res["falhou_em"] = e.etapa
        res["log"] = e.log
    except Exception as e:  # a missing file and the like: recorded as where it broke, the next variation still runs
        res["falhou_em"] = f"executor: {type(e).__name__}"
        res["log"] = str(e)
    res["minutos"] = round((time.time() - t0) / 60, 1)
    (OUT / "medidas").mkdir(parents=True, exist_ok=True)
    (OUT / "medidas" / f"{v['nome']}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    return res


def summary(variations):
    lines = ["Experimentos (variações de variacoes.json): uma linha por variação; a base é base_v11i.",
             "esticado = estiramento da blusa, p95 / máximo (mediana dos quadros, %); meia volta = quadros com a blusa dando mais de meia volta no antebraço E / D;",
             "invertidos = tetraedros invertidos (mediana, de 3,3 milhões); ms = tempo por quadro.", ""]
    for v in variations:
        p = OUT / "medidas" / f"{v['nome']}.json"
        if not p.exists():
            lines.append(f"{v['nome']:24s} (ainda não rodou)  {v.get('o_que', '')}")
            continue
        r = json.loads(p.read_text(encoding="utf-8"))
        if "falhou_em" in r:
            lines.append(f"{v['nome']:24s} FALHOU em: {r['falhou_em']}")
            continue
        m = r["medidas"]
        lines.append(f"{v['nome']:24s} esticado {m['blusa_esticado_p95_pct']:5.1f} / {m['blusa_esticado_max_pct']:6.1f}  "
                     f"meia volta {m['meia_volta_antebraco_E_D'][0]:3d} / {m['meia_volta_antebraco_E_D'][1]:3d}  "
                     f"invertidos {m['tetraedros_invertidos']:6d}  ms {m['ms_por_quadro']:5.0f}  {r['blend']}")
    (OUT / "resumo.txt").write_bytes(("\r\n".join(lines) + "\r\n").encode("utf-8"))


def main(argv):
    cat = json.loads((HERE / "variacoes.json").read_text(encoding="utf-8"))["variacoes"]
    names = [a for a in argv if not a.startswith("--")]
    OUT.mkdir(parents=True, exist_ok=True)
    if "--lista" in argv:
        for v in cat:
            state = "pronta" if (OUT / f"exp_{v['nome']}.blend").exists() else "pendente"
            print(f"{v['nome']:24s} {state:8s} {v.get('o_que', '')}")
        return
    missing = set(names) - {v["nome"] for v in cat}
    if missing:
        sys.exit(f"não há essas variações em variacoes.json: {sorted(missing)}")
    if names:
        todo = [v for v in cat if v["nome"] in names]
    else:
        todo = [v for v in cat if "--refazer" in argv or not (OUT / f"exp_{v['nome']}.blend").exists()]
    for v in todo:
        print(f"{time.strftime('%H:%M:%S')} {v['nome']} ...", flush=True)
        r = run_variation(v)
        print(f"{time.strftime('%H:%M:%S')} {v['nome']}: " + (f"FALHOU em {r['falhou_em']}" if "falhou_em" in r else f"ok ({r['minutos']} min)"), flush=True)
        summary(cat)
    summary(cat)


if __name__ == "__main__":
    main(sys.argv[1:])
