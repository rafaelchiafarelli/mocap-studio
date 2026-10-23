## 3. Drive the face, with gain

- **Type:** run, on top of one `mocap-blender` code task (CSV → shape keys,
  per-blendshape gain table), scoped there before this starts.
- **Depends on:** prework/3, test/2, that `mocap-blender` task
- **Contract:**
  - In: the CSV from `test/2`, the head from `prework/3`, the WAV
  - Requires: a gain table set by hand with Rafael (e.g. smile ×1.8, brows ×2),
    written in this file; values clamped to the shape keys' range
  - Delivers: a `.blend` and a short render with the voice, without gain and
    with gain side by side, in `G:\mocap-studio-downloads\review\<date>\`
- **Pre-work:** —
- **Out of scope:** making the gain table a declared character profile
  (`face-character`)
- **Tests:** in the `mocap-blender` task
