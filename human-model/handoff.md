# Handoff: pose-capture body with clothes, hands and contact (2026-11-15)

For the next session and for Rafael. It continues three earlier handoffs:
- [investigations/pose-capture/HANDOFF-2026-11-15-contato.md](investigations/pose-capture/HANDOFF-2026-11-15-contato.md): contact between body parts.
- [clothing-handoff.md](clothing-handoff.md): tissue and clothes simulated together.
- [investigations/pose-capture/HANDOFF-2026-11-14-tecidos.md](investigations/pose-capture/HANDOFF-2026-11-14-tecidos.md): the tetrahedral tissue.

The as-built is in [investigations/pose-capture/CLAUDE.md](investigations/pose-capture/CLAUDE.md). The math of every step is in [docs/transformações/](docs/transformações/), in Portuguese: a draw.io diagram, Typst sources and PDFs.

## Rafael's verdict at the end of this session

> "não ficou melhor não... a roupa continua 'enroscando' no punho, o punho está descolando do braço e a mesma coisa acontece com os tornozelos."

- **`tet_v10` is not better.** It has hands that collide, the cloth tested against every body part, and blended seams.
- **`tet_v8` was "bem melhor".** It has neutral gains and the clothes, with the hands as captured.
- **Neither is marked as the best.** The last marked best is still `tet_v6` (tag `pose-capture-melhor-2026-11-14`), which is without clothes.

## Decisions Rafael made in this session (don't reopen)

1. **All motion gains are neutral (1).** He wants to judge a first result before adding gain. This was his feeling from the start.
2. **The skin yields 5 mm** in the contact between parts. Past that, overlap is shown and counted as skeleton error.
3. **This work took over `drive_capture.py`:** planted feet are held by leg IK, and the hips drop when the feet are out of reach.
4. **Clothes must be in every result.** The naked body can't be shared, so every video would have to be made again.
5. **Hands are pendulums following the armature, with anatomical limits.** The wrist is "mixed": a spring towards the captured hand. *Nothing non-anatomical.*
6. **The clothes are 2 mm thick, as a volume without volumetric computation** (top and jeans).
   - **What he meant:** the thick-shell model. The answer given was yes: the main gain would be bending stiffness derived from the thickness, D = E·t³/12(1−ν²), instead of today's `flexao_N_m` by eye.
   - **Not built.** Waiting for his go-ahead.
   - **Not the same as the cloth-on-cloth contact built this session**, which is something else (see below).
7. **The work must hold for any garment and any body.** Anything tied to this one case is a problem; see "Tied to this case".
8. **The calibration without a board is not the main suspect.** He offered real sizes from the scene to anchor it, for later.

## What was found and built, in order

### 1. Why tet_v7 was terrible: the hips gain dragged the planted feet

- **Where:** `amplify_capture.py` rebuilds every point, feet included, from the amplified hips path. The legs don't compensate.
- **Effect, measured:** a planted foot's point slides 24 mm (median) during a contact before gain 3, and 188 mm after it (p90 392, max 509).
- **Consequence:** the IK then dropped the hips up to 174 mm to reach the feet.
- **At gain 1:** the drop is at most 42 mm, with no slip and no foot out of reach (`tet_v8`).
- **Documented:** in the diagram and in `07_ganho.typ` (docs/transformações).
- **Rule before using any gain again:** the gain must carry the legs with the hips. Fix `amplify_capture.py` first.

### 2. The transformations diagram

