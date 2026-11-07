# 1. The whole woman in layers, at rest

**Asked by Rafael, 2026-11-07.** After the thigh: the whole body built from the inside out, standing still. It's the zero point ("marco zero") for body shapes, and the base for the leg and hip walking next (epic 2), where bug `human-model/9` shows. Agreed order: at rest, then leg and hip walking, then the whole body walking.

## Contract

**In:** the neutral woman's build on `G:\mocap-studio-downloads\models\hm-build\female\`: the skin (`female.export.npz`), the 181 bones (`female.bones.npz`), the rig (`female.export.json`). Fat thickness per zone from `human-model/data/body_fat_female.json`, a new file Rafael edits, like `thigh_tissue.json`.

**Out:**
- `hmcore/layers.py` generalised from one limb to the body: the skin cut at the neck, wrists and ankles; every bone; the same 5 mm voxels and six tetrahedra per voxel; the skin's vertices tied to their tetrahedra.
- The inside-or-outside test on the GPU (Warp's mesh queries), because the body is about 50 times the thigh, and the thigh already took 33 s on the CPU.
- `tools/body_layers.py` and `<name>.body_layers.npz`, with every step kept as numbered files, as the thigh's were.
- Labels: bone, muscle, fat, skin band, and **cavity**: the trunk's organs as one soft volume, so the belly isn't muscle.

**Rules, declared, to be judged on the sections (task 2):**
- **Fat:** within the zone's thickness of the skin. Zones as plastic surgery names them: neck and chin, upper back, chest, breast, belly, flanks, lower back, buttocks, hips ("culote"), thigh front, back, inner and outer, knee, calf, upper arm front and back, forearm. A zone is chosen by the nearest rig bone and direction, and thicknesses blend smoothly between zones, as on the thigh.
- **Breast:** fat from the skin down to the chest muscle, which is a declared thickness over the ribs.
- **Muscle:** what's left, up to a declared distance from the nearest bone. Beyond it, in the trunk, is cavity.
- **Cavity:** inside the rib cage and between the ribs and the pelvis, beneath a declared abdominal wall.

## Agreed with Rafael (2026-11-07)

- The woman first, the man after.
- Face, hands and feet stay out: their skin will keep moving as it does today.
- Fat per zone set by eye, until `tissue-research` brings measured values.

## Dependencies

The thigh epic (`hmcore/layers.py`, `hmcore/xpbd.py`'s GPU image), `hm.sh --gpu`.

## Out of scope

Movement, joints, contact. Changing the skin's shape: the layers are built inside today's MPFB skin.
