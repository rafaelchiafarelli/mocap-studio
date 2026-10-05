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
  The `mocap-*` repositories are git submodules of this one
  (`git clone --recurse-submodules`, or `git submodule update --init`).
- Repositories only talk through **contracts** (`mocap-contracts`) and the **session
  folder layout**. None imports code from another.
- Contracts in `.harpia`, **one module per owner** (whoever produces the data defines
  the message; the others only import it).
- Linux on the capture PC. Webcam via FFmpeg with `-c:v copy` (MJPG without re-encoding),
  MKV, wall-clock timestamps. Tablets record internally and are imported via `adb`.
- Sync on the **recorder's host clock**: per-frame timestamps from every camera plus
  software START/END sync markers. No sync hardware. The LED flash (ESP32) is
  **parked** as a future option — revisit only if timestamp sync proves too
  imprecise and a flash gives a measured, clear improvement
  (`mocap-capture/initiatives/future/README.md`).
- Body and hands through FreeMoCap. Face, emotion and gaze are left for phase 2.
- A single PC in the baseline. Future parallelism = one take per worker.
- Work process: the `mocap-workflow` skill (copied into `.claude/skills/` of each repository).
- Software dependencies, pinned versions and where each one lives (submodule /
  Dockerfile / `/mnt/g/mocap-studio-downloads`): `DEPENDENCIES.md`.

## Repositories

| Repository | Role | Tasks |
|---|---|---|
| `mocap-contracts` | `.harpia` messages, generated Python package, session layout | 9 |
| `mocap-capture` | P1 + P2: cameras, recording, sync markers, take report | 13 |
| `mocap-sync-fw` | ESP32 LED flash firmware — **parked**, not scheduled | 3 |
| `mocap-extract` | P3: alignment, calibration, FreeMoCap, **per-camera metrics** | 12 |
| `mocap-adapt` | P4: smoothing, feet on the floor, `MocapTake` | 7 |
| `mocap-blender` | P5: add-on, animated empties, NLA | 5 |
| `mocap-studio` | environment, per-take CLI, **bottleneck study** | 8 |

Each repository has its own `initiatives/` folder and `.claude/` skill. Create
`main` and `dev` before starting the branch chain.

## Order between repositories

Critical path to the camera decision (adapt and blender are **not** on it):

1. `mocap-contracts`: bootstrap → messages-v0 → tag `v0.1.0`.
2. In parallel: `mocap-capture` (all epics) and
   `mocap-studio/bootstrap` (includes the hardware inventory, manual).
3. `mocap-extract`: bootstrap → alignment → calibration → body → quality.
4. `mocap-studio/camera-study`: protocol → baseline session (manual) → analysis → decision (manual).
5. After, or in parallel with step 4: `mocap-adapt` → `mocap-blender` → `mocap-studio/pipeline`.

## Architecture direction (2026-10-04) — supersedes parts of the above

Rafael's direction; how much of the baseline plan it changes is still open.

- **Central recorder PC.** Every camera delivers its frames to one recording
  computer, which stores **one file per camera** per take.
- **7 cameras planned:** 4 body (full body incl. feet, hands, arms, head),
  1 face, 1 per hand (2). The two hand cameras are still in doubt.
- **Preprocessing on the recorder**, before export: clean-up, rescale, crop and
  other clearly simple operations.
- **Heavy lifting on a second PC:** all neural-net work (pose, hands, face).
- The tablet streaming tests (`camera-stream-eval/`, `tablet-stream-test/`)
  measure whether an Android device can deliver live, clock-synced frames to
  the recorder.

**Plan items this conflicts with** (to re-plan with Rafael before implementing them):
- "A single PC in the baseline" → now recorder PC + processing PC.
- "Tablets record internally and are imported via `adb`"
  (`mocap-capture` devices/5) → cameras stream frames to the recorder.
  Internally recorded files also aren't on the host clock, which the
  timestamp sync needs.
- Where preprocessing lives (`mocap-capture` on the recorder, or a new repo)
  and what the recorder → processing PC hand-off looks like (session folder
  copy, network share, stream) — new contract in `mocap-contracts`.
- Face moves from phase 2 into the camera count; the face pipeline itself is
  still phase 2.
- **Live director monitor** (real-time view of every camera, milliseconds of
  delay): planned as `mocap-capture/initiatives/live-monitor/`. It needs the
  streaming camera source from this re-plan.

## Ask Rafael before implementing (open questions)

1. **Harpia's Python output doesn't exist yet** (it's in Harpia's backlog). The
   baseline uses `.harpia → .proto → protoc`. Building the Python output is an
   initiative in the Harpia repository, outside this plan.
2. The exact Harpia command to emit only the `.proto`, and the version to pin.
3. Commit the generated code in `mocap-contracts` (proposal: yes).
4. Sync precision target: how many ms of inter-camera error is acceptable with
   timestamp-only sync (decides whether the parked LED flash ever comes back).
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