`docs/transformações/`:
- the draw.io diagram (uncommitted, copied here at Rafael's request; he will translate it to English later);
- one Typst file per step, from MediaPipe's two-camera output to the assembled `.blend`;
- the PDFs;
- each step's "ponto de atenção" (what looked suspect).

### 3. Clothes brought in (step 17 of the other session)

- **Motion:** step 17 runs on the neutral motion, `tet_v8`.
- **Mesh:** the cloth solver needs a tissue mesh built at rest (`malha_v10_repouso_para_desenho`).
- **Values:** `roupas.json`, unchanged.

### 4. Cloth on cloth, 2 mm (`tissue_cloth_solver._cloth_cloth`)

- **How it works:** a cloth vertex keeps the pieces' `espessura_mm` from any cloth triangle, on the side it was on a substep before.
- **Neighbourhood excluded:** the same piece's triangles within `pano_pano_longe_em_repouso_mm` (25 mm) at rest.
- **Result: it made the top stretch more** (p95 median 19% against 15.5%). It is **off** (`pano_pano=0`) in tet_v10.
- **Likely reason, not checked:** at rest the top already overlaps itself and the jeans.

### 5. Hands as pendulums (`hand_pendulum.py`, values and sources in `maos.json`)

**What it does:**
- **Forearm rotation:** the hand's twist about its length moves to the forearm (pronation and supination, ±80°).
- **Wrist:** two damped springs towards the captured hand (3 Hz, ζ 0.7), plus the hand's weight and the wrist's acceleration.
- **Fingers:** MCP, PIP, DIP and the thumb's MCP and IP are damped pendulums (6 Hz, ζ 0.4) towards a relaxed hand. They bend only towards the palm.

**Limits** (the smaller where sources disagree):

| Joint | Range | Source |
|---|---|---|
| Wrist | flexion 75°, extension 70°, radial 20°, ulnar 30° | eatonhand; AAOS via Queen's |
| Fingers MCP / PIP / DIP | 80° / 90° / 65° | Hendriks 2020, AAOS-based |
| Thumb MCP / IP | 50° / 80° | Hendriks 2020 |
| Forearm rotation | ±80° | textbook, **not checked** |

**Measured:**
- The hand sits 10° (median) and 24° (p95) from the captured one.
- Blender's hand matches the model to 0.0°.
- The wrist is at a limit less than 0.3% of the time.

### 6. Hands collide (`tissue_cloth_sim.py corpo=…/corpo_repouso.npz`)

- **What collides:** MPFB's skin under the hand, palm and finger bones, skinned by the skeleton each frame. It pushes skin and cloth out and doesn't yield.
- **Measured:** at most 4 skin points (6 mm) and 2 cloth vertices inside a hand in the whole dance.

### 7. The cloth tested against every part's skin

- **Why:** against the nearest skin of the whole body, a cloth vertex lying 2 mm over the belly never saw the forearm coming down, and the arm went through the top.
- **Now:** the cloth is tested against the trunk's, each arm's and each leg's skin.

### 8. Seams at the cuts (`_drive_blend`)

- **Old way:** the cut's driven nodes (wrists, ankles, neck) followed one bone each. Blender skins the hand next to them by a blend of forearm and hand. With the wrist bent, the two came up to 15 mm apart (p95 7–8 mm).
- **Now:** they follow the rest skin's blended weights. `costura_rigida=1` restores the old way.
- **Rafael still sees wrists and ankles coming apart in tet_v10** (see Open, item 1).

## Files

### Review folder

`G:\mocap-studio-downloads\review\2026-11-14\pose_capture\`. Each `.blend` has an `abrir_*.bat` for the portable Blender 5.2.2.

| File | What it is |
|---|---|
| `tet_v7_*` | gain 3, held feet, contact. Rafael: "péssimo". `LEIA_tet_v7.txt` |
| `tet_v8_cenario_roupa.blend` | gains neutral, clothes, captured hands. Rafael: "bem melhor" |
| `tet_v9_cenario_roupa_maos.blend` / `…_sem_pano_pano.blend` | pendulum hands, with and without cloth-on-cloth |
| `tet_v10_cenario_roupa_maos.blend` | + hands colliding, cloth against every part, blended seams. Rafael: not better |
| `tet_v8_movimento/` | `movimento_ganho_1_pes_presos.blend`, `ossos_ganho_1.npz` |
| `tet_v9_movimento/` | `movimento_ganho_1_maos.blend`, `ossos_ganho_1_maos.npz`, `relatorio_maos.json`, `maos.json` |
| `tet_v10_roupa/` | `roupas.json`, `sim/` (pc2 and `relatorio.json`), `sim_log.txt` |
| `_scripts/` | check stills (`conferencia_tet_v8`, `_v9`, `_v10`) and test runs; wrong ones carry `_ERRADO_` |

### Code

**Committed:**
- `96c18ea`: contact between parts, held feet.
- `a37ee73`: the other session's clothing handoff.

**Uncommitted at the end of this session** (Rafael didn't ask for a commit):
- `investigations/pose-capture/`:
  - `tissue_cloth_solver.py`: cloth on cloth, the cloth against every part, hands, `_drive_blend`;
  - `tissue_cloth_sim.py`: `pano_pano=`, `corpo=`, `costura_rigida=`, the hands, the seam gap in the report;
  - `roupas.json`: `pano_pano_longe_em_repouso_mm`;
  - `CLAUDE.md`;
  - new: `hand_pendulum.py`, `maos.json`.
- `docs/transformações/`: new, not yet in git.
- **Not this session's:** `INTEGRATION-motion-filter.md` shows as deleted. The other session did that; leave it to them.

## How tet_v10 was built

From the repository root, with `R=/mnt/g/mocap-studio-downloads/review/2026-11-14/pose_capture`, `S=human-model/investigations/pose-capture` and `M=$R/11_tecidos/malha_v10_repouso_para_desenho/tecidos.npz`.

```sh
# motion: levelled capture (gain 1 = no amplify step), held feet
python3 human-model/blender_run.py --blend $R/02_corpo_com_rig.blend $S/drive_capture.py $R/15_chao_e_contatos/contatos.npz \
    $R/tet_v8_movimento/movimento_ganho_1_pes_presos.blend $R/tet_v8_movimento/relatorio_retarget.json --no-head
# hands as pendulums
python3 human-model/blender_run.py --blend $R/tet_v8_movimento/movimento_ganho_1_pes_presos.blend $S/hand_pendulum.py \
    $R/tet_v9_movimento/movimento_ganho_1_maos.blend $R/tet_v9_movimento/relatorio_maos.json $R/tet_v9_movimento/maos.json
python3 human-model/blender_run.py --blend $R/tet_v9_movimento/movimento_ganho_1_maos.blend $S/tissue_motion_dump.py $R/tet_v9_movimento/ossos_ganho_1_maos.npz
# tissue + clothes + hands (~0.66 s per frame, ~4 min)
human-model/hm.sh --gpu python $S/tissue_cloth_sim.py $M $R/tet_v9_movimento/ossos_ganho_1_maos.npz $R/17_roupa/roupa_repouso.npz \
    $R/tet_v10_roupa/roupas.json $R/tet_v10_roupa/sim pano_pano=0 corpo=$R/11_tecidos/corpo_repouso.npz
# assemble (as clothing-handoff.md step 17c)
python3 human-model/blender_run.py --blend $R/tet_v9_movimento/movimento_ganho_1_maos.blend $S/tissue_assemble.py $M $R/tet_v10_roupa/sim/pele.pc2 $R/tet_v10_roupa/montagem_pele.blend
python3 human-model/blender_run.py --blend $R/tet_v10_roupa/montagem_pele.blend $S/stage_video.py $R/tet_v10_roupa/x $R/tet_v10_roupa/montagem_cenario.blend --no-frames
python3 human-model/blender_run.py --blend $R/tet_v10_roupa/montagem_cenario.blend $S/dress_assemble.py $R/17_vestida_repouso.blend $R/tet_v10_roupa/sim blusinha,jeans $R/tet_v10_cenario_roupa_maos.blend
```

`$R/_scripts/confere_caches.py` checks that every Mesh Cache in a `.blend` finds its file and moves.

## Open, in the order I'd take them

1. **Wrists and ankles come apart from the arm and leg** (Rafael, tet_v10).
   - **What `_drive_blend` closed:** the gap at the cut's *driven nodes* (15 mm → 0 by construction). Rafael still sees the seam open, so the measurement didn't look at the right thing.
   - **First, measure what is seen.** In Blender, per frame, the distance from `HM_body`'s seam rings (skinned by the rig) to the nearest vertex of `HM_pele_simulada`.
   - **Hypotheses to check:**
     - the shown skin near the cut is tied to *free* tetrahedra, not to the driven nodes. Only nodes within `cap_drive_m` (12 mm) of the cut plane are driven, so the skin a few mm in can sag or swing away;
     - the forearm twist from `hand_pendulum.py` (up to ±80°) stretches the forearm's tissue, while Blender's linear skinning wraps the wrist;
     - the mesh is built at rest (A pose), and the ramp bringing the arms down inverts thousands of tetrahedra, some near the cuts.
   - **The ankles** have no pendulum, so the first hypothesis is the likelier one there.
2. **The top's hem snags around the wrist.** It started when the forearm became a collider for the cloth (tet_v10): the forearm coming down catches the hem, and the hem wraps it like a bracelet. Things to look at:
   - the friction against the skin (`atrito` 0.4) holds the hem on the forearm;
   - no cloth-on-cloth contact, so the hem folds through itself;
   - the hem, caught between the forearm and the belly, is pushed by two parts at once.
3. **The cloth's thickness as a thick shell** (Rafael's decision 6), once he agrees:
   - bending stiffness from the thickness and the fabric;
   - a Solidify modifier to show the 2 mm;
   - then try cloth-on-cloth again, checking first how much the pieces overlap at rest.
4. **Make general what is tied to this case** (Rafael's decision 7). Listed at the end of the investigation's `CLAUDE.md`:
   - `female_casualsuit01` split into top and jeans by "the upper connected part";
   - lengths in metres that depend on the body's size (`ARM_RADIUS_M`, `GLUTEAL_FOLD_M`, `BUTTOCK_BEHIND_M`, the skin-under-cloth rules of 2 cm, 5 cm and 12 mm);
   - values by eye per group or piece name;
   - MPFB rig names, which are general for MPFB characters only.
5. **The top still rides up and tears near the breasts.** Its p95 stretch is 16% (median), up to 27%. See `clothing-handoff.md` item 3; the nipple size is still Rafael's call.
6. **The checkered crease on the left thigh, at the hip** (Rafael, tet_v8). Not looked at.
7. **Gains:** before any gain other than 1, make `amplify_capture.py` carry the legs with the hips (finding 1).
8. **From earlier handoffs, still open:**
   - leg/trunk contact (buttock/thigh, belly/thigh);
   - a yield per region instead of 5 mm everywhere;
   - the breasts' rest shape;
   - left/right configured separately.

## Gotchas found this session

- **Measuring in Blender:** after keying, every frame must be evaluated (`scene.frame_set`). Measured while writing keys, the scene stayed on the last frame, and the hand read 32–49° off the capture when it was 10°.
- **A twist moved from the wrist to the forearm** must be split about the forearm's axis seen in the hand's frame, twist first, in the order the hand is rebuilt.
- **Cloth on cloth can't use the nearest-point query.** From a cloth vertex it always returns the vertex's own face. Walk the faces in a box (`mesh_query_aabb`) and skip the vertex's neighbourhood.
- **Cloth contact against the "nearest skin of the body" misses a second body part** a few mm further.
- **Contact pushes inside XPBD:** move `x_prev` with the push (pre-stabilization). Otherwise the push becomes velocity and pumps energy (`tissue_solver.ContactSolver`).
- **`tissue_assemble.py`'s Mesh Cache path** must be relative to the open file. Otherwise, with the motion in another folder, the skin stands still.
- **Another session shares this clone, branch and review folder.** Commit only your own files, by path, and give your outputs their own prefix (this one used `tet_v7`…`tet_v10`).

## Constraints that still hold

- **Licenses** must allow commercial use, even for tests.
- **Keep every attempt.** Wrong ones are renamed `_ERRADO_<why>`, never deleted.
- **No renders or videos for Rafael unless he asks.** Check stills go in `_scripts/`.
- **Every review `.blend` gets an `abrir_*.bat`.**
- **Explain a soft-tissue design to Rafael, with drawings, before changing it.**
