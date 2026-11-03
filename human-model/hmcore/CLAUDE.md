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
- `fit.py`: placing a bone: segment and box maps, winding number, skin profiles.
- `skeleton.py`: fits the whole skeleton to one individual.
- `parametric.py`: hyoid and larynx, which no allowed mesh covers.
- `jaw.py`: jaw opening as rotation, then sliding.
- `joints.py`: joint limits, measured and declared.
- `gait.py`: mean walking cycle from Fukuchi 2018.
- `muscle.py`: spindles, volume, landmarks to points, Rajagopal muscles.
- `softtissue.py`: skin displacement per muscle.
- `bodyskin.py`: breath and muscle-belly shapes.

## Key facts / gotchas

- A scan isn't centred on x=0, so "medial" and "midline" are always relative to the bone pair: `bonelib.py:30`.
- CT arms are almost always clipped by the sides of the field of view: `ctbones.py` `touches_scan_edge`, `measures.py` `COMPLETE_MIN`.
- Lips tear with cotangent weights, so `softtissue.py` uses uniform ones.
- Bulge is capped and off where no bone is near, or the chin swells: `softtissue.py`, search `NO_BONE`.
- Trunk width reads wrong near the armpit, where arms join the trunk: `skeleton.py`, search `armpit_limit`.
- Model frame: metres, the body faces -Y, its left is +X, up is +Z. Rotation only, never a mirror: `ctbones.py:5`.

## Touchpoints

`tools/`, `blender/` (reads the outputs), `G:\\mocap-studio-downloads\\models\\`.
