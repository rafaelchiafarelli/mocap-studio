# human-model — mocap-studio

**Status:** Current priority: the MVP is on hold until this model exists (Rafael,
2026-11-03). Proposed by him on 2026-11-02. All 7 epics implemented on 2026-11-03, on
the `human-model` branch, with decisions made on his behalf: see
[decisions](decisions.md). Every check that needs his judgement is still open, so this
folder stays and the branch isn't in `dev`.

**Goal:** our own full-body human model, male and female, built in layers from
bones to skin. Image and audio processing moves the bones, tongue, eyes and head,
and everything else follows because it's connected, so walking, speech and feeling
read as human.

**Why (Rafael):** reducing the anatomy too early risks "perder a humanidade do
caminhar, falar e transmitir um sentimento". Keep as much as possible "até não
precisarmos mais".

## Decisions by Rafael (2026-11-02)

- **Whole scope planned now:** the full body and both sexes, partly to understand
  how the two models differ.
- **Z-Anatomy is a reference, and it gets validated.** We don't derive the model by
  cutting it down. Its measurements and the behaviour of its movements are checked
  against other sources.
- **Layers are kept until data replaces them.** Bones stay until there's enough
  data not to need them, and muscles the same way. See "Retiring a layer".
- **"Good enough" is a moving target.** It's declared per element during
  development, not as one final bar. See "Good enough".
- **No genitalia** in either model.
- **Morphology comes from parameters** that shape the individual.
- **Tissue add-on for skin, alongside other experiments.** See the finding below.

## The layers

| Layer | Holds | Moved by |
|---|---|---|
| Input | OpenSeeFace, Parrot, mouth faders, body capture | Recordings |
| Translation | Actor's proportions and motion mapped to the character | Input |
| Bones | Skeleton as meshes, with joint rules | Translation |
| Eyes, tongue | Own controls | Translation |
| Muscles | Origin, insertion, line of pull, volume | Bones and activation |
| Soft tissue | Fat, fascia, retaining ligaments | Muscles |
| Skin | The surface the viewer sees | Soft tissue |
| Morphology | Parameters per individual, declared in a file | Declared per character |

## What we already know

