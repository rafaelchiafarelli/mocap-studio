# 3. Limbs and feet from the targets

The same for arms, legs and feet, which today are narrowed to the skin.

## Contract

**In:** task 1's targets.

**Out:**
- `skeleton.build` places and sizes shoulder girdle, arms, legs and feet from the targets, with the same output. A change of fat alone doesn't change any bone: tested.

## Dependencies

Task 2.

## Pre-work

None.

**Status:** Done (2026-11-08), unit-tested on the pure parts; that a change of fat alone changes no bone is tested at the targets (test_bone_targets.py), since the build reads them, not the trunk's skin. Head, hands and feet still follow their own skin.
