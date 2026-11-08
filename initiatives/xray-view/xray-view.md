# xray-view

**Goal:** see through the human model, with the opacity of each layer set separately: skin, fat, muscle, bone and the body's cavity (Rafael, 2026-11-08). An "X-ray" version of the model, or a tool that gives the same control. Rafael suspects Blender has something like this, but not as good as he wants.

**Status:** to be planned. This file only records the initiative: no epics, tasks or code yet.

## The order to try things

1. **In the model:** the built file and its add-on give each layer its own opacity, using what Blender already offers.
2. **Only if that can't reach what's wanted:** think about collaborating with blender.org on the missing feature.

## What exists today

- The layers are separate in the data: `bone`, `muscle`, `fat`, `skin` and `cavity` in the body at rest (`human-model/hmcore/body.py:10`).
- The built model keeps its bones in the collection `HM_bones` (`human-model/blender/assemble.py`, search `HM_bones`).
- A material can already be made see-through (`human-model/blender/hmblender.py:35`, its `alpha`), and the thigh view uses it for the skin (`human-model/blender/thigh_view.py:21`).
- The walk's videos show the inside only as a fixed section, the back half with the bones (`walk_inside` in `human-model/blender/body_walk_bake.py`).

## A cutting plane to move

Rafael (2026-11-08) wants to move the cut in Blender, instead of generating the inside view apart. Part of this same tool.

Today the section is fixed when the walk is simulated: the back half of the body, split at the middle of its depth (`human-model/tools/body_walk.py`, search `cut_faces`), and only that half's surfaces are kept. Moving it means simulating again.

What it would take: each layer kept as a whole closed surface, and a plane to drag, also during the walk, that fills the cut with each layer's colour. Blender's view clipping (Alt+B) moves in real time but leaves the pieces hollow, and a boolean per layer may be too heavy on a walk stored frame by frame.

## What Blender is known to offer (to be checked on our version, 5.2.2)

- The viewport's X-Ray, a single value for the whole view rather than per layer.
- A per-object "in front" display, which draws an object over everything else.
- Material transparency, per material, which would need one control driving each layer's materials.

## Questions to answer when planning

- **What falls short in Blender today?** Rafael's own description of what he tried and what he wants instead comes first.
- **What is it for?** Checking the anatomy while we build, looking at a walk, or images for a film: each asks for different quality and speed.
- **While moving, or only standing still?** The simulated body is baked per frame, so a heavy transparent view may not play in real time.
- **Which body?** The built `.blend` (skin, rig, bones, muscles) and the layered body (with fat and cavity) are different files today.
- **Overlapping layers:** with several see-through layers, the drawing order decides what looks right. This is the known hard part of transparency, and probably where Blender's limit is.
- **Controls:** one slider per layer in the existing Human Model Editor panel, or finer ones, such as per bone group or per muscle.

## If it ever goes to blender.org

A change to Blender's core is C/C++ and goes through its own review and GPL license, while this project works in Python: that needs Rafael's go-ahead first, and it is a commitment outside our control.
