# Sources and validation

What the model is built from, what each source allows, and how its measurements compare. Credits a film has to carry are in [`ATTRIBUTION.md`](../ATTRIBUTION.md).

## Licenses

These decisions were delegated by Rafael on 2026-11-03. This is an engineer's reading of the license texts, not legal advice.

| Source | Version | License as read | What we take | Commercial use | Open questions |
|---|---|---|---|---|---|
| [TotalSegmentator CT dataset](https://zenodo.org/records/10047292) | 2.0.1 | CC BY 4.0 (Zenodo API `cc-by-4.0`) | **Derive:** bone and muscle labels to meshes; **measure:** per-sex statistics | Yes, with attribution | De-identified patient scans, sex and age in `meta.csv`. Credit is required wherever the model ships |
| [BMF Toolkit](https://github.com/manishsreenivasa/BMFToolkit) | commit `e3e781e` | zlib | **Derive:** female lower-body bones, from Visible Human CT | Yes | Altered versions must be marked as altered |
| [Rajagopal 2016](https://simtk.org/home/full_body) | 4.0 | MIT (Stanford, read on SimTK's release page) | **Derive:** forearm and hand bones, muscle path points; joint axes | Yes | Copy comes from `opensim-org/opensim-models`, whose repository has no license file; SimTK's download needs a login. Same model, but the MIT grant was read on SimTK |
| [ANSUR II](https://www.openlab.psu.edu/ansur2/) | public CSVs | US Army data "approved for public release; distribution is unlimited"; no formal license | **Measure:** external validation only. Nothing ships | Yes in practice | Not a formal license, which is why it's validation only |
| [Fukuchi 2018](https://doi.org/10.6084/m9.figshare.5722711) | figshare 5722711 | CC BY 4.0 (figshare API) | **Derive:** walking joint angles; **measure** | Yes, with attribution | — |
| [CDC joint range study](https://archive.cdc.gov/www_cdc_gov/ncbddd/jointrom/index.html) | Soucie 2011 | US government public data | **Measure:** range limits | Yes | — |
| MPFB | 2.0.18 | Code GPL-3.0+; MakeHuman base mesh, targets and assets CC0 | **Derive:** skin, rig, eyes, teeth, tongue | Yes | This session didn't find a statement in the add-on on whether GPL reaches a generated character. The usual reading is that it doesn't, since the mesh and targets are CC0 |
| Tissue | 0.3.76 | GPL-3.0+ | **Tool:** pattern experiment | Yes (rule: GPL for tools) | — |
| Pose Shape Keys | — | GPL-3.0+ | Not used | Yes | — |
| Z-Anatomy, BodyParts3D | current | CC BY-SA 4.0 and CC BY-SA 2.1 JP, some parts NC | **Look and compare only:** validation numbers in reports | Share-alike isn't on the allowed list, and NC parts are forbidden | See decision 1 |
| MuSkeMo | — | No license found; one file CC-BY-NC | Nothing | No | — |
| anatomy3d-blender | — | GPL-2.0 | Nothing: draws fibers, no deformation | Tool only | — |
| Parrot Lipsync | 1.1.4 | Manifest MIT, repository GPL-3.0, not settled | Nothing new. `drive` reads phonemes from Allosaurus, as the faders do | Open | Already recorded in `DEPENDENCIES.md` |

**Decisions, taken on Rafael's behalf:**

1. **Z-Anatomy stays out of the model.** No mesh, patch or coordinate from it enters
   anything we build. This removes the share-alike question instead of answering it,
   so no lawyer is needed now. It's still measured as a comparison below,
   and those numbers stay in reports. The jaw proof of concept remains review-only.
2. **Bones come from CT labels and permissive meshes**, not from an atlas: this also
   closes the female gap, because the CT dataset has 510 female scans.
3. **MuSkeMo and anatomy3d-blender are dropped.**

**CC BY obligations:** [`ATTRIBUTION.md`](../ATTRIBUTION.md)
lists the credits a film using this model has to carry.

## What stays from Z-Anatomy's structures

Rebuilding means from the sources above, never from these meshes.

From `human-model/references/inventory.py` on `z_anatomy_original.blend`, with auto-run
off. 4,569 meshes and 2,094,701 vertices. Each mesh is counted once under its numbered
collection, so `Bonus collection` isn't added twice. "Rebuild" means from the sources in
the licenses above, never from these meshes.

| Group | Meshes | Vertices | Decision | Reason |
|---|---:|---:|---|---|
| 1 Skeletal system | 1,244 | 302,352 | Rebuild | Rafael: keep until data replaces it. Hyoid and larynx parts included |
| 2 Muscular insertions | 705 | 44,375 | Reference only | Our origins and insertions are declared per muscle from anatomy, on our own bones |
| 3 Joints | 480 | 86,320 | Rebuild as joint rules; ligament meshes left out | The behaviour matters. **Loss of detail:** no ligament geometry, but each joint keeps its limits |
| 4 Muscular system | 789 | 1,075,358 | Rebuild | Same rule as the bones, about 1 million vertices here is the speed risk |
| Rib cage, diaphragm, lungs | part of 1, 4, 8 | 9,674 (diaphragm) + 14,317 (lungs) | Rebuild as breathing rig and volume | Breathing is visible |
| Larynx | part of 8 | 16,376 | Rebuild as a moving volume with the hyoid | Visible when speaking |
| Eyes, teeth, tongue | part of 1, 7, 8 | 18,529 + 23,536 + 2,899 | Rebuild from MPFB's CC0 assets | Visible |
| 5 Cardiovascular | 60 | 34,407 | Leave out for now; superficial veins reopen for hands and neck in the skin work | No source to build from yet. **Loss of detail,** recorded here |
| 6 Lymphoid organs | 220 | 65,285 | Leave out | Not visible |
| 7 Nervous system and sense organs (other than eyes) | 460 | 398,709 | Reference only; brain left out | Possible way to group controls |
| 8 Visceral systems (other than the above) | 254 | 43,628 | Leave out | Not visible; the abdomen's volume comes from soft tissue |
| Genitalia | 28 | 2,678 | Leave out | Rafael |
| 9 Regions, reference lines, planes | 354 | 44,212 | Leave out | Atlas tools |

## Measurements

Scripts: `references/measure_reference.py` (inside Blender, read-only),
`tools/ct_stats.py`, `tools/validation_table.py`. Male columns,
because Z-Anatomy is one male body. The CT sample is 130 male and 108 female scans aged
20 to 65, without recorded trauma.

| Measurement | Z-Anatomy | Source mean ± SD (male) | n | z | Source |
|---|---:|---:|---:|---:|---|
| Stature, bone to bone (skin adds about 2 cm) | 1694 mm | 1756 ± 69 mm | 4082 | -0.9 | ANSUR II `stature` |
| Biacromial breadth (scapula to scapula) | 347 mm | 416 ± 19 mm | 4082 | -3.6 | ANSUR II `biacromialbreadth` |
| Bi-iliac breadth | 270 mm | 275 ± 18 mm | 4082 | -0.3 | ANSUR II `bicristalbreadth` |
| Bizygomatic breadth (bone; skin adds about 1 cm) | 125 mm | 143 ± 6 mm | 4082 | -2.9 | ANSUR II `bizygomaticbreadth` |
| Humerus length | 320 mm | too few complete labels | 1 | — | TotalSegmentator CT |
| Bi-iliac width | 270 mm | 286 ± 23 mm | 91 | -0.7 | TotalSegmentator CT, uncut labels |
| Pelvis height | 215 mm | 225 ± 13 mm | 91 | -0.8 | TotalSegmentator CT, uncut labels |
| Sacrum width | 123 mm | 119 ± 6 mm | 121 | +0.6 | TotalSegmentator CT, uncut labels |
| Clavicle length | 160 mm | 157 ± 12 mm | 11 | +0.3 | TotalSegmentator CT, uncut labels |
| Scapula length | 191 mm | 184 ± 22 mm | 12 | +0.3 | TotalSegmentator CT, uncut labels |

**What this says:** Z-Anatomy is on the small side but inside normal variation for
stature, pelvis and sacrum. Two gaps stand out: biacromial and bizygomatic breadth, at
about 3 SD below. Part of that is definition, because ANSUR measures over skin and muscle,
and Z-Anatomy here is bone only. So they're not proof of an error. Nothing was corrected,
as the contract says. Z-Anatomy stays a comparison only .

**Limits of the numbers:**

- ANSUR II is US Army personnel, not a civilian sample, and has no internal anatomy.
- The CT sample comes from clinical routine at the hospital sites coded in `meta.csv`, with disease
  recorded in many of them. Age and sex come from `meta.csv`.
- **Arms are almost always clipped in CT.** A first run reported a mean humerus of 128 mm,
  because the field of view cuts arms at its sides. Labels that touch any face of the volume
  or are shorter than a floor (`measures.COMPLETE_MIN`) now don't count. That floor can bias
  a mean upward, and it leaves humerus and skull with too few labels to compare.

**What no open source covers, as far as this session found:**

- **Female internal anatomy is no longer the largest gap for bones.** The CT dataset has 510
  female scans, and BMF is a female lower limb. Female forearm and hand bones still come from
  the Rajagopal model, whose geometry isn't female-specific. Muscle bodies exist only for the
  labels below.
- Muscle bodies in the CT labels: gluteus maximus, medius and minimus, iliopsoas and
  autochthon only. Their commercial task for thigh and shoulder muscles needs a paid license,
  which we don't use.
- Forearm, hand, shin and foot aren't in the CT labels at all.
- **Face muscle measurements:** no open dataset found. Face muscles are declared from
  anatomy descriptions and are the least validated part of the model.
- Hyoid and larynx: no mesh with an allowed license was found.

## Motion

"Declared" means no source was read and the value is ours, to be replaced.

Secondary mentions are marked. "Declared" means no source was read and the value is ours,
to be replaced. The tests run in `blender/motion_check.py`, except where a row names another.

| Joint or movement | How it moves | Range | Source | Data license | Test |
|---|---|---|---|---|---|
| Hip | Flexion, extension | M 130.4 / 17.4°, F 133.8 / 18.1° | [CDC study](https://archive.cdc.gov/www_cdc_gov/ncbddd/jointrom/index.html), ages 20–44, passive | US government | Bone meshes don't pass through each other at the limits |
| Knee | Flexion, extension | M 137.7 / 1.0°, F 141.9 / 1.6° | Same | Same | Same |
| Ankle | Dorsi, plantar flexion | M 12.7 / 54.6°, F 13.8 / 62.1° | Same | Same | Same |
| Shoulder | Flexion | M 168.8°, F 172.0° | Same | Same | Same |
| Elbow | Flexion, extension | M 144.6 / 0.8°, F 150.0 / 4.7° | Same | Same | Same |
| Shoulder extension, abduction, hip abduction, wrist, fingers, spine segments | — | `joints.DECLARED` | **Declared** | — | Same |
| Jaw | Rotation about the condyles, then rotation with condyle sliding forward and down | Incisor 46.6 mm, condyle 11.9 mm straight-line | [Travers 2000](https://utsouthwestern.elsevierpure.com/en/publications/associations-between-incisor-and-mandibular-condylar-movements-du), abstract read, not the full text | Numbers only | `tests/test_jaw_joints.py`: both values reached, rotation under the proof of concept's 38° |
| Jaw, end of pure rotation | — | 20 mm **declared** between the 10 and 25 mm reported | Starting leads above | — | Slide starts at the break |
| Hyoid during opening | Follows the jaw | **Declared.** Only direction found: up and back when the head extends, forward and down when it flexes | King 1952, through a [secondary mention](https://www.koreascience.or.kr/article/JAKO201926837943544.pdf) | — | Stays below the mandible, no passing through |
| Head during opening | Extends a little with the jaw | **Declared**, no numbers read | — | — | — |
| Gait, lower limb and pelvis | Time-normalized cycle at 101 samples | Measured curves, 24 young adults, treadmill trial T05 | [Fukuchi 2018](https://doi.org/10.6084/m9.figshare.5722711) | CC BY 4.0 | Foot doesn't slide in stance, `blender/motion_check.py` |
| Gait, trunk and arms | — | **Declared.** Fukuchi covers lower limbs and pelvis only | — | — | Rafael's judgement |
| Ribs | Pump handle above, bucket handle below | **Declared** rule; 5° at a deep breath | — | — | Chest expansion measured |
| Smile and blink | Fast closing, slower opening of the lid; blinks near the smile's end | No numbers: [Trutoiu's abstracts](https://ri.cmu.edu/?p=115350) give shape only | — | — | the fader comparison |
| Modiolus | Muscles converge at the corner of the mouth: zygomaticus major, orbicularis oris, buccinator, levator anguli oris, mentalis, depressor labii, depressor anguli oris, platysma, risorius. **Confirmed** | — | [Radiopaedia](https://radiopaedia.org/articles/modiolus-mouth), [2025 study](https://link.springer.com/article/10.1007/s00266-025-04696-0) | — | face muscles |
| Retaining ligaments | Orbital, zygomatic and mandibular bands from periosteum to dermis | Zygomatic ligament 66.5 mm and mandibular 114.8 mm from the tragus | [Cadaver study](https://avesis.mcbu.edu.tr/yayin/05770c7e-9d51-4615-96b6-957570185bf8/true-retaining-ligaments-of-face-as-surgical-landmarks-los-verdaderos-ligamentos-de-retencion-de-la-cara-como-marcadores-quirurgicos), abstract | — | soft tissue |
| FACS muscles | Standard AU mapping | The FACS manual is sold and wasn't read; only the widely published AU-to-muscle mapping is used | — | — | activation solve |

## Before the build: the anatomy research (2026-11-02)

**Proof of concept on Z-Anatomy, jaw only.** Review files are in
`G:\mocap-studio-downloads\review\2026-11-02\` (`z_anatomy_mandibula_vinculos.blend`,
`z_anatomy_mandibula_comparacao.png`). Scripts:
[`scratch/jaw-poc/`](../scratch/jaw-poc/README.md).

- **Works:** 26 parts of 13 muscle types were bound automatically from Z-Anatomy's
  origin and insertion patches, and the other 224 by proximity to bone. They now
  follow the jaw, and unrelated muscles stay still.
- **Doesn't yet:** to reach the target incisor drop (41.8 mm) it needed 38° of
  rotation, which looks too high, and the lower incisor moves back 36 mm. Muscle
  volume drifts widely: superficial masseter +34%, tongue −19%. Thin meshes
  measure unreliably. The neck tears and the hyoid stays fixed.

**Tissue doesn't bind skin to muscle.** It's a
[computational design add-on](https://extensions.blender.org/add-ons/tissue/)
(GPL-3.0+, 0.3.76, Blender 4.5 LTS and newer): tessellation, weight tools,
reaction-diffusion. Its page doesn't mention skin or soft tissue. It's tested here
for surface pattern and micro relief. Its binding comparison is in [skin.md](skin.md).

**Bones can't move most of the face.** Jaw, eyes and head are bone or rig problems.
A smile and a raised brow are muscles pulling skin. So tracking also has to become
muscle activation, which is underdetermined: 66 points and dozens of muscles. The
current plan restricts it to FACS groups and picks the least effort, and that needs
testing. OpenSeeFace doesn't measure the tongue, so it stays driven by phonemes.

**Z-Anatomy isn't validated.** Its own `TO DO List` asks to "correct and complete
the male model" and raises validation by a radiologist.

**There's no female in Z-Anatomy.** The CT dataset and BMF closed that gap for most bones.

### The repositories tested

Rafael asked for research into three repositories, with licensing set aside for the
investigation. They were opened and tested.

| Repository | What it is | Use to us |
|---|---|---|
| Z-Anatomy | Static atlas: 0 armatures, 0 shape keys, no skin. Has origin and insertion patches. Moving the mandible moves 38 of 4,569 meshes rigidly | Reference, to be validated |
| Z-Biomechanics (same repository) | 3 armatures, 22 actions, bones and insertion patches, no muscle bodies. Capture animations cross arms and legs when applied directly | Not a validation source |
| MuSkeMo | Path-point muscles between rigid bodies, for OpenSim. No face work. No license found; one file declares CC-BY-NC | None for the face |
| anatomy3d-blender | Geometry nodes drawing fibers, no simulation. Last commit on `main` 2022-12-30 | None for deformation |

- **The current face barely moves outside the mouth:** no channel animates
  `cheekSquint`, `eyeSquint` or the nose in the fader take, and no fader pose uses them.
- **The ARKit smile already pulls the right way:** the corner of the mouth moves about
  4° from the line of the zygomaticus major (one vertex, a different reference body).
- **Muscle activation from markers is published:**
  [Sifakis, Neverov and Fedkiw 2005](https://pages.cs.wisc.edu/~sifakis/papers/activations_siggraph_2005.pdf),
  a finite-element method. [FTS](https://pages.cs.wisc.edu/~sifakis/project_pages/fts.html)
  is its BSD code, but its page has no download link.
- **Liquid:** it captures conserved volume and tissue lag, but has no rest shape and no
  contraction along fibers. Both useful ideas can be kept without a fluid.
- **Rigging method:** [Rik Schutte's Blender Conference talk](https://youtu.be/_Ov0pFIOpug)
  combines bones, a lip guide and corrective shape keys, and builds brow shapes from
  weights, without sculpting. Pose Shape Keys is GPL-3.0+, and the Storm rig is CC-BY
  but needs a paid membership to download. It's a stylized character.

**License notes:** Z-Anatomy is CC BY-SA 4.0 and BodyParts3D
CC BY-SA 2.1 JP, with **some NC parts** (inner ear, kidney) that may be inside its zip, and
share-alike would pass to derived meshes. MuSkeMo has no license, so no permission by
default. anatomy3d-blender is GPL-2.0.

The fader character, checked on 2026-11-02:

- **Armature:** a metarig of 185 bones that deforms the mesh, including `jaw`,
  `chin`, `lip.T.*`, `lip.B.*`, `cheek.*`, `nose*` and `tongue*`, with matching
  vertex groups. The generated Rigify control rig isn't connected to the mesh.
- **Shapes:** the 52 ARKit shapes, generated by MPFB rather than made for this
  face, plus MPFB's character targets.
- **Bones already driving a pose:** the F pose pulls the `lip.B.*` bones back and
  up, and L and T raise the tongue bones. These values are a first pass.
- **Not used yet:** the other lip, chin and cheek bones.