**Proof of concept on Z-Anatomy, jaw only.** Review files are in
`G:\mocap-studio-downloads\review\2026-11-02\` (`z_anatomy_mandibula_vinculos.blend`,
`z_anatomy_mandibula_comparacao.png`). Scripts:
[`human-model/jaw-poc/`](../../human-model/jaw-poc/README.md).

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
for surface pattern and micro relief. The binding needs another tool, such as
Surface Deform or Mesh Deform. That comparison is an experiment, not a settled choice.

**Bones can't move most of the face.** Jaw, eyes and head are bone or rig problems.
A smile and a raised brow are muscles pulling skin. So tracking also has to become
muscle activation, which is underdetermined: 66 points and dozens of muscles. The
current plan restricts it to FACS groups and picks the least effort, and that needs
testing. OpenSeeFace doesn't measure the tongue, so it stays driven by phonemes.

**Z-Anatomy isn't validated.** Its own `TO DO List` asks to "correct and complete
the male model" and raises validation by a radiologist.

**There's no female in Z-Anatomy.** Its `TO DO List` lists that as future work. A
first search found no measured female anatomy with an open license:
[LHDL](https://mobile.hospimedica.com/surgical-techniques/articles/294730560/complete-human-female-3d-skeleton-model-is-available-for-download.amp.html)
is free only for nonprofit research, and marketplace models aren't openly licensed.
This is the largest data gap in the plan.

## From the anatomy research (2026-11-02)

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

**License notes to pick up in `references/1`:** Z-Anatomy is CC BY-SA 4.0 and BodyParts3D
CC BY-SA 2.1 JP, with **some NC parts** (inner ear, kidney) that may be inside its zip, and
share-alike would pass to derived meshes. MuSkeMo has no license, so no permission by
default. anatomy3d-blender is GPL-2.0.

What the character already has, checked on 2026-11-02:

- **Armature:** a metarig of 185 bones that deforms the mesh, including `jaw`,
  `chin`, `lip.T.*`, `lip.B.*`, `cheek.*`, `nose*` and `tongue*`, with matching
  vertex groups. The generated Rigify control rig isn't connected to the mesh.
- **Shapes:** the 52 ARKit shapes, generated by MPFB rather than made for this
  face, plus MPFB's character targets.
- **Bones already driving a pose:** the F pose pulls the `lip.B.*` bones back and
  up, and L and T raise the tongue bones. These values are a first pass.
- **Not used yet:** the other lip, chin and cheek bones.

**Open questions to bring to Rafael, none of them decided:**

1. **Which method solves the muscles?** Inverse kinematics usually solves joint angles.
   Solving activations is closer to inverse dynamics or optimization.
2. **Liquid or something else?** Variable-viscosity fluid was his starting idea. Muscle is
   usually modeled as a nearly incompressible soft solid or with Hill-type force models.
   Also say what Blender can do here: soft body, cloth, geometry nodes or an external solver.
3. **Is a full muscle model needed?** A simpler step may get most of the gain: lip and cheek
   bones, corrective shapes, jiggle and delay, wrinkles. The fader test got much of its gain
   from timing and shapes, without anatomy.

## Good-enough register

An element's verdict comes only from Rafael, never from a metric alone. A verdict marks
it as enough for now, and it can move.

| Element | What was compared | Verdict (Rafael's words) | Date | What would reopen it |
|---|---|---|---|---|
| Walking | `caminhar_masculino_ossos_e_pele.mp4` | Waiting | — | — |
| Muscle smile | `sorriso_neutro_arkit_musculo.png`, the current ARKit smile | Waiting | — | — |
| Face on a recording | `comparacao_faders_hibrido_musculos.mp4`, three variants | Waiting | — | — |
| Six individuals | `seis_individuos_pele.png`, `seis_individuos_ossos_musculos.png` | Waiting | — | — |

For faces, new work still has to beat the mouth faders on the same recording, in
Rafael's judgement.

## Retiring a layer

A layer can leave the model only when all of these hold:

1. The layers above it reproduce its effect from stored data, such as baked shapes
   or a fitted model.
2. A side-by-side on recordings it was not fitted to shows no loss, in Rafael's
   judgement.
3. The data and the method to rebuild it stay available.

Removing a layer to gain speed is a different decision and has to be presented as a
loss of detail.

## Where it lives

This plan stays here. Its tools go in [`human-model/`](../../human-model/CLAUDE.md) at the root
of this repository, not in a separate repository for now (Rafael, 2026-11-03).

## Constraints

- **Nobody can sculpt.** Everything is built with tools.
- **No AI generating final face pixels.**
- **Keep MPFB's topology on the skin** unless Rafael decides otherwise. Its
  parameter targets depend on it (to confirm in `skin`).
- **Licenses:** the rule in the `mocap-workflow` skill, including assets and data.
  For this investigation Rafael set licensing aside; `references/1` picks it up
  before anything is derived.
- **Consent:** the fader recording shows a real person and is a private test.
- **Repositories stay film-neutral.** A character's parameters live in the film root.
- **Local compute:** measure before adopting any model that runs on the RTX 4080.

## Risks

- **Size:** it's very large for a few hours a week. Every epic has its own check so
  it can stop without losing what was built.
- **Speed:** a full body in layers may be slow in Blender (Z-Anatomy's muscles alone
  have about 1 million vertices). `skin` and `retirement` measure this.
- **The viewer sees only skin.** Until `skin` passes on one expression, nothing is
  visibly better.
- **Body capture quality.** Rafael judges the current results bad and hasn't given
  details yet. A better model can't fix bad input, so `drive` starts by asking
  what's wrong.

**Initiative gate:** to be defined with Rafael. It moves with the good-enough
register.

**Out of scope:** genitalia, AI-generated final pixels, Unreal and MetaHuman (parked).
