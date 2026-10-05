# HANDOFF — mocap pipeline (Claude session in VS Code)

## Context

Video-based motion capture pipeline for filmic animation in Blender, in 5
processes: P1 setup, P2 capture, P3 extraction, P4 adaptation, P5 Blender.
The current initiative is the **baseline**: build it with the hardware Rafael
already has (tablets, a few cameras, one webcam), **without investing in
hardware**, and measure whether the cameras are the bottleneck. Cameras sit
behind an interface (`CameraSource`) so they can be swapped later without
touching the rest.

## Architecture (closed 2026-10-05)

```
cameras ──live──▶ RECORDER PC ──── rsync, file by file ────▶ PROCESSING PC ──▶ Blender
 UVC (USB)        P1 setup, P2 record (one file per   ──▶    watch: verify each file,
 STREAM (Wi-Fi    camera, host clock), report,               start each step when its
 H.264 + capture  preprocess per role (CPU only),            inputs are in → P3 extract
 time in SEI)     hand-off per file ── Harpia ZeroMQ ──▶     (all neural nets) → P4 → P5
                  events: TakeClosed, CameraFileReady
```

Diagrams (draw.io): `docs/diagrams/architecture.drawio` (machines, cameras,
links) and `docs/diagrams/pipeline.drawio` (P1–P5, numbered steps with
▶ In / ◀ Out). Task files trace back to the step numbers there.

- **Repositories.** This one (`mocap-studio`) is the organizer and holds no mocap
  logic. The `mocap-*` repositories are git submodules of this one
  (`git clone --recurse-submodules`, or `git submodule update --init`).
  Repositories only talk through **contracts** (`mocap-contracts`) and the
  **session folder layout**. None imports code from another.
- **Contracts** live in `.harpia`, **one module per owner** (whoever produces the data
  defines the message, and the others only import it). They're generated into Python
  by **Harpia V5's Python target** (and Java target, for the camera app) (a black box: used only through its documented
  interface), and the generated code is **committed** in `mocap-contracts`, so
  consumers need neither Harpia nor Docker.
- **Two PCs.**
  - **Recorder PC** (Linux): every camera delivers its frames live to it. It
    stores **one file per camera** per take, stamps every frame on its own host
    clock, writes the take report, and then **preprocesses** (crop/rescale,
    CPU only, one output frame per input frame) into `prep/`.
  - **Processing PC** (Windows + WSL2, RTX 4080): all neural-net work.
    Parallelism later = one take per worker.
- **Camera sources:** `UVC` (webcam via FFmpeg, `-c:v copy`, MKV, wall-clock
  timestamps) and `STREAM` (tablets/phones running **`mocap-camera-app`**).
  **No internal recording and no `adb` import.**
- **Camera app** (`mocap-camera-app`, Java, started from the
  `camera-stream-eval` app, which stays as the evaluation tool):
  - Video follows **stream protocol v1**: H.264 with each frame's capture time
    in SEI, plus a UDP clock sync before and after the take. It's a binary
    spec with fixtures in `mocap-contracts`, since Harpia can't express it.
  - Video transport: raw Annex-B H.264 over HTTP, with the timestamps only in
    the SEI.
  - **Control, info and stats** are `camera.harpia` messages over **Harpia
    ZeroMQ**.
- **Camera controls: every control a camera offers can be listed and set from
  the recorder**, for both camera types: V4L2 on webcams, Camera2 on tablets.
  - One vocabulary (`camera_control.harpia`: `ControlCapability`,
    `ControlSetting`, `ControlResult`) with native key names.
  - Values are always read back from the device. Clamped or unsupported
    settings are reported, never hidden.
  - Operator CLI: `mocap-capture camera controls|set|save`. Declared controls
    are applied before every take, and every result is recorded in
    `take.json`.
  - The contracts are generated for **Java** as well as Python.
- **Sync** on the **recorder's host clock**: per-frame timestamps from every camera
  plus software START/END sync markers. No sync hardware. The LED flash (ESP32) is
  **parked**, to revisit only if timestamp sync proves too imprecise and a flash
  gives a measured, clear improvement (`mocap-capture/initiatives/future/README.md`).
- **Hand-off: per file, as soon as each one is ready, never a take-level gate.**
  At END the recorder sends `take.json` and the timestamp files, then publishes
  `TakeClosed`, so the processing PC can align right away. As each camera
  finishes preprocessing, its video is copied (rsync over SSH, wired LAN) and
  then announced with `CameraFileReady` (size, sha256, frames). The events are
  **Harpia messages over Harpia's ZeroMQ transport** (`push`/`pull`),
  owned by `mocap-capture` in `capture.harpia`. Each event is also written as a
  JSON sidecar next to its file (`closed.json`, `<file>.ready.json`). The
  session folder stays the record, the event is the nudge, and
  `mocap-extract watch` rescans the sidecars after any restart. Video bytes
  never go through Harpia.
- **7 cameras planned:** 4 body (full body incl. feet, hands, arms, head),
  1 face, 1 per hand (2). The two hand cameras are still in doubt. Face moves
  into the camera count; the face pipeline itself is still phase 2.
- Body and hands through FreeMoCap.
- **Studio setup (P1):** `mocap-capture/initiatives/studio-setup/` (checklist,
  declared and printed ChArUco board declared in `mocap-contracts` as
  `CalibrationBoard`, locked camera controls, guided calibration take, quick check).
