# Morphology: how one individual gets built

To change a character, read [character-controls.md](character-controls.md). This page explains what the build does with those values.

## The order matters

1. **MPFB makes the skin and rig** from the macros and targets. All its data is CC0.
2. **Bones are fitted into that skin:** real shapes, resized.
3. **Muscles attach to those bones.**
4. **Fields are solved on that skin.**

So everything recomputes for each person, with no manual repair. It also means the skin decides and the inner layers follow.

## Where the bones come from

| Part | Source | Why |
|---|---|---|
| Skull, jaw, spine, ribs, sternum, cartilage, pelvis, scapula, clavicle, humerus | **CT scans,** TotalSegmentator, CC BY 4.0. One donor per sex: `s1045` (male, 62, no pathology recorded) and `s0933` (female, 55, bleeding recorded) | Real anatomy for both sexes. Set in `hmcore/bonelib.py` |
| Femur, patella, tibia, fibula, foot | **BMF Toolkit,** zlib: one real female body, for both sexes | CT femurs are cut at the knee, and there are no shin or foot labels |
| Forearm, hand | **Rajagopal 2016,** MIT | Those labels need a paid license. Not female-specific |
| Hyoid, larynx | **Parametric** | No allowed mesh found |
| Eyes, teeth, tongue | **MPFB,** CC0 | Ready-made |

Z-Anatomy enters nothing: it's only a comparison in [sources-and-validation.md](sources-and-validation.md).

**Credits are required** wherever the model ships: [`ATTRIBUTION.md`](../ATTRIBUTION.md).

## How a bone is placed

Each bone stays rigid and only scales, so its shape is the measured one. It follows the person's size but not their bone shape. `hmcore/skeleton.py`:

| Part | Rule |
|---|---|
| **Long bones** | Joint-to-joint onto the rig. Length scales fully, thickness to the power 0.7, since limbs don't thicken in proportion |
| **Pelvis** | Width from the hips' skin, minus a margin. Then moved forward, and tilted about the sockets if needed, until 6 mm of tissue covers the sacrum and the crests: 20 mm on the neutral woman, 33 mm and 9° on the man; the sacrum then sits 6 mm under L5. Its sockets become the true hip joints |
| **Spine** | Height spaced between hips and skull. Depth from the back's skin, so each spinous tip sits 12 mm under it |
| **Rib cage** | One map for ribs, sternum and cartilage. Width from the skin low on the chest, because arms join the trunk higher up. Depth from sternum to spine |
| **Scapula, humerus** | The humerus's head centre, a sphere fitted to it, sits on the rig's shoulder joint, and the scapula keeps its CT relation to it. Both go up, with the rig's joint, until the acromion lies 8 mm under the shoulder's skin, the same on both sides |
| **Clavicle** | Runs from the sternum's top, on the midline, to the placed acromion, with a 3 mm joint |
| **Settled under the skin** | Scapulae, clavicles and fibulae are then moved rigidly, by the smallest move, until 4 mm of tissue covers them: the scapula turns about its glenoid, the clavicle about its sternal end and back, the fibula about its head. Without it the right scapula came 27 mm through the back, because the CT donor's shoulders weren't level (bug `human-model/12`, fixed). The moves are in `anchors.settled` of `<name>.bones.npz.json` |
| **Skull** | A box inside the head's skin, with the tilt from the scanner's head rest removed. Solved so the jaw socket lands on the rig's hinge. Then shrunk until it stays under the skin, with the face held in place so the eyes keep their sockets |
| **Jaw** | From condyles to chin, levelled and centred. The donor's asymmetry is lost |
| **Foot** | Flat on the floor. BMF's body lay with its feet pointing down, so the sole and toes are turned flat. Length from the skin |
| **Fingers** | Each onto its rig bone, centred in the finger's skin |

Skin margins, in metres, are at the top of `hmcore/skeleton.py`: `TISSUE` for the head, `TRUNK_MARGIN`, `PELVIS_MARGIN`, `SETTLE_TISSUE`, `PELVIS_TISSUE`, `AC_JOINT`, `ACROMION_TISSUE`.

## CT quirks worth knowing

- **A scan isn't centred on x=0,** so "midline" is always relative to a pair of bones.
- **Arms are almost always clipped** by the sides of the field of view. A first run gave a mean humerus of 128 mm, so labels touching any face of the volume, or below a minimum length (`measures.COMPLETE_MIN`), no longer count.
- **The `skull` label holds the jaw too:** `ctbones.split_mandible` separates them with a watershed.
- **Only trauma scans cover the whole body,** and no fracture check was done beyond looking.
- **At 1.5 mm,** thin facial bones come out as lumps.

## Checks on every person

