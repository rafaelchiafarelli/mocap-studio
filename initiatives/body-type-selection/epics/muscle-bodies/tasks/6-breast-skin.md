# 6. The skin grows with the breast

Rafael (2026-11-09): the volume looks squeezed by the skin; the skin should grow, not press on the breast, and the areola and nipple are deformed. The skin was pushed vertex by vertex, along each one's normal, up to a volume.

## Contract

**In:** the first shape's skin, the sheet's bust and underbust, the shape and adjustments.

**Out:**
- `hmcore/breast_skin.py`, numpy only so Blender can use it: the breast's outline as a smooth surface the skin moves onto, keeping the mesh's small detail (areola, nipple) and fading out around the breast.
- The bust measured on the result matches the sheet's.
- Optional faders in the character file: `projection_cm`, `base_cm`, `upper`, `lower`, `power`.
- Tested on one body first: the neutral woman, ampulheta, bust 105, underbust 84, waist 80, hip 105, gluteus coração.

## Dependencies

Epic `muscle-bodies`, tasks 2 and 4.

## Pre-work

None.

**Status:** Partly done (2026-11-09): the skin grows with the breast, checked in stills and by Rafael's faders; the verdict is his, and the walked body has not yet been regenerated with the last two fixes.
