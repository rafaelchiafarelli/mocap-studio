# 2. The zero point again, on the pushed skin, with skin as a thin layer

**Asked by Rafael, 2026-11-07.** Whether the push improved the body: the layers rebuilt inside task 1's skin, compared with `body_v4`.

## Contract

**In:** `<name>.skin_fit.npz` (task 1), and everything epic `body-at-rest` used.

**Out:**
- `tools/body_layers.py` and `tools/body_report.py` take the pushed skin in place of the build's.
- **Masses from the volume inside the skin,** not from the voxels: real skin counts as its area times 1.5 mm, and fat is what's left after bone, muscle, cavity and skin. The 5 mm voxels made a 9 mm "skin" band and put the fat anywhere from 19% to 37%.
- The same sections, table and `.blend` as `body_v4`, side by side with it.

**Measured, and reported as measured:** bones through the skin (expected none but the misplaced ones), tissue shares, and the pattern measures against `body_v4`.

## Dependencies

Task 1.
