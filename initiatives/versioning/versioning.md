# versioning — mocap-studio

**Status:** To be planned with Rafael (asked 2026-10-31). No epics yet. It crosses
repositories, so it moved here from `mocap-writer` on 2026-11-03.

**Goal:** one versioning system for the whole workflow, so every part
of it (the script, the bible, the agents' memos and proposals, the
dashboard) can say which version of the film it was made from, and a
piece of work made against an older version can be found.

**Why now:** a proposal or a memo answers one state of the script; after
the next sync nobody can tell whether it still applies.

**What exists to build on:**
- `bible/scene-index.json` holds the hash of the whole script and of each
  scene's text; a change set holds the hashes it was made between.
- `history/` logs every record write with its time.
- Harpia stamps a schema version in each database it creates
  (`_harpia_schema_version`) and migrates older ones.

**Open questions for the planning:** what a version is (every save, every
accepted sync, a named milestone); whether it is a number, a hash or
both; where it is kept (`film.json`, the scene index, the workflow
database); what each consumer records (e.g. a `based_on` field on a
proposal, a `mocap-contracts` change); film roots without git.
