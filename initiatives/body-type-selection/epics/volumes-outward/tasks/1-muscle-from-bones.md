# 1. Muscle over the bones

Muscle is sized by the skin today (bug `human-model/6`).

## Contract

**In:** the bones from epic `bones-from-measures` and the biotype's muscle.

**Out:**
- A muscle layer built outward from the bones, per region, its volume set by the biotype. Without skin to read.

## Dependencies

Epics `bones-from-measures` and `tissues-and-regions`.

## Pre-work

None.

**Status:** Done (2026-11-08); per-zone thickness read from the neutral bodies' layers, on bones and the trunk's hull. Not run on bodies in this session, by Rafael's instruction.
