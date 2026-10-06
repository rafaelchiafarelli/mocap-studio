# Dependencies — what to download, and where it lives

**Status: agreed baseline list (2026-10-04).** Nothing here is installed or
downloaded yet. Versions marked **?** are still to be pinned.

## The three rules

| Kind | Where it lives | How the version is locked |
|---|---|---|
| **A. Software we compile ourselves** | Git submodule of the repo that builds it | Submodule pinned to a tag/commit |
| **B. Libraries our code imports** | The repo's `Dockerfile` | Base image by digest, apt packages by version, Python by lockfile with hashes |
| **C. Apps we run** (Blender, …) | `/mnt/g/mocap-studio-downloads/apps/` | Version in the folder name + `SHA256SUMS` |

Raw takes and other large data also go on `/mnt/g/mocap-studio-downloads/`
(layout at the end).

---

## A. Compiled ourselves → submodules

| Software | Used for | Submodule of | Pin | Notes |
|---|---|---|---|---|
| **Harpia** (`rafaelchiafarelli/harpia`) | `.harpia` → Python package and Java Gradle project (Harpia's Python and Java targets), including the ZeroMQ transport for the hand-off events and the camera control channel (pyzmq / JeroMQ on Android); used as a black box | `mocap-contracts` (`third_party/harpia`) | **`V5`** (2026-10-05: V4's code + ZeroMQ documented for Python and Java, USAGE §7.6–7.9, §11) | Used only through its documented interface. The pin moves V4 → V5 in `mocap-contracts` messages-v0/7 (same generated code). |

Nothing else is planned to be compiled from source. FFmpeg, OpenCV and
MediaPipe all come as prebuilt packages (B). **We'll probably have to patch
FreeMoCap ourselves.** When that happens, it moves here as a fork submodule of
`mocap-extract`, pinned to our patched commit.

---

## B. Libraries → Dockerfiles

One Dockerfile per Python repo, so each one keeps its own isolated environment.
This replaces the "separate venvs" in `initiatives/baseline/epics/bootstrap/tasks/1-repos-yaml-and-bootstrap.md`.

**Locking mechanism (proposal):** `requirements.in` (direct deps) →
`uv pip compile --generate-hashes` → `requirements.lock`, committed. The Dockerfile
installs only from the lockfile. Base images are pinned by `@sha256:` digest.

### Shared base

| Item | Version | Why |
|---|---|---|
| Python | **3.12** | FreeMoCap 1.8.2 needs `>=3.10,<3.13`; skellytracker `<3.13`. Use the same minor everywhere. |
| Base image | `ubuntu:24.04@sha256:…` (digest pinned when the first Dockerfile is written) | System Python is 3.12. Same base for every image, `mocap-extract` included (the CUDA runtime comes inside the torch wheels). |
| FFmpeg + ffprobe | apt, version from the base image | Recording (`-c:v copy`), per-frame timestamps, resampling |
| `v4l-utils` (`v4l2-ctl`) | apt | Only for UVC webcams, **parked** (`mocap-capture/initiatives/future/uvc/`): not needed now |
| `pytest` | lockfile | Test suite in every Python repo |

### Per repo

| Repo | Direct dependencies | Version constraints we already know |
|---|---|---|
| `mocap-contracts` | the generated Python package's own runtime deps (protobuf among them), `hatchling`. Generation needs only Harpia's Docker image, no `protoc` of ours. | **protobuf 4.25.x**: MediaPipe 0.10.14 needs `protobuf>=4.25.3,<5`. `mocap-extract` imports both, so the range the generated package declares must include 4.25.x (checked in bootstrap/2). Released: `v0.1.0` (baseline contracts), `v0.2.0` (camera protocol), `v0.2.1` (Harpia submodule over HTTPS, the one to pin). Its slow tests (`make test-slow`) use `gradle:8.7-jdk17`, pinned by digest. |
| `mocap-capture` | `mocap_contracts`, `pyyaml` + `pydantic` 2 (config validation), `typer`, `pyudev` | Runs on the recorder PC. `rsync` + `openssh-client` (apt) for the hand-off; the container needs `--device /dev/video*`. |
| `mocap-extract` | `mocap_contracts` (incl. its ZeroMQ receiver), `freemocap==1.8.2`, `opencv-contrib-python==4.8.*` | FreeMoCap pins `skellytracker[all]==2025.10.1024`, which pulls in `mediapipe==0.10.14`, `torch==2.8.*`, `torchvision==0.23.*`, `ultralytics~=8.3.132` and `numpy<2`. |
| `mocap-adapt` | `mocap_contracts`, `numpy<2`, `scipy` (Butterworth), One Euro filter (small, can be vendored) | Keep `numpy<2` so it matches extract. |
| `mocap-studio` | stdlib + `pyyaml` (CLI and study report) | `shellcheck` (apt) for `bootstrap.sh` |
| Streaming tests | already have their own Dockerfiles (JDK 17, Android SDK 34, Gradle 8.7, adb) | Base image and SDK packages aren't pinned by digest yet. |
| `mocap-camera-app` | Android SDK 34, JDK 17, Gradle (as `camera-stream-eval`); `mocap-contracts` generated Java (protobuf, gRPC, JeroMQ via Harpia's Java target) | Base image pinned by digest from the start (bootstrap/1). **`minSdk 24`** (Harpia's verified Android configuration). |

