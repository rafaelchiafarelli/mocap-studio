# human-model — epics (execution order)

Each epic's task files were written when it started, because their contracts depend on earlier results.

Inside each building epic the work goes in the same order: head and neck, then
trunk, then limbs. Male comes first, because that's where there's a reference;
`morphology` then adds the female.

## 1. references — what we measure against

Task files in `references/tasks/`.

1. `source-licenses` — what each source allows, before anything is derived
2. `structure-inventory` — what stays, what's rebuilt, what's left out
3. `measurement-validation` — Z-Anatomy's measurements against other sources
4. `motion-validation` — how each joint should move, with sources
5. `good-enough-register` — the register format

**Check:** Rafael approves the inventory and the validation sources. *Open: decided on his behalf.*

## 2. skeleton — bones and joints

1. `head-bones` — skull, jaw, teeth, hyoid, eyes and tongue inside the MPFB head
2. `jaw-motion` — rotation then sliding, per Posselt; the hyoid and head follow
3. `spine-ribs-breathing` — spine, rib cage and breathing
4. `shoulders-arms-hands`
5. `pelvis-legs-feet`
6. `motion-check` — ranges against `references/4`, and no bones passing through
   each other

**Check:** a full range of motion without collisions, and walking looks right to Rafael. *Collisions pass, apart from contact at joints. Walking open.*

## 3. muscles — the actuators

1. `muscle-builder` — a tool that builds one muscle from origin, insertion and volume
2. `volume-behaviour` — shortening bulges and stretching thins, with stable volume
3. `jaw-muscles`
4. `face-muscles` — including the anchor points muscles pull in skin, such as the
   modiolus
5. `contraction-test` — one real contraction (frontalis, then zygomaticus)
6. `tongue` — own controls, with internal structure to be researched
7. `trunk-and-limb-muscles`

**Check:** volume stays in a range to be agreed, and nothing tears. *Proposed range ±5%; measured within 0.1%. Open: the range is Rafael's.*

## 4. skin — what the viewer sees

1. `binding-comparison` — Surface Deform, Mesh Deform and others on one smile
2. `tissue-experiment` — Tissue for pattern and micro relief
3. `soft-tissue` — fat, fascia and retaining ligaments as anchors
4. `folds` — nasolabial fold and other wrinkles, geometry or maps
5. `body-skin` — shoulder, elbow, abdomen, breathing
6. `speed-measure`

**Check, and the plan's biggest bet:** the muscle-driven smile beats the current
smile, in Rafael's judgement. If it doesn't, stop and rethink before the next epics. *Open. The next epics went ahead on his instruction to implement everything.*

## 5. drive — recordings move the model

1. `body-input-review` — ask Rafael what's wrong with the body results first
2. `actor-to-character` — mapping proportions and motion
3. `face-bones` — OpenSeeFace to jaw, eyes and head
4. `tongue-from-phonemes` — Parrot and known-words alignment
5. `muscle-activation` — landmarks to FACS groups, testing the least-effort idea
6. `body-drive` — capture to skeleton
7. `fader-comparison` — same recording as the mouth faders

Contracts: new messages or files between applications start in `mocap-contracts`.

**Check:** beats the mouth faders on the same recording, in Rafael's judgement. *Open. Muscles alone don't, in this session's reading; the hybrid is his call.*

## 6. morphology — parameters and the female model

1. `parameter-set` — which MPFB parameters we keep, add or derive
2. `layers-follow` — bones, muscles and tissue follow the parameters
3. `female-data` — close the gap in measured female data
4. `female-model`
5. `male-female-differences` — a sourced, measured report on how the two differ
6. `character-declaration` — the per-character file, as a `mocap-contracts` task

**Check:** three different individuals of each sex work with no manual repair. *All six build, with no unrelated bones colliding and volume held; see bug `human-model/2`.*

## 7. retirement — keeping only what's needed

1. `bake-to-shapes` — store what the muscles do as data
2. `fit-from-data` — a fitted model, if measured to run well on the RTX 4080
3. `retire-trial` — one layer, under the rule in `human-model.md`

**Check:** Rafael approves each retirement. Nothing is retired by default. *Nothing retired.*

An epic only merges up into `epics` once all its tasks are `-done` and the suite is green. These epics merged with Rafael's checks open, on his instruction, and stop at the `human-model` branch.
