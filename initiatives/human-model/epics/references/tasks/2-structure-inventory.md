## 2. Structure inventory

- **Type:** research, with a read-only script over the reference file. Rafael approves.
- **Depends on:** `references/1`
- **Contract:**
  - In: Z-Anatomy's `Startup.blend`, opened with auto-run scripts off
  - Requires: Rafael's rule to keep as much as possible until it's no longer needed
  - Delivers: a table in this file with one row per structure group: count, vertices,
    decision (rebuild, keep as reference only, leave out), reason. The file's
    `Bonus collection` repeats structures, so counts must not add it twice
- **Pre-work:** —
- **Out of scope:** building any structure
- **Tests:** —

**Starting proposal, to be argued with Rafael:**

| Group | Proposal | Why |
|---|---|---|
| Skeleton | Rebuild | Rafael: keep until data replaces it |
| Muscles and joints | Rebuild | Same |
| Rib cage, diaphragm, lungs as volume | Rebuild as simple volume | Breathing is visible |
| Larynx | Rebuild | Visible when speaking |
| Eyes, teeth, tongue | Rebuild | Visible |
| Superficial veins and tendons | To be decided | May be visible on hands and neck |
| Brain, digestive system | Leave out | Rafael |
| Other organs, lymph nodes, deep vessels | Leave out | Not visible, to confirm |
| Nerves | Reference only | Possible way to group controls |
| Genitalia | Leave out | Rafael |
| Labels, reference lines, section planes | Leave out | Atlas tools |
