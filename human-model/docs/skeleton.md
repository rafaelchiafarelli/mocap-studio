# Skeleton

181 bone meshes, each rigid and parented to one rig bone. How they're chosen and placed is in [morphology.md](morphology.md).

## The rig

`HM_rig` is MPFB's Rigify metarig, 185 bones, which deforms the skin. The generated Rigify control rig isn't used. Three changes on top:

- **Thigh heads move into the sockets,** because MPFB's hips are wider than a real pelvis allows.
- **`DEF-*` weights are merged into metarig bones,** or some skin vertices stay behind when the body bends.
- **Added bones:** `hm_jaw`, `hm_hyoid`, `hm_larynx`, `hm_sternum`, and 24 `hm_rib_<n>_<side>`.

## Jaw

`jaw_open` from 0 to 1 does two things, as a real jaw does (Posselt's envelope):

1. **Rotation** about the condyles.
2. **From about 20 mm of opening,** the condyles also slide forward and down.

| | Value | Source |
|---|---:|---|
| Incisor travel at full opening | 46.6 mm | Travers 2000, abstract |
| Condyle travel | 11.9 mm | Travers 2000, abstract |
| Pure rotation ends at | 20 mm | **Declared,** sources say 10 to 25 |
| Slide angle | 35° | **Declared** |
| Hyoid following | 6 mm forward, 12 mm down | **Declared** |
| Head extension | 4° | **Declared** |

Resulting rotation: 32° male, 38.5° female, and the incisor ends 23 mm back. Your proof of concept needed 38° and went 36 mm back. The female rotation is as high because her jaw is shorter while the target isn't scaled to size. Constants are in `hmcore/jaw.py`. Skin follows because the rig's `jaw_master` now hangs from `hm_jaw`.

## Ribs and breathing

Each rib rotates on its own bone, around a line that changes from side-to-side up top ("pump handle") to front-to-back low down ("bucket handle"). `breath` from 0 to 1 gives 9° on ribs 1 to 10 and 3° on 11 and 12, lifts the sternum, and moves chest and belly skin.

Expansion: 4.0 cm male, 5.0 cm female. All of those rules and angles are declared; expansion is the only check. Cartilages move with the sternum as one rigid piece, so they don't bend.

## Joint limits

Measured means from the [CDC's joint range study](sources-and-validation.md#motion), ages 20 to 44, in `hmcore/joints.py`:

| Joint | Male | Female |
|---|---:|---:|
| Hip flexion, extension | 130.4°, 17.4° | 133.8°, 18.1° |
| Knee flexion, extension | 137.7°, 1.0° | 141.9°, 1.6° |
| Ankle dorsiflexion, plantarflexion | 12.7°, 54.6° | 13.8°, 62.1° |
| Shoulder flexion | 168.8° | 172.0° |
| Elbow flexion, extension | 144.6°, 0.8° | 150.0°, 4.7° |

Shoulder extension and abduction, hip abduction and adduction, wrist, fingers and spine are **declared**.

**Limits aren't enforced** (bug `human-model/3`): they're stored on the bones. `blender/motion_check.py` poses each joint at its limit. On every build, overlaps are only between two bones meeting at that joint, such as femur in hip socket, and never between unrelated bones. How deep those overlaps go isn't measured.

## Walking

`blender/walk.py` keys the mean cycle from Fukuchi 2018, 24 young adults at one treadmill speed, separately per sex (`data/gait_walk.json`). Measured: pelvis, hip, knee, ankle. **Declared:** arm swing 18°, relaxed elbow 18°, trunk counter-rotation, and the 1.1 s cycle. The body's forward and vertical motion is solved so the stance foot stays planted.

**Your verdict: jumpy.** Measured: at each step the body moves up to 27 mm in height in one frame (typical 8), and up to 72 mm forward (typical 45). Cause not proven; the handover between feet in the root solve is the likely one (bug `human-model/5`). Stride is 1.02 m male and 0.90 m female, so the male walks 0.93 m/s against 1.24 m/s measured (bug `human-model/4`).

## Known simplifications

- Radius and ulna don't cross in pronation: both are rigid on one forearm bone.
- The patella rides on the shin, with no track of its own.
- Hyoid and larynx are simple shapes; the larynx looks like a block.
- Finger bones are low resolution.
- Facial bones are lumps at CT's 1.5 mm; MPFB's eyes and teeth don't sit exactly in the donor's sockets.

Code: `hmcore/skeleton.py`, `hmcore/jaw.py`, `hmcore/joints.py`, `hmcore/parametric.py`, `hmcore/gait.py`, `blender/assemble.py`, `blender/posing.py`, `blender/walk.py`, `blender/motion_check.py`, `blender/breath_check.py`.
