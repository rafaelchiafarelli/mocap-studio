# animation-face

**Goal:** the face of the animation body, believable in speech and expression, built the way the body was: a simple physical model plus the right anatomy, judged against the mouth faders on the same recording (Rafael, 2026-11-12).

**Status:** planned 2026-11-12, epic 1 under way. Builds on branch `animation-body`.

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
