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

## Index

| Initiative | Status |
|---|---|
| [face-audio](face-audio/face-audio.md) | Planned — not started; **runs first**, alongside the MVP |
| [face-video](face-video/face-video.md) | Planned — after a `face-audio` pass |
| [face-character](face-character/face-character.md) | Planned — after a `face-audio` pass |
| [face-in-shot](face-in-shot/face-in-shot.md) | Planned — after a `face-audio` pass and the MVP shot |
| [baseline](baseline/baseline.md) | Planned — frozen by the MVP (`MVP-plan.md`) |
