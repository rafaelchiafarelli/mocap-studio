# Skeleton

181 bone meshes, each rigid and parented to one rig bone. How they're chosen and placed is in [morphology.md](morphology.md).

## The rig

`HM_rig` is MPFB's Rigify metarig, 185 bones, which deforms the skin. The generated Rigify control rig isn't used. Three changes on top:

- **Thigh heads move into the sockets,** because MPFB's hips are wider than a real pelvis allows. **Shoulder joints go up** with the shoulder girdle until the acromion lies just under the skin (19 mm on the neutral woman): MPFB's sit low, and its upper arm was 232 mm from joint to elbow.
- **`DEF-*` weights are merged into metarig bones,** or some skin vertices stay behind when the body bends.
- **Added bones:** `hm_jaw`, `hm_hyoid`, `hm_larynx`, `hm_sternum`, 24 `hm_rib_<n>_<side>`, and `hm_patella.<side>`.

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

**Limits are enforced only on the legs** (bug `human-model/3`): hip, knee and ankle by a Limit Rotation at the measured mean plus 10°, since the mean isn't a ceiling. They don't change the measured walk. Shoulder and elbow are only stored on the bones. `blender/motion_check.py` poses each joint at its limit. On every build, overlaps are only between two bones meeting at that joint, such as femur in hip socket, and never between unrelated bones. How deep those overlaps go isn't measured.

## Walking

`blender/walk.py` keys the mean cycle from Fukuchi 2018, 24 young adults at one treadmill speed, separately per sex (`data/gait_walk.json`). Measured: pelvis, hip, knee, ankle. **Declared:** arm swing 18°, relaxed elbow 18°, trunk counter-rotation, the 1.1 s cycle, toe-off at 61% of the cycle, the toes' most bend (55°) and the contact's width (4 mm).

How the walk is built (task `muscle-physics/body-walk/2`, 2026-11-07):
- **The pelvis's tilt is taken off the hip angle.** The data measures the thigh against a pelvis tilted about 10° forward; the rig's rest pelvis is level. Without it the thigh flexed 10° too far: the stance foot never lay flat, and the body jumped at every hand-over (bug `human-model/5`).
- **The toes roll at push-off:** they bend up until they lie as they do standing, so the trailing foot stands on the ball, not the toes' tips.
- **The root follows a soft contact:** the foot points within a few millimetres of the lowest share it, so the hand-over between feet takes several frames.
- **Each stance foot is planted** by a small correction of its hip, knee and ankle: a point that touches the floor stays there until the foot leaves. On the woman the correction is 3.8° at most, 0.3° on average.

Measured on the woman (`blender/walk_check.py`): height changes at most 8 mm a frame, a smooth wave lowest in double support; the planted foot slides at most 0.3 mm a frame and sits within 1.8 mm of the floor; stride 1.14 m, 1.04 m/s, against 1.24 m/s in the data (bug `human-model/4`). Before: 24 mm height steps, 12 mm slides, stride 0.90 m. Your verdict (2026-11-08): "Ficou ok, bem melhor agora". Both feet are down together for about one frame per hand-over, against about three in the data: bringing the heel down at heel strike bent the knee 30° off the data, so it wasn't kept.

**Stopping** (`stop_steps`, 2026-11-08): the walk can end with more steps that shrink to standing, taking 1.5 times as long as walking ones. Without it the walk stops dead, and the man's costal cartilage came through the skin in the one frame after.

## Known simplifications

- Radius and ulna don't cross in pronation: both are rigid on one forearm bone.
- The patella turns by half the knee's bend, with no real groove in the femur.
- Hyoid and larynx are simple shapes; the larynx looks like a block.
- Distal femur, patella, tibia, fibula and larynx are narrowed to fit the skin, so they are thinner than real ones there.
- Finger bones are low resolution.
- Facial bones are lumps at CT's 1.5 mm; MPFB's eyes and teeth don't sit exactly in the donor's sockets.

Code: `hmcore/skeleton.py`, `hmcore/jaw.py`, `hmcore/joints.py`, `hmcore/parametric.py`, `hmcore/gait.py`, `blender/assemble.py`, `blender/posing.py`, `blender/walk.py`, `blender/motion_check.py`, `blender/breath_check.py`.
