"""Cuts the stretches listed by check_reference.py --csv into clips, and writes a page to say which clips are the same model, coming, going or from the side.

    python3 human-model/tools/cut_stretches.py STRETCHES.csv OUT_DIR

Runs in WSL, with FFmpeg and no Docker. OUT_DIR gets clips/, thumbs/, trechos.csv and tabela.html. Open tabela.html on Windows; what is typed there
stays in that browser and leaves it through its "Salvar CSV" button, as modelos.csv.
"""
from __future__ import annotations

import csv
import html
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

WORKERS = 6
DIRECTION = {"frente": "vindo", "costas": "indo", "lado": "lado"}  # the first guess, from the view the checker saw

PAGE = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trechos das modelos</title>
<style>
:root{--bg:#f6f6f4;--card:#fff;--text:#1c1c1a;--muted:#6b6b66;--line:#dcdcd6;--accent:#1f5f8b}
@media (prefers-color-scheme:dark){:root{--bg:#191917;--card:#242421;--text:#ececE6;--muted:#a3a39b;--line:#3a3a35;--accent:#7cb8e0}}
body{margin:0;padding:16px;background:var(--bg);color:var(--text);font:15px/1.4 system-ui,sans-serif}
h1{font-size:20px;margin:0 0 4px}p{margin:0 0 12px;color:var(--muted)}
.bar{position:sticky;top:0;z-index:2;background:var(--bg);padding:8px 0;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
button{padding:8px 14px;border:0;border-radius:6px;background:var(--accent);color:#fff;font:inherit;cursor:pointer}
#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px}
.c{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px}.c.off{opacity:.4}
video{width:100%;height:300px;object-fit:contain;background:#000;border-radius:4px}
.t{font-size:12px;color:var(--muted);margin:4px 0 6px;overflow-wrap:anywhere}
label{display:block;font-size:13px;margin-top:4px}
input[type=text],select{width:100%;box-sizing:border-box;padding:5px;font:inherit;background:var(--bg);color:var(--text);border:1px solid var(--line);border-radius:4px}
input[type=checkbox]{margin-right:6px}
</style></head><body>
<h1>Trechos das modelos</h1>
<p>Dê o mesmo nome às passagens da mesma modelo e confira a direção, que foi preenchida como um palpite. Depois clique em Salvar CSV.</p>
<div class="bar"><button id="save">Salvar CSV</button><label><input type="checkbox" id="pending">Só os sem modelo</label><span id="count"></span></div>
<datalist id="names"></datalist><div id="grid"></div>
<script>
const rows = __ROWS__;
const key = "trechos-modelos-v1";
let saved = {};
try { saved = JSON.parse(localStorage.getItem(key) || "{}"); } catch (e) {}
const stateOf = r => saved[r.clip] || (saved[r.clip] = {modelo: "", direcao: r.direcao, descartar: false, obs: ""});
function store() { try { localStorage.setItem(key, JSON.stringify(saved)); } catch (e) {} }
function names() {
  const all = [...new Set(rows.map(r => stateOf(r).modelo.trim()).filter(Boolean))].sort();
  const list = document.getElementById("names");
  list.textContent = "";
  all.forEach(n => { const o = document.createElement("option"); o.value = n; list.appendChild(o); });
}
function counts() {
  const done = rows.filter(r => stateOf(r).modelo.trim() || stateOf(r).descartar).length;
  document.getElementById("count").textContent = done + " de " + rows.length + " resolvidos";
}
function filter() {
  const only = document.getElementById("pending").checked;
  rows.forEach(r => { const s = stateOf(r); r.el.style.display = only && (s.modelo.trim() || s.descartar) ? "none" : ""; });
}
const grid = document.getElementById("grid");
rows.forEach(r => {
  const s = stateOf(r), c = document.createElement("div");
  c.className = "c" + (s.descartar ? " off" : "");
  r.el = c;
  const v = document.createElement("video");
  v.src = r.clip; v.poster = r.thumb; v.controls = true; v.preload = "none"; v.muted = true; v.loop = true;
  const t = document.createElement("div");
  t.className = "t";
  t.textContent = r.video + " · " + r.inicio + " a " + r.fim + " · " + r.duracao + " s · visto como " + r.vista + " · " + r.nota;
  const name = document.createElement("input");
  name.type = "text"; name.value = s.modelo; name.setAttribute("list", "names");
  name.oninput = () => { s.modelo = name.value; store(); counts(); };
  name.onchange = () => { names(); filter(); };
  const dir = document.createElement("select");
  ["vindo", "indo", "lado", "outro"].forEach(d => { const o = document.createElement("option"); o.value = d; o.textContent = d; dir.appendChild(o); });
  dir.value = s.direcao || "outro";
  dir.onchange = () => { s.direcao = dir.value; store(); };
  const obs = document.createElement("input");
  obs.type = "text"; obs.value = s.obs; obs.oninput = () => { s.obs = obs.value; store(); };
  const off = document.createElement("input");
  off.type = "checkbox"; off.checked = s.descartar;
  off.onchange = () => { s.descartar = off.checked; c.classList.toggle("off", off.checked); store(); counts(); filter(); };
  const field = (text, el) => { const l = document.createElement("label"); l.textContent = text; l.appendChild(el); return l; };
  const drop = document.createElement("label"); drop.appendChild(off); drop.appendChild(document.createTextNode("Descartar"));
  c.append(v, t, field("Modelo", name), field("Direção", dir), field("Observação", obs), drop);
  grid.appendChild(c);
});
names(); counts();
document.getElementById("pending").onchange = filter;
document.getElementById("save").onclick = () => {
  const q = x => '"' + String(x).replace(/"/g, '""') + '"';
  const lines = ["clip,video,inicio_s,fim_s,vista_detectada,direcao,modelo,descartar,observacao"];
  rows.forEach(r => { const s = stateOf(r); lines.push([r.clip, r.video, r.start, r.end, r.vista, s.direcao, s.modelo.trim(), s.descartar ? "sim" : "nao", s.obs].map(q).join(",")); });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob(["\\ufeff" + lines.join("\\r\\n")], {type: "text/csv;charset=utf-8"}));
  a.download = "modelos.csv";
  a.click();
};
</script></body></html>
"""


def stamp(seconds: float) -> str:
    return f"{int(seconds // 60):02d}:{int(seconds % 60):02d}"


def safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")[:40]


def cut(job) -> str | None:
    """The clip re-encoded so it starts and ends where the table says, and a still from its middle."""
    source, start, end, clip, thumb = job
    if not clip.exists():
        done = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", source, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                               "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(clip)], capture_output=True, text=True)
        if done.returncode:
            return f"{clip.name}: {done.stderr.strip()[:200]}"
    if not thumb.exists():
        done = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{(start + end) / 2:.3f}", "-i", source, "-frames:v", "1", "-vf", "scale=-2:480", "-q:v", "4", str(thumb)], capture_output=True, text=True)
        if done.returncode:
            return f"{thumb.name}: {done.stderr.strip()[:200]}"
    return None


def main(args) -> int:
    if len(args) != 2:
        print(__doc__)
        return 2
    table, out = Path(args[0]), Path(args[1])
    with open(table, newline="", encoding="utf-8") as f:
        stretches = list(csv.DictReader(f))
    (out / "clips").mkdir(parents=True, exist_ok=True)
    (out / "thumbs").mkdir(exist_ok=True)

    jobs, rows = [], []
    for n, s in enumerate(stretches, 1):
        start, end = float(s["start_s"]), float(s["end_s"])
        video = Path(s["video"])
        name = f"{n:04d}_{safe(video.stem)}_{int(start):05d}"
        clip, thumb = out / "clips" / f"{name}.mp4", out / "thumbs" / f"{name}.jpg"
        jobs.append((s["video"], start, end, clip, thumb))
        rows.append({"clip": f"clips/{name}.mp4", "thumb": f"thumbs/{name}.jpg", "video": video.name, "start": f"{start:.3f}", "end": f"{end:.3f}", "inicio": stamp(start), "fim": stamp(end),
                     "duracao": f"{end - start:.1f}", "vista": s["view"], "nota": s["verdict"], "direcao": DIRECTION.get(s["view"], "outro"), "avisos": s["warnings"]})

    with ThreadPoolExecutor(WORKERS) as pool:
        failures = [f for f in pool.map(cut, jobs) if f]
    with open(out / "trechos.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, ["clip", "video", "inicio", "fim", "duracao", "vista", "nota", "direcao", "avisos"], extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    (out / "tabela.html").write_text(PAGE.replace("__ROWS__", json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")), encoding="utf-8")

    print(f"{len(rows)} trechos, {len(failures)} falhas: {html.escape(str(out))}")
    for f in failures[:20]:
        print(f"  {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
