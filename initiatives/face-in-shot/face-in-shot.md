# face-in-shot — mocap-studio

**Status:** Planned — starts when `face-audio` passes **and** the MVP shot
exists (`MVP-plan.md` step 6). Epics and tasks are scoped then.

**Goal:** the MVP character speaks: the actor's voice from the picked
performance take drives the face of the rigged character in the MVP shot.

**Scope (where Audio2Face fits the existing pipeline):**

- **P1 setup:** one lavalier per actor; audio/video sync (the MVP's clap, or
  timecode). With Audio2Face owning the mouth, the face camera only needs eyes
  and brows.
- **P2 capture:** clean audio becomes take data next to the videos.
- **P3 extraction:** Audio2Face per take, a new step in `mocap-extract` and a
  new box in `docs/diagrams/pipeline.drawio`.
- **P4 adaptation:** body (FreeMoCap) + upper face (video, if `face-video`
  passed) + mouth/jaw/tongue (Audio2Face) in one `MocapTake`, with an explicit
  rule for which source owns each blendshape. The contract already has
  `face_blendshape_names`, `face_blendshapes` and `emotion`; the ownership rule
  and the audio are what may need a `mocap-contracts` change.
- **P5 Blender:** the `face-character` profile applied to the merged result.

**Out of scope:** anything the MVP's "what's broken" list doesn't ask for.

**Initiative gate:** the MVP shot re-rendered with a speaking face.
