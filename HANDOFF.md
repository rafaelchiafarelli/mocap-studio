# HANDOFF — mocap pipeline (Claude session in VS Code)

## Context

Video-based motion capture pipeline for filmic animation in Blender, in 5
processes: P1 setup, P2 capture, P3 extraction, P4 adaptation, P5 Blender.
The current initiative is the **baseline**: build it with the hardware Rafael
already has (tablets, a few cameras, one webcam), **without investing in
hardware**, and measure whether the cameras are the bottleneck. Cameras sit
behind an interface (`CameraSource`) so they can be swapped later without
touching the rest.

## Decisions already made

- Multiple repositories; this one (`mocap-studio`) is the organizer and holds no mocap logic.
- Repositories only talk through **contracts** (`mocap-contracts`) and the **session
  folder layout**. None imports code from another.
- Contracts in `.harpia`, **one module per owner** (whoever produces the data defines
  the message; the others only import it).
- Linux on the capture PC. Webcam via FFmpeg with `-c:v copy` (MJPG without re-encoding),
  MKV, wall-clock timestamps. Tablets record internally and are imported via `adb`.
- Sync via an **LED flash** at the start and end of each take (ESP32; manual fallback).
- Body and hands through FreeMoCap. Face, emotion and gaze are left for phase 2.
- A single PC in the baseline. Future parallelism = one take per worker.
- Work process: the `mocap-workflow` skill (copied into `.claude/skills/` of each repository).

## Repositories

| Repository | Role | Tasks |
|---|---|---|
| `mocap-contracts` | `.harpia` messages, generated Python package, session layout | 9 |
| `mocap-capture` | P1 + P2: cameras, recording, flash, take report | 14 |
| `mocap-sync-fw` | ESP32 flash firmware | 3 |
| `mocap-extract` | P3: alignment, calibration, FreeMoCap, **per-camera metrics** | 12 |
| `mocap-adapt` | P4: smoothing, feet on the floor, `MocapTake` | 7 |
| `mocap-blender` | P5: add-on, animated empties, NLA | 5 |
| `mocap-studio` | environment, per-take CLI, **bottleneck study** | 8 |

Each repository has its own `initiatives/` folder and `.claude/` skill. Create
`main` and `dev` before starting the branch chain.

## Order between repositories

Critical path to the camera decision (adapt and blender are **not** on it):

1. `mocap-contracts`: bootstrap → messages-v0 → tag `v0.1.0`.
2. In parallel: `mocap-capture` (all epics), `mocap-sync-fw` and
   `mocap-studio/bootstrap` (includes the hardware inventory, manual).
3. `mocap-extract`: bootstrap → alignment → calibration → body → quality.
4. `mocap-studio/camera-study`: protocol → baseline session (manual) → analysis → decision (manual).
5. After, or in parallel with step 4: `mocap-adapt` → `mocap-blender` → `mocap-studio/pipeline`.

## Ask Rafael before implementing (open questions)

1. **Harpia's Python output doesn't exist yet** (it's in Harpia's backlog). The
   baseline uses `.harpia → .proto → protoc`. Building the Python output is an
   initiative in the Harpia repository, outside this plan.
2. The exact Harpia command to emit only the `.proto`, and the version to pin.
3. Commit the generated code in `mocap-contracts` (proposal: yes).
4. Firmware: PlatformIO + Arduino or ESP-IDF; ESP32 board model; pin, LED and MOSFET.
5. Folder where the tablets save video; Python/FreeMoCap and Blender versions.
6. Study decision thresholds (detection rate, reprojection error, bone stability).

## Known risks the study must confirm or rule out

- Tablets without manual control: variable FPS and auto exposure (resampling in
  `mocap-extract/alignment` handles FPS; exposure shows up in the metrics).
- 2 MP front camera on the tablets: enough for the body, probably weak for the hands.
- Cameras differ from each other: acceptable, because calibration is per camera.

## Phase 2 (outside the baseline — becomes a new initiative when the time comes)

Helmet camera with Face Landmarker; DeepFace with a mood and script layer;
character profile; custom retargeting; Harpia database + ZMQ; add-on linked to
the database; distributed workers; camera replacement according to the study's decision.

## First action of the session

Read the skill, then `mocap-contracts/initiatives/baseline/`, go over points 1–3
above with Rafael, and only then create the branch chain for the task
`bootstrap/1-package-skeleton`.
