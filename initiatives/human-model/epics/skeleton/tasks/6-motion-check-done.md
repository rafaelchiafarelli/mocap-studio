## 6. Motion check

- **Type:** code.
- **Depends on:** `skeleton/1`–`5`, `references/4`
- **Contract:**
  - In: `references/4` limits, Fukuchi 2018 T05
  - Requires: A verdict on walking only from Rafael
  - Delivers: `blender/motion_check.py`, `blender/walk.py`, `data/gait_walk.json`, `tools/make_gait_table.py`, review video
- **Pre-work:** —
- **Out of scope:** —
- **Tests:** Mesh overlap at each limit

## Result (2026-11-03)

In 14 poses per model, every overlap is between two bones meeting at that joint (femur in hip socket, tibia on femur, talus on tibia, humerus on scapula). None between unrelated bones. **Depth isn't measured,** and joint limits are stored on the bones and applied by `posing.py`, not as Blender constraints, so a hand-posed joint can pass them. Walking: stride 1.02 m at a declared 1.1 s cycle, so 0.93 m/s against 1.24 m/s measured on trial T05: the stride is short. Arms and trunk are declared. Video: `G:\mocap-studio-downloads\review\2026-11-03\caminhar_masculino_ossos_e_pele.mp4`.
