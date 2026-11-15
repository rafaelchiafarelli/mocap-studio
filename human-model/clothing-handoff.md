# Handoff: clothes on the pose-capture body

Written 2026-11-15, at the end of the session that dressed the pose-capture body. It is for the session that merges this work with the soft-tissue work, and for Rafael.

The code is in `human-model/investigations/pose-capture/`, on branch `pose-capture`. Its as-built is in that folder's [CLAUDE.md](investigations/pose-capture/CLAUDE.md). Review files are in `G:\mocap-studio-downloads\review\2026-11-14\pose_capture\`.

## What Rafael asked for and decided

1. **Dress the body in jeans and a top, made of mesh** (2026-11-14). Open-source tools only, licensed for commercial use.
2. **Option (b): real cloth that the body pushes**, rather than clothes glued to the skin.
3. **Blender cloth over the already-simulated skin failed at the armpit** (step 16). Arm and flank skin pass through each other in the tetrahedral simulation, and the sleeve is crushed between them.
4. **Then he set the approach:** "take the original model, in its original pose, dress it, then make the physics simulate with it". Tissue and cloth are now one simulation (step 17).
5. **His verdict on step 17:** "não está ruim, realmente está melhor do que eu tinha imaginado". The nipple comes through the top.
6. **His proposed fix: make the nipple smaller.** He prefers this to more contact rules. **Not done yet:** the amount, and whether it applies only to the dressed body, are still his to decide (see "Pending").

## Where things stand

**Code:**
- **Commits:** `3074cff` (steps 16 and 17a) and `79abbbf` (step 17b/c), both pushed.
- **Tag:** `pose-capture-roupa-v1-2026-11-14`. Use it to get back to the version that produced the review file.

**Review files** (open each with its `abrir_*.bat`, in the portable Blender 5.2.2):
- `17_cenario_roupa_v1.blend`: **the result.** The captured dance on the gridded stage, with simulated skin, top and jeans.
- `17_vestida_repouso.blend`: the body dressed in MPFB's A pose, before any simulation.
- `16_blusinha_v1.blend`: step 16's file, saved before its cloth was baked. It has no cloth cache; kept only as a record.
- `17_roupa/`: `roupa_repouso.npz` (+ `.json`), `roupas_v1.json` (the values of the run), `sim_v1/` (the whole dance), `teste_*` (short runs, wrong ones marked `_ERRADO_`) and `montagem_*` (assembly steps).
- `16_roupa/`: step 16's values and log.
- `_scripts/teste_roupa*`, `_scripts/teste_17`, `_scripts/vestida_repouso`: check runs and stills.

**The clothes:** MPFB's `female_casualsuit01`, from the MakeHuman system assets (CC0). It is one mesh: its upper connected part is the top, its lower part the jeans. It is installed with MPFB in the portable Blender:
`G:\mocap-studio-downloads\apps\blender\5.2.2\blender-5.2.2-windows-x64\portable\extensions\.user\user_default\mpfb\data\clothes\female_casualsuit01\`.

## Merging with the soft-tissue work

**Read this first.**
- **The cloth solver imports the tissue code.** `tissue_cloth_solver.py` subclasses `tissue_solver.GradedSolver` and uses its `_apply`, `_glue`, `_velocity_relative_nodes` and `GLUE_COMPLIANCE`. `tissue_cloth_sim.py` imports `GROUPS`, `ramp_transforms` and `write_pc2` from `tissue_sim.py`.
- **The other session has uncommitted changes in those files.** At the end of this session, `tissue_solver.py`, `tissue_sim.py`, `tissue_mesh.py` and `drive_capture.py` were modified and uncommitted. Those changes belong to the other session; this session never touched them.
- **What to check after merging:**
  - `GradedSolver.__init__`'s signature and `_substeps` are unchanged. `ClothTissueSolver._substeps` copies the tissue part of `_substeps`, so a change to the tissue's substep must be repeated there.
  - The mesh npz from `tissue_mesh.py` still has `sub_tet`, `sub_bary`, `sub_rest`, `sub_faces`, `group`, `node_bone`, `driven`, `drive_bone`, `emb_*` and `pose_frame`.
- **Mesh built at rest.** The cloth simulation needs the tissue mesh built at rest (`tissue_mesh.py` without `pose=`), because the clothes are fitted at rest. The soft-tissue session's best run (`tet_v6`, `malha_v11_quadro1_grupos_corrigidos`) is built in the dance's first frame. Step 17 used `malha_v10_repouso_para_desenho`: the same configuration as v11, but at rest.
- **Built at rest, the ramp inverts tetrahedra.** When the arms come down, 1,500 to 5,500 tetrahedra invert (the frame-1 mesh has ~41 at the start). With contact this is fewer than before: 4,981 inverted at the end of the ramp without contact, 2,971 with it.
- **Same output folder.** Both sessions write into the same review folder. This one's outputs are numbered `16_` and `17_`; the soft-tissue session uses `tet_v6_*`.

## How it's built (step 17)

```
R=/mnt/g/mocap-studio-downloads/review/2026-11-14/pose_capture
C=/mnt/g/mocap-studio-downloads/apps/blender/5.2.2/blender-5.2.2-windows-x64/portable/extensions/.user/user_default/mpfb/data/clothes/female_casualsuit01
P=human-model/investigations/pose-capture

