# Muscle physics: what we've learned

An experiment, separate from the model: nothing here changes [muscles.md](muscles.md). The initiative is `initiatives/muscle-physics/`.

## Experiment 1: a liquid-filled sphere lifts a box

A sphere of 5 cm radius hangs from a fixed box and carries a 1 kg box. Fibres run from top to bottom. When they contract the box rises, the sphere flattens, and its volume holds. When they let go, the box falls and the sphere extends.

**Results, measured on `solver_v9_amortecedor_final`:**

| | Height | Width | Box, against frame 1 | Volume | Pressure |
|---|---:|---:|---:|---:|---:|
| Hanging at rest | 105.7 mm | 96.9 mm | 0 | 0.5235 L | 2 kPa |
| Contracted, held | 78.6 mm | 108.2 mm | +27.1 mm | 0.5235 L | 79 kPa |
| Lowest after letting go | 110.7 mm | | −4.9 mm | 0.5235 L | |

The volume stays at 1.000000 of its start in every frame.

## Blender's Cloth couldn't do it

`blender/muscle_sphere_cloth.py` uses Cloth with pressure and a target volume, the closest thing Blender has to a bag of liquid. Its limits:

- **Stiff membrane:** the volume falls only to 93%, but the 1 kg barely counts. At ten times the gravity, the box still barely gives.
- **Soft membrane:** the load counts, but the volume falls to 62% and the surface crumples.
- **More pressure to hold the volume:** at a stiffness of 0.02 and a pressure of 1000, it blew up.
- **No mass per point:** Cloth has one mass for every vertex, so the 1 kg had to be a hidden block of 1331 points.
- **Contraction:** Cloth's own shrink is the same in all directions, so the test animated the rest shape through a shape key.

## The solver

`blender/muscle_sphere.py` runs in Blender's Python, with NumPy only. The result is stored in the file as shape keys, so it plays without simulating and without scripts.

- **Liquid:** one pressure, whatever it takes for the volume to hold (`muscle_sphere.py:122`), plus the liquid's weight as hydrostatic pressure (`muscle_sphere.py:96`) and its inertia on the wall's points. There's no flow inside.
- **Wall:** springs on the mesh's edges. How much an edge counts as fibre depends on how much it runs from pole to pole (`muscle_sphere.py:73`).
- **Contraction:** the fibres' rest length shrinks. The lift comes from that force against the load: the box isn't animated.
- **Load:** the box receives the wall's forces, its weight and the damper. It moves without turning, a simplification.

## What we learned

**A sphere is close to the worst shape for a muscle.** Told to shorten 40%, the fibres shortened about 6%, and the pressure rose to 79 kPa. A sphere already holds the most volume for its surface, so with the volume fixed it has little room to flatten. That matches what's known of a sealed bag of inextensible fibres, a "mylar balloon": its height can't go much below 0.6 of its width, which at this volume would be about 69 mm tall and 115 mm wide (formula recalled from memory, not checked against a source). We reached 79 mm and 108 mm. It suggests why muscles are long.

**Load is really felt.** With 5 kg instead of 1 kg, on the settings of `solver_v2`, the contracted height is 90 mm instead of 81 mm.

**The liquid's friction didn't stop the bounce.** Without a damper the box bounces at about 6 Hz for seconds, and ten times the viscosity still leaves it bouncing for almost two seconds, since that motion is the whole box on its spring. `DAMPER` (`muscle_sphere.py:21`) is the declared value that fixes it, and it isn't derived from anything. At its current value the bounce ends in about 0.3 s, which may be too dead.

**The mesh barely matters.** With four times the points (`solver_v6`, against `solver_v5`, same settings), the contracted height is 78.4 mm against 78.7, the lift 28.3 mm against 27.1, and the height at rest 106.7 mm against 105.7.

## The breast preset

Rafael ran his own test, `meu_teste`, and said (2026-11-05): "agora podemos dizer que o meu_teste é o simulador do seio". Its values are `PRESETS["breast"]` (`muscle_sphere.py:27`):

| | Default | Breast |
|---|---:|---:|
| `LIQUID`, kg/m³ | 1000 | 2000 |
| `VISCOSITY`, N s/m | 0.12 | 0.3 |
| `DAMPER`, N s/m | 20 | 50 |

`preset=breast` reproduces `meu_teste.json` with zero difference. On it, the box rises 27.4 mm, drops 1.0 mm below rest after letting go, and is still within about 8 frames. The density is twice water's, which real fat isn't (fat is lighter than water; general knowledge, not from a source read here): treat it as a value for the look, not tissue data. It's still the sphere and the box: nothing on the body uses it yet.

## What isn't simulated

Flow inside the liquid, fibres as separate objects, force changing with fibre length or speed as in real muscle, the box turning. The values `FIBRE`, `HOOP`, `SHORTEN`, `VISCOSITY` and `DAMPER` were chosen by trial, not measured from tissue. The caps' flat edge shows small steps in close-up.

