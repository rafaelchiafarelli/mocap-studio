# Face tests: what was tried and what was learned (2026-11-01 and 02)

**All of this is embryonic:** a few short clips, judged by eye, with few measurements.
The verdicts are Rafael's. This file keeps the detail, and the summary is in
[`initiatives/faces/`](../../initiatives/faces/faces.md).

## Ranking so far

1. **Mouth faders:** "bem melhor do que eu imaginava".
2. **Parrot Lipsync:** rhythm only "marginalmente melhor" than OpenSeeFace's mouth.
3. **OpenSeeFace alone:** eyes much better, mouth better but "ainda não está bom".
4. **MediaPipe and Audio2Face:** "definitely bad" and "worse".

Dense skin tracking hasn't been judged by Rafael.

## What makes the faders work

Three sources, each used for what it does best:

| Part | Source | Why |
|---|---|---|
| Eyes, brows, head | OpenSeeFace | Rafael judged these much better |
| Mouth shape | 13 poses on the character | The tracker can't describe an F or pressed lips |
| Which sounds, and when | Known words, timed by the recognizer | The recognizer alone gets few Fs and Ps right |
| How far it opens, when it shuts | Tracked lip opening | Keeps the rhythm of the performance |

## Measurements on the final recording

| Setup | Sounds | Jaw correlation with video | Jaw at M | Jaw at F | Lip tuck at F | Press at M | Jaw max |
|---|---|---|---|---|---|---|---|
| A: dry, like Parrot | Recognizer | 0.329 | 0.102 | 0.135 | 0.199 | 0.143 | 0.419 |
| B: blended | Known words | 0.278 | 0.025 | 0.103 | 0.880 | 0.429 | 0.420 |
| C: B plus tracked opening | Known words | 0.869 | 0.003 | 0.035 | 0.880 | 0.429 | 0.660 |

**Diagnosis:** Parrot fails for two separate reasons. Wrong sounds put F and M in the
wrong places, which known words fix. Rhythm without performance makes every vowel open
alike, and known words don't fix that (0.33 to 0.28). Half of C's opening comes from
the video, so its 0.87 explains the diagnosis and doesn't score quality.

## Recordings

| Name | Content | Used for |
|---|---|---|
| Take 1 | Webcam, 46 s, performer with beard and glasses | First tracker numbers; its overlay video came out empty |
| Take 2 | 51 s, same performer, closer, better light | Beard and glasses as a hard case |
| Take 3 | 80 s, performer with no glasses or facial hair; someone off-camera prompts each word | OpenSeeFace on the character, judged by Rafael |
| Take 4 | 20 s, same performer alone, "farol, pipoca, farofa" three times, then a comment with the head turned | Parrot and the faders; **the baseline** |

These are private tests of real people. Consent for any other use isn't established.

## OpenSeeFace

- **Good:** never lost the face in any take; about 12 ms per frame on CPU; about 0.3 px of
  jitter at rest; brows and blinks follow well.
- **F:** the lip contact isn't described. With beard and glasses, F read as closed lips
  (0.00–0.01 against 0.01–0.03). On the clean face it read 0.04–0.09, above closed lips
  (0.01) but overlapping a half-open mouth (0.03–0.05). Those few frames were picked by
  rhythm, and some may be Fs themselves.
- **Pressed lips:** the outer points stay on the skin as if the lips were still full.
- **Half-open mouth:** the measured opening is smaller than the image shows.
- **No tongue data.**

## Parrot Lipsync and Allosaurus

- **What it does:** audio → sounds with start times → a table → one of 12 poses plus rest,
  keyed at each start time.
- **Recognition, take 4:** 2 of 9 Fs and 2 of 6 Ps right even set to Portuguese. Fs mostly
  became `s`.
- **The stock table doesn't fit Portuguese:** on take 3, 123 of 451 sounds were outside it,
  and the R in "farofa" (`ɾ`) mapped to rest, shutting the mouth mid-word.
- **In its code:** every sound gets a full pose (the strength options aren't read by the
  function that keys them), durations are ignored, and it writes to one object.
- **It animates any voice:** take 3's off-camera prompts were recognized better than the
  performer, with her lips shut.
- **License:** its manifest says MIT and its repository GPL-3.0. Allosaurus is GPL-3.0, and
  the terms of its `uni2005` model weren't found. This must be settled before production.

## The character

- With `jawOpen` at 1, the lips open 3.45 cm. The eye distance is 5.83 cm.
- The armature has lip, chin, jaw, cheek and tongue bones that deform the mesh. Only the
  lower lip and tongue bones are used so far.
- The F pose combines rolling the lower lip, lifting the upper lip and pulling the lower-lip
  bones back and up.
- The neutral mouth looks sad, so some poses inherit it.

## Technical traps

| Trap | What to do |
|---|---|
| OpenSeeFace's log header has 435 names, and its rows 453 | Read columns by position |
| It stores points as (row, column) | Head axes are swapped; check signs against a real head turn |
| The first frames fit badly and give false 100° turns | Drop frames with a fit error above 20 |
| `--video-out` wrote a 0-byte file, cause unconfirmed | Draw the overlay from the log |
| A sideways camera reads as a turned head | Shift the lens instead of moving the camera |
| Normalizing by a channel's own range inflates tiny motion | Give each channel a floor |
| A median over a whole take isn't neutral | Use a still window; it differs per recording |
| Hair strands slow playback | Hide scalp and fine hair in the viewport; keep the brows visible |
| Tongue bones turned the wrong way go through the chin | Check poses in renders first |
| Parrot opens its table with the system encoding | Write the table in ASCII |
| Parrot copies absolute handles from the poses | Update the curves afterwards; the faders avoid this |
| Parrot needs `ffmpeg` for anything but `.wav` | Give it `.wav` |
| The `.blend` opens in whichever Blender is associated | Open it through `abrir_faders.bat` |
| `G:` gave one transient read error | Copy the file and try again |

## Reviewed and not used

| Option | Why not |
|---|---|
| GaussianAvatars, SplattingAvatar, VHAP | CC BY-NC-SA; learn the filmed person, not a character |
| HRAvatar, LightHeadEd, BecomingLit, Relightable Gaussian Codec Avatars | Person-specific; license, GPU or capture limits |
| Duix-Avatar | Clones a person into generated video; capped community license |
| Wan Animate, LivePortrait | Generate the final pixels, which Rafael rejected |
| MetaHuman on Unreal | Parked by Rafael as too large; **never tested** |

If Unreal is reopened: the EULA (read 2026-11-02) makes rendered films royalty-free, needs no
seat under USD 1M gross revenue in 12 months (funds raised count), requires credits notices,
and in section 6(c) bars combining Unreal with GPL code. The Epic Content License Agreement
wasn't read. Poly Hammer's Character DNA add-on (free core, GPLv3) is a route back to Blender,
and its material support is unconfirmed.

## Still open

- **Mannerisms:** Rafael: "o photorealismo está somente na imagem, mas não em todos os
  trejeitos humanos". Next: [human-model](../../initiatives/human-model/human-model.md).
- **Emotion in the mouth:** only upper-face tracking and the tracked opening carry performance.
- **Tongue:** poses only.
- **A general tool for known words:** this alignment was built for one recording.
- **No playback was checked by the agent:** only renders and numbers. Rafael judged the motion.
