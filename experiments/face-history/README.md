# Older face test code (2026-11-01 and 02)

Earlier experiments, kept so they aren't lost. **These weren't run again after being copied
here.** Film names were replaced with `character`, and the original files used real object
names, so they need adjusting before they run. Hardcoded paths remain.

| Folder | Test | Verdict or state |
|---|---|---|
| `video_test_1/` | MediaPipe → 52 ARKit shapes | "Definitely bad" |
| `video_test_2/` | Same, mapping reworked | Problems remain, mainly Ps and Fs |
| `audio2face/` | Audio2Face-3D mouth, video blinks and brows | "Worse" |
| `dense_face/` | Dense skin tracking with BootsTAPIR | Not judged by Rafael; its run order is below |
| `character/` | The character generator's scripts, without its `recipe.json` | Rafael: "good for now" |
| `parrot_on.py` | Runs Parrot itself on the character | "Marginalmente melhor"; replaced by the faders |

**Left out of git:**

- Footage, `.blend` files, weights and outputs: in `G:\mocap-studio-downloads\face\` and in
  `scratch\` in Rafael's clone. `scratch\` is only in that clone, so `git clean -x` would delete it.
- The character's `recipe.json`: it's the film's design. A copy is in the baseline folder's
  `inputs/character/`, and the original is in the film root, which isn't versioned.
- `dense_face`'s `third_party/` and `.venv`: 7 GB in `scratch\dense_face\`.

**Dense tracking run order**, from `dense_face/`:

    python stage1_track.py third_party/tapnet <video> <bootstapir.pt> <face_landmarker.task> out/stage1.npz 130 610 0 760
    python stage1_report.py <video> out/stage1.npz out/overlay.mp4
    python stage1_pose.py <video> <face_landmarker.task> out/stage1.npz out/lm3d.npy
    blender -b <character>.blend --python stage3_neutral.py -- out/stage3
    python stage3_solve.py out/stage1.npz out/stage3 <face_landmarker.task>
    blender -b <character>.blend --python stage3_apply.py -- out/stage3/face.pc2 out/stage3/channels.json <audio.wav> out/stage3/test.blend
