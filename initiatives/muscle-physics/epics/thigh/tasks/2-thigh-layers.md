# 2. A thigh in layers: bone, muscle, fat, skin

**Asked by Rafael, 2026-11-07.** Build the body from the inside out, on one thigh: the femur, muscle around it, fat under the skin, and the skin over everything. Today the skin comes first and the bones are fitted inside it, which is why bones can come through it (bugs `human-model/2` and `human-model/9`).

## Contract

**In:** the neutral female build on `G:\mocap-studio-downloads\models\hm-build\female\`: the femur from `female.bones.npz`, the skin from `female.export.npz`, the thigh muscles' paths from `female.muscles.json`. The fat's thickness is **declared**, one value per zone (front, back, inner, outer, as in liposuction zones), set at the top of the script.

**Out:**
- `human-model/tools/thigh_layers.py`: cuts the left thigh between the gluteal fold and just above the knee, fills it with tetrahedra on a voxel grid (NumPy, no new dependency), and labels each one bone, muscle or fat. The skin is the MPFB vertices of that patch, each tied to the tetrahedron it sits in.
- `<name>.thigh_layers.npz`: the tetrahedra, their labels, the skin's ties.
- A `.blend` with each layer as its own object, to look at.

**Every intermediate is kept** (Rafael, 2026-11-07, "mesmo que errados"): the cut skin, the voxel grid, the labels before and after cleanup, each with a name that says what it is, on `G:\mocap-studio-downloads\review\<date>\`.

**Measured, and reported as measured:** the femur inside the skin everywhere, with its smallest distance to the skin; tetrahedra per layer; the fat's actual thickness against the declared one.

## Dependencies

Task 1 isn't needed: this runs on the CPU. `hmcore/bonelib.py` and the built female files.

## To agree with Rafael before implementing

- **Female, left thigh.** Recommended: the gynoid fat on the thigh makes movement easiest to judge.
- **Muscle is one volume** between the bone and the fat, not separate muscles. Separate muscles are a later step.
- **Fat thickness declared by eye,** since we have no measured data yet. CT tissue labels could replace it later, once their license is checked.

## Out of scope

Hip, knee, the rest of the leg. The editor and the built model: nothing in them changes.
