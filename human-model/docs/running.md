# Running the human model

Every command here was run from a clean folder on 2026-11-03. Run them from WSL at the repository's root.

## Setup, once

| You need | How to check or get it |
|---|---|
| WSL with Python 3 | `python3 -V` |
| Docker running | `docker ps`. `hm.sh` builds its image the first time |
| Blender 5.2.2 on Windows | `apps/blender/5.2.2/` on `G:`, or set `HM_BLENDER` to another `blender.exe` |
| MPFB 2.0.18 and its system assets, installed in that Blender | See `DEPENDENCIES.md`. Without them the build fails on `bl_ext.user_default.mpfb` |
| The source data | `python3 -I human-model/tools/fetch_sources.py`. Keeps what's already there |

Tests: `human-model/hm.sh pytest`

## Build a person

```sh
python3 human-model/build_model.py human-model/data/recipes/male.json /mnt/g/mocap-studio-downloads/models/hm-build/male
```

| Argument | Meaning |
|---|---|
| `RECIPE` | The person's JSON file, below |
| `OUT_DIR` | Must be under `/mnt/g` or `/tmp`, the folders Docker can see |
| `--from STAGE` | Start at `export`, `bones`, `muscles`, `fields` or `assemble`. Earlier results must already be in `OUT_DIR` |
| `--to STAGE` | Stop after this stage |

It takes about 4.5 minutes. Which stage to restart from:

| You changed | Run from |
|---|---|
| The recipe's macros or targets | `export` |
| Bone code | `bones` |
| `data/muscles.json` | `muscles` |
| `softtissue.py` or `bodyskin.py` | `fields` |
| `assemble.py` or `hmmuscles.py` | `assemble` |

**What it writes, as `OUT_DIR/<name>.*`:**

| File | Contents |
|---|---|
| `<name>.blend` | **The model** |
| `.export.npz`, `.export.json` | Skin vertices, polygons, rig bones, vertex groups |
| `.bones.npz`, `.bones.npz.json` | Every bone's mesh and parent; anchors, jaw table, joint limits |
| `.bones.npz.containment.json` | Share of each bone's checked points outside the skin |
| `.muscles.json` | Every muscle's points, parents and radius |
| `.fields.npz` | Skin displacement per muscle, and the body shapes |

