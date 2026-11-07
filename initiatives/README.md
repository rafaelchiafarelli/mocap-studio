# Initiatives

The full process (initiative → epic → task → contract, branch chain, per-task
loop, stop-and-ask rules) lives in the **mocap-workflow** skill
(`.claude/skills/mocap-workflow/SKILL.md`). Read it before anything else.

Rules specific to this repository:

- **Layout:** `initiatives/<initiative>/epics/<epic>/tasks/<n>-<task>.md`.
  The number is the implementation order, and the file name is the branch name.
- **Done marker:** `-done` suffix on the **file name** (`git mv` in a separate
  commit, right after the implementation commit). Never a status line.
- **Order between epics:** in `initiatives/<initiative>/epics/README.md`.
- **Order between repositories:** in `mocap-studio/HANDOFF.md`.
- **Test suite:** `pytest` at the root (Python repositories) or
  `pio test -e native` (mocap-sync-fw). "Not broken" = green suite.
- **Contracts between repositories** only through the `mocap-contracts` package
  and the session folder layout. Never import code from another mocap repository.
  A change that crosses repositories starts in `mocap-contracts`.

## Open problems

- **Faces, major (2026-11-02):** believable faces are a requirement, and Rafael is
  reconsidering the project over them. **Read [faces](faces/faces.md) before any face,
  character or planning work.**
- **Body results are also bad (Rafael, 2026-11-02).** He'll discuss this later, and
  gave no details yet. Don't treat body capture as working; ask him before planning
  body work.

## Index

| Initiative | Status |
|---|---|
| [faces](faces/faces.md) | Open — the major open problem, its results and the best tool so far |
| **human-model** — our own full-body male and female model in layers, bones to skin | First pass done 2026-11-03, read `human-model/docs/` (history: `git log -- initiatives/human-model`) |
| [muscle-physics](muscle-physics/muscle-physics.md) | Open — what simulated tissue can do: one muscle, then a thigh in layers on the GPU |
| [bugs](bugs/bugs.md) | Backlog |
| [baseline](baseline/baseline.md) | Planned — not active while the MVP (`MVP-plan.md`) is on hold |
| [versioning](versioning/versioning.md) | To be planned — one versioning system for the whole workflow |
| **face-anatomy** — anatomy research for a character that moves like a person | Done 2026-11-02; findings in `human-model` (history: `git log -- initiatives/face-anatomy`) |
| **face-audio** — mouth from recorded speech with Audio2Face-3D | Retired 2026-11-03; see [faces](faces/faces.md) (history: `git log -- initiatives/face-audio`) |
| **face-video** — eyes and brows from video, merged with the Audio2Face mouth | Retired 2026-11-03; see [faces](faces/faces.md) (history: `git log -- initiatives/face-video`) |
| **face-character** — declared per-character face gain | Retired 2026-11-03; see [faces](faces/faces.md) (history: `git log -- initiatives/face-character`) |
| **face-in-shot** — the MVP character speaks | Retired 2026-11-03; see [faces](faces/faces.md) (history: `git log -- initiatives/face-in-shot`) |
| **environments** | Moved 2026-11-03 to `mocap-blender` `initiatives/environments/` |
