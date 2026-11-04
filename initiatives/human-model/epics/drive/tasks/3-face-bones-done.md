## 3. Face bones

- **Type:** code.
- **Depends on:** `skeleton/2`
- **Contract:**
  - In: OpenSeeFace through the existing `experiments/face-mouth/osf_to_arkit.py`
  - Requires: —
  - Delivers: `blender/dump_take.py` reads the keyed head, jaw and eyes of a take
- **Pre-work:** —
- **Out of scope:** —
- **Tests:** —

## Result (2026-11-03)

Head, jaw and eyes keep the fader file's tracked values on its existing rig. **They aren't yet connected to `hm_jaw`:** the comparison character opens its jaw with its `jawOpen` shape, so it doesn't use the sliding jaw. Connecting them is the next step if the hybrid is kept.
