# 6. The belly's viscera apart from the chest

One cavity today stands for lungs and viscera, and it compresses too much.

## Contract

**In:** the cavity in `hmcore/body.py`, which already tells the chest from the rest.

**Out:**
- A label for the abdominal viscera, on the same tetrahedra, with its own values, in the woman and the man.
- Measured: its volume through the walk, and whether keeping it nearly incompressible needs more steps per frame.

## Agreed and declared

- Computationally simple (Rafael, 2026-11-08).

## Dependencies

Task 3.

## Pre-work

None.

## Stop and bring to Rafael if

- It only holds its volume at a cost in steps that slows the whole body noticeably.

**Status:** Done (2026-11-08), label and values; the measured part (the viscera's volume through a walk, whether they need more steps per frame) is not done, since no body was computed in this session, by Rafael's instruction.
