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
3. **Fill.** A 5 mm voxel grid: a voxel counts if its centre is inside the skin, or close enough to it that every skin vertex lies in a counted voxel (`layers.py:187`).
4. **Label.** Inside the femur is bone. Within the declared fat thickness of the skin is fat. The rest is muscle. A voxel outside the skin is fat (`layers.py:204`). The thickness changes smoothly around the femur between front, back, inner and outer.
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
