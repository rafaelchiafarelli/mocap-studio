# face-audio — mocap-studio

**Goal:** see whether mouth, jaw and tongue generated from recorded speech look
convincing on a caricatured face. This is the core idea of the project (an
expressive, exaggerated face), tested before anything else is built for it.

**Why first** (Rafael, 2026-10-23): the P1–P5 plan kept growing with every new
tool. The face is validated with the smallest possible test: no cameras, no
body, no new hardware, no integration. The face initiatives only grow by
automating pain found in these tests.

**Scope:** ~10 s of speech → NVIDIA **Audio2Face-3D** (with an emotion label)
→ per-frame blendshapes → hand-set per-blendshape gain (e.g. smile ×1.8,
brows ×2) → shape keys of an ARKit face in Blender → a short render Rafael
judges.

**Out of scope:** cameras and video (`face-video`), declared character
profiles (`face-character`), the MVP character and shot (`face-in-shot`),
`.harpia` messages, the dashboard.

**Initiative gate:** Rafael's verdict on the render (`test/4`). If it is not
convincing here, no pipeline will fix it; the other face initiatives start
only on a pass.

## Relation to the MVP

Runs alongside `MVP-plan.md`, which is not paused: it needs no cameras or
capture code, so it doesn't compete with the MVP's calibration work. It is
the one exception to the MVP rule "no new initiatives".

## Technical findings (research, October 2026)

- **Audio2Face-3D** (open source since 2025) generates skin, tongue, jaw and
  eyes from audio; every network takes audio **and emotion labels**, a natural
  fit for emotion coming from the script later. SDK in C++ (MIT), training
  framework in Python (Apache-2.0), models under the NVIDIA Open Model License.
  Official plugins for Unreal and Maya, **not Blender**: needs a bridge
  (keyframes → shape keys). The samples write per-frame keyframes to CSV.
- **The tongue cannot come from video.** MediaPipe's 478-point mesh has no
  tongue and never emits `tongueOut` (google/mediapipe#4403). Audio is the only
  source for it.
- `mocap-contracts` already carries a face: `MocapTakeHeader.face_blendshape_names`,
  `MocapFrame.face_blendshapes` and an optional `emotion`. This test stays on
  CSV; `face-in-shot` decides whether those fields are enough.

## Tools

| Tool | Role | Note |
|---|---|---|
| [Audio2Face-3D SDK](https://github.com/NVIDIA/Audio2Face-3D-SDK) | audio → blendshapes, tongue included | core; C++ (see prework/1) |
| [Audio2Face-3D Samples](https://github.com/NVIDIA/Audio2Face-3D-Samples) | Python client, CSV export | practical start; check which runtime it needs |

Epics and their order: `epics/README.md`.
