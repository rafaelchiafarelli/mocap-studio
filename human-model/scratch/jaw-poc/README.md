# Jaw proof of concept on Z-Anatomy (2026-11-02)

The test behind "What we already know" in
[the sources page](../../docs/sources-and-validation.md). **Embryonic, and these
copies weren't run again.** The `.blend` files and images stay in
`G:\mocap-studio-downloads\review\2026-11-02\`, because they're large.

Run inside Blender, in this order, with the arguments after `--`:

1. `v_names.py <out>`: lists the file's structures as JSON.
2. `v_build.py <names.json> <source.blend> <out.blend>`: builds the jaw scene and its bindings.
3. `v_check.py <outdir>`: measures the result.

Licensing was set aside for this investigation, and the decision since is that Z-Anatomy stays out of the model, so nothing here may be used in production.
