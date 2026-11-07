# 3. The layered thigh walks, simulated on the GPU

**Asked by Rafael, 2026-11-07.** The thigh of task 2 goes through one walking cycle. The femur is moved; muscle, fat and skin follow by simulation on the RTX 4080. The question is whether this way of building a body is worth it: fast enough for overnight batches, no bone through the skin, and tissue that moves like a person's.

## Contract

**In:** `<name>.thigh_layers.npz` (task 2), the GPU image (task 1), the female cycle in `human-model/data/gait_walk.json`: hip and knee angles move the femur, and the cut ends at the hip and the knee move with it. Stiffness, damping and density of muscle and fat are **declared** at the top of the script, muscle stiffer than fat.

**Out:**
- `human-model/tools/thigh_walk.py`: XPBD in Warp, a fixed number of steps per frame at 24 frames per second, writes the skin's positions per frame.
- `human-model/blender/thigh_bake.py`: puts them in a `.blend` as stored shapes, so it plays without simulating, as the sphere does.
- Beside it, the same step on the current model's thigh, `female_walk_review.blend`, for comparison.

**Every run is kept** with its values in the name, like `thigh_v3_fat-soft_damp-20`, on `G:\mocap-studio-downloads\review\<date>\`: the `.blend`, a video and the per-frame table.

**Measured, and reported as measured:**
- Milliseconds per frame on the GPU, and peak VRAM.
- Bone through the skin: how many skin points and how deep, per frame, against the current model on the same step.
- Movement: the skin's motion in the femur's frame, as the nipple was measured. Its amplitude at heel strike, and the time it takes to settle.
- Volume of muscle and fat per frame, against the start.

## What counts as working

To confirm with Rafael:
- **No skin point inside the bone,** in any frame.
- **Fast enough for overnight:** a two-minute scene is 2,880 frames, and eight hours is 10 s per frame for the **whole body**. The thigh is a small part of it, so it should take under 1 s per frame.
- **Movement:** Rafael's verdict, from the videos.

## Dependencies

Tasks 1 and 2.

## Out of scope

Muscle contraction during the step: the muscle is passive here. Contact between the two thighs. The rest of the body. Any change to the built model or the editor.
