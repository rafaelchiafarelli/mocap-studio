# Handoff: pose-capture seams, cloth snags, thick shell, gain with planted feet (2026-11-15, afternoon)

For the next session and for Rafael. It continues [handoff-2026-11-15-maos.md](handoff-2026-11-15-maos.md) (the morning: pendulum hands, tet_v8–v10). Its decisions still hold; read its "Decisions" and "Constraints" first.

The as-built is in [investigations/pose-capture/CLAUDE.md](investigations/pose-capture/CLAUDE.md). Rafael's guide to the files is `LEIA_tet_v11.txt` in the review folder, in Portuguese.

## What Rafael asked

- **The request:** do every open item of the morning handoff without asking.
- **Intermediate results:** save every one, each with a `.bat`.
- **He hasn't seen the results yet.** Next is his verdict on `tet_v11i_cenario_roupa.blend`.
- **The marked best is still `tet_v6`**, which has no clothes.

## What was done, by item of the morning's "Open" list

### 1. Wrists and ankles "coming apart": it was the assembly, not the simulation

- **Measured (`seam_gap.py`):** the simulated border lies within 1.4 mm of the rig's skin at the same points, every frame.
- **What showed:** HM_body coarse (no Subsurf), with two rings under the smooth simulated skin. The two surfaces crossed in a jagged line with a step in shading.
- **Fix in `tissue_assemble.py`:**
  - HM_body is subdivided twice, as the simulated skin was built.
  - The simulated faces are deleted exactly by index (Geometry Nodes).
  - The simulated border is glued onto the body.
  - `--aneis` gives the old way.
- **Check stills:** `_scripts/conferencia_tet_v11_costura/`.

### 2. The top's hem wrapping the wrist: cloth went through the forearm

- **Measured (`cloth_snag.py`):**
  - **The mechanism:** pinched between forearm and waist, a hem vertex pushed past the forearm's middle was pushed out through the far side.
  - **The rule it ran on:** `_cloth_contact` pushed out through the nearest face.
- **Fix, three parts:**
  - **`entrada=1`:** a cloth vertex goes back out where it came in (the face nearest its last place outside every part and hand).
  - **`mao_folga=1`:** covered skin keeps the cloth's room from a hand.
  - **`pele_folga=1`:** between two parts' skins, room for the cloth over each.
- **Over half a turn round a forearm:**

| Side | tet_v10 | tet_v11i |
|---|---|---|
| Left | 96 frames | 0 |
| Right | 48 frames | 10 |

- **Cost:** inverted tetrahedra rose (median 5,200 against 3,900, of 3.3 M).

### 3. Thick shell (Rafael's decision 6)

- **Bending:** Bergou 2006's isometric quadratic bending (`_bend`), calibrated on a cylinder, using measured bending rigidity. Sources are in `roupas.json`:
  - jersey: B = 0.02 gf·cm²/cm;
  - denim: B = 0.273.
- **For Rafael: the formula he named doesn't fit fabric.**
  - D = E t³/12(1−ν²) with the tensile modulus would make the jersey ~50 times stiffer than measured. A fabric is yarns, not a sheet.
  - The report gives the modulus a solid 2 mm sheet would need: 2.7 kPa for the jersey, 37 kPa for the denim.
- **The big finding:** the old across-edge bending pairs were counted in the Jacobi mean and diluted the edges' stretch correction.

| Top's stretch | tet_v10 | tet_v11i |
|---|---|---|
| p95 | 16% | 7.5% |
| max | 386% | 115% |
| Spikes in the cloth | 274 frames | 4 frames |

- **The 2 mm shown:** a Solidify, plain offset, clamped. With even thickness it shot needles; that file is marked `_ERRADO_`.
- **Cloth on cloth, retried:** at rest only 32 vertices overlap. The result is not better (a spike off the jeans, a more crumpled top), so it stays off.

### 4. Made general (Rafael's decision 7); same result for this body and suit, checked to the bit

