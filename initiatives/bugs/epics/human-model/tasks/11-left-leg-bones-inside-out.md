# The left leg's bone meshes are inside out

- **Symptom:** 30 bone meshes have a negative volume, their triangles wound inward: femur, patella, tibia, fibula and every foot bone of the left side.
- **Where:** `human-model/hmcore/bonelib.py`: the left leg is the right leg's BMF Toolkit mesh mirrored, and a mirror reverses the winding unless the triangles are flipped too.
- **Reproduce:** the signed volume of each `<bone>__v`/`__f` pair in `<name>.bones.npz`. Found on 2026-11-07, when `body_layers.py`'s first runs had no left femur.
- **Impact:** anything using the bones' normals or winding: inside-or-outside tests, backface culling, outward offsets. `hmcore/body.py` reorients them before use (`body.outward`), so the layered body isn't affected. Renders look normal, since Blender shades both faces.
- **Status:** Open. Likely fix: flip the triangles where `bonelib.py` mirrors the leg.
