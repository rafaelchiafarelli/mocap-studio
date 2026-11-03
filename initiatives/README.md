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
a requirement of this project. **The best tool so far is the mouth faders, below.**
Rafael says it's much better than he expected, but he's keeping this problem open:
the realism is in the image, not yet in human mannerisms. His next research is
[face-anatomy](face-anatomy/face-anatomy.md). No pipeline has been chosen.

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

**Also EMBRYONIC: dense skin tracking (2026-11-02).** Rafael's idea: track face
pixels in 2–3 cameras and move the character's mesh directly, skipping the 52
values. BootsTAPIR (Apache-2.0, weights included) did the tracking.

| Stage | Test | Result |
|---|---|---|
| 1. Tracking | About 2,800 points on one real frontal clip | Stayed on the face; 0.10 s per frame; 0.95 lip-gap correlation with MediaPipe; about 1 mm round-trip drift |
| 2. 3D | Three **rendered** cameras with known true positions; no real multi-camera footage exists yet | Lips 0.85 mm median, 1.95 mm p95. One camera 1 frame late: 1.05 and 2.77 mm; 2 frames late: 1.20 and 4.49 mm |
| 3. Transfer | That one real camera onto the character's mesh | Works but weak: mouth opens too little, skin and brow flap at one temple, head turns still leak in. Rafael hasn't judged it |

Stage 2 is a best case: perfect calibration, no real-camera noise, start points
given. Stage 3 used one camera, so it loses depth and only estimates head motion.
**The real test, 2–3 synced cameras on a real face, hasn't been done.**

### Best tool so far: mouth faders (2026-11-02)

**Rafael's verdict:** "gostei... bem melhor do que eu imaginava". With it he can
stress chosen moments to build the illusion he wants. This is one 20-second
recording, judged in the Blender file, and it isn't a finished tool or a chosen
pipeline.

**How it works:** a Blender add-on with faders that re-bake the mouth at once. Each
sound pulls the mouth towards one of 13 poses built from existing shapes and bones,
with neighbouring sounds blending. The pose gives the shape, and the tracked video
can set how far the mouth opens and when it shuts. Eyes, brows and head come from
OpenSeeFace.

| Test | Result | Rafael's verdict |
|---|---|---|
| OpenSeeFace landmarks → 34 ARKit shapes and head | Stable; lips open and close well; no tongue, and the F and pressed-lip shapes are lost | Eyes much better, mouth better but "ainda não está bom"; best at the time |
| Parrot Lipsync: phonemes → poses | The recognizer got 2 of 9 Fs and 2 of 6 Ps right, even set to Portuguese | Rhythm only "marginalmente melhor" |
| Mouth faders | See below | **Best so far** |

| Fader setup | Sounds | Jaw correlation with video | Jaw at M | Lip tuck at F |
|---|---|---|---|---|
| A: dry, like Parrot | Recognizer | 0.33 | 0.10 | 0.20 |
| B: blended | Known words | 0.28 | 0.02 | 0.88 |
| C: B plus tracked opening | Known words | 0.87 | 0.00 | 0.88 |

Half of C's opening comes from the video, so its correlation is high by
construction. These numbers explain the diagnosis, and they don't score quality.

**Limits:**

- The known-words alignment was built for this recording, with two sounds placed
  by hand. It isn't a general tool.
- Tongue motion comes from poses, not data, and there's no emotion in the mouth.
- The poses are a first pass.

**Decided by Rafael (2026-11-02):**

- The actor performs and the character keeps its own face, so person-specific
  avatars (GaussianAvatars, SplattingAvatar and similar) are out.
- AI doesn't generate the final face pixels.
- Unreal and MetaHuman are parked as too large for this project. They were never
  tested. If reopened, read the EULA's section 6(c) ban on combining Unreal with GPL
  code, and the unread Epic Content License Agreement.

**Don't lose this result:**

- Code, how to repeat it and every finding: [`experiments/face-mouth/`](../experiments/face-mouth/README.md).
  Process diagram: [`face-mouth-experiment.drawio`](../docs/diagrams/face-mouth-experiment.drawio).
- Frozen baseline (recording, character, approved `.blend`, expected results):
  `G:\mocap-studio-downloads\face\baseline_mouth_faders_2026-11-02\`, not in git and on
  one drive only.
- New face work must beat it on the same recording, in Rafael's judgement. Only Rafael
  moves the reference.
- To open it: `abrir_faders.bat` in `G:\mocap-studio-downloads\review\2026-11-02\`.
  Only the portable Blender has the add-on.

**Ideas not tried, none chosen:** a less realistic character (photoreal is only the
current choice); dense tracking with real multi-camera footage; a small model
trained on one actor; face shapes captured from a real person; a general
known-words alignment from the script.

**Not suitable (reviewed):** openFACS (Unreal only, its own character, fewer mouth
controls); First Order Motion Model (moves 2D pixels, no data to drive a rig).
**Blocked by the license rule:** CoTracker and MASt3R (non-commercial).

**Body results are also bad (Rafael, 2026-11-02).** He'll discuss this later, and
gave no details yet. Don't treat body capture as working; ask him before planning
body work.

**Files** (outside git, and two tests use third-party footage: private tests
only, never film material):

- Tests and scripts: `G:\mocap-studio-downloads\face\`
- Comparison images and videos: `G:\mocap-studio-downloads\review\2026-11-01\`
  and `2026-11-02\`
- Character recipe and scripts: `<film-root>\character_work\`
- Models and asset packs: `G:\mocap-studio-downloads\models\` and `apps\mpfb\`,
  not yet listed in `DEPENDENCIES.md`
- Older experiment code: [`experiments/face-history/`](../experiments/face-history/README.md).
  Its full working copies stay in `scratch\` in Rafael's clone, not in git

## Index

| Initiative | Status |
|---|---|
| [face-audio](face-audio/face-audio.md) | Planned — tasks not done; **see the open problem above**. Was set to run first, alongside the MVP |
| [face-video](face-video/face-video.md) | Planned — after a `face-audio` pass; **see the open problem above** |
| [face-character](face-character/face-character.md) | Planned — after a `face-audio` pass; **see the open problem above** |
| [face-in-shot](face-in-shot/face-in-shot.md) | Planned — after a `face-audio` pass and the MVP shot; **see the open problem above** |
| [baseline](baseline/baseline.md) | Planned — frozen by the MVP (`MVP-plan.md`) |
| [environments](environments/environments.md) | Proposed — free library-and-rules set building for a free camera; not scoped, nothing tested |
| [face-anatomy](face-anatomy/face-anatomy.md) | Proposed — research handoff on an anatomy-based rig and muscle physics; not scoped, nothing built |
