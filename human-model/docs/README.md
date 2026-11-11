# The human model

A full-body male and female model built in layers from bones to skin, with no sculpting. Rafael declared this a **good first pass** on 2026-11-03: not perfect, and good enough to start testing by hand.

## Where to start

| You want to | Read |
|---|---|
| Understand the whole thing in five minutes | The rest of this page |
| Run it, know every command and parameter | [running.md](running.md) |
| **Change a character by hand in Blender** | **[character-editor.md](character-editor.md)** |
| See every slider and what follows a change | [character-controls.md](character-controls.md) |
| Understand how one individual gets built | [morphology.md](morphology.md) |
| Understand the bones, jaw, ribs and walking | [skeleton.md](skeleton.md) |
| Understand the muscles | [muscles.md](muscles.md) |
| See what a simulated muscle can do, and a thigh built from the inside out (experiments) | [muscle-physics.md](muscle-physics.md) |
| See the walking simulation's stages, drawn (open in draw.io, in Portuguese) | [diagrams/](diagrams/) |
| Understand how the skin moves | [skin.md](skin.md) |
| Connect recordings to the model | [drive.md](drive.md) |
| See what works, what doesn't, what's next | [status.md](status.md) |
| See why each decision went the way it did | [decisions.md](decisions.md) |
| Check a license or a measurement | [sources-and-validation.md](sources-and-validation.md) |

## How it works

A **recipe**, one small JSON file, defines a person. `build_model.py` turns it into a `.blend` file through five stages:

```
recipe.json
   │
   ├─ export     MPFB builds the skin and the rig from the sliders
   ├─ bones      real bones are placed inside that skin
   ├─ muscles    200 muscles are attached to those bones
   ├─ fields     each face muscle's pull on the skin is solved once, and stored
   └─ assemble   everything goes into one .blend, with controls
```

The layers in the finished file:

| Layer | What it is | What moves it |
|---|---|---|
| **Skin** | MPFB's mesh, 13,380 vertices | The rig's bones, plus one shape key per muscle |
| **Bones** | 181 meshes from CT scans and permissive models | The rig |
| **Muscles** | 200 spindles that keep their volume | Their attachment points, on bones or skin |
| **Controls** | `HM_controls`: 56 sliders for the jaw, breath, tongue and face muscles | You, or keyframes |

## The three things to understand first

**1. Identity is baked; expression is live.** Sliders such as height or nose width are read at build time, and the bones and fields are computed for that exact body. Changing the character means editing the recipe and rebuilding, about 4.5 minutes. Controls such as `jaw_open` or a face muscle are live in the file and can be animated.

**2. The inner layers are fitted to the skin, not the other way round.** The plan's idea was that skin results from what's under it. Today it's the reverse: MPFB makes the skin first, and bones and muscles are placed inside it. So a bigger gluteus or more muscle changes only the skin ([character-controls.md](character-controls.md#what-follows-a-change)).

**3. Muscles don't move the skin at run time.** A muscle's pull was solved once and stored as a shape key. At run time the shape key moves the skin, and the visible muscle body follows the skin. Removing the muscle bodies changes the skin by exactly 0 mm ([status.md](status.md)).

## Where things are

| What | Where |
|---|---|
| Code, data, these docs | `human-model/` in this repository |
| Source meshes and data | `G:\mocap-studio-downloads\models\` |
| Built models | `G:\mocap-studio-downloads\models\hm-build\` |
| Review images and videos | `G:\mocap-studio-downloads\review\2026-11-03\` |
| Open bugs | `initiatives/bugs/epics/human-model/` |
| The plan and task files | Removed when this was declared a first pass: `git log -- initiatives/human-model` |- [animation-body.md](animation-body.md): the new body for animation, its stages and what was measured.

