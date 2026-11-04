## 4. Tongue from phonemes

- **Type:** code.
- **Depends on:** `muscles/6`
- **Contract:**
  - In: The take's known-words track, 13 mouth groups
  - Requires: —
  - Delivers: `hmcore/tongue.py`
- **Pre-work:** —
- **Out of scope:** —
- **Tests:** `tests/test_drive.py`

## Result (2026-11-03)

Each group has a tongue pose with attack and release; values declared from where the sound is articulated. The curves are computed but **no render shows them on the model's tongue controls**: the comparison character keeps its existing tongue keys.
