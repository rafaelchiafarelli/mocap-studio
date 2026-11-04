# Decisions

The first pass was implemented on 2026-11-03, with every decision taken on my recommendation, as you asked. This records what the options were. Current state and open work: [status.md](status.md).

Each table gives the options I weighed. The chosen one is first.

### Sources and licenses

| Decision | Options | Why | To reverse |
|---|---|---|---|
| **Z-Anatomy stays out of the model** | Out, numbers only in reports · Measure it and build from the measurements · Derive meshes and accept share-alike | This removes your legal question rather than answering it, so no lawyer is needed. It has NC parts too | Allowed only with legal advice |
| **Bones from CT labels** | TotalSegmentator (CC BY 4.0) · Procedural bones · Marketplace models · Visible Human directly | Real anatomy, both sexes, 1,228 scans. Procedural can't match it, since nobody sculpts. **You must credit it:** [`ATTRIBUTION.md`](../ATTRIBUTION.md) | Replace `bonelib.py` |
| **Legs and feet from BMF** (zlib), for both sexes | BMF · Rajagopal's meshes · CT labels | CT femurs are cut at the knee and the labels have no shin or foot. Rajagopal's femur has only 132 points. **Loss:** male legs have female shape | Swap per sex |
| **Forearm and hand from Rajagopal** (MIT) | Rajagopal · Procedural · The CT "appendicular" model | That CT model needs a paid license. **Loss:** low resolution, not female-specific. The MIT grant was read on SimTK, but the files came from `opensim-models`, because SimTK needs a login | Log in to SimTK and compare |
| **Hyoid and larynx parametric** | Parametric · Leave out · A Z-Anatomy copy | No allowed mesh found. **Loss:** the larynx is a simple shield, and it looks like a block | Replace when a source appears |
| **Donors s1045 (male, 62) and s0933 (female, 55)** | These · The younger s0224 and s0790 | Only trauma scans cover the whole body. s0224 is recorded as trauma, and s0790's femurs and hips are cut. s1045 records no pathology. s0933 records bleeding, not bone damage. No fracture check was done beyond looking | One line in `bonelib.py` |
| **Dataset read by byte range** | Only the files needed (508 MB) · Whole zip (23.6 GB, about 11 hours) | Same data. The whole zip can still be fetched | — |
| **MuSkeMo, anatomy3d-blender, Pose Shape Keys not used** | Not used · Used | No license found, no deformation, and no need, respectively | — |
| **ANSUR II for validation only** | Validation · Build from it | "Public release" isn't a formal license, and nothing ships from it | — |

### Skeleton

