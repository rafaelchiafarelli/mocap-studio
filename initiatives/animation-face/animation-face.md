# animation-face

**Goal:** the face of the animation body, believable in speech and expression, built the way the body was: a simple physical model plus the right anatomy, judged against the mouth faders on the same recording (Rafael, 2026-11-12).

**Status:** planned 2026-11-12. Epic 1 done the same day, awaiting Rafael: the faders ran unchanged on the new woman (`blender/face_character.py`), with the same mouth curves as the approved baseline (jaw correlation 0.33, 0.28 and 0.87 for setups A, B, C); video in `G:\\mocap-studio-downloads\\review\\2026-11-12\\rosto\\`. Builds on branch `animation-body`.

Epic 2 first round (2026-11-12), awaiting Rafael. Measured on the baseline: at each M only 38 to 47% of the mouth's width touched (the sides stayed 1 to 6 mm open, teeth showing), and at each F the lower lip stopped 0.5 to 1.4 mm short of the upper teeth, rolled in under the upper lip. With `blender/lip_contact.py`, 82 to 84% of the width touches at M, with no lip crossing the other, and the F reaches 0.2 mm from the teeth; the largest give is 4.6 mm. A first try met the lips by vertical rays and misread a lip behind the other as inside it. The F still looks sucked in, since its pose rolls the lower lip (`mouthRollLower` 0.7, `lipBite` 1.0); a copy with 0.2 and 0.3, the contact lifting the lip to the teeth, is offered beside it, not applied to the fader reference. Video in `G:\\mocap-studio-downloads\\review\\2026-11-12\\rosto\\contato_labios\\`.

## Decided by Rafael (2026-11-12)

- Start with the recordings we already have; then record videos aimed at the problems found.
- Other actors will likely go through the same process, for variety in the face mesh and its detection.
- Audio to face has to be tested.
- Carried over from `initiatives/faces/faces.md`: the actor performs and the character keeps its own face; AI doesn't make the final face pixels; new work must beat the mouth faders on the same recording, in his judgement; only he moves that reference.

## Epics, in order

1. **faders-on-new-face**: the mouth faders, unchanged, on the animation body's woman, with the 52 ARKit shapes from MPFB's Faceunits 01 (CC0), on the baseline recording. The reference to beat on this face.
2. **lip-contact**: P, B and M need the lips pressing together, and F the lower lip on the upper teeth; contact, not a shape imitating it (as with the hands: they touch and the skin gives).
3. **face-soft-tissue**: cheeks, jowls and lips with a little inertia, moved by the head and the step's impact.
4. **eyes-alive**: small gaze movements and blinks with the lid's own motion.
5. **audio-to-face**: Audio2Face-3D (NVIDIA Open Model License, commercial use allowed) again on this face, and a sound-to-pose route through the faders' phoneme table; Portuguese to be checked.
6. **variety**: a recording plan aimed at the problems found, and other actors, to see how the face mesh detection varies.

Each epic is judged by Rafael in simple videos with the recording's sound.
