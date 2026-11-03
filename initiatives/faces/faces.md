# faces — mocap-studio

**Status:** Open problem, recorded 2026-11-02. No epics or tasks; no pipeline chosen.
[human-model](../human-model/human-model.md) is one candidate answer, not the chosen one.

**Goal:** believable faces.

**Initiative gate:** to be defined with Rafael. New work has to beat the mouth faders
on the same recording, in his judgement.

**Read this before any face, character or planning work.**

**Read this before any face, character or planning work.** Believable faces are
a requirement of this project. **The best tool so far is the mouth faders, below.**
Rafael says it's much better than he expected, but he's keeping this problem open:
the realism is in the image, not yet in human mannerisms. His anatomy research led to the proposed
[human-model](../human-model/human-model.md). No pipeline has been chosen.

- **Requirement (Rafael):** "I need faces... regardless of what my audience
  really needs." Staging around the face, such as hiding the mouth or using
  voice-over, doesn't solve this.
- **Impact (Rafael):** these results made him seriously reconsider the project.
  The parts may produce an initial version of the animation, but "it will not
  give me what I really need". Treat this as a question about the project's
  direction, not a tuning task.

## Results so far: EMBRYONIC

The first face tests ran on 2026-11-01. **These results are embryonic: a few
short clips, judged by eye and with few measurements. They need further
investigation and prove nothing either way, for or against any tool.**

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

## Best tool so far: mouth faders (2026-11-02)

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

- Code, how to repeat it and every finding: [`experiments/face-mouth/`](../../experiments/face-mouth/README.md).
  Process diagram: [`face-mouth-experiment.drawio`](../../experiments/face-mouth/face-mouth-experiment.drawio).
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

**Files** (outside git, and two tests use third-party footage: private tests
only, never film material):

- Tests and scripts: `G:\mocap-studio-downloads\face\`
- Comparison images and videos: `G:\mocap-studio-downloads\review\2026-11-01\`
  and `2026-11-02\`
- Character recipe and scripts: `<film-root>\character_work\`
- Models and asset packs: `G:\mocap-studio-downloads\models\` and `apps\mpfb\`, listed in `DEPENDENCIES.md`
- Older experiment code: [`experiments/face-history/`](../../experiments/face-history/README.md).
  Its full working copies stay in `scratch\` in Rafael's clone, not in git

## Kept from the retired plans

`face-audio`, `face-video`, `face-character` and `face-in-shot` were retired on
2026-11-03. Their shared premise, Audio2Face owning the mouth behind a `face-audio`
pass, was overtaken by these results, and their per-character gain on ARKit values
differs from `human-model`'s bones and muscles. **That isn't a ruling against
Audio2Face:** the tests above are embryonic. Git keeps the plans
(`git log -- initiatives/face-audio`). What still applies:

- **The tongue can't come from video.** MediaPipe's mesh has no tongue and never emits
  `tongueOut` (google/mediapipe#4403), and OpenSeeFace doesn't measure it either.
- **`mocap-contracts` already carries a face:** `MocapTakeHeader.face_blendshape_names`,
  `MocapFrame.face_blendshapes` and an optional `emotion`.
- **Per-character exaggeration must be declared, never inferred by code.** The
  declaration is planned in `human-model`, epic `morphology`.
- **When a face method is chosen, it has to enter the pipeline:** audio and sync in P1
  and P2, a new step in P3, a rule in P4 for which source owns each channel, and the
  character's declaration in P5.
- **Still open for Rafael:** whether the face camera is fixed or worn, and whether the
  face stays photoreal (the first plans said caricatured).
- **Tools not tried, licenses to check:** VIPER Blender Facial MoCap, Phiz, Mocapy and
  BlendArMocap. EMOCA is excluded by its non-commercial license.
