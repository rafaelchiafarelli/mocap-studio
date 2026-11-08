# floor-contact

**Goal:** research a floor the character really stands on, without the foot being glued to it (Rafael, 2026-11-08). Three levels, each going further than the last.

**Status:** research, to be planned. This file only records the initiative: no epics, tasks or code yet.

## What exists today

- **The walk glues the foot.** A foot point that touches the floor keeps that place until the foot leaves, and the leg's hip, knee and ankle are corrected to hold it (`human-model/blender/walk.py:144`). This floor is a height rule, with no forces.
- **The GPU solver has a floor,** used only by the soft cube test (`human-model/tools/gpu_bench.py:31`). A point that touches it stays where it touched, so its friction is total, which is also a kind of glue (`human-model/hmcore/xpbd.py:60`).
- **The simulated body ends at the ankles** (`human-model/hmcore/body.py:16`): the feet aren't in the layers, so nothing there could touch a floor.
- **Bones are imposed.** The simulation carries tissue on bones whose motion is already decided, so a floor can't hold or push a bone back. The foot only sticks by friction if the foot is part of what gets solved.

## The three levels

### Level 1: a rigid foot with friction

The foot rolls from heel to toe and stays only where friction holds it; under a large enough sideways force it slips. Worked out in the motion, before the tissue simulation.

To research: friction models for a rigid foot, how the contact moves along the sole, how far the leg may be corrected from the actor's motion, and how this meets the joint limits (bug `human-model/3`).

Also the base for a character whose legs differ from the actor's: the foot has to reach the floor or a step on a different body.

### Level 2: a soft foot on the floor

The foot joins the simulated layers and the floor presses the sole: heel and arch squash at each step. Without level 1 the sole would squash while the foot still slides, since the bones keep following their data.

To research: building the foot's layers (bones, fat pad, skin of the sole, at a fine enough voxel size), friction better than the solver's all-or-nothing, and what it costs on the GPU.

### Level 3: a body held up by the floor

The body's weight is carried by the floor's reaction, with balance simulated, so the weight is real and not implied.

**Rafael (2026-11-08): this level is important and will bring important conflicts in the future; to be revisited later.** It stays recorded here and isn't dropped.

To research: full-body dynamics that follow captured motion, balance, and where the body's mass comes from. One conflict is already visible: physics may change what the actor performed, and the performance is the point of capturing it. Others are to be found.

## Beyond a flat floor

A flat floor is the simple case, and far simpler than contact between body parts (bug `human-model/15`). Relief or steps would ask the solver for mesh queries, which `human-model/hmcore/meshgpu.py` already does for other purposes.

## Suggested order

Level 1, then 2, with 3 revisited later, as Rafael asked. To be confirmed when this is planned.
