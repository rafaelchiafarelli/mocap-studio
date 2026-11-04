# Muscles

## What a muscle is here

Each muscle is a **spindle**: a chain of straight segments between attachment points, thin at the tendons and thick at the belly. There are 200, about 16 thousand vertices in total, against about 1 million in Z-Anatomy.

| Group | Count (both sides) | Where the values come from |
|---|---:|---|
| Legs and hips | 80 | **Measured:** Rajagopal 2016 path points, force and fiber length (MIT) |
| Trunk and arms | 50 | **Declared** from anatomy descriptions |
| Face | 44 | **Declared** |
| Jaw | 18 | **Declared** |
| Tongue | 8 | **Declared** |

"Declared" means written by hand from anatomy text, not measured. These are the least validated numbers in the model.

**Why spindles:** volume holds exactly, and they're light. **What's lost:** no fibers, no fascia, and wide sheets such as trapezius, latissimus and the obliques are single spindles, so the trunk looks sparse.

## How volume holds

Blender's Stretch To constraint, in `VOLUME_XZX` mode, widens a segment as it shortens: length × s means width ÷ √s. Measured in five poses on every build, each muscle stays within 0.1% of its rest volume. Your jaw test drifted up to +34%.

A muscle's path is straight between its points, so it can pass through a bone or another muscle: that isn't checked.

## How it's wired

Muscles sit on their own armature, `HM_muscle_rig`, because a bone on the main rig following a skin vertex would be a dependency cycle. Each segment has:

1. A **Copy Location** to an empty at its origin.
2. A **Stretch To** an empty at its insertion.

Those empties (`HM_muscle_targets`) are parented to a rig bone, or to a skin vertex for face muscles. Nothing depends on the muscle bodies, so they can be hidden or removed without changing the skin.

## The table

`human-model/data/muscles.json` holds the declared muscles, in sections `face`, `sphincters`, `jaw`, `tongue` and `trunk`. An attachment looks like this:

```json
{"rig": "cheek.T.{s}", "t": 0, "off": [0.002, 0.004, -0.006], "snap": "cranium"}
```

| Field | Meaning |
|---|---|
| `rig` | A rig bone; `{s}` becomes `L` or `R` |
| `t` | Where along that bone: 0 head, 1 tail |
| `off` | Offset in metres, for the left side: +X left, −Y front, +Z up. Mirrored for the right, and scaled by head width |
| `snap` | Move to the nearest point of this bone mesh. Omit it to leave the point free |

