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
