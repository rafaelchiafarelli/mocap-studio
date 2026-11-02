# Initiatives

The full process (initiative → epic → task → contract, branch chain, per-task
loop, stop-and-ask rules) lives in the **mocap-workflow** skill
(`.claude/skills/mocap-workflow/SKILL.md`). Read it before anything else.

Rules specific to this repository:

- **Layout:** `initiatives/<initiative>/epics/<epic>/tasks/<n>-<task>.md`.
  The number is the implementation order, and the file name is the branch name.
- **Done marker:** `-done` suffix on the **file name** (`git mv` in a separate
  commit, right after the implementation commit). Never a status line.
- **Order between epics:** in `initiatives/<initiative>/epics/README.md`.
- **Order between repositories:** in `mocap-studio/HANDOFF.md`.
- **Test suite:** `pytest` at the root (Python repositories) or
  `pio test -e native` (mocap-sync-fw). "Not broken" = green suite.
- **Contracts between repositories** only through the `mocap-contracts` package
  and the session folder layout. Never import code from another mocap repository.
  A change that crosses repositories starts in `mocap-contracts`.

## ⚠ Major open problem: faces (recorded 2026-11-02)

**Read this before any face, character or planning work.** Believable faces are
a requirement of this project, and nothing tried so far delivers them. Rafael
will come back to this soon. **No approach has been chosen.**

- **Requirement (Rafael):** "I need faces... regardless of what my audience
  really needs." Staging around the face, such as hiding the mouth or using
  voice-over, doesn't solve this.
- **Impact (Rafael):** these results made him seriously reconsider the project.
  The parts may produce an initial version of the animation, but "it will not
  give me what I really need". Treat this as a question about the project's
  direction, not a tuning task.

### Results so far: EMBRYONIC

The first face tests ran on 2026-11-01. **These results are embryonic: a few
short clips, judged by eye and with few measurements. They need further
investigation and prove nothing either way, for or against any tool.** None of
this completes a task in the face initiatives below.

| Test | What was done | Rafael's verdict |
|---|---|---|
| Character | MPFB targets, CC0 assets, generated hair and aging; no sculpting (nobody available can sculpt) | "Good for now", not perfect |
| Video → face, clip with glasses and head turns | MediaPipe Face Landmarker → 52 ARKit shapes | "Definitely bad" |
| Video → face, frontal clip | Same, with the mapping reworked | Problems remain, mainly Ps and Fs; eye movement not visible |
| Audio → face | Audio2Face-3D v3.0 mouth (ONNX model run from Python), video blinks and brows | "Worse"; mouth worse, lids out of sync |

**Measured:**

- Lips near closed on the frames where the source's lips close: 31 of 39 with
  video, 15 of 39 with audio. Audio can't copy one speaker's exact timing, so
  this doesn't rank the methods.
- Mouth-gap correlation with the source: 0.90 with video, 0.81 with audio.
- Audio2Face-3D on CPU: 0.6 s of computing per second of audio, 1.9 GB of RAM.

**Likely causes, not proven:**

- Every step between performance and face loses detail: source → 52 generic
  values → auto-generated shapes on a thin-lipped base mesh → photoreal skin.
- Audio2Face weights are solved for NVIDIA's face, not this one.
- ARKit has no dedicated "lower lip against upper teeth" shape for Fs.
- A full sideways eye shape on this character turns the eye only about 15°.

**Known defects in the test files, so don't judge the methods by them alone:**

- The audio test file has sync off at 60 fps. Rafael heard the audio end midway,
  probably because playback lags under the hair strands.
- Blink thresholds exaggerate left/right differences.
- An eye jump Rafael saw at frames 135–136 is unexplained.
- The head doesn't move.
- Fine facial hair drifts from the skin in some frames.
- The Rigify control rig generates, but the mesh isn't connected to it.

**Not established:**

- Whether the face camera needs 120 fps. Nothing measured supports that number.
- Whether Audio2Face-3D works with Portuguese; its model card lists English
  training audio.
- How the official Audio2Face SDK performs. It wasn't built; its logic was
  reproduced in Python, so quality may differ.
- Licenses for the Audio2Face route: read, but not yet confirmed by Rafael.

**Ideas not tried, none chosen:** a mouth pose per sound, built on the character
and timed from the audio; a less realistic character (photoreal is only the
current choice); motion transferred directly from geometry or landmarks,
skipping the 52 values.

**Files** (outside git, and two tests use third-party footage: private tests
only, never film material):

- Tests and scripts: `G:\mocap-studio-downloads\face\`
- Comparison images: `G:\mocap-studio-downloads\review\2026-11-01\`
- Character recipe and scripts: `<film-root>\character_work\`
- Models and asset packs: `G:\mocap-studio-downloads\models\` and `apps\mpfb\`,
  not yet listed in `DEPENDENCIES.md`

## Index

| Initiative | Status |
|---|---|
| [face-audio](face-audio/face-audio.md) | Planned — tasks not done; **see the open problem above**. Was set to run first, alongside the MVP |
| [face-video](face-video/face-video.md) | Planned — after a `face-audio` pass; **see the open problem above** |
| [face-character](face-character/face-character.md) | Planned — after a `face-audio` pass; **see the open problem above** |
| [face-in-shot](face-in-shot/face-in-shot.md) | Planned — after a `face-audio` pass and the MVP shot; **see the open problem above** |
| [baseline](baseline/baseline.md) | Planned — frozen by the MVP (`MVP-plan.md`) |
| [environments](environments/environments.md) | Proposed — free library-and-rules set building for a free camera; not scoped, nothing tested |
