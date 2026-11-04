# Skin

## What moves the skin

Three things add up on MPFB's mesh:

1. **Bones:** the rig's weights from MPFB, for the body and the jaw.
2. **Muscle fields:** one shape key per face muscle, `F_<muscle>_<side>`, driven by its control.
3. **Body shapes:** `B_breath` from the `breath` control; `B_biceps_*`, `B_triceps_*`, `B_deltoid_*` from joint angles.

Nothing is simulated at run time, which is why it's fast: about 250 frames per second headless.

## How a field is made

For each face muscle, `hmcore/softtissue.py` works out once where the skin goes at full contraction. Think of the skin as a smooth elastic sheet over the skull, pinned in places.

**1. The muscle grabs a patch.** Around the insertion, weights fall off with distance *along the skin*, so an upper lip's patch can't jump the gap to the lower lip.

**2. The patch is moved.** It moves toward the muscle's origin by `contraction × length`, kept mostly tangent to the skin. Sphincters and lids pull toward a centre instead, and lips also push forward when pursed.

**3. The sheet solves the rest.** Every other vertex settles as smoothly as it can between the moved patch and the pins (a bi-Laplacian solve: it resists bending as well as stretching).

**4. Tissue bunches.** Where skin is compressed against bone, its thickness has to go somewhere, so it bulges outward. That gives the cheek's bunching. It's off where no bone is near, or the chin swells, and it's capped.

**5. Skin is kept off the bone.** A vertex can't sink closer than 60% of its rest distance to the skull or jaw.

**6. Lines are added.** Frontalis and the eye's orbital muscle get small ripples where they compress the skin: forehead lines and crow's feet.

Each result is one shape key. Activation is a linear blend, so two muscles simply add. That's cheap, but real tissue doesn't add linearly.

## What's pinned

| Where | How firmly | Why |
|---|---|---|
| Boundary with the body, scalp behind the ear, ears, top of the nose | Hard | They don't move with the face |
| Nose | Medium (`NOSE_STIFFNESS`) | Bone and cartilage: without it a smile widens the nose |
| Eyelids | Medium, unless the muscle is an eye muscle (`LIDS_STIFFNESS`) | Lids move only with their own muscles |
| Zygomatic, mandibular and masseteric ligaments | Soft (`LIGAMENT_STIFFNESS`) | Real bands from bone to skin |
| Orbital ligament, a ring around the eye | Soft | Same |

The **nasolabial fold isn't modeled:** it emerges between the pulled patch and these anchors. Ligament positions are placed near rig landmarks, not from the cadaver study's measured distances.

## What to tune

All at the top of `hmcore/softtissue.py`, all declared. After changing them, rebuild from `fields`.

| Constant | Value | Raise it and |
|---|---:|---|
| `LIGAMENT_STIFFNESS` | 0.3 | Folds get sharper, cheeks move less |
| `NOSE_STIFFNESS` | 1.0 | Nose stays stiller |
| `LIDS_STIFFNESS` | 1.0 | Lids ignore other muscles more |
| `BULGE_GAIN` | 0.8 | Cheeks bunch more |
| `BULGE_MAX` | 4 mm | Allows more bunching |
| `THICK_CAP` | 12 mm | Thick tissue counts for more |
| `NO_BONE` | 30 mm | Bulge reaches further from bone |
| `FOLD_DEPTH` | 0.7 mm | Deeper lines |
| `FOLD_WAVE_FOREHEAD` | 14 mm | Forehead lines further apart |
| `FOLD_RAYS` | 16 | More crow's feet |

Each muscle's `contraction` and `patch` are in `data/muscles.json`: [muscles.md](muscles.md).

**The first solve tore the lips,** because MPFB's lips have very thin triangles, and cotangent mesh weights break on them. So the operator uses uniform weights. If you try a better one, that's what to test.

## How it compares

**The smile.** `sorriso_neutro_arkit_musculo.png` compares neutral, ARKit and muscle on one character. The ARKit shape moves skin up to 17.8 mm and the muscle one 12.0 mm. Your read: "the fader one is too incisive", and the muscle one is "too biten". More investigation needed.

**Muscles can't reproduce ARKit's shapes.** Fitting each active shape with the fields left a relative residual of 0.62 to 1.0, and 0.49 to 0.86 with no limits on the activations. No shape reached the 0.6 needed to replace it. The fields are too local and hand-declared.

**Other ways to bind skin**, on one smile, against the field:

| Method | Shell | Bind | Mean error | Worst error |
|---|---:|---:|---:|---:|
| Direct shape key | — | — | 0 | 0 |
| Surface Deform | 2,294 faces | 0.03 s | 0.68 mm | 10.8 mm |
| Mesh Deform | 2,294 faces | 0.20 s | 1.50 mm | 10.1 mm |

We already know each vertex's displacement, so a shell only loses detail. These would matter only with a volumetric simulation driving a cage.

**Tissue:** inconclusive. It installs on Blender 5.2.2, but its operator cancelled when run headless on a very small patch, and no pattern was rendered. It adds geometry per face, too costly for pores, so normal or displacement maps are the better route for micro relief. It's still installed in the portable Blender.

## Your three open questions

| Question | Answer so far |
|---|---|
| Which method solves muscles? | Least-effort non-negative least squares, tested in [drive.md](drive.md). It regularizes well, but the fields don't reach the data |
| Liquid or something else? | Neither fluid nor FEM was built. A sheet solved once is what's here. Your liquid idea's two useful parts, conserved volume and tissue lag, are half covered: the bulge conserves volume loosely, and there's no lag at all |
| Is a full muscle model needed? | Not justified yet: the faders with bones and shapes are ahead |

## Body skin

| Shape | Driven by | Status |
|---|---|---|
| `B_breath` | `breath`. Chest and belly | Chest expansion 4.0 cm male, 5.0 cm female (ribs) |
| `B_biceps_*`, `B_triceps_*` | Elbow angle | **Declared bumps,** not checked in a render |
| `B_deltoid_*` | Arm against the chest | **Declared bump,** not checked in a render |

Not done: abdomen compression on bending, elbow-crease collapse. Skin there deforms only by MPFB's weights.

## What's wrong, and what's next

- **Smiles tear at the corners on a changed face:** bug `human-model/7`. A smaller crease shows on the neutral face too.
- **The inside of the mouth can come through the cheek** at strong activations: bug `human-model/1`.
- **No real fat or fascia layers,** and no breast tissue.
- **Identity must stay still:** the fields are solved for one exact skin, so changing a slider afterwards leaves them wrong. Rebuild.

Code: `hmcore/softtissue.py`, `hmcore/bodyskin.py`, `blender/hmmuscles.py`, `tools/build_fields.py`, `tests/test_softtissue.py`.
