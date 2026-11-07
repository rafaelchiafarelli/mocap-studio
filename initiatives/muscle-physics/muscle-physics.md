# muscle-physics

**Goal:** learn what a physically simulated muscle can and can't do in Blender, starting from the smallest possible case, before deciding anything about the human model (Rafael, 2026-11-04). Nothing in the current model is removed or changed by this initiative.

Since 2026-11-07 it also tests building tissue from the inside out, bone then muscle then fat then skin, simulated on the GPU outside Blender. Rafael accepted the workflow it would serve: a fast model blocks the scene, and the realistic one is simulated overnight in batches.

**Gate:** Rafael's verdict on each experiment. There is no decision yet to replace the spindles in `human-model/docs/muscles.md`, or to change how the model's skin is made.

## Epics

- `single-muscle`: one muscle, one load. Done.
- `thigh`: one thigh in layers, simulated on the GPU through a walking step. Done.
- `body-at-rest`: the whole woman in layers, standing still. Done.
- `inside-out-skin`: the skin pushed out over the bones. Order in [epics/README.md](epics/README.md).

## Next, proposed and not planned

- **The breast on the body** (Rafael, 2026-11-05: "vamos portar essa solução para o restante do código"). The breast preset moving the model's breasts while it walks. To agree before planning: which patch of skin, how it hangs from the rib cage, how the skin around it follows, its cost per frame, and the body's shape, which another session is discussing.
