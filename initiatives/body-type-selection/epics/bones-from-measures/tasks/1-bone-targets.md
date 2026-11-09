# 1. From the sheet to bone targets

Bones stop being fitted to the skin and come from measures.

## Contract

**In:** a resolved sheet, which has the pattern-sheet distances and the bone parameters.

**Out:**
- `hmcore/bone_targets.py`: biacromial width, pelvis width, trunk length, thigh and shin, humerus and forearm, bone thickness per region, as metres.
- A blank bone parameter comes from a proportion of the height, recorded as such.
- The measures from `Modelagem_Plana-referencia.pdf` that are bony (7, 9) and near it (4, 5, 12, and 8, 14, 15 for thickness) are read as such. The rest aren't used for bones.
- Compared with the neutral bodies' bones as built today, as a table.

## Agreed and declared

- The pelvis's real width, thigh/shin and humerus/forearm splits are parameters (Rafael, 2026-11-08).

## Dependencies

Epic `character-sheet`.

## Pre-work

None.