## Running it

    python3 human-model/blender_run.py human-model/blender/muscle_sphere.py OUT.blend OUT.json [NAME=value ...]
    python3 human-model/blender_run.py --blend OUT.blend human-model/blender/muscle_render.py FRAMES_DIR

`preset=breast` loads the breast values. `NAME=value` overrides a constant at the top of the script, as in `FIBRE=3000` or `DAMPER=0`, after the preset. A run takes about two minutes, without rendering.

## Experiment 2: a thigh built from the inside out

Epic `thigh` of `initiatives/muscle-physics/`. Today the skin comes first and the bones are fitted inside it. Here the order is turned round on one thigh: the femur, muscle around it, fat under the skin, and the skin tied to them. Task 2 builds it at rest; task 3 will make it walk on the GPU.

**How it's built** (`hmcore/layers.py`, `tools/thigh_layers.py`):

1. **Cut.** The left thigh's skin between 2 cm under the crotch and 8 cm above the femur's lowest point. Only whole MPFB triangles are kept, so the patch ends at the nearest ring of vertices, about 3 cm short of each cut.
2. **Close.** Each open end gets a fan to its centre, so inside and outside can be told apart (winding number, `fit.winding_number`).
3. **Fill.** A 5 mm voxel grid: a voxel counts if its centre is inside the skin, or close enough to it that every skin vertex lies in a counted voxel (`layers.py:189`).
4. **Label.** Inside the femur is bone. Within the declared fat thickness of the skin is fat. The rest is muscle. A voxel outside the skin is fat (`layers.py:206`). The thickness changes smoothly around the femur between front, back, inner and outer.
5. **Clean.** Only the largest piece of bone and of muscle is kept. The rest becomes muscle and fat.
6. **Tetrahedra.** Six per voxel, on shared corners.
7. **Tie the skin.** Each skin vertex gets the tetrahedron that holds it, with its barycentric weights. The skin stays smooth while the tetrahedra are steps.

**The fat is declared by eye** (agreed with Rafael, 2026-11-07): front 15 mm, back 25 mm, inner 25 mm, outer 22 mm. Measured data is for initiative `tissue-research`.

**Results on the neutral woman, at rest** (`thigh_v3_section-along-femur`):

| | Value |
|---|---:|
| Femur points inside the skin, between the two rings | 574 of 574 |
| Femur's closest approach to the skin | 23.5 mm (median 44.5) |
| Tetrahedra: bone, muscle, fat | 6,012 · 68,178 · 95,730 |
| Corners (nodes) | 32,299 |
| Skin vertices tied | 169 |
| Fat, median against declared: front, back, inner, outer | 15.6/15 · 23.8/25 · 23.7/25 · 21.4/22 mm |
| Time on the CPU | 33 s |

**What it shows:**

- **At rest, the bone is well inside.** Bug `human-model/9` happens while walking, which task 3 measures.
- **MPFB's thigh skin is coarse:** 169 vertices over 16 cm. The tetrahedra can't put more detail in the skin than its own vertices carry.
- **Fat outnumbers muscle in tetrahedra,** partly because the skin's outer band of voxels counts as fat.

