# Handoff: contact between surfaces, and the filtered motion with held feet

Written 2026-11-15 for the next session and for Rafael. It continues [HANDOFF-2026-11-14-tecidos.md](HANDOFF-2026-11-14-tecidos.md) (items 1 of "Open") and [../../INTEGRATION-motion-filter.md](../../INTEGRATION-motion-filter.md). The as-built is in [CLAUDE.md](CLAUDE.md).

## Rafael's decisions (2026-11-14)

- **The skin yields 5 mm.** Any overlap the skeleton makes beyond that stays visible and is counted as skeleton error.
- **The motion is levelled, with hips gain 3.**
- **This session took over `drive_capture.py`** to hold the planted feet.

## What was built

1. **Motion.**
   - **Chain:** `15_chao_e_contatos/contatos.npz` → `amplify_capture.py --hips 3` → `drive_capture.py --no-head`, which now holds planted feet.
   - **Output:** `tet_v7_movimento/` on G:.
   - **How the feet are held:** each foot's heel or toe stays where it landed, and the leg reaches it by two-bone IK.
   - **Hips:** at gain 3 the legs can't reach, so the hips drop up to 174 mm, smoothed over two passes.
   - **Measured:** no slip on held frames.
2. **Separate volumes** (`tissue_mesh.py`).
   - **Parts:** trunk, left and right arm, left and right leg.
   - **Split:** arm and trunk, and the two legs, are split where they only touch in this pose. They stay joined where they move together, at the shoulder and the crotch.
   - **Leg and trunk are always joined**, because their split at the hip was tangled.
   - **Effect:** arm and flank no longer fuse at the armpit (the cut `cortes/axila_parte.png` shows them apart).
3. **Contact** (`ContactSolver` in `tissue_solver.py`, on in `tissue_sim.py`).
   - **What collides:** each part's 3 mm skin surface, against the other parts and against the hands, which follow the skeleton.
   - **Pairs left out:** leg/trunk, and each hand against its own arm.
   - **Check:** `test_tissue_contact.py` passes. Pressed 4 mm (inside the yield), 0.1 mm stays inside. Pressed 8 mm, 3.2 mm stays inside, against 3 expected.

## Results (`malha_v19_partes_perna_tronco_unidas`, `sim_v10_contato` / `sim_v10_sem_contato`)

- **Stability:** stable over the whole dance. Volume is 99.6–100.2%, and up to 19,000 tetrahedra invert (0.6%; 6,800 on tet_v6's gentler motion).
- **Cost:** 1.04 s per frame with contact, 0.23 s without, so 6 min for the dance.
- **Visible effect of contact: small.** Side by side with and without, at frames 60 and 200 (`_scripts/conferencia_lado_*.png`), the two look almost the same. The hand on the belly rests on it.
- **Not resolved:** about 980 surface nodes per frame (median) stay inside past what is allowed, up to 50 mm. They are in two places:
  - ankle against ankle, where both caps are driven by the skeleton, so neither side can yield;
  - the armpit, 18–24 mm from the shoulder join.
- **Skeleton past the 5 mm yield:** in 340 of 341 frames, up to 45 mm, mostly leg/trunk (not tested) and arm/trunk.
- **Defects seen with and without contact,** so the contact doesn't cause them:
  - a torn, crumpled patch at the side of the hip and the back of the thigh;
  - jagged skin at the armpits, where the shown skin crosses the arm/trunk split. 1,317 skin vertices are tied past the split, up to 27.6 mm.

## Open, in the order I'd take them

1. **The tear at the side of the hip.** It appears with the new motion and mesh, with or without contact. Check whether it is the gain-3 motion: run the same mesh on the levelled motion at gain 1 (`15_.../movimento_nivelado.blend`, re-dumped).
2. **Armpit skin across the split.** Real armpit skin is continuous. Options:
   - tie the vertices near the split to both parts, blended;
   - shrink the overlap at the build pose, for instance by building in a frame with the arms away from the body.
3. **Leg/trunk contact** (buttock/thigh, belly/thigh): needs a clean split at the hip first.
4. **Is 5 mm right?** At the groin and under the buttock, real tissue compresses by centimetres. A yield per region may suit better. It's Rafael's call.
5. **Still open from the earlier handoff:** the remaining creases, the breasts' rest shape (pre-stress), blending between groups, left and right configured separately.

## Gotchas found

See CLAUDE.md, "Contact, the failures that shaped it". The one that matters most for others: `tissue_assemble.py` must make the cache path relative to the open file. Otherwise, with the motion in another folder, the skin stands still.
