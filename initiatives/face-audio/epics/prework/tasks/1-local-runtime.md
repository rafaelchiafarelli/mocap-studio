## 1. Local runtime for Audio2Face-3D

- **Type:** research + measurement (the session installs and measures; no project code).
- **Depends on:** —
- **Contract:**
  - In: the processing PC (RTX 4080 16 GB, WSL2, Docker with `--gpus all`; `DEPENDENCIES.md`)
  - Requires: the local-AI rule in the `mocap-workflow` skill: a model runs
    locally only if it performs well here, measured
  - Delivers: a short note in this file: how Audio2Face-3D runs here (build or
    container, versions, where it lives under `/mnt/g/mocap-studio-downloads/`),
    time per second of audio, VRAM peak, and a pass/fail against "a 10 s clip in
    well under a minute"
- **Decision for Rafael before installing:** the SDK is C++, and the stack is
  Python. Options: (a) build the SDK once and treat it as an external app
  called from Python, like the Blender binary (we write no C++); (b) the
  samples' route, if it needs a container service, provided its license
  passes `prework/2`. Any other language or runtime needs his go-ahead.
- **Pre-work:** none
- **Out of scope:** quality judgement (that's `test/4`)
- **Tests:** —
