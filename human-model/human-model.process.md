# human-model — process

What `build_model.py` does, stage by stage.

## 1. export (Blender)
`blender/export_human.py`: MPFB builds the skin and the Rigify metarig from the recipe's macros. Writes the skin's vertices and polygons, the bones' heads and tails, and the vertex groups.

## 2. bones (Docker)
`tools/build_bones.py`: `hmcore/bonelib.py` meshes the CT labels of the sex's donor (`bonelib.py:13`), and caches them on G:. `hmcore/skeleton.py` fits each bone to this individual; `tools/spec.py` adds the jaw table and joint limits.

## 3. assemble (Blender)
`blender/assemble.py`: rebuilds the human, moves the thigh heads into the sockets, adds `hm_jaw`, `hm_hyoid`, `hm_larynx`, `hm_sternum` and 24 `hm_rib_*` bones, parents every bone mesh, and adds `HM_controls` with its drivers. Saves `<name>.blend`.
