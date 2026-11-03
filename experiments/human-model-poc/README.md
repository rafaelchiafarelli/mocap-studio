# Jaw proof of concept on Z-Anatomy (2026-11-02)

The test behind "What we already know" in
[`human-model`](../../initiatives/human-model/human-model.md). **Embryonic, and these
copies weren't run again.** The `.blend` files and images stay in
`G:\mocap-studio-downloads\review\2026-11-02\`, because they're large.

Run inside Blender, in this order, with the arguments after `--`:

1. `v_names.py <out>`: lists the file's structures as JSON.
2. `v_build.py <names.json> <source.blend> <out.blend>`: builds the jaw scene and its bindings.
3. `v_check.py <outdir>`: measures the result.

For licenses, see `human-model`: licensing was set aside for this investigation, so
nothing here may be used in production until `references/1` clears it.
