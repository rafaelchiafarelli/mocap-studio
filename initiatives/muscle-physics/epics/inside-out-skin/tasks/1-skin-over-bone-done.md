# 1. Push the skin out where a bone is too close

**Asked by Rafael, 2026-11-07** ("vamos ver se esse próximo passo melhora"), after the zero point found bones through the skin at rest (bug `human-model/10`). The first step where the layers shape the skin instead of fitting inside it.

## Contract

**In:** the neutral woman's build (skin, bones, rig). A least depth of tissue over each bone, and the most the skin may be pushed, from a new file `human-model/data/skin_over_bone_female.json`, which Rafael edits.

**Out:**
- `hmcore/skinfit.py`: moves the skin vertices outward along their normals until every bone has at least its declared depth of tissue under the skin, then smooths the push over the skin so no bump shows. The ends at the neck, wrists and ankles don't move, so head, hands and feet still join. MPFB's mesh and vertex order are kept.
- `tools/skin_over_bone.py`: writes `<name>.skin_fit.npz` (the new body vertices) and its table, every step numbered for review: the push needed, the push after smoothing, before and after.
- A `.blend` with the skin before and after, painted by how far it moved.

**Measured, and reported as measured:** bone points outside the skin, and the least tissue over each bone, before and after; the largest push and where; how far the pattern-making girths moved.

**A bone that would need more than the most push isn't covered by moving the skin:** it's reported as a misplaced bone. The right scapula, 27 mm out against the left one's 7.6, is expected to be one: moving the skin that far would grow a hump on her back.

## Declared, to be agreed with Rafael on the result

Least tissue, by eye, from where bones lie close under the skin in a person: 3 mm over the patella, the shin's front and the larynx; 4 mm over the clavicles, the scapulae's spines, the spinous processes and the ankle's bones; 6 mm over the sacrum and the hip bones' crests; 2 mm anywhere else. Most push: 15 mm.

## Dependencies

Epic `body-at-rest` (`hmcore/body.py`, `meshgpu.py`).

## Out of scope

Moving bones. The scapula's fit is a fix of its own.
