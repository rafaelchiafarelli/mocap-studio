# hmcore — pure Python for the human model

**Role:** everything testable without Blender.

**Entry points:** imported by `tools/`; tests in `tests/`.

**Inputs → Outputs:** source meshes and the individual's export → fitted bones, tables.

## Files

- `remote_zip.py`: reads single members of a remote zip by byte range.
- `tsdata.py`: the CT dataset's metadata and coverage from the zip index.
- `measures.py`: ANSUR values and CT measurements, in metres.
- `ctbones.py`: labels to meshes in the model's frame; `split_mandible`.
- `sources.py`: `.vtp`, `.osim` and BMF `.mat` readers.
- `bonelib.py`: the bone library of one sex.
- `fit.py`: placing a bone: segment and box maps, winding number, skin profiles, `outward` winding; `SkinDepth`, signed depth under the skin on the CPU, and `settle`, the smallest rigid move that leaves a bone under enough tissue.
- `skeleton.py`: fits the whole skeleton to one individual; `settle_superficial` then moves the scapulae, clavicles and fibulae under the skin.
- `parametric.py`: hyoid and larynx, which no allowed mesh covers.
- `jaw.py`: jaw opening as rotation, then sliding.
- `joints.py`: joint limits, measured and declared.
- `gait.py`: mean walking cycle from Fukuchi 2018.
- `muscle.py`: spindles, volume, landmarks to points, Rajagopal muscles.
- `softtissue.py`: skin displacement per muscle.
- `bodyskin.py`: breath and muscle-belly shapes.
- `activation.py`: shapes or landmarks to muscle activations, with an effort penalty.
- `tongue.py`: tongue controls from phonemes.
- `retarget.py`: capture as bone directions, and capture quality measures.
- `morph.py`: real sizes to sliders; height so far.
- `retire.py`: a compact linear basis of the fields.
- `xpbd.py`: soft tissue as tetrahedra on the GPU, Neo-Hookean, XPBD, through Warp. GPU image only. [docs/muscle-physics.md](../docs/muscle-physics.md#the-gpu-what-tissue-costs).
- `body.py`: the whole body in layers at rest: cut at neck, wrists and ankles, plastic-surgery zones, bone, muscle, fat, skin band and cavity. Takes the GPU mesh class as an argument, so it imports without Warp.
- `skinfit.py`: pushes the skin out where a bone has less tissue over it than declared; a bone that would need more than the most push is left alone as misplaced.
- `meshgpu.py`: inside-or-outside and closest point for millions of points, on Warp's meshes. GPU image only.
- `layers.py`: a limb from the inside out: skin patch, voxels labelled bone, muscle or fat, tetrahedra, and the skin tied to them. [docs/muscle-physics.md](../docs/muscle-physics.md#experiment-2-a-thigh-built-from-the-inside-out).

## Key facts / gotchas

- A scan isn't centred on x=0, so "medial" and "midline" are always relative to the bone pair: `bonelib.py:33`.
- CT arms are almost always clipped by the sides of the field of view: `ctbones.py` `touches_scan_edge`, `measures.py` `COMPLETE_MIN`.
- Lips tear with cotangent weights, so `softtissue.py` uses uniform ones.
- Bulge is capped and off where no bone is near, or the chin swells: `softtissue.py`, search `NO_BONE`.
- Trunk width reads wrong near the armpit, where arms join the trunk: `skeleton.py`, search `armpit_limit`.
- The CT sternum's highest point lies off the midline, so `anchors["sternum_top"]` takes the sternum's middle x: `skeleton.py:261`.
- `fit.SkinDepth` signs a depth by the nearest sample's triangle normal, so it is off by up to half its spacing, and can be wrong in a deep crease; `fit.winding_number` is the exact test: `fit.py:145`.
- `fit.settle` searches a grid, so a bone with three moves costs about 2,000 skin queries; the settling takes about 4 of the build's minutes: `fit.py:156`.
- The clavicle's lateral end stops 17 to 20 mm short of the scapula's acromion (bug [human-model/18](../../initiatives/bugs/epics/human-model/tasks/18-clavicle-misses-acromion.md)).
- `layers.cut_patch` keeps whole triangles only, so a patch ends at the ring of vertices short of each cut, about 3 cm on the thigh. `layers.measure` counts between the rings: `layers.py:230`.
- `body.zones` reads the trunk's zone by height against the rib cage's bottom and the hip bones' top, and front, back or side from the trunk's middle; the breast zone is wherever the rig's breast bone is nearest, which is most of the front of the chest: `body.py:57`.
- BMF's left leg comes wound inward in the source file itself, so `bonelib.bmf_library` turns every BMF mesh outward (`fit.outward`). `body.build` and the tools still turn every bone outward before use, since builds made earlier have the left leg inside out, and Warp's winding number then calls their inside outside: `body.py:147`.
- `skinfit.spread` shrinks the push at each step (`falloff`); without it the push spread over the whole skin and grew the bust 3.2 cm: `skinfit.py:23`.
- `layers.cut_patch` takes `side=None` to keep both sides, as `body.cut_skin` does.
- `xpbd.Solver` needs tetrahedra in colours that share no node: `voxel_colours` for voxel tetrahedra, `colours` otherwise (`xpbd.py:126`). Within a colour the solve writes positions in place.
- `xpbd.Solver.drive` with `all_rest` damps motion relative to the carried frame. Without it damping acts like air and a carried body trails behind: `xpbd.py:173`.
- `xpbd.Solver.step` records a CUDA graph on its second call and replays it while `dt` and substeps stay the same (`xpbd.py:198`). Launching one by one cost more than the work.
- Model frame: metres, the body faces -Y, its left is +X, up is +Z. Rotation only, never a mirror: `ctbones.py:5`.

## Touchpoints

`tools/`, `blender/` (reads the outputs), `G:\\mocap-studio-downloads\\models\\`.
