# 1. Every bone carries its own tissue

**Asked by Rafael, 2026-11-07** ("faça a perna e o quadril caminhando"). The thigh had one bone; the lower body has a dozen, each moving its own way. This task gives the solver and the walk dump what that needs.

## Contract

**Out:**
- `blender/body_walk_dump.py`: every bone mesh's transform from rest, every frame of a walk file, and the current skin, like `thigh_walk_dump.py` for one femur.
- `hmcore/xpbd.py`: driven nodes each follow their own bone's transform, and damping slows each node's motion relative to its nearest bone. One bone, as on the thigh, stays the same call.
- Tests: two blocks carried by two bones moving apart follow each.

## Dependencies

Epic `thigh` (`xpbd.py`), the woman's `female_walk_review.blend`.