| Decision | Options | Why | To reverse |
|---|---|---|---|
| **Keep MPFB's rig and skin, add our bones** | Add to it · Our own rig | Your constraint: its targets depend on the topology. It also gave a ready set of named face landmarks | — |
| **Each bone rigid, plus a scale** | Rigid · Bend to fit | Keeps measured shapes. **Cost:** bones don't follow an individual's shape, only size | — |
| **True hip joints:** thigh heads moved into the sockets | Move the rig · Keep MPFB's | MPFB's hips are wider than a real pelvis allows. The skin stays bound | `rig_edits` |
| **Pelvis sized from the hips' skin** | Skin · Rig hip distance | The rig's distance made a pelvis 1.5 times too large | — |
| **Spine placed from the back's skin** | Skin · Rig's spine | The rig's spine runs through the middle of the body | — |
| **Skull fitted from the rig's jaw hinge** | Hinge · Box only · Chin match | The scanner's head rest tilts the head, and the chin match gave a wrong jaw. **Limits:** thin facial bones are lumps at 1.5 mm, MPFB's eyes and teeth don't sit exactly in the donor's sockets | — |
| **Jaw:** rotate, then slide; Travers 2000 targets | Two phases · Rotation only (your proof of concept) | Reaches 46.6 mm with 11.9 mm of slide. Rotation is 32° male, down from 38°, though still 38.5° female. Incisor goes back 23 mm, down from 36 | `jaw.py` |
| **Declared, no source:** slide starts at 20 mm, eminence 35°, hyoid follow, 4° head extension, 9° ribs, arm swing 18°, elbow 18°, walk cycle 1.1 s, shoulder and spine limits | Declare and mark · Stop and research each | Each is marked in the code and in [sources](sources-and-validation.md#motion), to be replaced | Constants |
| **Joint limits as data, not Blender constraints** | Data · Constraints | Faster to build. **Cost:** a hand pose can pass them (bug `human-model/3`) | Add constraints |

### Muscles

| Decision | Options | Why | To reverse |
|---|---|---|---|
| **Spindles between points** | Spindles · Full meshes · Fibers | Volume holds exactly, and it's light: about 16 thousand vertices against 1 million. **Loss, against your rule on detail:** no fibers, and wide sheets such as trapezius are single spindles, so the trunk looks sparse | Add sheets per muscle |
| **Volume through Stretch To** | Constraint · Simulation | Exact, with no simulation cost | — |
| **Leg muscles from Rajagopal** (80, measured); **trunk, arm, face, jaw declared** by me from anatomy descriptions | Data where it exists · Declare all | The declared coordinates are the least validated part of the model. Against CT: gluteus medius matches, gluteus maximus is 54% too large, back muscles too small | `data/muscles.json` |
| **A separate armature for muscles** | Separate · Main rig | On the main rig it's a dependency cycle | — |
| **Tongue: 3 bones, 4 controls** | Bones · Volume-preserving model | **Loss:** can't groove or narrow. It's the largest simplification in the head | — |

### Skin

| Decision | Options | Why | To reverse |
|---|---|---|---|
| **Your liquid idea and FEM:** neither. A smooth sheet solved once per muscle, stored as a shape key | Sheet · Fluid · FEM (Sifakis) · Hill-type model | Sheet is cheap, and it runs anywhere. **It's the core limit:** no physics at run time, and it sums linearly. FTS has no download. See [skin.md](skin.md#your-three-open-questions) | Replace `softtissue.py` |
| **Direct shape keys** over Surface Deform or Mesh Deform | Measured: 0 error · 0.68 mm RMS, 10.8 max · 1.50 mm RMS, 10.1 max | We already have the displacement, so a shell only loses detail | — |
| **Uniform mesh weights** | Uniform · Cotangent | Cotangent tore the lips | — |
| **Ligaments as soft anchors; bulge as a surface rule** | Rule · Real fat layers | The nasolabial fold emerges from this. **Loss:** no fascia, no fat compartments | — |
| **Forehead and eye lines as geometry** | Geometry · Normal maps | Quick to test. **Limit:** the mesh is barely fine enough | — |
| **Not Tissue for micro relief** | Maps · Tissue | **Inconclusive:** its operator cancelled when run without the interface. But it adds geometry per face, which is too costly for pores. It's installed in your portable Blender | Remove it there |

### Drive

| Decision | Options | Why | To reverse |
|---|---|---|---|
| **Effort 1e-5** for the least-effort solve | 0 · 1e-5 · 1e-4 · 1e-3 | 60% less activation for a small rise in residual. 1e-4 stops the face | One constant |
| **Compare on your character and recording** | Same file · A new character | The only fair test, thanks to shared topology | — |
| **Added a hybrid** the plan didn't ask for | Hybrid · Muscles only | Replacement wasn't supported (no ARKit shape reached the limit), and the plan's finding was that the face barely moves outside the mouth | Drop it |
| **Body as bone directions; no filter** | Directions · Positions · Filtered | Keeps proportions. No filter, so you can judge the input. **Loss:** no twist | — |
| **Capture test on the FreeMoCap fixture** | Fixture · Your recordings | It was at hand. It's 60 frames of someone else's recording, AGPL, for tests only | Rerun on yours |

### Morphology and retirement

| Decision | Options | Why | To reverse |
|---|---|---|---|
| **Six test people** at extremes of height, weight, muscle and age | These · Real characters | Repositories stay film-neutral | — |
| **`CharacterBody` on a branch, not released** | Branch · Tag and bump the pointer | It's a shared contract, so it's yours to release | — |
| **Nothing retired** | Keep · Retire muscle bodies | Your rule. Removing them changes the skin by 0 mm, which shows they aren't connected, not that they aren't needed | — |
| **Fields not compressed** | Keep 44 · PCA | They cost 4.4 MB and little time, and compression moves a lip or lid by millimetres | — |

### Process

| Decision | Why |
|---|---|
| **I continued past the "stop and rethink" check.** | You asked for everything, and you review afterwards. So the later epics rest on an unapproved bet |
| **Epics merged with your checks open.** | Later epics needed the earlier ones. You then asked for the merge to `dev`, and declared a first pass |
| **Merged leaf branches were deleted locally;** nothing was pushed. | The chain reuses the name `tasks` per epic. The merges keep the history |
| **As-built docs were written per epic, not per task,** and some task commits hold only results, because `assemble.py` is shared. | A departure from your workflow. Tell me if you want it redone |
| **Libraries in a Docker image with a hashed lockfile,** per `DEPENDENCIES.md`; 41 tests. | Rule B. Blender scripts have no unit tests: they were checked by running them |
| **Sources and builds on `G:`:** about 1.8 GB in `models/`. | Large files stay out of git |
