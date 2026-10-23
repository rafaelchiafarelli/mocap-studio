# face-video — mocap-studio

**Status:** Planned — starts only if `face-audio` passes. Epics and tasks are
scoped then.

**Goal:** eyes and brows from video, merged with the Audio2Face mouth, and a
measurement of whether the camera is the bottleneck for the upper face before
anything is bought.

**Scope (current reality):** the MVP already has a **face tablet** (`.3`,
role `face`, `mocap-camera-app` at 1600×1200, 30 fps, streamed to
`mocap-capture`). Record the same speech on it and on the best phone camera,
run **MediaPipe Face Landmarker** (~52 ARKit-style blendshapes, index 0 is
`_neutral`; known to be weak around the eyes) on both, and compare. The mouth,
jaw and tongue still come from Audio2Face; video owns only eyes and brows.

**Out of scope:** body, calibration, new hardware.

**Initiative gate:** Rafael judges eyes/brows from the tablet against the
phone, and decides whether the face camera needs an upgrade.

**Open for Rafael:** fixed or worn face camera (HANDOFF open question 8).

## Tools to look at

| Tool | Role | Note |
|---|---|---|
| MediaPipe Face Landmarker | video → blendshapes | already in the stack through FreeMoCap |
| [VIPER Blender Facial MoCap](https://github.com/Daniel-W-Blender-Python/VIPER-Blender-Facial-Motion-Capture) | MediaPipe → Rigify face, real time | license to check |
| [Phiz](https://github.com/SpookyCorgi/phiz) | in-browser face capture | judge MediaPipe quality with no install; license to check |
| [Mocapy](https://github.com/justinjohn0306/Mocapy) | video → BVH + per-frame `.morphs.json` | close to the per-frame face idea; license to check |
| [BlendArMocap](https://github.com/cgtinker/BlendArMocap) | face/hands/body via MediaPipe, imports FreeMoCap | not actively maintained; license to check |
| [blender_livelinkface](https://github.com/JRicardoSan/blender_livelinkface) | Live Link Face → Blender | only with a TrueDepth iPhone/iPad, which we don't have |
| ~~[EMOCA](https://github.com/radekd91/emoca)~~ | emotion-focused 3D face | **excluded:** Max Planck non-commercial license |