Every run is kept in `G:\mocap-studio-downloads\review\2026-11-07\`: `thigh_v1_first-try_bone-count-wrong-at-cuts` counted femur points past the rings as outside the skin (89), and `thigh_v2_measure-between-rings` cut the section on a flat plane, which missed most of the leaning femur.

**Running it:**

    human-model/hm.sh python human-model/tools/thigh_layers.py BUILD_DIR NAME OUT_DIR [NAME=value ...]
    python3 human-model/blender_run.py human-model/blender/thigh_view.py OUT_DIR/NAME.thigh_layers.npz OUT_DIR/08_thigh_layers.blend

`NAME=value` overrides a constant at the top of `thigh_layers.py`, as in `FAT_FRONT=20` or `VOXEL=0.004`. In the `.blend`, the collection `thigh_cutaway` is the back half in section.

## The GPU: what tissue costs

Task 1 of epic `thigh`: can the RTX 4080 SUPER simulate soft tissue fast enough for overnight batches? `tools/gpu_bench.py` drops a 20 cm cube of soft tetrahedra 5 cm onto a floor, for one second at 24 frames per second, and times it (`hm.sh --gpu`).

**The solver** (`hmcore/xpbd.py`): XPBD, the method made for GPUs, in NVIDIA Warp. The tissue is Neo-Hookean, set by Young's modulus and Poisson's ratio per tetrahedron, as two constraints: one resists change of shape, the other change of volume (Macklin and Müller 2021). The tetrahedra are solved in 48 groups that share no corner.

**Three versions, all kept** in `G:\mocap-studio-downloads\review\2026-11-07\`:

| Version | What it did | Result |
|---|---|---|
| `gpu_bench_v1_edges-jacobi_cube-collapses` | Springs on edges plus volume, all solved at once and averaged | Fast, but far too weak: the cube flattened and lost up to 93% of its volume |
| `gpu_bench_v2_neo-hookean-coloured` | Neo-Hookean, in groups | Holds its shape up to 330,000 tetrahedra; 1,000,000 collapses. 17 ms per frame at every size: launching a thousand small jobs cost more than the work |
| `gpu_bench_v3_cuda-graph_substeps-{20,40,80}` | The frame recorded once and replayed (CUDA graph), with 20, 40 or 80 steps per frame | Below |

**Measured, v3,** soft tissue (20 kPa, Poisson 0.45, 1,000 kg/m³; declared):

| Tetrahedra | Steps per frame | ms per frame | Peak VRAM | Volume kept |
|---:|---:|---:|---:|---:|
| 10,368 | 20 | 3.4 | 0.7 MiB | 98.6% |
| 105,456 | 20 | 3.4 | 7.2 MiB | 97.9% |
| 329,232 | 20 | 3.4 | 22.4 MiB | 93.6% |
| 998,250 | 20 | 6.0 | 67.6 MiB | **0.1%: collapses** |
| 998,250 | 40 | 11.9 | 67.6 MiB | 97.3% |
| 998,250 | 80 | 24.8 | 67.6 MiB | 99.0% |
| 10,368 on the CPU (Warp, one core) | 80 | 77.8 | — | 99.0% |

**What it shows:**

- **Speed isn't the problem.** A million tetrahedra, about five times the thigh, take 25 ms per frame. The goal for the thigh is under 1 s.
- **Finer tetrahedra need more steps per frame.** A million collapse at 20 steps and hold at 40. The thigh will need the same check.
- **Memory is small:** 68 MiB of the card's 16 GB for a million.
- **The CPU is about six times slower** on the smallest cube, and that's Warp on one core. The GPU's lead grows with size.

**Running it:**

    sudo human-model/setup_gpu_host.sh        # once
    human-model/hm.sh --gpu python human-model/tools/gpu_bench.py OUT_DIR [NAME=value ...]

## Experiment 3: the layered thigh walks

Task 3 of epic `thigh`. The thigh of experiment 2 goes through the neutral woman's walk (`female_walk_review.blend`, 105 frames, 4.4 s), then holds still for one second. The femur is moved exactly as in that file; muscle, fat and skin follow on the GPU. The same steps, measured on the current model's skin, are the comparison.

**How it runs:**

1. `blender/thigh_walk_dump.py` reads, every frame, the femur's transform from rest, and the current skin.
2. `tools/thigh_walk.py` simulates on the GPU (`hmcore/xpbd.py`):
   - The bone, and both cut ends from each skin ring outward, are carried by the femur.
   - Each frame the carried nodes move part of the way at every step, so there is no jolt between frames (`xpbd.py:176`).
   - Damping slows only the tissue's motion relative to the femur (`xpbd.py:76`).
   - It measures and writes the table.
3. `blender/thigh_bake.py` makes the `.blend` and the frames, and `ffmpeg` makes the videos.

**Declared values, by look, no measured data** (see initiative `tissue-research`): passive muscle 15 kPa, fat 3 kPa, a 5 mm skin band 150 kPa (real skin is about 0.5 MPa over 1.5 mm, spread over the band), Poisson 0.45, muscle 1,060 and fat 900 kg/m³, damping 5 per second.

**Six runs, all kept** in `G:\mocap-studio-downloads\review\2026-11-07\thigh_walk\`:

| Run | What changed | Bone through skin | Skin's peak motion against the femur | Lesson |
|---|---|---:|---:|---|
| `v1_damping-held-tissue-back` | First try | 10 frames, 45 mm deep | 127 mm | Two faults. Damping slowed the absolute velocity, like moving through honey. The sloping top end was held only at its highest point, so it hung loose |
| `v2_ends-pinned_no-skin_fat-swings-10cm` | Both fixed | none | 106 mm | Fat at 3 kPa can't hold itself up: the thigh pinches at every step. Videos made, to see it |
| `v3_skin-150k` | A skin band at 150 kPa | none | 48 mm | The skin holds the fat in |
| `v4_skin-150k_substeps-80` | 80 steps per frame | none | 25 mm | The answer still depended on the steps: not converged |
| **`v5_skin-150k_substeps-160`** | **160 steps** | **none** | **21 mm** | **Converged.** Videos made |
| `v6_skin-150k_substeps-320` | 320 steps | none | 21 mm | Same as v5: confirms it |

**v5, against the three agreed criteria:**

- **No skin point inside the bone, in any frame:** met. **But the current model doesn't poke here either:** between the two skin rings, the femur stayed inside its skin in every frame too. Bug `human-model/9`'s poking must be nearer the hip or the knee, outside this slab, so this experiment doesn't show the difference on that bug.
- **Under 1 s per frame:** met. 70 ms median and 137 ms at worst, for 169,920 tetrahedra at 160 steps per frame, 12 MiB of VRAM. Times vary between frames for a reason not found: the GPU benchmark's 25 ms for a million suggests some of it is overhead around each frame.
- **Movement:** Rafael's verdict, from the videos.

**Other measures, v5:**
- Volume held within 2% for both fat and muscle.
- After the walk stops, the skin settles in 0.62 s.
- Measured against the femur, the current model's skin moves 33 mm at its peak. That comes from its other bones' weights near the hip and knee, not from any tissue.

**What the walk itself does:** the thigh's centre reaches 45 m/s², about 4.5 g, at its hardest moment. That's high for a walk and may come from bug `human-model/5`, the jumps at each step. The tissue responds to whatever the input does, so a smoother walk will move it less.

**Videos:** in v2 and v5, `<run>_compare.mp4` shows our skin on the left and the current model's on the right, from the front, following the thigh. `<run>_inside.mp4` shows the back half in section with the femur. Each run's `.blend` plays without simulating, and its `thigh_walk_frames.csv` has every frame's numbers.

**Running it:**

    python3 human-model/blender_run.py --blend .../female_walk_review.blend human-model/blender/thigh_walk_dump.py OUT/00_female_walk_dump.npz
    human-model/hm.sh --gpu python human-model/tools/thigh_walk.py LAYERS.npz OUT/00_female_walk_dump.npz RUN_DIR [SUBSTEPS=160 ...]
    python3 human-model/blender_run.py human-model/blender/thigh_bake.py RUN_DIR/thigh_walk.npz LAYERS.npz OUT/00_female_walk_dump.npz RUN_DIR/thigh_walk.blend RUN_DIR/frames
    ffmpeg -framerate 24 -i RUN_DIR/frames/compare/%04d.png -c:v libx264 -pix_fmt yuv420p RUN_DIR/compare.mp4

`thigh_walk.py` reads its tissue values from `data/thigh_tissue.json`, 160 steps per frame among them, the converged value.

**Rafael's verdict on v5 (2026-11-07):** "parece um ser humano é forçar a amizade, mas mostra que tem futuro". It looks like cartoon jelly: the damping must go up somewhere, and he expects the rest to be a matter of better values.

| Run | Change | Peak motion against the femur | Settles after stopping |
|---|---|---:|---:|
| v5 | damping 5 per second | 21.0 mm | 0.62 s |
| `v7_damp-20` | damping 20 per second | 14.0 mm | 0.17 s |
| `rafa8`, Rafael's own | damping 20, fat 4 kPa, skin 100 kPa, fat 750 and muscle 900 kg/m³ | 15.5 mm | 0.21 s |

**Rafael on `rafa8`:** "agora parece que está bom". Its values are the defaults since (2026-11-07), in `data/thigh_tissue.json`.

### Changing the values and running again

One command, from the `mocap-studio` folder in WSL, does everything up to the videos (about two minutes):

    human-model/thigh_run.sh NAME [NAME=value ...]
    human-model/thigh_run.sh v8_damp-40_muscle-30k DAMPING=40 MUSCLE_YOUNG=30000

The defaults are in `human-model/data/thigh_tissue.json`. Edit that file to change them for every run; `NAME=value` changes one for this run only. A name the script doesn't know stops it.

It writes `G:\mocap-studio-downloads\review\<today>\thigh_walk\<NAME>\`, prints the peak motion and the settling time, and refuses a name that already exists, so every run is kept. Put the values in the name, so the folder says what it is.

| Value | Default | What it does |
|---|---:|---|
| `DAMPING` | 20 | Per second. **The jelly:** higher stops the wobble sooner. It slows only motion relative to the bone |
| `FAT_YOUNG` | 4000 | Pa. Fat's stiffness: higher wobbles less and faster |
| `MUSCLE_YOUNG` | 15000 | Pa. Relaxed muscle's stiffness. A working muscle is much stiffer |
| `SKIN_YOUNG` | 100000 | Pa. The skin band, which holds the fat in. 0 removes it (as in v2) |
| `POISSON` | 0.45 | How much the tissue resists changing volume, up to 0.5 |
| `FAT_DENSITY`, `MUSCLE_DENSITY` | 750, 900 | kg/m³. Heavier swings more |
| `SUBSTEPS` | 160 | Steps per frame. Fewer is faster but softer than asked, as v3 and v4 showed |

None of these are measured yet: they're for look, until initiative `tissue-research`.

## Experiment 4: the whole woman in layers, at rest

Epic `body-at-rest`: the zero point ("marco zero") for body shapes. The thigh's method, applied to the whole body: bone, muscle, fat by plastic-surgery zone, a skin band, and the trunk's organs as one soft **cavity**, all inside today's MPFB skin. Head, hands and feet are cut off at the neck, wrists and ankles (agreed with Rafael, 2026-11-07).

**How it's built** (task 1: `hmcore/body.py`, `tools/body_layers.py`, on the GPU through `hmcore/meshgpu.py`):

1. **Cut.** The head goes where the rig moves the skin mostly with the head's bones, a border that runs under the jaw (`body.py:26`); near each wrist and ankle, skin vertices past the joint's plane are dropped; then the largest piece is kept (`body.py:47`).
2. **Zones.** Each skin vertex gets a zone from its nearest rig bone (`body.py:103`). On the trunk, the zone also depends on height (against the bottom of the rib cage and the top of the hip bones) and on whether the vertex faces front, back or side. The thicknesses are smoothed over the skin, so they change gradually.
3. **Fill.** The same 5 mm voxels as the thigh. Inside-or-outside and distances are computed on the GPU, about 4 million points in seconds. Bone meshes are first turned outward (`body.py:193`), because builds made before bug `human-model/11` was fixed have the left leg inside out.
4. **Label.** Bone wins over everything. Within one voxel of the skin is skin. Within the zone's fat thickness is fat.
   - **Cavity** (`body.py:250`):
     - in the chest: everything inside the rib cage, beside the spine too, where the lungs reach;
     - lower down: inside the hull of ribs, spine and pelvis, no more than 30 mm behind the spine's front, and deeper than the fat plus a 15 mm abdominal wall.
   - **Breast** (`body.py:253`): fat down to a 15 mm chest muscle over the ribs.
   - **Muscle:** whatever remains.
5. **Clean, tetrahedra, tie the skin.** As on the thigh.

The values are in `data/body_fat_female.json`, by eye (agreed with Rafael, 2026-11-07). A run can override one, as `fat.belly=30` or `structure.pectoral_mm=20`.

**The report** (task 2: `blender/body_tape.py`, `tools/body_report.py`):
- **Sections**, as a CT scan or a pattern room would cut them: crosswise at the bust, under the bust, the waist, the hip and the thigh, at the heights where the editor's tape takes those girths; lengthwise through the middle and through the left leg.
- **The table** `marco_zero.md`, in Portuguese: masses, fat by zone, bones through the skin, the pattern-making measures.

**Results** (`body_v4_belly-beside-spine`, 15 s on the GPU):

| | Litres | kg | Share of mass | Usual for an adult woman* |
|---|---:|---:|---:|---|
| Bone | 3.6 | 5.4 | 10% | 12–15% |
| Muscle | 17.0 | 18.0 | 35% | 30–36% |
| Fat | 11.2 | 10.1 | 19% | 25–31% |
| Skin band | 11.1 | 12.2 | 24% | — |
| Cavity | 7.0 | 6.3 | 12% | — |
| **Total**, without head, hands and feet | 49.9 | 52.0 | | |

\* General knowledge, not from a source read here: a comparison, not a target. The densities are declared too.

Other figures:
- 2.4 million tetrahedra.
- The fat measures within 2.5 mm of the declared value in 15 of 19 zones.
- Pattern measures: bust 83.9 cm, under the bust 67.9, waist 65.2, hip 90.6, height 159.1.

**What it shows:**

- **Superficial bones come through the skin even at rest** (bug `human-model/10`):
  - the right scapula by 27 mm, while the left is out by only 7.6, so the right one sits wrong;
  - the larynx, the left clavicle and the fibulae by about 11 mm, the tibiae 10, the patellae 9, the right hip bone 7, the sacrum 5.

  Today's skin comes first and the bones are fitted into it, and this is where that order fails. The next step is to build the skin from the inside, with a least depth of tissue over each bone.
- **The skin band decides the fat share.** It averages 9.2 mm, against about 1.5 mm of real skin. The fat is 19% of the mass if the band is all skin, and 37% if everything in it beyond 1.5 mm is fat. The usual range sits between the two. A thinner skin layer is needed before the fat share means anything.
- **The cavity**, 7 L, is still on the small side of the 10 to 15 L of organs in a woman's trunk (general knowledge).
- **The breast zone covers most of the front of the chest,** because its rig bone is the nearest there.
- **A ragged collar under the chin:** the neck's cut leaves part of the jaw's underside. Since fixed by cutting along the rig's head weights (bug `human-model/17`): `body_v7_neck-cut-by-weights\13_pescoco_antes_depois.png`.

**Every run is kept** in `G:\mocap-studio-downloads\review\2026-11-07\`:

| Run | What it got wrong |
|---|---|
| `body_v1_first-try_cut-bones-counted-as-poking` | Counted the bones past the cuts as poking |
| `body_v2_cuts-apart` | **No bone in the left leg,** whose meshes are inside out. The lungs stopped in front of the spine. Couldn't be renamed: a file in it was open |
| `body_v3_bones-outward_lungs-beside-spine` | The belly's cavity stopped in front of the lumbar spine, so the waist had only a sliver of it |
| `body_v4_belly-beside-spine` | **The current one**: `12_sections.png`, `marco_zero.md`, `08_body_layers.blend`, and `08_body_layers_zones.png` with the zones painted |

**Running it:**

    human-model/hm.sh --gpu python human-model/tools/body_layers.py BUILD_DIR NAME OUT_DIR [fat.<zone>=mm ...] [structure.<name>=value ...]
    python3 human-model/blender_run.py human-model/blender/body_view.py OUT_DIR/NAME.body_layers.npz OUT_DIR/08_body_layers.blend
    python3 human-model/blender_run.py human-model/blender/body_tape.py human-model/data/recipes/female.json OUT_DIR/09_tape.json
    human-model/hm.sh python human-model/tools/body_report.py OUT_DIR NAME OUT_DIR/09_tape.json OUT_DIR

## Experiment 5: the skin pushed out over the bones

Epic `inside-out-skin`, task 1. The zero point found bones through the skin at rest (bug `human-model/10`). Here, for the first time, the layers shape the skin: wherever a bone has less tissue over it than declared, the skin moves out.

**How** (`hmcore/skinfit.py`, `tools/skin_over_bone.py`, on the GPU):

1. **Each bone point asks for its least depth of tissue**, from `data/skin_over_bone_female.json`, set by eye: 3 mm over the patella, the shin's front and the larynx; 4 mm over the clavicles, scapulae, spinous processes and ankle; 6 mm over the sacrum and the hip bones' crests; 2 mm elsewhere. Bones past the neck, wrist and ankle cuts are left out (`body.near_a_cut`, with each cut's plane taken from the cut skin's border).
2. **A bone that needs more than 15 mm anywhere is left alone** and reported as misplaced (`skinfit.py:70`): moving the skin that far would grow a hump.
3. **The skin vertices of the nearest triangle move out along their normals** by what's missing.
4. **The push is spread** to neighbours, shrinking by a fifth at each step, so it fades over a few centimetres (`skinfit.py:23`). The cuts' rings stay put, so the head, hands and feet still join.
5. **Repeat** until nothing changes. It takes 0.7 s. MPFB's mesh and vertex order are kept.

**Result on the neutral woman** (`skin_v4_along-skin-normal`):

- **Every bone pushed for now has its tissue,** except the sacrum, which reaches the skin (0 mm) but no further. It sits in the cleft between the buttocks, where no push along the skin covers it. Bug `human-model/2` says the pelvis sits too far back, so this is likely a bone fault too.
- **Misplaced, left alone:** the right scapula (needs 31 mm), and, just over the limit, the left clavicle and both fibulae (about 15.2 mm each). A limit of 16 mm would include those three. Since fixed by settling those bones under the skin (bug `human-model/12`): see `skin_v5_bones-settled` below.
- **The figure barely changes:** bust +0.4 cm, under the bust +0.6, waist +0.1, hip +0.1, thigh 0, knee +1.2, ankle +1.0. 636 vertices moved more than 1 mm; at most 15.6 mm, on the neck and buttocks.

**Every run is kept** in `G:\mocap-studio-downloads\review\2026-11-07\`:

| Run | What went wrong |
|---|---|
| `skin_v1_spread-everywhere_hump-on-scapula` | The push spread over the whole skin, so the bust grew 3.2 cm and the ankle 3.8. The right scapula was pushed 15 mm anyway, growing a hump |
| `skin_v2_falloff_misplaced-left-alone` | Fixed both. The sacrum stopped at 0 mm |
| `skin_v3_push-away-from-bone_sacrum-worse` | Pushing away from the bone instead of along the skin: the sacrum came 7 mm out (`skinfit.py:94`) |
| `skin_v4_along-skin-normal` | The same as v2: `04_skin_fit.blend` and its front and back stills, before and after, painted by how far the skin moved |
| `skin_v5_bones-settled` | **The current one,** on bones settled under the skin (bug `human-model/12`, fixed; bones in `models/hm-build/female_settled`): nothing left alone, bust and under the bust no longer change, 570 vertices moved over 1 mm. Only the sacrum still short. `05_ombros_*` and `06_tornozelos_*` are point views of the bones before and after (colours differ between the two) |

**Running it:**

    human-model/hm.sh --gpu python human-model/tools/skin_over_bone.py BUILD_DIR NAME TAPE.json OUT_DIR [depth.<prefix>=mm ...] [MAX_PUSH_MM=mm]
    python3 human-model/blender_run.py human-model/blender/skin_fit_view.py OUT_DIR/NAME.skin_fit.npz BUILD_DIR/NAME.export.npz OUT_DIR/04_skin_fit.blend

### The zero point on the pushed skin

Task 2. The layers rebuilt inside the pushed skin (`body_layers.py ... SKIN=<name>.skin_fit.npz`). The masses now come from the volume inside the skin, not from the voxels (`body_report.inside_skin`):
- bone, muscle and cavity from their voxels, which lie deep;
- real skin as its area times 1.5 mm;
- fat as what's left.

The voxels had counted 4.7 L too many, because their band reaches past the skin.

| | Before the push, same count (`body_v4b`) | After (`body_v5_pushed-skin`) | Usual for an adult woman* |
|---|---:|---:|---|
| Bone | 12% | 12% | 12–15% |
| Muscle | 40% | 40% | 30–36% |
| Fat | 30% | 30% | 25–31% |
| Skin | 4% | 4% | — |
| Cavity | 14% | 14% | — |
| Bones through the skin | 28 | **4**, the misplaced ones | — |
| Bust, waist, hip | 83.9, 65.2, 90.6 cm | 84.3, 65.3, 90.7 cm | — |

\* General knowledge, not from a source read here.

**What it shows:**
- **The push fixes the bones through the skin** without changing the figure: 24 of 28 bones are now covered. The other four are bones out of place: the right scapula, the left clavicle and both fibulae.
- **The fat's share was a counting problem, not a body problem.** Counted inside the skin, it's 30%, within the usual range, both before and after the push.
- **Muscle reads high** (40% against 30–36%). Everything that isn't bone, fat or cavity is called muscle, including the tissue between organs, the neck's and the pelvic floor's.

`marco_zero.md` in `body_v5_pushed-skin` has both columns side by side.

## Experiment 6: the woman's lower body walks

Epic `leg-walk`, the agreed second stage. Since `body-walk`, the tool is `tools/body_walk.py` and the bake `blender/body_walk_bake.py`, with every cut ring held by its nearest bone; the run below used the waist and ankle rules they replaced (Rafael, 2026-11-07, "faça a perna e o quadril caminhando"). Bug `human-model/9` is about bones coming through the skin near the hip while walking, so the walk now carries the pelvis and both legs, built from the inside out on the pushed skin (`body_v5_pushed-skin`).

**How** (then `tools/lower_body_walk.py`, now `tools/body_walk.py`, on the GPU):

1. **The region:** the voxels below 2 cm over the hip bones' top, as one connected piece. The hands hang that low in the rest pose but join it nowhere, so they drop out. Whole voxels only, since the solve colours them by sixes.
2. **Every node has a bone,** the nearest bone vertex among those holding some of the region's bone voxels: 17 bones, from the lumbar vertebrae to the ankles.
3. **Bone voxels follow their bone,** and the cut ends follow their nearest bone. The motion is read from the woman's walk file by `blender/body_walk_dump.py`, one transform per bone and frame. Damping slows each node only against its own bone (`xpbd.Solver.drive` with `bone` and `all_bone`).
4. **The body eases from the rest pose into the first step over a second,** holds half a second, walks, then holds a second.
5. **Tissue values** are in `data/body_tissue.json`: Rafael's `rafa8` for muscle, fat and skin, plus the cavity (the pelvis' organs), set by eye at 3 kPa and 1,000 kg/m³.
6. **Every frame,** each bone's points are checked against our skin and against the current model's skin, which is MPFB's, not pushed.

**Results, run `v2_region-bones-only`:**

| | Simulated | Current model |
|---|---:|---:|
| Bones through the skin | the two fibulae only, at most 40 points, 4.6 mm | femurs, hip bones, patellae, sacrum and fibulae, up to 3,770 points, 12.7 mm |
| Frames with any | 129 of 129 (the fibulae) | 105 of 105 |

Other figures:
- 1.4 million tetrahedra, 72 ms per frame (142 at worst), 103 MiB of VRAM.
- Volume held within 1.5% for muscle, fat and skin.
- The cavity varies from 86% to 106%. The pelvis' organs are soft and get squeezed as the hip flexes.
- At most 2,339 tetrahedra turn inside out in a frame (0.17%), at the knees and hips, where the tissue between two bones folds.

**What it shows:**

- **Bug 9 doesn't happen in the layered body.** Only the fibulae touch the skin, and they were already left alone as misplaced bones (experiment 5).
- **The skin's motion against its nearest bone reads 6 to 87 mm per zone.** Most of it isn't jiggle: near a joint, the nearest bone isn't the one the skin hangs from, so a bending knee or hip counts as motion. Only the flanks (6 mm) and lower back (8 mm) are far from joints. Separating jiggle from joint bending needs a better measure.
- **No contact between the thighs yet:** where they pass through each other isn't prevented, nor measured.

**Every run is kept** in `G:\\mocap-studio-downloads\\review\\2026-11-07\\leg_walk\\`:
- `v1_fingers-counted-session-ended-at-frame-30` counted the hands' bones as poking. The session ended at frame 30, so only its log exists.
- `v2_region-bones-only` has `lower_body_walk.blend` and two videos:
  - `leg_walk_v2_compare.mp4`: from the side, our skin (pink) in front and the current model's (blue) 80 cm behind it on the same step;
  - `leg_walk_v2_inside.mp4`: the back half in section, with the bones.

  `leg_walk_v2_compare_current-hides-ours.mp4` is the first render, where the current skin stood beside ours and hid it.

**Rafael's verdict (2026-11-07):** "ainda teremos que mexer nos parâmetros, mas nesse momento acho que é mais importante seguir adiante". The values are to be tuned later; the next stage comes first.

**Running it:**

    python3 human-model/blender_run.py --blend .../female_walk_review.blend human-model/blender/body_walk_dump.py OUT/00_female_body_walk_dump.npz
    human-model/hm.sh --gpu python human-model/tools/body_walk.py LAYERS.npz BONES.npz OUT/00_female_body_walk_dump.npz RUN_DIR [NAME=value ...]
    python3 human-model/blender_run.py human-model/blender/body_walk_bake.py RUN_DIR/body_walk.npz LAYERS.npz BONES.npz DUMP.npz RUN_DIR/body_walk.blend RUN_DIR/frames

## Experiment 7: the whole woman walks

Epic `body-walk`, the agreed third stage (Rafael, 2026-11-07, "nesse momento acho que é mais importante seguir adiante"). The same tool as the lower body, `tools/body_walk.py` with `ABOVE_HIP=10`, so nothing is cut at the waist:
- **Cut rings:** the neck, both wrists and both ankles. Each is held by its nearest bone: nodes past the ring's plane, within half again its radius, follow that bone (`body_walk.cut_zones`, `near_cuts`).
- **Bone checks:** points within 3 cm of a cut aren't checked against the skin.
- **Tissue values:** the lower body's, to be tuned later.
- **Not modelled:** contact, breathing, the head, hands and feet.

**Results, run `v1_whole-body`:**

| | Simulated | Current model |
|---|---:|---:|
| Bones through the skin | 4, the misplaced ones only: right scapula, left clavicle, both fibulae; up to 29.9 mm (the scapula) | 30 bones, up to 27.0 mm |
| Points out in the worst frame | 6,449 | 14,300 |

Other figures:
- 2.4 million tetrahedra on 83 bones.
- 145 ms per frame, 342 at worst; 181 MiB of VRAM.
- Volume held within 2% for muscle, fat and skin. The cavity varies from 90% to 105%.
- At most 2,365 tetrahedra inside out in a frame (0.1%).

**What it shows:** away from the four misplaced bones, no bone comes through the skin anywhere on the walking body, while the current model has 30 doing so. The cranium shows in the section video floating over the neck: it holds the neck's tissue, but the head isn't simulated.

The run's summary first said 19 cuts: a name reused for the fat zones overwrote the rings' count in the summary only. It's corrected by hand in that file and fixed in the tool.

Kept in `G:\mocap-studio-downloads\review\2026-11-07\body_walk\v1_whole-body\`: `body_walk_v1_compare.mp4` (from the side, ours in front, the current model 80 cm behind), `body_walk_v1_inside.mp4` (the back half in section), `body_walk.blend`.

**Run `v2_bones-settled`:** the same walk on bones settled under the skin (bug `human-model/12`, fixed on `dev` in `fixes/0000d0/four-bones-misplaced`). The chain: bones in `models\hm-build\female_settled\`, the skin pushed over them (`review\2026-11-07\skin_v5_bones-settled\`), the layers rebuilt on it (`body_v6_bones-settled\`), then the walk.

| | `v1_whole-body` | `v2_bones-settled` |
|---|---:|---:|
| Frames with a bone through the skin | 129 | **0** |
| Deepest point out | 29.9 mm (right scapula) | **0** |
| Tetrahedra inside out, worst frame | 2,365 | 2,464 |
| ms per frame, median | 145 | 137 |

The skin's motion per zone and the volumes are within a millimetre or a fraction of a percent of v1; only the front of the calf moves more (17.6 mm against 11.5), next to the moved fibula. **Rafael's verdict (2026-11-07): "Parece bom".**

Kept in `G:\mocap-studio-downloads\review\2026-11-07\body_walk\v2_bones-settled\`: `body_walk_v2_compare.mp4`, `body_walk_v2_inside.mp4`, `body_walk.blend`.

**Run `v3_feet-planted`:** the same body on the walk with planted feet (task `body-walk/2`: the pelvis's tilt taken off the hip angle, toes rolling, each stance foot planted; `walk_root\v9_final_walk.blend`). The walk no longer jumps, so the tissue swings less:

| Peak skin motion, mm | belly | breast | chest | flanks | buttocks | hips | thigh front | calf back |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `v2_bones-settled` | 72.6 | 40.6 | 41.4 | 50.1 | 71.3 | 71.0 | 86.4 | 56.7 |
| `v3_feet-planted` | 54.6 | 22.0 | 22.1 | 23.3 | 52.1 | 50.2 | 75.9 | 42.0 |

Those numbers still count joint bending (bug `human-model/14`), so they compare the two runs, not the tissue's jiggle. With the thigh now at its true angle, the patellae touch the skin in 4 frames of each swing, up to 1.8 mm (bug `human-model/19`); no other bone does. Tetrahedra inside out: 2,538 at worst. **Rafael's verdict on the walk (2026-11-08): "Ficou ok, bem melhor agora".** Kept in `body_walk\v3_feet-planted\`: `body_walk_v3_compare.mp4`, `body_walk_v3_inside.mp4`, `body_walk.blend`, and the walk's dump.

**Running it:**

    human-model/hm.sh --gpu python human-model/tools/body_walk.py LAYERS.npz BONES.npz DUMP.npz RUN_DIR ABOVE_HIP=10 [NAME=value ...]
    python3 human-model/blender_run.py human-model/blender/body_walk_bake.py RUN_DIR/body_walk.npz LAYERS.npz BONES.npz DUMP.npz RUN_DIR/body_walk.blend RUN_DIR/frames
