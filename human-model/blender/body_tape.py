"""A recipe's pattern-making measures and the height of each girth, from the Human Model Editor's tape, for tools/body_report.py.
Args: RECIPE.json OUT.json. The human stands on the floor at x = 0, as the build's export does, so the heights match the layered body."""
import json, sys
import bpy
import numpy as np
from bl_ext.user_default.hm_editor import human, tape

recipe_path, out = sys.argv[sys.argv.index("--") + 1:][:2]
recipe = json.load(open(recipe_path, encoding="utf-8"))
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
body = human.create(recipe)
human.settle(body)
values, lines, marks = tape.measure(human.tape_topology(body), human.all_verts(body))
labels = {m.key: (m.label, m.kind) for m in tape.MEASURES}
result = {"name": recipe["name"],
          "measures": {k: {"label": labels[k][0], "kind": labels[k][1], "cm": round(v * 100, 1)} for k, v in values.items()},
          "girth_z_m": {k: round(float(np.asarray(lines[k])[:, 2].mean()), 4) for k in values if labels[k][1] == "girth" and k in lines},
          "marks": {k: round(float(v), 4) for k, v in marks.items() if isinstance(v, (int, float)) or np.ndim(v) == 0 and not isinstance(v, dict)}}
with open(out, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=1, ensure_ascii=False)
print(json.dumps(result["girth_z_m"]))
