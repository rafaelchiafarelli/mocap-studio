## 6. Body drive

- **Type:** code.
- **Depends on:** `drive/2`
- **Contract:**
  - In: The fixture's body points
  - Requires: —
  - Delivers: `blender/body_drive.py`; review video
- **Pre-work:** —
- **Out of scope:** —
- **Tests:** —

## Result (2026-11-03)

Works on the fixture without manual steps: the person turns, reaches and bends. Hands, fingers and spine bending aren't driven. Jitter passes straight through; no filter was added, so the input can still be judged. Video: `G:\mocap-studio-downloads\review\2026-11-03\captura_corpo_no_modelo.mp4`. It found one fault that the walk hid: skin vertices stayed behind on bending, fixed in `assemble.py`.
