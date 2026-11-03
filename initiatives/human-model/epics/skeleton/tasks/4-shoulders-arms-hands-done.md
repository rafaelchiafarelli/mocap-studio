## 4. Shoulders, arms and hands

- **Type:** code.
- **Depends on:** `skeleton/1`
- **Contract:**
  - In: CT scapula, clavicle, humerus; Rajagopal forearm and hand
  - Requires: —
  - Delivers: Fit per bone, `blender/posing.py` rotations in rest axes
- **Pre-work:** —
- **Out of scope:** —
- **Tests:** —

## Result (2026-11-03)

Scapula, clavicle and humerus are CT. Forearm and hand are Rajagopal, low resolution (radius 194 points). **Loss:** radius and ulna don't cross in pronation, because both are rigid on one forearm bone. Fingers follow the rig's finger bones.