If `bonelib.py` or a donor changes, delete `ct_library_<sex>.pkl` in `G:\mocap-studio-downloads\models\hm-cache\`.

## What to prepare: the recipe

The only input you need to write. Full example in [character-controls.md](character-controls.md).

| Field | Required | Values | Meaning |
|---|---|---|---|
| `name` | Yes | Text | Names the output files and the objects in the `.blend` |
| `sex` | Yes | `male` or `female` | Picks the CT donor and the joint limits. Keep it in step with `gender` |
| `macros.gender` | Yes | 1.0 male, 0.0 female | MPFB's sex slider. In-between values are untested |
| `macros.age` | Yes | 0.5 to 1.0 for adults | **Below 0.5 it's a child's body** |
| `macros.height` | Yes | 0 to 1 | Not linear: see the table in [character-controls.md](character-controls.md#real-units) |
| `macros.weight`, `muscle`, `proportions` | Yes | 0 to 1 | Body build |
| `macros.cupsize`, `firmness` | Yes | 0 to 1 | Breasts |
| `macros.race` | Yes | `african`, `asian`, `caucasian`, summing to 1 | MPFB's ancestry blend |
| `targets` | No | `{"target-name": 0 to 1}` | Any of MPFB's morph targets. Stay around 0.8 or below |
| `assets` | No | `eyes`, `teeth`, `tongue` paths | MPFB assets. **Skin material, hair and clothes aren't applied yet** |

`human-model/data/recipes/` has a neutral `male.json` and `female.json`, and six extremes in `test_people/`.

## What a built file contains

| Name | What it is |
|---|---|
| `<name>.skin` | The skin |
| `HM_rig` | The main armature: MPFB's 185 bones, plus `hm_jaw`, `hm_hyoid`, `hm_larynx`, `hm_sternum`, 24 `hm_rib_*` |
| `HM_controls` | An empty holding the control sliders as custom properties |
| `HM_bones` | Collection of the 181 bone meshes, each parented to a rig bone |
| `HM_muscles` | Collection: the `HM_muscles` mesh, and `HM_muscle_rig` |
| `HM_muscle_targets` | Empties the muscles attach to (about 490) |
| `<name>.high-poly`, `.teeth_base`, `.tongue01` | Eyes, teeth, tongue |

`blender/list_controls.py` writes the exact list for any file.

### Controls

All are custom properties on `HM_controls`, with simple-expression drivers, so they work with auto-run off.

| Control | Range | What it does |
|---|---|---|
| `jaw_open` | 0 to 1 | Opens the jaw: rotation, then sliding. Hyoid and head follow |
| `breath` | 0 to 1 | Ribs, sternum, chest and belly skin |
| `tongue_tip_raise`, `tongue_body_raise`, `tongue_back_raise`, `tongue_protrude` | −1 to 1 | The tongue's three bones |
| `m_<muscle>_L`, `m_<muscle>_R` | 0 to 1 | 22 face muscles per side: list in [muscles.md](muscles.md#face-muscles) |
| `b_biceps_*`, `b_triceps_*`, `b_deltoid_*` | — | **Do nothing.** They're leftovers: joint angles drive those shapes, so a new session can drop them |

Shape keys are `F_<muscle>_<side>` (face) and `B_<name>` (body). Drive the control, not the key.

### Bones and joints

Pose `HM_rig` directly. Main bones: `spine`, `spine.001` to `.006`, `thigh.*`, `shin.*`, `foot.*`, `toe.*`, `shoulder.*`, `upper_arm.*`, `forearm.*`, `hand.*`, fingers `f_index.01.*` and so on, `palm.*`, `thumb.*`.

Joint limits are stored as the bone property `hm_limit_deg` and **not enforced**: a new session could turn them into Limit Rotation constraints. Note that the bones' own axes differ: `blender/posing.py` converts rotations from the rest pose's axes, where +X is the body's left, +Y its back and +Z up. In those axes hip flexion is negative about X, and knee flexion positive.

## What's live and what's baked

This decides how handles have to work.

| Change | In a built file? | How |
|---|---|---|
| Jaw, breath, tongue, face muscles | **Live** | Set or key the control |
| Joint poses | **Live** | Pose `HM_rig` |
| Height, weight, nose, lips, ribs, and so on | **Baked** | Edit the recipe and rebuild. Moving those shape keys in the file moves the skin only, and bones, muscles and fields stay behind |
| Muscle contraction amounts, ligaments | **Baked** | Edit the data or constants, rebuild from `muscles` or `fields` |

**The character editor** does this loop from a panel: sliders on a plain MPFB human, for instant feedback; save the recipe; rebuild every layer with `build_model.py`. See [character-editor.md](character-editor.md). It reads only macros and named targets, so nothing else done to a human by hand reaches the recipe.

The editor is installed with `python3 human-model/install_editor.py`, with Blender closed.

## Running a script inside Blender

```sh
python3 human-model/blender_run.py [--blend FILE] SCRIPT [ARG ...]
```

Runs Windows Blender in the background with auto-run off. Arguments starting with `/` become Windows paths.

| Script in `human-model/blender/` | Needs `--blend` | Arguments | What it does |
|---|---|---|---|
| `render_views.py` | Yes | `PREFIX VIEWS [skin=0] [muscles=0] [control=value ...]` | Stills. Views: `body`, `side`, `head`, `headside`, comma-separated |
| `render_seq.py` | Yes | `OUT_DIR walkside\|head START END [skin=0] [res=WxH]` | A frame sequence |
| `list_controls.py` | Yes | `OUT.json` | Everything the file offers |
| `walk.py` | Yes | `data/gait_walk.json male\|female OUT.blend [CYCLES]` | Keys measured walking |
| `motion_check.py` | Yes | `OUT.json` | Joints at their limits, bone overlap |
| `volume_check.py` | Yes | `OUT.json` | Muscle volume in test poses |
| `breath_check.py` | Yes | `OUT.json` | Chest expansion |
| `contraction_check.py` | Yes | `OUT.json` | Frontalis and zygomaticus, measured |
| `speed_measure.py` | Yes, a walk file | `OUT.json` | Frames per second by layer |
| `retire_trial.py` | Yes, a walk file | `OUT.json` | Removes muscle bodies, measures the skin |
| `recipe_from_file.py` | Yes | `BODY_OBJECT NAME SEX OUT.json` | Reads a human back into a recipe |
| `editor_check.py` | Yes, a built model | `RECIPE.json OUT_DIR` | Checks the installed editor without its interface. Needs `install_editor.py` first |
| `body_drive.py` | Yes | `MOTION.json OUT.blend` | Keys capture onto the rig |
| `feature_sheet.py` | No | `RECIPE OUT_DIR LIST.json [head\|body]` | Renders what each target does |
| `macro_sweep.py` | No | `OUT.json` | Real sizes per macro slider |
| `binding_compare.py` | Yes | `OUT.json` | Surface and Mesh Deform against the field |
| `tissue_experiment.py` | Yes | `ADDON.zip PREFIX` | Tissue on a skin patch |

Examples:

```sh
M=/mnt/g/mocap-studio-downloads/models/hm-build/male

