## 2. Structure inventory

- **Type:** research, with a read-only script over the reference file. Rafael approves.
- **Depends on:** `references/1`
- **Contract:**
  - In: Z-Anatomy's `Startup.blend`, opened with auto-run scripts off
  - Requires: Rafael's rule to keep as much as possible until it's no longer needed
  - Delivers: a table in this file with one row per structure group: count, vertices,
    decision (rebuild, keep as reference only, leave out), reason. The file's
    `Bonus collection` repeats structures, so counts must not add it twice
- **Pre-work:** —
- **Out of scope:** building any structure
- **Tests:** —

**Starting proposal, to be argued with Rafael:**

| Group | Proposal | Why |
|---|---|---|
| Skeleton | Rebuild | Rafael: keep until data replaces it |
| Muscles and joints | Rebuild | Same |
| Rib cage, diaphragm, lungs as volume | Rebuild as simple volume | Breathing is visible |
| Larynx | Rebuild | Visible when speaking |
| Eyes, teeth, tongue | Rebuild | Visible |
| Superficial veins and tendons | To be decided | May be visible on hands and neck |
| Brain, digestive system | Leave out | Rafael |
| Other organs, lymph nodes, deep vessels | Leave out | Not visible, to confirm |
| Nerves | Reference only | Possible way to group controls |
| Genitalia | Leave out | Rafael |
| Labels, reference lines, section planes | Leave out | Atlas tools |

## Result (2026-11-03)

From `human-model/references/inventory.py` on `z_anatomy_original.blend`, with auto-run
off. 4,569 meshes and 2,094,701 vertices. Each mesh is counted once under its numbered
collection, so `Bonus collection` isn't added twice. "Rebuild" means from the sources in
`references/1`, never from these meshes.

| Group | Meshes | Vertices | Decision | Reason |
|---|---:|---:|---|---|
| 1 Skeletal system | 1,244 | 302,352 | Rebuild | Rafael: keep until data replaces it. Hyoid and larynx parts included |
| 2 Muscular insertions | 705 | 44,375 | Reference only | Our origins and insertions are declared per muscle from anatomy, on our own bones |
| 3 Joints | 480 | 86,320 | Rebuild as joint rules; ligament meshes left out | The behaviour matters. **Loss of detail:** no ligament geometry, but each joint keeps its limits |
| 4 Muscular system | 789 | 1,075,358 | Rebuild | Same rule as the bones, about 1 million vertices here is the speed risk |
| Rib cage, diaphragm, lungs | part of 1, 4, 8 | 9,674 (diaphragm) + 14,317 (lungs) | Rebuild as breathing rig and volume | Breathing is visible |
| Larynx | part of 8 | 16,376 | Rebuild as a moving volume with the hyoid | Visible when speaking |
| Eyes, teeth, tongue | part of 1, 7, 8 | 18,529 + 23,536 + 2,899 | Rebuild from MPFB's CC0 assets | Visible |
| 5 Cardiovascular | 60 | 34,407 | Leave out for now; superficial veins reopen for hands and neck in `skin` | No source to build from yet. **Loss of detail,** recorded here |
| 6 Lymphoid organs | 220 | 65,285 | Leave out | Not visible |
| 7 Nervous system and sense organs (other than eyes) | 460 | 398,709 | Reference only; brain left out | Possible way to group controls |
| 8 Visceral systems (other than the above) | 254 | 43,628 | Leave out | Not visible; the abdomen's volume comes from soft tissue |
| Genitalia | 28 | 2,678 | Leave out | Rafael |
| 9 Regions, reference lines, planes | 354 | 44,212 | Leave out | Atlas tools |
