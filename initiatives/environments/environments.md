# environments — mocap-studio

**Status:** Proposed (Rafael's direction, 2026-11-01). Nothing is built or
tested yet, and there are no epics or tasks. Rafael hasn't approved scoping.

**Goal:** a free, controllable way to build the sets a free camera needs. Rafael
gives creative direction without nitpicking every object, and the agent does the
assembly.

**Why this shape:** Rafael has a few hours a week for this, so a set can't be
hand-built object by object, and there's no time for a long evaluation of tools.
A free camera also means many more things have to exist in a set than a fixed
camera would need.

## The system Rafael asked for

1. **Library:** a big open-source or free collection of designed objects.
2. **Fit:** a tool that adapts an object to the scene: resize, change materials,
   add shaders.
3. **Relationships:** objects linked so an AI can work with them, for example
   "put the cloth on top of the table, beside the character's hand".
4. **Motion:** interaction rules for things that move, by physics or simulation:
   a clock, a cloth, clothing.

No single tool was found that does all four. Blender covers most of it for free,
and the relationships layer is the only really new piece. None of the claims
below have been tried on this project.

## What already exists in the project

[`mocap-blender/methodology_study.md`](../../mocap-blender/methodology_study.md)
already holds much of this. It's a study, not a plan. This initiative builds on
it rather than replacing it:

- **Recipes and a runner:** sets are built from a layout file (`set.yaml`) with
  named marks. The AI writes text and code, and deterministic scripts do the
  build, with no AI at build time.
- **Order of preference:** reuse from the library, download, generate from a
  recipe. "Make by hand" no longer applies to anything needing sculpting, because
  nobody available can sculpt.
- **Curated tools (checked 2026-10-07, each still to be confirmed on 5.2):**
  built-in scatter, sky and volumes; A.N.T. Landscape; Modular Tree; Blosm;
  ambientCG; BlenderKit; Poly Haven by hand.
- **Known gap:** buildings and interiors have no maintained free generator on
  Blender 5.x.

### Conflicts to clear up

The `integration` initiative in `mocap-blender` is older than the study and
disagrees with it. The study already says that initiative must be reworked.

- [`sets/1-infinigen-exteriors`](../../mocap-blender/initiatives/integration/epics/sets/tasks/1-infinigen-exteriors.md)
  and [`sets/2-infinigen-indoors`](../../mocap-blender/initiatives/integration/epics/sets/tasks/2-infinigen-indoors.md)
  plan to use Infinigen, which the study moved to its watch list (Blender 4.2,
  last release 2024).
- [`assets/1-poly-haven`](../../mocap-blender/initiatives/integration/epics/assets/tasks/1-poly-haven.md)
  fetches through BlenderMCP. Poly Haven's API is non-commercial only, so if
  BlenderMCP uses it, this breaks the license rule. Not yet checked.

## Rejected

| Option | Why (Rafael, 2026-11-01) |
|---|---|
| World Labs Marble | A hosted AI generator, so it will never be free. Rafael has a few hours a week, not a month, to spend on evaluating it |
| Gaussian splats | Would need a physical set, and Rafael doesn't have one |

The research also found open-weight world generators (NVIDIA Lyra 2.0, Tencent
HY-World 2.0). Their licenses and VRAM needs were not checked, and they are not
candidates under this direction.

## Proposed design

| Piece | Covered by | Status |
|---|---|---|
| Library | BlenderKit, ambientCG, ShareTextures, Poly Haven by hand | Exists. BlenderKit's automation and Blender 5 support are unverified |
| Catalog | One entry per approved asset: tags, real size, license, usable surfaces | To build. The AI chooses only from checked assets |
| Fit | Blender scripts: real-world scale, material swaps, shaders | To write, small |
| Relationships | Set file with named surfaces and rules, plus a placement script | **The new piece** |
| Room shells | A simple parametric generator for walls, windows and doors | To write. Answers the known gap |
| Motion | Keyframes or drivers, rigid-body and cloth simulation, props attached to bones | Exists in Blender. Each needs setup rules and testing |

The AI picks relationships and the script calculates positions, so the AI never
guesses coordinates. Research systems such as Holodeck split the work the same
way, but we don't depend on their code, whose licenses weren't checked.

Sketch only; **the format is not defined** (open question 5 in the study):

```yaml
- id: cloth
  asset: kitchen_towel_01
  on: table.top
  near: { target: character.hand_r, at_frame: 120, distance_cm: 8 }
  motion: cloth_sim
- id: clock
  asset: wall_clock_03
  on: wall_north
  motion: { type: clock, time: "21:40" }
```

## Expected difficulties

- **Quality:** free libraries vary, and weak props will show next to a photoreal
  character. The first batch needs choosing by eye, once per asset.
- **Clothing:** the hardest motion item. It depends on the character work, so it
  comes last and is coordinated with that work.
- **Hand contact:** placing or picking up a prop depends on clean hand motion
  from capture. Older Blender bug reports describe problems with animating the
  Child Of constraint. Check whether they still apply on 5.2.
- **BlenderKit licenses:** assets are royalty-free or CC0, and royalty-free isn't
  on the skill's list of example licenses. The study accepts it with a per-asset
  check. Record each asset's license in the catalog.

## First goal, if approved

One small scene: a table, a cloth, a wall clock and a lamp, with a character's
hand beside the cloth. It should prove all four pieces end to end from a text
file. This doesn't change the MVP's blockout set.

**Gate:** rebuilding from the set file gives the same scene, a free camera can
orbit it, and Rafael accepts the look.

## Open decisions for Rafael

1. Approve scoping this into epics and tasks?
2. Where does it live? The study suggests a new film-toolbox repository
   (submodule of `mocap-studio`), with `mocap-blender` staying the P5 importer.
3. Does this replace the `sets` epic of `integration` in `mocap-blender`?

**Out of scope:** film-specific sets (they belong in the film root), the face
problem in the [initiatives README](../README.md), and any paid tool.

**Cross-repository:** `set.yaml` becomes a `mocap-contracts` task if another
application needs to read it. New asset or tool versions go in `DEPENDENCIES.md`.

## Sources (researched 2026-11-01)

- [BlenderKit free asset count (CG Channel)](https://www.cgchannel.com/2026/08/get-60000-free-3d-assets-for-maya-godot-and-rhino-from-blendkit/)
- [BlenderKit FAQ](https://www.blenderkit.com/faq-frequently-asked-questions/)
- [ShareTextures CC0 models](https://www.blendernation.com/2023/09/21/free-cc0-3d-models-by-sharetextures/)
- [Holodeck paper](https://arxiv.org/pdf/2312.09067)
- [Blender Child Of constraint](https://docs.blender.org/manual/id/dev/animation/constraints/relationship/child_of.html)
- [Marble export docs](https://docs.worldlabs.ai/marble/export/gaussian-splat)
