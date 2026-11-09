"""What the human model's long runs are doing now, from WSL, refreshing until Ctrl+C: python3 human-model/tools/hm_status.py [--once] [--every SECONDS] [--hours N]
Reads only what is already there: Docker's containers, Blender's process, nvidia-smi and the output files on G:. A stage counts as done if its output was written in the last N hours."""
import argparse, datetime, glob, json, os, shutil, subprocess, time

ROOT = "/mnt/g/mocap-studio-downloads"
BUILD, REVIEW = f"{ROOT}/models/hm-build/*", f"{ROOT}/review/*/*"
FAST_REVIEW = f"{ROOT}/review/*/fast_review/*/*/run.json"
# stage, words of its command line, where its output lands
STAGES = (
    ("Ossos", ("build_bones", "spec.py"), [f"{BUILD}/*.bones.npz"]),
    ("Músculos", ("build_muscles",), [f"{BUILD}/*.muscles.json"]),
    ("Campos da pele", ("build_fields",), [f"{BUILD}/*.fields.npz"]),
    ("Modelo (Blender)", ("assemble.py", "export_human"), [f"{BUILD}/*.blend"]),
    ("Empurrão da pele", ("skin_over_bone",), [f"{REVIEW}/*.skin_fit.json"]),
    ("Camadas", ("body_layers",), [f"{REVIEW}/*.body_layers.npz"]),
    ("Caminhada (Blender)", ("blender\\walk.py", "blender/walk.py"), [f"{BUILD}/*_walk_review.blend", f"{BUILD}/*_walk_slow_stop.blend"]),
    ("Extrair movimento", ("body_walk_dump",), [f"{REVIEW}/*dump.npz", f"{REVIEW}/*/*dump.npz"]),
    ("Simulação na GPU", ("tools/body_walk.py",), [f"{REVIEW}/body_walk.json", f"{REVIEW}/*/body_walk.json"]),
    ("Vídeos", ("body_walk_bake",), [f"{REVIEW}/body_walk.blend", f"{REVIEW}/*/body_walk.blend"]),
    ("Arquivo com os dois", ("body_walk_pair",), [f"{REVIEW}/mulher_e_homem.blend"]),
)


def run(*cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def ago(seconds):
    seconds = int(seconds)
    return f"{seconds}s" if seconds < 60 else f"{seconds // 60}min" if seconds < 3600 else f"{seconds // 3600}h{seconds % 3600 // 60:02d}"


def processes():
    """(what it runs, how long) for each running container and Blender."""
    found = []
    for line in run("docker", "ps", "--no-trunc", "--format", "{{.RunningFor}}\t{{.Command}}").splitlines():
        since, command = line.split("\t", 1)
        found.append((command.strip('"'), since.replace(" ago", "")))
    for line in run("ps", "-eo", "etimes=,args=").splitlines():  # Windows' Blender doesn't show in WSL's process list: what runs it, blender_run.py, does
        seconds, args = line.strip().split(None, 1)
        if args.split()[0].endswith("python3") and "blender_run.py" in args:
            found.append((args[args.index("blender_run.py"):], ago(int(seconds))))
    return found


def script_of(command):
    """The script a command runs: its arguments name other stages' files, so only this says which stage it is."""
    return next((t for t in command.split() if t.endswith(".py") and not t.endswith("blender_run.py")), command)


def newest(patterns, skip=()):
    files = [f for p in patterns for f in glob.glob(p) if not any(s in f for s in skip)]
    return max(files, key=os.path.getmtime) if files else None


def gpu():
    out = run("nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu", "--format=csv,noheader,nounits").strip()
    if not out:
        return "sem leitura do nvidia-smi"
    use, used, total, temp = [x.strip() for x in out.split(",")]
    return f"{use}% de uso · {int(used) / 1024:.1f} de {int(total) / 1024:.0f} GB · {temp}°C"


def last_line(path):
    with open(path, errors="replace") as f:
        lines = [x.strip() for x in f.read()[-4000:].splitlines() if x.strip()]
    return lines[-1] if lines else "(vazio)"


def fast_review_lines(pattern, now, hours):
    """One line per run of fast_review.py whose run.json changed in the last hours: nickname, body, its stage and how far it got."""
    lines = []
    for path in sorted(glob.glob(pattern), key=os.path.getmtime):
        if now - os.path.getmtime(path) >= hours * 3600:
            continue
        try:
            with open(path, encoding="utf-8") as f:
                r = json.load(f)
        except (OSError, ValueError):
            continue
        done = sum(s.get("status") == "done" for s in r.get("stages", {}).values())
        current = next((k for k, s in r.get("stages", {}).items() if s.get("status") in ("running", "failed")), "")
        word = {"running": "▶", "done": "✓", "failed": "✗"}.get(r.get("status"), "?")
        lines.append(f"  {word} {r.get('nickname', '?')}/{r.get('sex', '?')}: {done}/{len(r.get('stages', {}))} etapas" + (f", {current}" if current else ""))
    return lines


def screen(hours):
    now, width = time.time(), shutil.get_terminal_size((100, 24)).columns
    cut = lambda s: s if len(s) <= width else s[:width - 1] + "…"
    running = processes()
    out = [f"Modelo humano · {datetime.datetime.now():%H:%M:%S}", ""]
    out.append("RODANDO AGORA")
    out += [cut(f"  {since:>12}  {command}") for command, since in running] or ["  nada"]
    out += ["", f"GPU: {gpu()}", "", f"ETAPAS (saídas das últimas {hours:g} h)"]
    for name, words, patterns in STAGES:
        active = next((since for command, since in running if any(w in script_of(command) for w in words)), None)
        file = newest(patterns, skip=("_walk_", ) if name == "Modelo (Blender)" else ())
        if active:
            state = f"▶ rodando há {active}"
        elif file and now - os.path.getmtime(file) < hours * 3600:
            state = f"✓ há {ago(now - os.path.getmtime(file))} · {os.path.basename(os.path.dirname(file))}"
        else:
            state = "·"
        out.append(cut(f"  {name:<22}{state}"))
    reviews = fast_review_lines(FAST_REVIEW, now, hours)
    if reviews:
        out += ["", "FAST REVIEW", *[cut(x) for x in reviews]]
    log = newest([f"{BUILD}/*log*.txt", f"{REVIEW}/*log*.txt", f"{REVIEW}/*/*log*.txt"])
    if log and now - os.path.getmtime(log) < hours * 3600:
        out += ["", cut(f"ÚLTIMO LOG: {os.path.basename(os.path.dirname(log))}/{os.path.basename(log)}, há {ago(now - os.path.getmtime(log))}"), cut(f"  {last_line(log)}")]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Status of the human model's long runs")
    ap.add_argument("--once", action="store_true", help="print once and leave")
    ap.add_argument("--every", type=float, default=5.0, help="seconds between refreshes")
    ap.add_argument("--hours", type=float, default=6.0, help="how recent an output must be to count as done")
    a = ap.parse_args()
    if a.once:
        print(screen(a.hours))
        return
    try:
        while True:
            text = screen(a.hours)
            print("\033[2J\033[H" + text + "\n\nCtrl+C para sair (o processamento continua)", flush=True)
            time.sleep(a.every)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