| Check | Tool | Result on the six test people |
|---|---|---|
| All build with no repair | `build_model.py` | Yes |
| Bones inside the skin | `.containment.json` | Cranium 4–8% of points outside. The sacrum was about 47% out in the men before the pelvis was moved forward (bug `human-model/2`, fixed 2026-11-08); now none. Fibula up to 37%. Mean 19–25%, mostly tiny hand and foot bones where the check is noisy |
| Unrelated bones colliding | `motion_check.py` | None |
| Muscle volume | `volume_check.py` | Within 0.1% |

Images: `seis_individuos_pele.png`, `seis_individuos_ossos_musculos.png`.

## How male and female differ

Measured, not assumed: ANSUR II for the body's outside, a CT sample for inside. *d* is the difference in pooled standard deviations; (n) is the sample size.

| Measure | Male (n) | Female (n) | Female vs male | Effect size d | Source |
|---|---:|---:|---:|---:|---|
| Stature | 1756 ± 69 mm (4082) | 1628 ± 64 mm (1986) | -7% | +1.92 | ANSUR II |
| Biacromial breadth | 416 ± 19 mm (4082) | 365 ± 18 mm (1986) | -12% | +2.69 | ANSUR II |
| Bi-iliac breadth | 275 ± 18 mm (4082) | 273 ± 22 mm (1986) | -1% | +0.11 | ANSUR II |
| Hip breadth | 346 ± 24 mm (4082) | 354 ± 27 mm (1986) | +2% | -0.32 | ANSUR II |
| Bizygomatic breadth | 143 ± 6 mm (4082) | 134 ± 6 mm (1986) | -6% | +1.50 | ANSUR II |
| Head breadth | 154 ± 6 mm (4082) | 148 ± 5 mm (1986) | -4% | +1.22 | ANSUR II |
| Head length | 200 ± 7 mm (4082) | 190 ± 7 mm (1986) | -5% | +1.34 | ANSUR II |
| Sitting height | 918 ± 36 mm (4082) | 857 ± 33 mm (1986) | -7% | +1.79 | ANSUR II |
| Hand length | 193 ± 10 mm (4082) | 181 ± 10 mm (1986) | -6% | +1.22 | ANSUR II |
| Foot length | 271 ± 13 mm (4082) | 246 ± 12 mm (1986) | -9% | +1.95 | ANSUR II |
| Forearm-hand length | 480 ± 23 mm (4082) | 440 ± 23 mm (1986) | -8% | +1.73 | ANSUR II |
| Bi-iliac width, bone | 286 ± 23 mm (91) | 280 ± 20 mm (85) | -2% | +0.29 | CT sample |
| Pelvis height, bone | 225 ± 13 mm (91) | 213 ± 43 mm (85) | -5% | +0.37 | CT sample |
| Pelvis depth, bone | 157 ± 11 mm (91) | 152 ± 12 mm (85) | -3% | +0.46 | CT sample |
| Sacrum width | 119 ± 6 mm (121) | 120 ± 7 mm (103) | +0% | -0.03 | CT sample |
| Sacrum height | 148 ± 12 mm (121) | 134 ± 14 mm (103) | -9% | +1.09 | CT sample |
| Clavicle length | 157 ± 12 mm (11) | 142 ± 7 mm (23) | -9% | +1.46 | CT sample |
| Scapula length | 184 ± 22 mm (12) | 171 ± 14 mm (14) | -7% | +0.73 | CT sample |
| Hip bone volume | 413 ± 54 ml (91) | 316 ± 53 ml (85) | -23% | +1.80 | CT sample |
| L3 vertebra volume | 68 ± 16 ml (123) | 56 ± 11 ml (102) | -18% | +0.90 | CT sample |
| T6 vertebra volume | 29 ± 7 ml (58) | 22 ± 5 ml (56) | -24% | +1.12 | CT sample |
| Gluteus medius volume | 279 ± 50 ml (125) | 211 ± 37 ml (100) | -24% | +1.55 | CT sample |
| Iliopsoas volume | 338 ± 83 ml (103) | 228 ± 41 ml (86) | -33% | +1.68 | CT sample |

**Reading it:** the largest differences are shoulder breadth, overall size, and bone and muscle volume. Absolute pelvic width barely differs, so it's wider relative to a smaller body. What's most often described as the female pelvis, a wider inlet and a shallower shape, **wasn't measured:** these are bounding boxes. The female pelvis height has a suspicious spread, likely some clipped scans. ANSUR is military, and the CT sample is hospital patients.

**What the model does with this:** the skin's differences come from MPFB. Trunk and skull come from a donor of that sex, joint limits and walking are per sex. **Not sex-specific:** legs and feet (one female body), forearm and hand, muscle table, and the Rajagopal leg muscles.

Code: `hmcore/bonelib.py`, `hmcore/skeleton.py`, `hmcore/fit.py`, `hmcore/ctbones.py`, `hmcore/sources.py`, `hmcore/parametric.py`, `tools/build_bones.py`, `tools/sex_report.py`, `tests/test_fit.py`, `tests/test_measures.py`.