- **`dress_rest.py`:** pieces come from `roupas.json` `vestir` (asset and `toda`/`cima`/`baixo` by the body's waist).
- **`tissue_mesh.py`:** zone lengths scale with the body's height (`L()`, `body_scale`).
- **`tissue_cloth_sim.py`:** the skin-under-cloth rules scale with the cloth's median edge.
- **Still tied:** listed at the end of the as-built.

### 5. Top riding up and tearing near the breasts

- **Mostly gone with the shell:** top edges over 30% stretched near the breasts went from 13 to 2 (summed over every 5th frame).
- **Remaining:**
  - shards of the hem near the right wrist late in the dance;
  - a tear line on the back (the shoulder's diagonal);
  - a thin tear under the breasts at the end;
  - stretch at the armpits (sleeve squeezed).

### 6. The "checkered crease" on the left thigh

- **What it was:** faceted creases in the jeans under the buttock, along the cloth's grid. The old bending gave no resistance to small bends.
- **With the shell:** broad, soft folds.
- **Check stills:** `_scripts/conferencia_tet_v11_quadril/`.
- **Not confirmed with Rafael** that this is what he meant.

### 7. Gain carries the legs (`amplify_capture.py`, `plant_feet`)

- **What it does:**
  - Planted feet keep their captured place.
  - The knee comes from two-bone IK.
  - The hips' path gain drops where a leg can't reach.
- **On this take:**
  - A foot is planted 96% of the time.
  - The planted legs are nearly straight: 4–6 mm short of full reach, median.
  - So at hips gain 3 the path gain falls to 1 everywhere. The hips can only travel further by dropping. The pelvis's rotation gain still applies.
- **Rafael's choice, not built:** allow a hip drop (knee bend) budget.
- **Docs:** `docs/transformações/07_ganho.typ` doesn't describe this yet.

### 8. Not done: soft-tissue design changes need Rafael's drawing review first (standing constraint)

- leg/trunk contact;
- a yield per region;
- the breasts' rest shape;
- left/right configured separately.

## Seen but not addressed

- **A hand pressed into the belly dents it deeply.**
  - The hand collider doesn't yield, and the capture puts the hand inside the body.
  - Decision 2 (5 mm yield, the rest shown as skeleton error) covers contact between parts, not hands.

## How tet_v11i was built

From the repository root, with `R`, `S` and `M` as in the morning handoff.

```sh
human-model/hm.sh --gpu python $S/tissue_cloth_sim.py $M $R/tet_v9_movimento/ossos_ganho_1_maos.npz $R/17_roupa/roupa_repouso.npz \
    $R/tet_v11_roupa/roupas_v11i.json $R/tet_v11_roupa/sim_v11i pano_pano=0 corpo=$R/11_tecidos/corpo_repouso.npz
ROUPAS=$R/tet_v11_roupa/roupas_v11i.json $R/_scripts/monta_tet_v11.sh $R/tet_v11_roupa/sim_v11i tet_v11i_cenario_roupa
```

- **The defaults are on:** `entrada`, `mao_folga`, `pele_folga` and `flexao=isometrica`.
- **What `monta_tet_v11.sh` runs:** `tissue_assemble.py`, `stage_video.py --no-frames` and `dress_assemble.py` (with ROUPAS for the Solidify).
- **It also writes the `.bat`.**
- **Measures:**
  - `cloth_snag.py` (forearm snags);
  - `seam_gap.py` (seams);
  - `_scripts/still_costura.py`, `still_quadril.py`, `still_tronco.py`, `still_maos.py` (check stills).

## Code

- **All committed on `pose-capture`:** `434ce38`, `2b0de0f`, `3e820d3`, `d5ebe03`, `d1762b4`, `9492a2a`, `37c20e4`. Not pushed.
- **Another session's work, committed at Rafael's request (2026-11-15):** `INTEGRATION-motion-filter.md` deleted, `experiments/anny-mpfb/`, `experiments/mpfb-ganho/`.

## Gotchas found

- **Jacobi mean:** any constraint added to the same mean as the edges dilutes them.
  - This hit the old bending pairs and the first `_bend`.
  - Keep weak constraints out of the count.
- **Blender's Solidify with Even Thickness** shoots needles at sharp folds.
- **The seam measure** must use HM_body subdivided as the shown skin was built (`sub_ids` index into it), and `matrix_world` applied.
- **Bergou's cotangent weights** assume the hinge's two triangles are not flipped. A test mesh with too much noise flipped some and broke the flat-is-zero check.

## Experiments (2026-11-15, evening)

Runner `investigations/pose-capture/experimentos.py`, catalogue `variacoes.json`, outputs and `resumo.txt` in `G:\mocap-studio-downloads\review\2026-11-15\experimentos\` (one `.blend` + `.bat` per variation). Run-to-run noise on the same settings: ~1 point of top stretch, ~500 inverted tetrahedra (GPU atomics).

- **Experiment 1, Rafael's new bodies** (`2nd_test_female` 1.87 m, `2nd_test_male` 1.90 m): the whole chain runs with no code change. The female's top blows up (NaN) at frame ~90: arms retargeted by direction go ~5 cm into her chest after the ramp (833 skin points against 0 on the base). The male completes, but the casual suit is too short for his belly (tears, rides up), right-forearm snag in 213 frames, 4x the inverted tetrahedra. Break points: retarget ignores the body's width; MPFB clothes don't fit far bodies; no divergence guard in the sim. Fixes proposed, waiting for Rafael.
- **Experiment 2, 31 variations against the base** (top stretch p95 8.1%, snags 0/10, 5,400 inverted):
  - better: `mov_suave_4q` (5.0%, no snags, 4,200), `roupa_1mm` (4.9%, 4,200), `tec_gordura_firme` and `tec_volume_049` (fewer inverted: 3,700 and 2,800);
  - worse: `mov_suave_1q` (snags 26/45), `cm_sem_folga_pele` (43 right), `tec_gordura_mole` (2x inverted), `tec_pele_50kpa` (11%, max 470%), `tec_pele_300kpa` (2x inverted), `cm_passos_80` (3x inverted), `roupa_3mm` (13.7%), `roupa_pano_pano` (9.3%);
  - within noise: hands, wrist frequency, loose feet, ramp 60, caps 20 mm, skin gap 3 mm, damping, real density, cloth bending, traction, friction.
  - **`cm_passos_320` blew up** (937,000 inverted, 6.7 s per frame): twice the substeps should be steadier. Likely a solver defect (something that scales with h); not investigated.
- `comb_suave4q_pano1mm` (smoothing 4 frames + 1 mm cloth): top stretch 4.3%, snags 0/1, 3,400 inverted: better than either alone, the best result so far; waiting for Rafael's look.
