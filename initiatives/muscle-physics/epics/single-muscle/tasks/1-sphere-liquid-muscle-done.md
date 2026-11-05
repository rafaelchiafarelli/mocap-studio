# 1. A liquid-filled sphere that lifts a box

**Asked by Rafael, 2026-11-04.** A spherical muscle joined to two boxes. The top box stays still. Contracting raises the bottom box, as if pulling a weight. The volume doesn't grow, the shape changes. The inside behaves as a liquid. After the pull, the force is let go and the sphere extends.

## Contract

**In:** nothing but Blender. Declared values: bottom box 1 kg, Earth gravity (9.81 m/s²), sphere radius and liquid density at the top of the script.

**Out:**
- `human-model/blender/muscle_sphere.py`: builds the scene, runs the simulation, saves the `.blend` and a per-frame table.
- On `G:\mocap-studio-downloads\review\<date>\`: the `.blend` and a video.

**Measured, and reported as measured:**
- Enclosed volume per frame, against the start.
- Height of the bottom box per frame: lift when contracted, drop when released.
- Top box doesn't move.
- The lift comes from the simulated force against the load, not from animating the box.

## Dependencies

Blender 5.2.2 (`DEPENDENCIES.md`), `human-model/blender_run.py`. Blender's own physics first; anything else gets reported as a finding.

## Out of scope

The human model, any real muscle's data, skin or fat. No conclusion on replacing the spindles.