- **Live director monitor:** `mocap-capture/initiatives/live-monitor/`, fed by
  the STREAM source.
- **Compliance profile** (Harpia, `mocap-contracts/schema/project.harpia.yaml`):
  class_a, networked, no PHI. No hardened transport on the closed studio LAN.
- Work process: the `mocap-workflow` skill (copied into `.claude/skills/` of each repository).
- Software dependencies, pinned versions and where each one lives (submodule /
  Dockerfile / `/mnt/g/mocap-studio-downloads`): `DEPENDENCIES.md`.

## Repositories

| Repository | Role | Baseline tasks |
|---|---|---|
| `mocap-contracts` | `.harpia` messages, generated Python + Java (Harpia V5), hand-off event transport (ZeroMQ), session layout; **camera-protocol**: stream protocol v1, `camera.harpia` | 11 + 5 |
| `mocap-camera-app` | Android STREAM camera (Java): protocol v1, foreground service, ZeroMQ control, every Camera2 control | 8 |
| `mocap-capture` | Recorder PC: P1 + P2, cameras (UVC + STREAM), recording, sync markers, take report, per-role preprocessing, per-file hand-off + events | 18 (+ studio-setup, live-monitor) |
| `mocap-sync-fw` | ESP32 LED flash firmware — **parked**, not scheduled | 3 |
| `mocap-extract` | Processing PC: P3, intake + `watch` listener, alignment, calibration, FreeMoCap, **per-camera metrics** | 14 |
| `mocap-adapt` | P4: smoothing, feet on the floor, `MocapTake` | 7 |
| `mocap-blender` | P5: add-on, animated empties, NLA | 5 |
| `mocap-studio` | environment, per-take CLI, **bottleneck study** | 8 |

Each repository has its own `initiatives/` folder and `.claude/` skill. Create
`main` and `dev` before starting the branch chain.

## Order between repositories

Critical path to the camera decision (adapt and blender are **not** on it):

1. `mocap-contracts`: bootstrap → messages-v0 → tag `v0.1.0`. **Done 2026-10-05** (`v0.1.0` tagged on `dev`; see its `CHANGELOG.md`). Consumers pin `mocap-contracts[zmq] @ git+…@v0.1.0`.
2. **Can start now.** In parallel: `mocap-capture` (all baseline epics; devices/5 needs stream
   protocol v1 from `mocap-contracts` camera-protocol), `mocap-camera-app`
   (all epics; control needs `mocap-contracts` camera-messages) and
   `mocap-studio/bootstrap` (includes the hardware inventory, manual).
3. `mocap-extract`: bootstrap → alignment → calibration → body → quality.
4. `mocap-studio/camera-study`: protocol → baseline session (manual) → analysis → decision (manual).
5. After, or in parallel with step 4: `mocap-adapt` → `mocap-blender` → `mocap-studio/pipeline`.

## Ask Rafael before implementing (open questions)

1. **Preprocessing output codec** (`mocap-capture` preprocess/2). Proposal: FFV1
   lossless. Recorder "clean-up" beyond crop/rescale is undefined. Each
   operation gets its own task once it's declared.
2. **Are `raw/` videos handed off?** (`mocap-capture` handoff/3). Proposal: no.
   They stay on the recorder as the archive. Timestamps always travel.
3. **Hand-off network and SSH target** (`mocap-capture` handoff/2): wired LAN
   proposed. The processing PC runs WSL2 behind NAT, so how it accepts rsync
   over SSH and the ZeroMQ events (Windows OpenSSH / port forward into WSL) is
   still to be decided.
4. **Per-camera 2D in FreeMoCap** (`mocap-extract` body/1 pre-work): can headless
   FreeMoCap 1.8.2 run 2D per camera, separately from triangulation? If not,
   2D waits for every role (or we patch FreeMoCap).
5. Sync precision target: how many ms of inter-camera error is acceptable with
   timestamp-only sync (decides whether the parked LED flash ever comes back).
6. Python/FreeMoCap and Blender versions (see `DEPENDENCIES.md` for what's pinned).
7. Study decision thresholds (detection rate, reprojection error, bone stability).
8. Initiative-level decisions listed in `studio-setup.md` and `live-monitor.md`.

## Known risks the study must confirm or rule out

- Tablets without manual control: variable FPS and auto exposure (resampling in
  `mocap-extract/alignment` handles FPS; exposure shows up in the metrics).
- 2 MP front camera on the tablets: enough for the body, probably weak for the hands.
- Cameras differ from each other: acceptable, because calibration is per camera.
- Wi-Fi capacity with 7 STREAM cameras: 4 × 20 Mbps measured fine on one 2.4 GHz
  access point (`camera-stream-eval/reference/`). More cameras haven't been measured.

## Phase 2 (outside the baseline — becomes a new initiative when the time comes)

Helmet camera with Face Landmarker; DeepFace with a mood and script layer;
character profile; custom retargeting; Harpia database and control plane (remote
trigger, dashboard); live forwarding of frames to the processing PC; add-on linked to the database; distributed
workers; camera replacement according to the study's decision.

## First action of the session

Read the skill, then `mocap-contracts/initiatives/baseline/` and the two
diagrams in `docs/diagrams/`. Harpia is pinned to V5, which documents everything the plan uses, and only then create the branch
chain for the task `bootstrap/1-package-skeleton`.
