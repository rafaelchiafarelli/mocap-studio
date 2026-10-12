# HANDOFF — mocap pipeline (Claude session in VS Code)

## Context

Video-based motion capture pipeline for filmic animation in Blender, in 5
processes: P1 setup, P2 capture, P3 extraction, P4 adaptation, P5 Blender.
The current initiative is the **baseline**: build it with the hardware Rafael
already has (tablets running the camera app; **no webcam**, decided 2026-10-06), **without investing in
hardware**, and measure whether the cameras are the bottleneck. Cameras sit
behind an interface (`CameraSource`, a registry per source kind) so other
image sources can be added later without touching the rest.

## Architecture (closed 2026-10-05)

```
cameras ──live──▶ RECORDER PC ──── rsync, file by file ────▶ PROCESSING PC ──▶ Blender
 STREAM (Wi-Fi    P1 setup, P2 record (one file per   ──▶    watch: verify each file,
 tablets,         camera, host clock), report,               start each step when its
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
- **Camera sources:** `STREAM` (tablets/phones running **`mocap-camera-app`**).
  USB webcams (`UVC`) are **parked**: no webcam will be used, and their tasks
  wait in `mocap-capture/initiatives/future/uvc/`. `CameraConfig` keeps the
  `UVC` kind; a take that declares one fails before START.
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
  the recorder**: Camera2 on the tablets (V4L2 for webcams is parked with UVC).
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

## Film production side (added 2026-10-11)

Mocap Studio is not only the capture pipeline: it takes a film **from script
to delivery**. The capture pipeline (P1–P5) is the production stage for
performances. Around it:

```
script ─▶ mocap-preprod agents ─▶ creative brief + worklist ─▶ specialist specs ─▶ production
          (readiness analyst,      (creator decides,           (story, visual,      (capture P1–P5,
           decision facilitator)    agents propose)             character, perf,     audio, Blender)
                                                                props, sound, cam)
                    ▲                                                                    │
                    └──────────── mocap-dashboard: state, work packages, agent runs ─────┘