**Decisions for B**
- **FreeMoCap 1.8.2 for the baseline** (decided).
  **Watch item:** check FreeMoCap 2.0 (`v2.0.0-alpha.x`: SkellyCam/SkellyTracker
  rewrite, Blender 5 support) for a stable release whenever we touch
  `mocap-extract`. We'll probably patch FreeMoCap, so a newer line on the horizon
  matters: a patch may be easier to make, or already made, on 2.0.
- **Processing PC GPU: NVIDIA GeForce RTX 4080, 16 GB VRAM** (Ada, `sm_89`), Windows
  driver 591.86, which supports up to CUDA 13.1.
  **`mocap-extract` uses the CUDA 12.8 build of torch:** `torch==2.8.*+cu128` and
  `torchvision==0.23.*+cu128` from `https://download.pytorch.org/whl/cu128`,
  on the shared `ubuntu:24.04` base. The torch wheels bundle the CUDA runtime, so
  no `nvidia/cuda` base image is needed. The only host requirement is a Windows
  NVIDIA driver that supports CUDA ≥ 12.8 (driver ≥ 570), and 591.86 does.
  Don't drop the driver below that.
- The processing PC runs **Windows**, so the containers run in Docker Desktop on
  WSL2 with GPU passthrough (NVIDIA Windows driver + `--gpus all`). No Linux CUDA
  driver inside WSL.
- FreeMoCap pulls in PySide6 (GUI). We run it headless, so we only accept the size cost (no display needed).

---

## C. Apps → `/mnt/g/mocap-studio-downloads/apps/`

| App | Version | Files to download | Runs on |
|---|---|---|---|
| **Blender** | **5.2.2 LTS** (supported until July 2028) | `blender-5.2.2-windows-x64.zip` (portable, no installer) | Windows PC (the best machine, same as the processing PC) |
| **FreeMoCap Blender add-on** | `v2026.04.1041` | release `.zip` | Installed into Blender |
| Android platform-tools (`adb`) | **?** (pin a release zip) | `platform-tools_r<ver>-<os>.zip` | Only needed outside Docker, e.g. Windows side |
| `usbipd-win` | **?** | `.msi` | Windows host, to attach USB devices to WSL2. Only UVC webcams (**parked**) needed it: not needed now |
| Windows Python | **?** (3.12.x) | python.org installer | Windows host. The stream-eval scripts measure from Windows because WSL2 NAT stalls TCP. |
| Docker Engine / Desktop | **?** | — | Every PC. It runs B, so it can't live inside B. |

The add-on and the `mocap-contracts` wheel have to work with **Blender's bundled
Python**, which is not ours. Check which Python version Blender 5.2 bundles before
the `mocap-blender` bootstrap task.

**Notes for C**
- Blender runs on **Windows** for now. The Linux archive gets added only if that changes.
- Is Blender 5.2 OK with the FreeMoCap add-on? It claims Blender 5 support since
  `v2026.04.1041`. To verify in `mocap-blender` bootstrap.
- `/mnt/g/` is the Windows `G:` drive, so the Windows apps run straight from
  `G:\mocap-studio-downloads\apps\`.

---

## D. Models and data files (not in the three rules — proposal)

| Item | Needed by | Proposal |
|---|---|---|
| MediaPipe pose/hand models | FreeMoCap (baseline) | Bundled inside the `mediapipe` wheel, so they're locked by B. Nothing to download. |
| YOLO weights (if skellytracker uses them) | FreeMoCap | `downloads/models/` with SHA256, mounted read-only into the container |
| `face_landmarker.task`, DeepFace weights | Phase 2 (face) | Same as YOLO. Not downloaded now. |
| ChArUco calibration board | Calibration | PDF generated from FreeMoCap's board parameters, kept in `downloads/calibration/` |

---

## Proposed layout of `/mnt/g/mocap-studio-downloads`

```
/mnt/g/mocap-studio-downloads/
├── apps/
│   ├── blender/5.2.2/                     blender-5.2.2-linux-x64.tar.xz …
│   ├── freemocap-blender-addon/v2026.04.1041/
│   └── …/<version>/
├── models/<name>/<version>/               weights + SHA256
├── calibration/                           board PDFs
├── sessions/<session>/<take>/             raw takes (one file per camera)
├── SHA256SUMS                             one line per downloaded file
└── MANIFEST.md                            what, version, source URL, date — mirrors section C/D
```

Docker volumes mount `models/` (read-only) and `sessions/` into the containers.

**Takes are recorded to the recorder PC's local fast SSD first and copied here
afterwards** (decided). This drive is the archive, not the recording target. The
recorder PC (fast SSD, 2 CPUs) is currently commissioned to another task. How
and when the copy happens is part of the recorder → processing PC hand-off
contract, still to be planned in `mocap-contracts`.
