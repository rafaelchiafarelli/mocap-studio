# Settled bones go into their neighbours: fibula into tibia, clavicle into the first ribs

- **Symptom:** in the woman's build, 16% of each fibula's sampled points lie inside its tibia (none before settling). Clavicle points inside rib 1: 5.4% left, 4.6% right (4.4 and 1.8 before), and inside rib 2: 3.6 and 1.6 (none before), and 1% inside the scapula.
- **Where:** `human-model/hmcore/fit.py`, `settle`, its `avoid`: it measures the distance to the neighbour's vertices, which can't tell a point inside the neighbour from one outside it. Introduced by the fix of bug 12.
- **Reproduce:** winding number of the settled bone's vertices against the neighbour's mesh in `female.bones.npz`; compare with `models\hm-build\female_2026-11-07_before-bone-fixes\`. Measured on 2026-11-08 on 500 sampled points per bone.
- **Impact:** hidden under the skin. In the layered body both are bone voxels, so the walk isn't affected; it would show if bones are displayed or simulated apart.
- **Status:** Open. Likely fix: make `avoid` test inside-or-outside by the neighbour's winding number.
