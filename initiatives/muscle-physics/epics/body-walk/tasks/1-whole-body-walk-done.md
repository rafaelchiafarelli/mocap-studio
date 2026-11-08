# 1. The whole woman walks

**Asked by Rafael, 2026-11-07** ("nesse momento acho que é mais importante seguir adiante"). The agreed third stage, after the lower body: the whole body in layers walking, with arms, trunk, breasts and belly.

## Contract

**In:** what epic `leg-walk` used: the zero point on the pushed skin, the bones, the walk dump, `data/body_tissue.json`.

**Out:**
- `tools/lower_body_walk.py` becomes `tools/body_walk.py`, cutting the region at any height (the lower body as before, or none for the whole body). Every place where the skin is cut is held by its nearest bone: the waist when there's one, and always the neck, wrists and ankles.
- `blender/lower_body_bake.py` becomes `blender/body_walk_bake.py`, framing whatever region it gets.
- The same measures as the lower body, over every bone in the region; videos beside the current model and in section; every run kept.

## Agreed and declared

- The woman; face, hands and feet stay out, their skin as today (2026-11-07).
- Tissue values as the lower body's: Rafael will tune them later.
- No contact (thighs, arms against the trunk). Ribs don't breathe. Misplaced bones stay as they are.

## Dependencies

Epic `leg-walk`.
