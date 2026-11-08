# The left leg's bone meshes are inside out

- **Symptom:** 30 bone meshes have a negative volume, their triangles wound inward: femur, patella, tibia, fibula and every foot bone of the left side.
- **Where:** `human-model/hmcore/bonelib.py`, `bmf_library`. Not a mirror in our code, as first thought: the BMF Toolkit's own file has the left leg's faces wound inward.
- **Reproduce:** the signed volume of each `<bone>__v`/`__f` pair in `<name>.bones.npz`. Found on 2026-11-07, when `body_layers.py`'s first runs had no left femur.
- **Impact:** anything using the bones' normals or winding: inside-or-outside tests, backface culling, outward offsets. `hmcore/body.py` reorients them before use (`body.outward`), so the layered body isn't affected. Renders look normal, since Blender shades both faces.
- **Status:** Fixed (2026-11-07) — fixes/0000d1/left-leg-bones-inside-out. `bmf_library` turns every BMF mesh outward as it reads it (`fit.outward`); a rebuild of the woman's bones has no mesh with a negative volume and the same containment (`models\hm-build\female_left-leg-outward\`).
