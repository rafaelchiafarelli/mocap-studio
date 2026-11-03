## 1. Binding comparison

- **Type:** experiment.
- **Depends on:** `muscles/4`
- **Contract:**
  - In: The zygomaticus smile's field
  - Requires: Same smile through each method
  - Delivers: `blender/binding_compare.py`; a recommendation
- **Pre-work:** —
- **Out of scope:** —
- **Tests:** Compares against the direct field

## Result (2026-11-03)

| Method | Shell faces | Bind | RMS error | Max error |
|---|---:|---:|---:|---:|
| Direct shape key (reference) | — | — | 0 | 0 |
| Surface Deform | 2,294 | 0.03 s | 0.68 mm | 10.8 mm |
| Mesh Deform, inflated cage | 2,294 | 0.20 s | 1.50 mm | 10.1 mm |

**Decision: direct shape keys.** We already have the displacement per vertex, so a shell only loses detail. Surface Deform or Mesh Deform would matter only with a real volumetric simulation driving a cage, which we don't have. A "fine" Surface Deform run is left out of the table: its shell wasn't coarser than the skin, so its zero error means nothing.
