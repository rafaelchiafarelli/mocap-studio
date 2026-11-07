# 2. The woman's lower body walks

**Asked by Rafael, 2026-11-07.** The agreed second stage: the legs and the pelvis walking, where bug `human-model/9` shows (bones through the skin near the hip, when walking).

## Contract

**In:** the zero point on the pushed skin (`body_v5_pushed-skin`), the walk dump of task 1, tissue values from a new `data/body_tissue.json`: Rafael's `rafa8` values for muscle, fat and skin, plus the cavity's (the pelvis' organs), declared.

**Out:**
- `tools/lower_body_walk.py`: the tetrahedra below the waist, both legs and the pelvis, to the ankles. Bone nodes follow their bone; the cuts at the waist and the ankles follow the nearest bone. Simulated on the GPU through the walk, then a second of standing.
- `blender/lower_body_bake.py`: the `.blend` and the videos, our skin beside the current model's, and a section.
- Every run kept, values in its name, on `G:\mocap-studio-downloads\review\<date>\`.

**Measured, and reported as measured:** bone points through the skin per bone and frame, ours against the current model's; time per frame and VRAM; volume per tissue; the skin's motion against its nearest bone, per zone; tetrahedra turned inside out at the joints.

## Agreed and declared

- The woman, from the waist down; face, arms, hands and feet stay out (2026-11-07).
- No contact between the thighs yet: where they pass through each other is measured, not prevented.
- The misplaced bones (the fibulae among them) stay as they are.

## Dependencies

Task 1, epics `body-at-rest` and `inside-out-skin`.
