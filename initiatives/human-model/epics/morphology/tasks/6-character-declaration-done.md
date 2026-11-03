## 6. Character declaration

- **Type:** contract.
- **Depends on:** `morphology/1`
- **Contract:**
  - In: A recipe
  - Requires: A new file between applications starts in `mocap-contracts`
  - Delivers: `human_model.harpia`: `CharacterBody`, on branch `fixes/0000ca/character-body` of `mocap-contracts`
- **Pre-work:** —
- **Out of scope:** —
- **Tests:** `mocap-contracts/tests/test_human_model.py`; that repository's suite passes

## Result (2026-11-03)

**Not merged, tagged or pushed,** and the submodule pointer here didn't move, because a shared contract is Rafael's to release. `build_model.py` still reads the plain recipe format until that's released. A film's character would live in its film root.