```

- **Project, workhorse, film** (vocabulary, 2026-10-12). The **project** is
  the code and agents (these repositories). The **workhorse** is the workflow
  that makes a film. A **film** lives in its own **film root** (script,
  `analysis/` brief, worklist, memos, assets). A session works on the project
  or on a film, never both; full rules in the `mocap-workflow` skill. The pilot film is **TicTac** at `/mnt/g/TicTac` (not versioned,
  Rafael's choice). Tool repositories never name it; what it taught lives in
  `mocap-dashboard/initiatives/workflow-dashboard/workflow-dashboard.md`
  ("Lessons from the pilot film").
- **Stack.** Python 3.12 everywhere. Exceptions: the Android camera app
  (Java) and the dashboard's React UI. Applications exchange messages through
  Harpia contracts in `mocap-contracts`.
- **Agents** (`mocap-preprod/.claude/agents/`, canonical; `.github/agents/`
  are Copilot adapters generated by `scripts/sync_agents.py`). They run as the
  main session because they interview the creator:
  `claude --agent <name> --add-dir <film-root>` from `mocap-preprod`.
  Agents propose, and the creator approves; question and option counts are bounded.
- **Dashboard** (`mocap-dashboard`). FastAPI backend + React UI, loopback
  only. The first slice is a read-only Markdown inventory of a film root.
  Its plan: `initiatives/workflow-dashboard/` (workflow-model → dashboard →
  automation).
- **Audio** (`mocap-audio`). Survey of open-source generators by need, with
  weights licenses: `docs/local-audio-stack.md`. Each generator gets its own
  environment, and nothing generated is approved until the film's creator
  says so.

## Repositories

| Repository | Role | Baseline tasks |
|---|---|---|
| `mocap-contracts` | `.harpia` messages, generated Python + Java (Harpia V5), hand-off event transport (ZeroMQ), session layout; **camera-protocol**: stream protocol v1, `camera.harpia` | 11 + 5 |
| `mocap-camera-app` | Android STREAM camera (Java): protocol v1, foreground service, ZeroMQ control, every Camera2 control | 8 |
| `mocap-capture` | Recorder PC: P1 + P2, STREAM cameras, recording, sync markers, take report, per-role preprocessing, per-file hand-off + events | 12 (+ studio-setup, live-monitor); UVC parked |
| `mocap-sync-fw` | ESP32 LED flash firmware — **parked**, not scheduled | 3 |
| `mocap-extract` | Processing PC: P3, intake + `watch` listener, alignment, calibration, FreeMoCap, **per-camera metrics** | 14 |
| `mocap-adapt` | P4: smoothing, feet on the floor, `MocapTake` | 7 |
| `mocap-blender` | P5: add-on, animated empties, NLA | 5 |
| `mocap-preprod` | pre-production agents (readiness, decisions, 7 specialists) | none open |
| `mocap-audio` | audio generation survey + shared utilities | none open |
| `mocap-dashboard` | film workflow dashboard (Python + React) | `workflow-dashboard` initiative (planning; first slice ported to Python) |
| `mocap-studio` | environment, per-take CLI, **bottleneck study** | 8 |

Each repository has its own `initiatives/` folder and `.claude/` skill. Create
`main` and `dev` before starting the branch chain.

## Order between repositories

Critical path to the camera decision (adapt and blender are **not** on it):

1. `mocap-contracts`: bootstrap → messages-v0 → tag `v0.1.0`. **Done 2026-10-05** (`v0.1.0` tagged on `dev`; see its `CHANGELOG.md`). Consumers pin `mocap-contracts[zmq] @ git+…@v0.2.1`. The `camera-protocol` initiative is **done too: `v0.2.0`** (stream protocol v1 spec + reference reader + fixtures, `camera.harpia`, Java generation, the camera ZeroMQ channel). mocap-capture's STREAM source and the camera app pin `v0.2.0`. **Pin `v0.2.1`** (same contracts, Harpia submodule over HTTPS so installs work without SSH keys).
2. **Can start now.** In parallel: `mocap-capture` (**every baseline epic done 2026-10-06**, on its `baseline` branch: STREAM source, `mocap-capture take` → take.json + report.json → per-file hand-off with Harpia events; `mocap-capture send` resends. Verified locally against `mocap-extract`'s intake. **Initiative gate not yet run**: it needs ≥2 tablets running the camera app and the processing PC reachable. For that, `mocap-extract watch` must bind the two ports the recorder's `config.yaml` `handoff:` declares, `take_closed_port` and `file_ready_port` (one PUSH/PULL socket per event type); UVC parked), `mocap-camera-app`
   (all epics; `minSdk 24`, contracts `v0.2.1`) and
   `mocap-studio/bootstrap` (includes the hardware inventory, manual).
3. `mocap-extract`: bootstrap → alignment → calibration → body → quality. **bootstrap and alignment done 2026-10-06** (30 fps, nearest frame, warns past 33.3 ms); calibration/1 waits for the printed board and a real calibration take.
4. `mocap-studio/camera-study`: protocol → baseline session (manual) → analysis → decision (manual).
5. After, or in parallel with step 4: `mocap-adapt` → `mocap-blender` → `mocap-studio/pipeline`.

## Ask Rafael before implementing (open questions)

1. ~~**Preprocessing output codec**~~ **Answered 2026-10-06: FFV1 lossless**
   (`mocap-capture` preprocess/2). Recorder "clean-up" beyond crop/rescale is
   still undefined; each operation gets its own task once it's declared.
2. ~~**Are `raw/` videos handed off?**~~ **Answered 2026-10-06: no.** They stay
   on the recorder as the archive. Timestamps always travel.
3. ~~**Hand-off network and SSH target**~~ **Answered 2026-10-06: the wired
   LAN, WSL2 in mirrored networking mode** on the processing PC (`sshd` inside
   WSL; rsync and the ZeroMQ events reach WSL on the Windows LAN IP, no port
   forward; Windows 11 22H2+). Still manual: the recorder's SSH key on the
   processing PC.
4. ~~**Per-camera 2D in FreeMoCap**~~ **Answered 2026-10-06: yes, without
   patching.** 2D run one camera at a time and stacked gives 2D and 3D identical
   to the stock run on FreeMoCap's test recording (details in `mocap-extract`
   body/1). Only triangulation waits for every role.
5. ~~**Sync precision target**~~ **Answered 2026-10-12: one shutter (exposure)
   time.** Beyond that, rethink the timestamp strategy. Task:
   `mocap-extract` alignment/3.
6. ~~**Versions**~~ **Confirmed 2026-10-12:** Python 3.12, FreeMoCap 1.8.2,
   Blender 5.2.2 LTS. Upgrades get a manifest + checker: `mocap-studio`
   bootstrap/3.
7. ~~**Study thresholds**~~ **Answered 2026-10-12** (`camera-study/1`): body
   detected in ≥ 90 % of frames **from GO** (new ready-set-go step,
   `mocap-capture` live-monitor/ready-check); calibration good to 1 cm; sync
   within one exposure; residual bone jitter 1–3 mm after filtering (research
   task `mocap-adapt` filtering/0).
8. **Studio and monitor:** mostly answered 2026-10-12 (see `studio-setup.md`
   and `live-monitor.md`): 3 × 3 × 3 m cube (config only), one body camera per
   side, recalibration per location; board **FreeMoCap 5x3, 55 mm squares, A4** (changed from A0, 2026-10-12)
   (`/mnt/g/mocap-studio-downloads/calibration/charuco-5x3-55mm-A4.pdf`);
   director on the recorder's screen; no overlays for now. **Still open:**
   monitor layout (options being compared), latency target confirmation,
   where the quick check runs, and whether the face camera is fixed or worn
   (hand cameras TBD).

### Film side (open as of 2026-10-11)

9. ~~**Who builds assets**~~ **Answered 2026-10-12:** Rafael's team, procedural
   tools first (rigs, faces, eyes, …), with AI adjusting; specialised asset
   agents drive the procedural tools rather than making assets themselves
   (`mocap-blender/methodology_study.md`). The agent roster is defined when
   TicTac enters production.
10. ~~**Dashboard runtime**~~ **Answered 2026-10-12: Docker** (`make up` in
    `mocap-dashboard`: loopback only, film folders mounted at the same path).
    The Claude Code CLI is **inside the image** (pinned, login mounted,
    `--pid=host` so `claude agents --json` sees host sessions).
11. ~~**First Harpia messages for the film side**~~ **Delegated 2026-10-12:**
    Claude defines them as `mocap-contracts` tasks when a real need appears;
    Rafael steps in only if problems show up.
12. ~~**First-try example project in `mocap-blender`**~~ **Answered
    2026-10-12: removed.** Its general findings are kept in
    `mocap-blender/methodology_study.md`.
13. ~~**Local AI compute vs. generated assets**~~ **Answered 2026-10-12:** code,
    model/asset making and script analysis use the hosted agent only; local
    audio generation is allowed. `mocap-audio` does recording, editing,
    analysis and generation. **Licenses:** only open/free licenses that allow
    commercial use, never NC or capped community licenses, not even for tests
    (rule in the `mocap-workflow` skill).
14. **Asset methodology questions** (8, in `mocap-blender/methodology_study.md`):
    ~~commercial film or not~~ (answered: treat every film as commercial), storyboard style, where the film toolbox lives,
    versioning of built outputs, recipe/shot file formats, target skeleton,
    agent editing rules, preferred add-ons. They shape the production stage.
15. **Splitting into parallel sessions.** Deferred on purpose until the work
    ahead is known well enough to scope.

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
