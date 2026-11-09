# 1. Every tetrahedron knows its zone

`hmcore/body.py` knows the zone per voxel and drops it, so the simulation can only vary by tissue.

## Contract

**In:** today's body in layers.

**Out:**
- `<name>.body_layers.npz` keeps each tetrahedron's zone, and `tools/body_walk.py` reads it.

## Agreed and declared

- Can be done on today's body, ahead of the redesign.

## Dependencies

None.

## Pre-work

None.

**Status:** Done (2026-11-08).
