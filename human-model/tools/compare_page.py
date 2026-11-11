"""A page with the model's simple images beside the reference clips of the same view, for Rafael's verdict.

    python3 human-model/tools/compare_page.py STILLS_DIR MODELOS.csv OUT.html

STILLS_DIR holds simple_stills.py's images. The clips are named by MODELOS.csv and are found through it, so OUT.html must be opened where it can reach them (paths are relative to OUT.html). Runs in WSL."""
from __future__ import annotations

import csv
import html
import os
import sys
from pathlib import Path

VIEW = {"vindo": "frente", "indo": "costas", "lado": "lado"}
TITLE = {"frente": "De frente (vindo)", "costas": "De costas (indo)", "lado": "De lado"}


def main(args) -> int:
    if len(args) != 3:
        print(__doc__)
        return 2
    stills, table, out = Path(args[0]), Path(args[1]), Path(args[2])
    base = table.parent
    groups: dict[str, list] = {v: [] for v in VIEW.values()}
    with open(table, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            view = VIEW.get(row["direcao"])
            if view and row["descartar"] != "sim" and row["modelo"].strip():
                groups[view].append(row)
    rel = lambda p: os.path.relpath(p, out.parent).replace(os.sep, "/")
    parts = []
    for view, rows in groups.items():
        images = "".join(f'<figure><img loading="lazy" src="{html.escape(rel(p))}" alt=""><figcaption>{html.escape(p.stem)}</figcaption></figure>' for p in sorted(stills.glob(f"*_{view}_*.png")))
        clips = "".join(f'<figure><video muted loop controls preload="none" poster="{html.escape(rel(base / r["clip"].replace("clips/", "thumbs/").replace(".mp4", ".jpg")))}" src="{html.escape(rel(base / r["clip"]))}"></video><figcaption>modelo {html.escape(r["modelo"].strip())}</figcaption></figure>' for r in rows[:18])
        parts.append(f'<h2>{TITLE[view]}</h2><h3>Nosso modelo</h3><div class="g">{images}</div><h3>Referências ({len(rows)})</h3><div class="g">{clips}</div>')
    out.write_text("""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Modelo e referências</title><style>
:root{--bg:#f6f6f4;--text:#1c1c1a;--muted:#6b6b66}@media (prefers-color-scheme:dark){:root{--bg:#191917;--text:#ececE6;--muted:#a3a39b}}
body{margin:0;padding:16px;background:var(--bg);color:var(--text);font:15px/1.4 system-ui,sans-serif}h1{font-size:20px;margin:0 0 4px}h2{font-size:18px;margin:24px 0 4px}h3{font-size:14px;color:var(--muted);margin:10px 0 6px}
.g{display:flex;flex-wrap:wrap;gap:8px}figure{margin:0}img,video{height:340px;display:block;background:#000;border-radius:4px}figcaption{font-size:12px;color:var(--muted)}</style></head><body>
<h1>Modelo e referências</h1>""" + "".join(parts) + "</body></html>", encoding="utf-8")
    print(out, {k: len(v) for k, v in groups.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
