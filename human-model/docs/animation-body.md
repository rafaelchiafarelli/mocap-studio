# The animation body

The new start of initiative `animation-body` (Rafael, 2026-11-10): a whole MPFB2 woman with far less anatomy and physics. No bones, muscles or tissue inside: what shows in the animation is built directly on the skin.

**Command:** `python3 human-model/tools/animation_body.py human-model/data/recipes/female_reference.json OUT_DIR` (WSL, about two minutes). Each stage reads the previous stage's file and keeps its own.

| Stage | Script | What it adds |
|---|---|---|
| `01_corpo` | `blender/clean_body.py` | The body from a recipe alone, its rig, helpers masked. Weights of bones the metarig lacks go to real bones |
| `02_amplitude` | `blender/range_of_motion.py` | A range-of-motion test, and how much skin collapses per pose |
| `03_correcoes` | `blender/pose_corrections.py` | Volume-preserving skinning, fading out at the elbows |
| `04_caminhada` | `blender/walk.py` (`smooth_stop`), `arm_pendulum.py`, `apply_corrections.py` | The measured walk, feet planted, slowing smoothly to a stop; arms as damped pendulums with fists, colliding with the body; those corrections |
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

Delta Mush was tried at the four joints and lowered the collapse at none. Wave peaks at the medium step impact: 14 mm breast, 16 mm buttocks, 12 mm thigh, 5 mm flanks, 4 mm belly, 2 mm calf, 1 mm upper arm. Rafael's round on 2026-11-11: the stop walked back at up to 0.85 m/s, now slows forward to rest; hands answer to gravity and give before the arm (no frame through the body; the arm passed 5 degrees in 14 frames on the left, up to 7.5, and 8 on the right, up to 19); skin sinks 5 mm at most; the fold under the buttock is shallower (9 mm, 30% at rest). Arms as damped triple pendulums with collision (Rafael, later the same day): they swing from -41 to +26 degrees and the elbow bends up to 63 from the trunk's motion alone, with nothing left inside the body after any frame. Then (same day): hands 15% shorter through MPFB's `hand-scale-decr` at 0.75 in the recipe (17.9 to 15.2 cm), joint damping 50% higher, and the forearm turned so the palm faces the thigh; swing -31 to +20 degrees, elbow up to 41, nothing inside. Then: the arms weren't swapped (measured: each on its side, palm to the thigh, thumb forward), but the elbow bent sideways as a ball joint; it is now a forward-only hinge, its correction shared by elbow and wrist so the arm opens at the shoulder instead; the arms start hanging and settle moving at the walk's first speed. Swing -28 to -2 degrees: a passive arm only trails, pushed back by the thigh. Then: the hands back to MPFB's size (15% shorter looked small once the fingers bent the right way); the upper arm and forearm twist about their length as damped springs following the trunk's turn and, a little, the swing: up to 9 and 10 degrees. Then (2026-11-12): the passive arms looked like hanging wood, swung by the thigh's hits. The shoulder and elbow now have muscles, soft springs towards a swing opposite the legs (65% of the leg's angle, arm 5 degrees out, elbow 12 to 27 degrees), and the elbow a 13-degree carrying angle so the hands pass beside the hips: swing -18 to +12 degrees, elbow 14 to 32, no contact in any step. Then: an intention in the swing (Rafael: "we throw the arms forwards on purpose"): the shoulder pulls three times harder while the target goes forward, 6 degrees further and with 10 more of elbow, with a push at the start; on the way back it relaxes to 0.3 and the arm falls by its weight. Swing -18 to +16 degrees, elbow 13 to 35, no contact; reaching 3 degrees inwards brought back thousands of contacts, so it is 0. Then: jumps (Rafael). Measured: the forearm turned up to 38 and 53 degrees in one frame, against 3 to 4 usually, where the intention switched at once, the muscles were stiff enough to reach a changed target within a frame, and the stop dropped leg corrections of up to 15 degrees the frame a foot left the ground. Now the intention eases over 0.12 s, the muscles are a third as strong, the arms settle with them on, no point of the arm moves faster than 2.5 m/s against the shoulder, and the stop's leg corrections ease in and out: at most 17 to 18 degrees a frame for the forearm, 8 for the thigh. All values are by eye; Rafael's verdict hasn't been given.
