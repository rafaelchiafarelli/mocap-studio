# Handoff: the tetrahedral soft tissue on the captured dance

Written 2026-11-14, at the end of the session that took the pose-capture investigation from MediaPipe to a simulated soft tissue. It is for the next session and for Rafael. The first handoff, [HANDOFF.md](HANDOFF.md), explains why this investigation exists. The as-built is in [CLAUDE.md](CLAUDE.md), with every file and the gotchas.

## Where things stand

**Best so far** (Rafael asked for it to be marked):
- **Code:** git tag `pose-capture-melhor-2026-11-14` on branch `pose-capture` (commit `dd3bffa`), pushed.
- **Review files:** in `G:\mocap-studio-downloads\review\2026-11-14\pose_capture\`, listed in `MELHOR_ATE_AGORA.txt`:
  - `tet_v6_cenario.blend` (open with `abrir_tet_v6_cenario.bat`);
  - `tet_v6_tecidos.blend`;
  - `tet_v6_comparacao_sem_fisica_ondas_tetraedros.mp4`;
  - `13_parametros_por_regiao.html`, every parameter per region, with drawings from the mesh.

**Rafael's verdicts and decisions, in order:**
1. **Single-camera MediaPipe is not enough.** The body floats, leans forward, and high heels throw the feet. Two cameras are needed.
2. **The two-camera setup has no calibration board.** The cameras are found from the body itself, and a clap syncs the sound. Rafael recorded himself (`G:\mocap-studio-downloads\media_pipe_videos\`). Use only stretches where the whole body is in both cameras. The person is taken as 1.70 m tall.
3. **Two-camera result (step 07): "está ruim, mas podemos seguir".** The dance's hip motion was not captured.
4. **The architecture is fixed in three layers.** These are his words; don't reopen them:
   - the skeleton (limb positions, body motion, balance) comes from MediaPipe as it is;
   - skin, fat and muscle come from a simulation;
   - limbs are kept from passing through the body by contact between surfaces.
5. **Soft tissue is option A, a tetrahedral volume (XPBD).** It is still an investigation, not an initiative. It must be explained with drawings before it is changed:
   - tetrahedra graded from the skin inward: 3 layers each of 3, 6 and 9 mm, then 12 mm;
   - material per limb group;
   - one fat volume per breast, as its own group, between the skin and the rib cage.
6. **Option asked for:** a neutral density, `densidade_neutra`. It is implemented and off by default.
7. **Next agreed step: contact between surfaces.** It was not started.

## The pipeline (step 11, all in this folder)

Paths below are under `G:\…\pose_capture\` (`/mnt/g/…` from WSL). Blender scripts run through `human-model/blender_run.py`. Warp scripts need `hm.sh --gpu`, because the plain image has no Warp.

```
# 11a  rest body, breastless body, subdivided skin (Blender, on the rigged body)
python3 human-model/blender_run.py --blend $R/02_corpo_com_rig.blend human-model/investigations/pose-capture/tissue_export.py $R/11_tecidos/corpo_repouso.npz
# 11c  bone transforms per frame of the motion (Blender)
python3 human-model/blender_run.py --blend $R/07_movimento_duas_cameras_31-43s.blend human-model/investigations/pose-capture/tissue_motion_dump.py $R/11_tecidos/ossos_07.npz
# 11b  graded mesh, built in the dance's first frame (~3 min)
human-model/hm.sh --gpu python human-model/investigations/pose-capture/tissue_mesh.py $R/11_tecidos/corpo_repouso.npz $R/11_tecidos/malha_NAME pose=$R/11_tecidos/ossos_07.npz:1 [group.key=value ...]
# 11d  simulation (~1.5 min, 160 steps per frame)
human-model/hm.sh --gpu python human-model/investigations/pose-capture/tissue_sim.py $R/11_tecidos/malha_NAME/tecidos.npz $R/11_tecidos/ossos_07.npz $R/11_tecidos/sim_NAME
# 11e  into Blender, then the gridded stage and its frames
python3 human-model/blender_run.py --blend $R/07_movimento_duas_cameras_31-43s.blend human-model/investigations/pose-capture/tissue_assemble.py $R/11_tecidos/malha_NAME/tecidos.npz $R/11_tecidos/sim_NAME/pele.pc2 $R/OUT.blend
python3 human-model/blender_run.py --blend $R/OUT.blend human-model/investigations/pose-capture/stage_video.py $R/FRAMES_DIR $R/OUT_cenario.blend
# measure: crease edges against the skinned skin (12 frames dumped in 11_tecidos/pele_esqueleto_subdividida.npz)
human-model/hm.sh python human-model/investigations/pose-capture/creases.py $R/11_tecidos/malha_NAME/tecidos.npz $R/11_tecidos/sim_NAME/pele.pc2 $R/11_tecidos/pele_esqueleto_subdividida.npz
# drawings for the parameter page (from a mesh built WITHOUT pose=), then the page is spliced by _scripts/splice13.py on G:
human-model/hm.sh python human-model/investigations/pose-capture/tissue_drawings.py $R/11_tecidos/malha_REST/tecidos.npz $R/11_tecidos/corpo_repouso.npz $R/13_parametros_imagens
```

The values live in `tissue_groups.json`: material per group, the reduced anatomy and the mesh bands. The comparison video is assembled with ffmpeg, as in the commits for steps 09 and 12: camera A, then the frames of `09_quadros_cenario_sem_fisica`, `09_quadros_cenario_com_ondas` and the new stage frames, side by side.

## Measured (best run: malha_v11_quadro1_grupos_corrigidos, sim_v8_grupos_corrigidos)

**Mesh and cost:**
- **Size:** 3.34 M tetrahedra (2.53 M of them 3 mm) and 63,611 shown skin vertices.
- **Speed:** 224 ms per frame; the 341 frames take ~1.5 min.
- **Convergence:** 160, 320 and 640 steps per frame give the same motion.

**Simulation:**
- **Volume and inversion:** 99.7–100% of the volume is kept. 41 tetrahedra are inverted at frame 1 and up to ~6,800 (0.2%) during the dance.
- **Tissue's own motion against its bone:** p95 of 25–60 mm, with breasts and belly the largest.
- **Breasts:** 1.13 L and 1.11 L.

**Creases** (crease edges over 12 frames):
- **Totals:** best run 26,664. One density and one damping gave 26,331, and fixing the bands' overlap gave 26,661, so neither is the cause.

## Open, in the order I'd take them

1. **Contact between surfaces** (agreed next).
   - **What's wrong:** hands go into the body.
   - **Probably the creases too:** with the arms down in frame 1, the skinned arm and flank overlap, and the mesh fuses them into one volume. About 1,070 crease vertices already show at frame 1, at 1.18–1.24 m, where the arm meets the trunk and high on the chest.
   - **What it likely needs:**
     - Build arm and trunk as separate volumes. Cut the mesh by group at the armpit, and between the thighs if needed.
     - Add skin-to-skin collision in `GradedSolver`, where the softer side yields (memory `contact-over-avoidance`).
     - Measure, not hide, any skeleton penetration beyond what the tissue absorbs. The design drawing (`10_desenho_tecidos.html`) leaves "how far the skin may yield" for Rafael to set (5–30 mm).
2. **Find the remaining creases.** `creases.py` counts them. Map them on the skin, and check them against the rigid edges (rib cage top at spine.004 + 3 cm, pelvis block, shoulder capsules) and against the ankle and neck seams. Many crease edges sit at z ≈ 0.11, which is the ankle seam.
3. **Breast rest shape.** MPFB's shape is already the standing shape, and the simulation adds gravity on top, so breasts sag ~25 mm. It needs a pre-stressed rest shape whose equilibrium under gravity is MPFB's. Rafael's "breast simulator" values (`meu_teste`, 2026-11-05, memory `muscle-physics-experiments`) were not carried over: `seio_E` and `seio_D` are by eye.
4. **Promised in the design but not built:**
   - blending values over ~2 cm between neighbouring groups;
   - left and right configured separately. Groups are per limb, not per side, except the breasts.
5. **Capture itself:**
   - the head is ignored, and kept on the chest with `--no-head`;
   - the phones' focal length is assumed 26 mm;
   - MediaPipe misses the pelvis's tilt and roll. Rafael rejected patching that and chose the layered architecture above.

## Things that cost time today

- **Another session shares this clone, branch and review folder.** It does floor levelling and clothes (`dress_cloth.py`, `roupas.json`) and numbers its review outputs `14_`, `15_`. Rafael: "não esquenta com a outra sessão". Commit only your own files, by path, and give your outputs a prefix of their own (this session's latest are `tet_v6_*`).
- **OpenCV in the reference image doesn't apply a phone video's rotation.** Set `CAP_PROP_ORIENTATION_AUTO`, as already done in `capture_pose.py` and `two_cameras.py`.
- **Debug scripts are kept on G:** in `pose_capture/_scripts/`. Never name one like a stdlib module: an `inspect.py` there broke numpy's import. Run them with `python -I`.
- **Blender path arguments must start with `/`** to be converted to Windows paths (`blender_run.py`).
- **Don't wait on a process with `pgrep -f <name>`** inside the same shell command: it matches itself.
- **Keep every attempt.** Wrong ones are renamed `_ERRADO_<why>`, never deleted (memory `keep-intermediate-results`). Every `.blend` gets an `abrir_*.bat` for the portable Blender 5.2.2.
