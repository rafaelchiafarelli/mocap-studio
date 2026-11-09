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

## Report (2026-11-08)

Blender 5.2.2 headless, 2 runs (`c0`, `c4`), the files and JSON in `G:\mocap-studio-downloads\review\2026-11-08\fast_review_links_trial\`.

| | Links | Copies |
|---|---|---|
| The file | 0.00 GB (linking 12.8 s) | 1.58 GB (copying 12.7 s) |
| Opens in | 10.7 s | 6.8 s |
| Peak memory | 5.91 GB | 5.89 GB |
| A frame step, CPU only (median) | 3.4 ms | 3.3 ms |
| Shape keys play | yes, 4 skins | yes, 4 skins |
| Bones play | yes, 4 femurs | yes, 4 femurs |

Moves were checked by reading an evaluated skin vertex and a bone at frames 1 and 40 through the linked instances: skin 1.7 to 1.9 m, femur 2.1 to 2.4 m, as the walks go.

**Not measured:** viewport playback FPS. Blender has no GPU viewport in background mode, so the step above is the depsgraph on the CPU: a lower bound on what playback costs, not the frame rate Rafael will see. Rafael's opening of the file is the real test.

**Recommendation:** links. Copying saves no memory and costs 0.8 GB per run on disk, against a file of a few kilobytes. Memory is about 3 GB per run either way, so 64 GB holds around 18 runs at once.

**Status:** Done (2026-11-08): links, by the report above; viewport playback is left to Rafael's opening of the file.