# 17a  dress the rest body (MPFB's own fitting, A pose); clothes pushed 3 mm out of the tissue's shown skin
python3 human-model/blender_run.py --blend $R/02_corpo_com_rig.blend $P/dress_rest.py $C $R/17_vestida_repouso.blend $R/17_roupa/roupa_repouso.npz
# (tissue mesh at rest, if a new one is needed: tissue_export.py, then tissue_mesh.py WITHOUT pose=; see HANDOFF-2026-11-14-tecidos.md)
# 17b  tissue + clothes together on the GPU (~0.5 s per frame, the 341-frame dance in ~3 min)
human-model/hm.sh --gpu python $P/tissue_cloth_sim.py $R/11_tecidos/malha_v10_repouso_para_desenho/tecidos.npz $R/11_tecidos/ossos_07.npz \
    $R/17_roupa/roupa_repouso.npz $R/17_roupa/roupas_v1.json $R/17_roupa/sim_v1 [pecas=blusinha,jeans] [frames=N] [hold=F] [sob_pano=tronco|todos|nao]
# 17c  into Blender: skin, stage, clothes
python3 human-model/blender_run.py --blend $R/07_movimento_duas_cameras_31-43s.blend $P/tissue_assemble.py $R/11_tecidos/malha_v10_repouso_para_desenho/tecidos.npz $R/17_roupa/sim_v1/pele.pc2 $R/17_roupa/montagem_pele_v1.blend
python3 human-model/blender_run.py --blend $R/17_roupa/montagem_pele_v1.blend $P/stage_video.py $R/17_roupa/x $R/17_roupa/montagem_cenario_v1.blend --no-frames
python3 human-model/blender_run.py --blend $R/17_roupa/montagem_cenario_v1.blend $P/dress_assemble.py $R/17_vestida_repouso.blend $R/17_roupa/sim_v1 blusinha,jeans $R/17_cenario_roupa_v1.blend
```

**Files:**
- **`mhclo_fit.py`:** MPFB's mhclo fitting in plain numpy, at rest or posed. Each offset turns with its triangle when posed.
- **`dress_rest.py`:** step 17a.
- **`tissue_cloth_solver.py`:** `ClothTissueSolver`, which adds three things to `GradedSolver`:
  - **Cloth:** the cloth's vertices are appended to the tissue's nodes with their real mass. Edges and bending pairs are XPBD distances, solved Jacobi-style and averaged per vertex.
  - **Contact:** three kinds, all two-way through the skin points' tetrahedra:
    - cloth on skin, with friction;
    - skin on the skin of another part (trunk, each arm, each leg);
    - skin kept under the cloth that lay over it at rest.
  - **Contact filter:** a contact counts only along the face's normal (`FACING`).
- **`tissue_cloth_sim.py`:** step 17b: the schedule (ramp, hold, dance), the waistband, and the report.
- **`dress_assemble.py`:** step 17c.
- **`roupas.json`:** the fabric values.
  - Under `pecas`: step 16's Blender-cloth values.
  - Under `solver_tetraedros`: step 17's, which are:
    - per piece: weight in g/m², stretch and bending stiffness in N/m, shrink, thickness, friction and damping;
    - the jeans' `encolhimento_cos` and `cos_mm`;
    - the skin-on-skin gap, and how far apart two points must be at rest to count as contact.
- **`dress_cloth.py`:** step 16, Blender cloth over the simulated skin. Superseded; kept as the record of why.

## Measured (sim_v1, the whole dance)

| | |
|---|---|
| Time | 490 ms per frame (tissue alone: ~224) |
| Skin inside another part's skin | 0–8 points, up to 6 mm (the armpit used to fuse) |
| Top inside the skin | up to ~150 of 5,148 vertices, ≤ 3.3 mm |
| Jeans inside the skin | up to ~25 vertices, one frame 7.8 mm |
| Top stretch, p95 | 10% at frame 1, growing to 17% by the end |
| Jeans stretch, p95 | 4–7% |
| Jeans waist against the body | settles ~16 mm lower than fitted, then holds |
| Inverted tetrahedra | 1,500–5,500 (0.05–0.16%) |

## Gotchas found

- **Blender cloth's real mass:** at 160 g/m², 18 mg per vertex, it blew apart in the first frames. Blender's preset of 0.3 kg per vertex holds. In the tetrahedral solver (XPBD), the real mass works.
- **Blender cloth's disk cache:** a disk cache starting at a negative frame was written but never read back. Use a memory cache, saved inside the `.blend`.
- **Surface Deform:** it won't bind to `HM_pele_simulada`'s concave quads. Add a Triangulate modifier first.
- **Relative paths:** Blender rewrites them when it appends and again on save-as. `dress_assemble.py` sets them after saving. `tissue_assemble.py` alone gives the skin a wrong path when the output is in another folder; `dress_assemble.py` repoints it.
- **Coarse skin through the top:** shown without subdivision, MPFB's coarse skin stands out of the smooth skin on every curve and comes through the clothes. `17_vestida_repouso.blend` shows the body subdivided twice, as the tissue does.
- **A nearest-face normal off an open border signs nothing** (wrist, neck, a part's edge). Without the `FACING` filter, 2,045 skin points read as "inside another part" at rest.
- **Skin under cloth:**
  - **Same part, near at rest:** it must use the cloth that lay over the same part, within 2 cm at rest. Otherwise the inner arm was pushed under the top's side into the trunk (`teste_3`), and arm and flank both pulled the sleeve, stretching it 50% (`teste_4`, `teste_5`).
  - **Trunk only:** even then it is limited to the trunk, more than 5 cm from the arms (`sob_pano=tronco`).
  - **Nipple tips:** at rest they already poke through between the cloth's vertices, so points within 12 mm on the outer side also count as covered.
- **Jeans:** with 2% shrink everywhere they slid 23 mm in 10 frames. A waistband shrunk 6% holds them.

## Open, in the order I'd take them

1. **Nipple through the top.** Rafael's fix is to make it smaller.
   - **The body's sliders:** `nipple-size-incr` 1.5, `nipple-point-incr` 0.63, `breast-point-incr` 0.51 (MPFB's default is 0).
   - **Waiting on him:** how much to reduce, and whether only on the dressed body.
   - **The work:** a copy of `02_corpo_com_rig.blend` with the sliders changed, then the whole chain again: `tissue_export.py`, `tissue_mesh.py` at rest, `dress_rest.py`, `tissue_cloth_sim.py` and assembly. About 20 minutes.
2. **Hands aren't in the simulation.** They go through the top and the body. They need to become contact objects, at least as points driven by the rig.
3. **The top rides up during the dance, and tears near the breasts by frame ~150.** This goes with the stretch growing from 10% to 17%. Possible causes:
   - friction too low against the arms' lift;
   - the shrink;
   - no cloth-on-cloth contact.
4. **No cloth-on-cloth contact.** The top's hem can pass inside the jeans' waistband, and the top can pass through itself.
5. **A diagonal fold on the back of the top,** where the skin has its known diagonal crease (soft-tissue open item).
6. **The collar is ragged at the neck cut.** The simulated skin ends there and the head isn't a collider.
7. **The clothes don't follow the body's sliders** (Rafael asked). Everything in step 17 is a recording, so a body change means running the chain again.

## Constraints that still hold

- **Licenses must allow commercial use, even for tests.** The clothes are CC0.
- **Keep every attempt.** Wrong ones are renamed `_ERRADO_<why>`, never deleted.
- **Every review `.blend` gets an `abrir_*.bat`.**
- **No renders or videos for Rafael unless he asks.** Check stills go in `_scripts/`.
- **Commit only your own files, by path.** Another session shares this clone and branch.
