# human-model — mocap-studio

**Status:** Proposed by Rafael, 2026-11-02. Scope planned, epics listed, only the
first epic has task files. Nothing built yet. It comes out of the
[face-anatomy](../face-anatomy/face-anatomy.md) research.

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
`z_anatomy_mandibula_comparacao.png`, scripts in `human_model_poc_scripts\`).

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

## Good enough

The register is a list in this file, added by `references/5`. Each entry records
the element, what was compared, Rafael's verdict, the date and what would reopen it.
A verdict marks that element as enough for now, and it can move.

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
