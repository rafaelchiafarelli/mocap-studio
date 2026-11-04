## 2. Actor to character

- **Type:** code.
- **Depends on:** `skeleton`
- **Contract:**
  - In: Capture points per frame
  - Requires: The character keeps its proportions
  - Delivers: `hmcore/retarget.py`: motion as bone directions; `tests/test_drive.py`
- **Pre-work:** —
- **Out of scope:** —
- **Tests:** —

## Result (2026-11-03)

Bones take the actor's directions, not positions or lengths. Root motion is scaled by leg length. **Limit:** a direction doesn't say how a bone twists, so forearm and thigh twist aren't carried.
