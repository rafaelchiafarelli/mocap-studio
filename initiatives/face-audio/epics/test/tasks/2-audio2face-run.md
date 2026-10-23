## 2. Audio2Face-3D run

- **Type:** run (the session runs the tool set up in `prework/1`; no project code).
- **Depends on:** prework/1, prework/2, test/1
- **Contract:**
  - In: the WAV and emotion label from `test/1`
  - Requires: the same runtime and versions recorded in `prework/1`
  - Delivers: per-frame blendshape keyframes (CSV, frame rate and blendshape
    names in the header) next to the WAV, and the exact command in this file
- **Pre-work:** —
- **Out of scope:** gain, Blender
- **Tests:** —
