# 1. Do linked runs play in one file?

Rafael wants every run in one Blender file. Copying costs 855 MB per run, so the agreed way is a file that links to each run's own. Nobody has checked that this works.

## Contract

**In:** two existing pair files: `c0` and `c4` under `review\2026-11-08\investigacao_simulacao\comparativo_tempo\`.

**Out:**
- A file that links both runs' collections, placed apart along X.
- Measured and written in the task's report: whether the walk's shape keys and bones play, frames per second of playback, memory used, seconds to open, and the same for the two runs appended instead of linked.
- A recommendation: links or copies, and how many runs fit.

## Agreed and declared

- Windows has 64 GB. A trial, so its file goes in the review folder, not the repository.

## Dependencies

None. Independent of the epic `one-command`.

## Pre-work

None.

## Stop and bring to Rafael if

- Neither links nor copies play at a usable speed: the idea of one file for every run has to change.
