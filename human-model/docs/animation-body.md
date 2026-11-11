# The animation body

The new start of initiative `animation-body` (Rafael, 2026-11-10): a whole MPFB2 woman with far less anatomy and physics. No bones, muscles or tissue inside: what shows in the animation is built directly on the skin.

**Command:** `python3 human-model/tools/animation_body.py human-model/data/recipes/female_reference.json OUT_DIR` (WSL, about two minutes). Each stage reads the previous stage's file and keeps its own.

| Stage | Script | What it adds |
|---|---|---|
| `01_corpo` | `blender/clean_body.py` | The body from a recipe alone, its rig, helpers masked. Weights of bones the metarig lacks go to real bones |
| `02_amplitude` | `blender/range_of_motion.py` | A range-of-motion test, and how much skin collapses per pose |
| `03_correcoes` | `blender/pose_corrections.py` | Volume-preserving skinning, fading out at the elbows |
| `04_caminhada` | `blender/walk.py` (`smooth_stop`), `hands.py`, `arm_clearance.py`, `apply_corrections.py` | The measured walk, feet planted, slowing smoothly to a stop; relaxed hands with a wrist spring; hands touching the body (skin up to 5 mm, then fingers, wrist, arm); those corrections |
| `05_dobras` | `blender/fold_lines.py`, `fold_apply.py` | 17 folds as shape keys following the pose |
| `06_malha_fina` | `blender/fold_fine.py` | A thin crease per fold on the subdivided skin |
| `07_ondas` | `blender/skin_dump.py`, `tools/skin_waves.py`, `blender/wave_bake.py` | Sway, travelling waves and the step's impact, baked per frame |

`tools/fit_proportions.py` makes the recipe from target proportions. `tools/compare_page.py` and `blender/simple_stills.py` put the model beside the reference clips.

**In the file:** the object `HM_controls`, tab Object Properties, Custom Properties: one fader per fold (`fold_<name>`), `fold_fat`, and `wave_amount`. The body's values are in `data/folds.json` and `data/skin_waves.json`; a wave value changes per run with `NAME.key=value`, as `breast.gain=0.8`.

**Measured on the reference woman (2026-11-11):**

| Pose | Collapsed triangles near the joint, plain | With volume preservation |
|---|---:|---:|
| Knee bent | 5.8% | 3.4% |
| Hip flexed | 5.5% | 4.5% |
| Squat | 5.3% | 4.7% |
| Arms overhead | 5.1% | 3.4% |
| Elbow bent | 4.7% | 4.7% |

Delta Mush was tried at the four joints and lowered the collapse at none. Wave peaks at the medium step impact: 14 mm breast, 16 mm buttocks, 12 mm thigh, 5 mm flanks, 4 mm belly, 2 mm calf, 1 mm upper arm. Rafael's round on 2026-11-11: the stop walked back at up to 0.85 m/s, now slows forward to rest; hands answer to gravity and give before the arm (no frame through the body; the arm passed 5 degrees in 14 frames on the left, up to 7.5, and 8 on the right, up to 19); skin sinks 5 mm at most; the fold under the buttock is shallower (9 mm, 30% at rest). All values are by eye; Rafael's verdict hasn't been given.
