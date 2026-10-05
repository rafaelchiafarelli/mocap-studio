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
cameras ──live──▶ RECORDER PC ───────────────────────────▶ PROCESSING PC ──▶ Blender
 UVC (USB)        P1 setup, P2 record (one file per        P3 extract (all neural
 STREAM (Wi-Fi    camera, host clock), report,             nets: body, hands,
 H.264 + capture  preprocess (crop/rescale, CPU only),     later face) → P4 adapt
 time in SEI)     manifest ── rsync of the take folder ──▶ intake check → P5
```

- **Repositories.** This one (`mocap-studio`) is the organizer and holds no mocap
  logic. The `mocap-*` repositories are git submodules of this one
  (`git clone --recurse-submodules`, or `git submodule update --init`).
  Repositories only talk through **contracts** (`mocap-contracts`) and the
  **session folder layout**. None imports code from another.
- **Contracts** live in `.harpia`, **one module per owner** (whoever produces the data
  defines the message, and the others only import it). They're generated into Python
  by **Harpia V3's Python target** (a black box: used only through its documented
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
  timestamps) and `STREAM` (tablets/phones running the camera app: H.264 over
  Wi-Fi with each frame's capture time in SEI, mapped to the host clock by a
  clock sync before and after the take, as measured in `camera-stream-eval`).
  **No internal recording and no `adb` import.**
- **Sync** on the **recorder's host clock**: per-frame timestamps from every camera
  plus software START/END sync markers. No sync hardware. The LED flash (ESP32) is
  **parked**, to revisit only if timestamp sync proves too imprecise and a flash
  gives a measured, clear improvement (`mocap-capture/initiatives/future/README.md`).
- **Hand-off:** once a take is finished, the recorder writes `manifest.json`
  (sha256 of every file handed off) **last**, then copies the take folder to
  the same `layout` path on the processing PC with `rsync`, the manifest last
  again. `mocap-extract` refuses any take that doesn't match its manifest.
- **7 cameras planned:** 4 body (full body incl. feet, hands, arms, head),
  1 face, 1 per hand (2). The two hand cameras are still in doubt. Face moves
  into the camera count; the face pipeline itself is still phase 2.
- Body and hands through FreeMoCap.
- **Studio setup (P1):** `mocap-capture/initiatives/studio-setup/` (checklist,
  declared and printed ChArUco board declared in `mocap-contracts` as
  `CalibrationBoard`, locked camera controls, guided calibration take, quick check).
- **Live director monitor:** `mocap-capture/initiatives/live-monitor/`, fed by
  the STREAM source.
- Work process: the `mocap-workflow` skill (copied into `.claude/skills/` of each repository).
- Software dependencies, pinned versions and where each one lives (submodule /
  Dockerfile / `/mnt/g/mocap-studio-downloads`): `DEPENDENCIES.md`.

## Repositories

| Repository | Role | Baseline tasks |
|---|---|---|
| `mocap-contracts` | `.harpia` messages, generated Python package (Harpia V3), session layout | 9 |
| `mocap-capture` | Recorder PC: P1 + P2, cameras (UVC + STREAM), recording, sync markers, take report, preprocessing, hand-off | 17 |
| `mocap-sync-fw` | ESP32 LED flash firmware — **parked**, not scheduled | 3 |
| `mocap-extract` | Processing PC: P3, take intake, alignment, calibration, FreeMoCap, **per-camera metrics** | 13 |
| `mocap-adapt` | P4: smoothing, feet on the floor, `MocapTake` | 7 |
| `mocap-blender` | P5: add-on, animated empties, NLA | 5 |
| `mocap-studio` | environment, per-take CLI, **bottleneck study** | 8 |

Each repository has its own `initiatives/` folder and `.claude/` skill. Create
`main` and `dev` before starting the branch chain.

## Order between repositories

Critical path to the camera decision (adapt and blender are **not** on it):

1. `mocap-contracts`: bootstrap → messages-v0 → tag `v0.1.0`.
2. In parallel: `mocap-capture` (all baseline epics; devices/5 needs the camera
   app, see open question 1) and `mocap-studio/bootstrap` (includes the hardware
   inventory, manual).
3. `mocap-extract`: bootstrap → alignment → calibration → body → quality.
4. `mocap-studio/camera-study`: protocol → baseline session (manual) → analysis → decision (manual).
5. After, or in parallel with step 4: `mocap-adapt` → `mocap-blender` → `mocap-studio/pipeline`.

## Ask Rafael before implementing (open questions)

1. **Production camera app** for STREAM devices. `camera-stream-eval`'s app is a
   decision tool, not the product. Which repo does it live in? Proposal: a new
   `mocap-camera-app` submodule, starting from the eval app, with its stream
   and `/control` protocol written down as a contract. This blocks `mocap-capture`
   devices/5, `studio-setup` cameras/3 and `live-monitor` preview-tap/3.
2. **Harpia's Python target isn't in V3's documented interface** (`USAGE.md`
   covers only the C++ project). It needs documenting on Harpia's side before
   `mocap-contracts` bootstrap/2 starts.
3. **Preprocessing output codec** (`mocap-capture` preprocess/2). Proposal: FFV1
   lossless. Recorder "clean-up" beyond crop/rescale is undefined. Each
   operation gets its own task once it's declared.
4. **Is `raw/` handed off?** (`mocap-capture` handoff/1). Proposal: no. It stays
   on the recorder as the archive, and only `prep/` + metadata travel.
5. **Hand-off network and SSH target** (`mocap-capture` handoff/2): wired LAN
   proposed. The processing PC runs WSL2 behind NAT, so how it accepts rsync over
   SSH (Windows OpenSSH vs. a port forward into WSL) is still to be decided.
6. Sync precision target: how many ms of inter-camera error is acceptable with
   timestamp-only sync (decides whether the parked LED flash ever comes back).
7. Python/FreeMoCap and Blender versions (see `DEPENDENCIES.md` for what's pinned).
8. Study decision thresholds (detection rate, reprojection error, bone stability).
9. Initiative-level decisions listed in `studio-setup.md` and `live-monitor.md`.

## Known risks the study must confirm or rule out

- Tablets without manual control: variable FPS and auto exposure (resampling in
  `mocap-extract/alignment` handles FPS; exposure shows up in the metrics).
- 2 MP front camera on the tablets: enough for the body, probably weak for the hands.
- Cameras differ from each other: acceptable, because calibration is per camera.
- Wi-Fi capacity with 7 STREAM cameras: 4 × 20 Mbps measured fine on one 2.4 GHz
  access point (`camera-stream-eval/reference/`). More cameras haven't been measured.

## Phase 2 (outside the baseline — becomes a new initiative when the time comes)

Helmet camera with Face Landmarker; DeepFace with a mood and script layer;
character profile; custom retargeting; Harpia database + ZMQ; live streaming from
the recorder to the processing PC; add-on linked to the database; distributed
workers; camera replacement according to the study's decision.

## First action of the session

Read the skill, then `mocap-contracts/initiatives/baseline/`. Check open
question 2 (Harpia's Python target documented), and only then create the branch
chain for the task `bootstrap/1-package-skeleton`.
