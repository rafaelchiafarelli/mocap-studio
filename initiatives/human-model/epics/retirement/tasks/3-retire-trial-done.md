## 3. Retire trial

- **Type:** check.
- **Depends on:** `retirement/1`
- **Contract:**
  - In: Muscle bodies, the walk
  - Requires: Rule in `human-model.md`; nothing retired by default
  - Delivers: `blender/retire_trial.py`
- **Pre-work:** —
- **Out of scope:** —
- **Tests:** —

## Result (2026-11-03)

Removing the muscle bodies changes the skin by **exactly 0 mm** over 40 walking frames, and saves about 1.2 ms per frame (5.0 to 3.8).

**That's a finding about the model, not a win.** The muscle bodies follow bones and skin, and nothing follows them. The plan's aim, muscles moving skin because they're connected, is true only in how the fields were built, not at run time.

Against the rule: 1. holds, trivially. 2. needs Rafael's eyes on a recording, though the difference is zero. 3. holds. **Nothing was retired.** Recommendation: keep them, because they show anatomy and they're where a real simulation would connect.
