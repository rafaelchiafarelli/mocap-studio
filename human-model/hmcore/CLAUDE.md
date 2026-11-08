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
- `body.py`: the whole body in layers at rest: cut at neck (along the rig's head weights), wrists and ankles, plastic-surgery zones, bone, muscle, fat, skin band and cavity. Takes the GPU mesh class as an argument, so it imports without Warp.
- `skinfit.py`: pushes the skin out where a bone has less tissue over it than declared; a bone that would need more than the most push is left alone as misplaced.
- `meshgpu.py`: inside-or-outside and closest point for millions of points, on Warp's meshes. GPU image only.
- `layers.py`: a limb from the inside out: skin patch, voxels labelled bone, muscle or fat, tetrahedra, and the skin tied to them. [docs/muscle-physics.md](../docs/muscle-physics.md#experiment-2-a-thigh-built-from-the-inside-out).

## Key facts / gotchas

- A scan isn't centred on x=0, so "medial" and "midline" are always relative to the bone pair: `bonelib.py:33`.
- CT arms are almost always clipped by the sides of the field of view: `ctbones.py` `touches_scan_edge`, `measures.py` `COMPLETE_MIN`.
- Lips tear with cotangent weights, so `softtissue.py` uses uniform ones.
- Bulge is capped and off where no bone is near, or the chin swells: `softtissue.py`, search `NO_BONE`.
- Trunk width reads wrong near the armpit, where arms join the trunk: `skeleton.py`, search `armpit_limit`.
- The CT sternum's highest point lies off the midline, so `anchors["sternum_top"]` takes the sternum's middle x: `skeleton.py:298`.
- `fit.SkinDepth` signs a depth by the nearest sample's triangle normal, so it is off by up to half its spacing, and wrong in deep creases: in the groin for 1 to 3% of the pelvis's points, up to 90 mm deep. `SkinDepth.inside` is the exact test (winding number): `fit.py:150`.
- `fit.settle` checks each sampled point's sign once by the exact test: a point that starts inside and stays more than `DEEP` (30 mm) from the skin counts as inside, and other points where the tests disagree are left out. With `exact`, points nearer than `DEEP` are signed by the exact test on every try, as the pelvis needs: `fit.py:161`.
- `fit.settle` searches a grid, so a bone with three moves costs about 2,000 skin queries; settling takes about 4 of the build's minutes, the pelvis's exact signs 2 more: `fit.py:164`.
- Scaled from the hips alone, the pelvis sat 2 to 3 cm behind the spine, the sacrum through the skin; it moves forward, and may tilt about the sockets, until 6 mm of tissue covers it, the hip joints with it (`anchors.pelvis_move`): `skeleton.py:310`.
- The shoulder girdle hangs from the CT humerus's head centre (a fitted sphere) on the rig's shoulder joint. The scapula's points nearest the humerus's end are the acromion's underside, 25 mm above the head, not the glenoid; hung from them the girdle sat 4 to 5 cm low: `skeleton.py:178`.
- MPFB's shoulder joint sits low: the girdle and the rig's `upper_arm` heads go up together (`anchors.rig_edits`) until the acromion lies 8 mm under the shoulder's skin, by the mean of both sides so the shoulders stay level (19 mm on the neutral woman): `skeleton.py:161`.
- The clavicle is stretched to the placed acromion with a 3 mm joint before it settles, and settling may not move its lateral end more than 4 mm (`fit.settle`'s `keep`): `skeleton.py:428`.
- `layers.cut_patch` keeps whole triangles only, so a patch ends at the ring of vertices short of each cut, about 3 cm on the thigh. `layers.measure` counts between the rings: `layers.py:230`.
- `body.zones` reads the trunk's zone by height against the rib cage's bottom and the hip bones' top, and front, back or side from the trunk's middle; the breast zone is wherever the rig's breast bone is nearest, which is most of the front of the chest: `body.py:103`.
- BMF's left leg comes wound inward in the source file itself, so `bonelib.bmf_library` turns every BMF mesh outward (`fit.outward`). `body.build` and the tools still turn every bone outward before use, since builds made earlier have the left leg inside out, and Warp's winding number then calls their inside outside: `body.py:193`.
- `skinfit.spread` shrinks the push at each step (`falloff`); without it the push spread over the whole skin and grew the bust 3.2 cm: `skinfit.py:23`.
- `layers.cut_patch` takes `side=None` to keep both sides, as `body.cut_skin` does.
- `body.near_a_cut` takes each cut's plane from the cut skin's own border (`body.cut_planes`), as `skinfit` and `body_layers.py` pass it; without planes it falls back to the joints' planes, which since the head's cut follows the rig's weights counted the neck's C4 as 44 mm out: `body.py:78`.
- `body.cut_skin` cuts the head where the rig's weights pass from the head's bones to the neck's, and needs the export's vertex groups for it; without them it falls back to a plane at the head's base, which leaves a collar under the chin (bug `human-model/17`, fixed): `body.py:26`.
- `xpbd.Solver` needs tetrahedra in colours that share no node: `voxel_colours` for voxel tetrahedra, `colours` otherwise (`xpbd.py:129`). Within a colour the solve writes positions in place.
- `xpbd.Solver.drive` takes one transform per bone: `bone` for each driven node, `all_bone` for each node's nearest, whose motion its damping follows. With `all_rest` it damps motion relative to the carried frame. Without it damping acts like air and a carried body trails behind: `xpbd.py:176`.
- `xpbd.Solver.step` records a CUDA graph on its second call and replays it while `dt` and substeps stay the same (`xpbd.py:206`). Launching one by one cost more than the work.
- Model frame: metres, the body faces -Y, its left is +X, up is +Z. Rotation only, never a mirror: `ctbones.py:5`.

## Touchpoints

`tools/`, `blender/` (reads the outputs), `G:\\mocap-studio-downloads\\models\\`.