Other fields: `radius` (m), and for face muscles `contraction` (share of the muscle's length at full activation), `patch` (how much skin it grabs, m), `facs`.

After changing it, rebuild from `muscles`. `hmcore/muscle.py` resolves the table for each individual, so one table serves everybody.

## Face muscles

Each has `m_<name>_L` and `m_<name>_R` on `HM_controls`, from 0 to 1. Contraction is a share of length; sphincters and lids pull toward a centre instead.

| Name | What it does | FACS | Contraction |
|---|---|---|---:|
| `zygomaticus_major` | Pulls the mouth's corner up and out: the smile | AU12 | 0.21 |
| `zygomaticus_minor` | Raises the upper lip's outer part | AU13 | 0.15 |
| `levator_labii_superioris` | Raises the upper lip | AU10 | 0.17 |
| `levator_labii_alaeque_nasi` | Raises the lip and nose wing | AU9 | 0.15 |
| `levator_anguli_oris` | Raises the corner | AU14 | 0.18 |
| `risorius` | Pulls the corner sideways | AU20 | 0.13 |
| `buccinator` | Presses the cheek in, pulls the corner back | AU14 | 0.11 |
| `depressor_anguli_oris` | Pulls the corner down | AU15 | 0.15 |
| `depressor_labii_inferioris` | Pulls the lower lip down | AU16 | 0.15 |
| `mentalis` | Raises the chin's skin | AU17 | 0.15 |
| `frontalis_medial` | Raises the inner brow | AU1 | 0.16 |
| `frontalis_lateral` | Raises the outer brow, with forehead lines | AU2 | 0.16 |
| `corrugator` | Pulls the brow in and down | AU4 | 0.18 |
| `procerus` | Pulls the skin between the brows down | AU4, AU9 | 0.15 |
| `nasalis` | Narrows the nostril | AU9, AU38 | 0.12 |
| `platysma` | Pulls the lower face and corner down | AU20, AU21 | 0.07 |
| `orbicularis_oris_upper`, `_lower` | Purses the lips (a sphincter, with a push forward) | AU18, AU23, AU24 | 0.15 |
| `orbicularis_oculi_orbital` | Squeezes around the eye, lifts the cheek, crow's feet | AU6 | 0.15 |
| `orbicularis_oculi_upper_lid` | Closes the upper lid | AU43, AU45 | 0.85 |
| `orbicularis_oculi_lower_lid` | Raises the lower lid | AU7, AU45 | 0.25 |
| `levator_palpebrae` | Raises the upper lid | AU5 | 0.45 |

The AU mapping is the widely published one: the FACS manual is sold, and wasn't read. Contractions were tuned by eye for reasonable movement.

**Good first tests, measured on the neutral male:** zygomaticus major shortens 18%, 11% wider, skin moves 14.8 mm. Lateral frontalis shortens 15%, 8% wider, skin moves 13.4 mm.

The modiolus, where several muscles meet at the mouth's corner, has no geometry: its muscles share an insertion near the corner. Its anatomy is confirmed in the [sources](sources-and-validation.md#motion).

## Other muscles

These follow bones. They have no controls and don't drive anything.

- **Jaw:** `masseter_superficial`, `masseter_deep`, `temporalis`, `lateral_pterygoid`, `medial_pterygoid`, `digastric_anterior`, `digastric_posterior`, `mylohyoid`, `geniohyoid`. Jaw motion stays kinematic, so they don't open it.
- **Tongue:** `genioglossus`, `hyoglossus`, `styloglossus`, `palatoglossus`. The tongue itself has 3 bones and 4 controls. Its intrinsic muscles aren't modeled, so it can't groove or narrow. It's the largest simplification in the head, since a tongue is a muscular hydrostat.
- **Trunk and arm:** `deltoid_anterior`, `_middle`, `_posterior`, `pectoralis_major_clavicular`, `_sternal`, `latissimus_dorsi`, `trapezius_upper`, `_middle`, `_lower`, `rhomboid`, `serratus_anterior`, `sternocleidomastoid`, `scalenes`, `rectus_abdominis`, `external_oblique`, `erector_spinae_lumbar`, `_thoracic`, `splenius`, `biceps_brachii`, `triceps_brachii`, `brachialis`, `brachioradialis`, `forearm_flexors`, `forearm_extensors`, `hand_intrinsics`.
- **Legs and hips** (`_l` and `_r`): `addbrev`, `addlong`, `addmagDist`, `addmagIsch`, `addmagMid`, `addmagProx`, `bflh`, `bfsh`, `edl`, `ehl`, `fdl`, `fhl`, `gaslat`, `gasmed`, `glmax1`–`3`, `glmed1`–`3`, `glmin1`–`3`, `grac`, `iliacus`, `perbrev`, `perlong`, `piri`, `psoas`, `recfem`, `sart`, `semimem`, `semiten`, `soleus`, `tfl`, `tibant`, `tibpost`, `vasint`, `vaslat`, `vasmed`.

Leg volume is force ÷ 60 N/cm² × fiber length; the 60 is declared.

## How right are the sizes?

Against the CT sample, male, one side:

| Muscle | Model | CT | |
|---|---:|---:|---|
| Gluteus medius | 0.28 L | 0.28 L | Matches |
| Iliopsoas | 0.41 L | 0.34 L | 20% over |
| Gluteus maximus | 0.77 L | 0.50 L | **54% over** |
| Autochthon, the back's deep muscles | below 0.25 L | 0.44 L | **Too small** |

Total muscle is 15.4 L, under the roughly 25 to 30 L of a male body (that range is general knowledge, not from a source read here).

## What's wrong, and what's next

- **Thickness ignores the muscle slider,** and even goes the wrong way: bug `human-model/6`.
- **Declared values:** the [biomedical tables research](status.md#open-work) could replace them.
- **Muscles don't drive anything:** the skin moves through stored shapes ([skin.md](skin.md)).

Code: `hmcore/muscle.py`, `blender/hmmuscles.py`, `tools/build_muscles.py`, `tests/test_muscle.py`.