# a still with the mouth open and a half smile
python3 human-model/blender_run.py --blend $M/male.blend human-model/blender/render_views.py /tmp/still head jaw_open=0.3 m_zygomaticus_major_L=0.5 m_zygomaticus_major_R=0.5

# bones only, no muscles
python3 human-model/blender_run.py --blend $M/male.blend human-model/blender/render_views.py /tmp/bones body,side skin=0 muscles=0

# walking
python3 human-model/blender_run.py --blend $M/male.blend human-model/blender/walk.py human-model/data/gait_walk.json male $M/walk.blend
```

## Running a tool in Docker

```sh
human-model/hm.sh python human-model/tools/<script>.py ARGS
```

Paths must be under the repository (relative), `/mnt/g` or `/tmp`.

| Script | Arguments | What it does |
|---|---|---|
| `build_bones.py` | `SEX EXPORT.npz EXPORT.json OUT.npz [CACHE_DIR]` | The fitted skeleton |
| `spec.py` | `BONES.npz SEX` | Adds jaw table and limits |
| `build_muscles.py` | `EXPORT.npz EXPORT.json BONES.npz OUT.json SEX` | The muscle list |
| `build_fields.py` | `EXPORT.npz EXPORT.json BONES.npz MUSCLES.json OUT.npz` | Skin fields and body shapes |
| `body_motion.py` | `BODY_3D.npy BODY_3D.csv OUT.json REPORT.json FPS [HIP_HEIGHT_M]` | Capture to bone directions, and a quality report |
| `solve_take.py` | `FIELDS TAKE EXPORT.npz EXPORT.json MOUTH_DATA TRACKER.csv OUT.npz IPD_M REPORT.json` | A take's activations |
| `fit_fields.py` | `FIELDS.npz ACTIV.npz REPORT.json` | How far fields compress |
| `debug_view.py` | `BONES.npz EXPORT.npz OUT.png [x0 x1 y0 y1 z0 z1]` | Quick fit check, no Blender |
| `contact_sheet.py` | `IN_DIR OUT.png COLUMNS [f\|s]` | A labelled grid |
| `morph_set.py` | `OUT_DIR` | Writes the test people |
| `ct_stats.py`, `validation_table.py`, `sex_report.py` | See their first line | The tables in these docs |
| `make_gait_table.py` | `FUKUCHI_DIR OUT.json` | Writes `data/gait_walk.json` |

`fetch_sources.py` and `pull_ct_sample.py` need no Docker: run them with `python3 -I`.

## Using an existing character file

For a character that already exists as a `.blend`, built with MPFB's topology and metarig:

```sh
A=character.blend; B=/mnt/g/.../out/character
python3 human-model/blender_run.py --blend $A human-model/blender/export_blend.py BODY_OBJECT RIG_OBJECT $B.export.npz $B.export.json
human-model/hm.sh python human-model/tools/build_bones.py male $B.export.npz $B.export.json $B.bones.npz /mnt/g/mocap-studio-downloads/models/hm-cache
human-model/hm.sh python human-model/tools/spec.py $B.bones.npz male
human-model/hm.sh python human-model/tools/build_muscles.py $B.export.npz $B.export.json $B.bones.npz $B.muscles.json male
human-model/hm.sh python human-model/tools/build_fields.py $B.export.npz $B.export.json $B.bones.npz $B.muscles.json $B.fields.npz
python3 human-model/blender_run.py --blend $A human-model/blender/add_fields.py BODY_OBJECT RIG_OBJECT $B.fields.npz $B.muscles.json $B.muscle.blend
```

This adds only the face fields and their controls to that file. Its bones, muscle bodies and sliding jaw aren't added. Take commands are in [drive.md](drive.md).

## Known traps

- **Headless scripts:** after setting a control, call `ctrl.update_tag()` and `scene.frame_set(frame)`, or the drivers don't run.
- **Vertex numbers:** the first 13,380 are the body on every MPFB character; helpers follow.
- **`.blend1` files** pile up next to rebuilt models. They're safe to delete.
- **The walk jumps** (bug `human-model/5`), and its stride is short (bug `human-model/4`).
