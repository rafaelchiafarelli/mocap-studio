# 3. Restart from a stage, reusing an earlier run

A change to the tissue values needs only the simulation and the file, not the bones.

## Contract

**In:** task 2's runs, a stage name and an earlier nickname.

**Out:**
- `fast_review.py NICKNAME --from STAGE --base EARLIER`: stages before `STAGE` are read from the earlier run, not copied.
- `run.json` records where each reused part came from, following the chain back if the earlier run reused too.
- A base run that lacks a needed stage's output is refused before anything runs.

## Agreed and declared

- Rafael says the stage; the command doesn't detect what changed (2026-11-08).

## Dependencies

Task 2.

## Pre-work

None.

**Status:** Done (2026-11-08), unit-tested; not run on real bodies in this session, by Rafael's instruction.
