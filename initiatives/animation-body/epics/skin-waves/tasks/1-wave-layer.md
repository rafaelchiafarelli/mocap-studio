# 1. A wave layer on the skin

Sway and travelling waves on the skin alone: each point moves along its normal and passes the motion to its neighbours.

## Contract

**In:** skin mesh per frame, bone motion, values per vertex.

**Out:**
- `hmcore/skin_waves.py`: per frame, each vertex's offset along its normal, from the bones' acceleration, per-vertex stiffness, wave speed and damping.
- Tested on a small mesh: a pulse travels, and it dies out.

## Agreed and declared

- Gives up true volume and skin pushing on skin (2026-11-10).
- Offsets are bounded, so skin cannot leak through the body.

## Dependencies

Epic `clean-body`.

## Pre-work

None.
