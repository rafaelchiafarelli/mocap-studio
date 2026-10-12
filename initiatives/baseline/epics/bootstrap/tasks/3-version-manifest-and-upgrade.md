## 3. Version manifest and upgrade path

- **Depends on:** 1 (repos.yaml)
- **Contract:**
  - In: the versions confirmed by Rafael on 2026-10-12: Python 3.12,
    FreeMoCap 1.8.2, Blender 5.2.2 LTS (plus everything else pinned in
    `DEPENDENCIES.md`: Harpia V5, `mocap-contracts` tag, torch 2.8 cu128,
    numpy < 2, base image digests, Node 22 for the dashboard UI)
  - Requires:
    - one machine-readable manifest, `versions.yaml`, as the single source of
      every shared version, with where each one is pinned (file + key per repo)
    - `scripts/check_versions.py`: reads the manifest and every pin location,
      reports any repo that disagrees, exits non-zero on drift. Read-only
    - `scripts/check_versions.py --plan <name> <new-version>`: lists every file
      and line to change for an upgrade, plus the repos whose tests must pass.
      It **doesn't edit** them: each repo is upgraded on its own fix branch, so
      a failing repo doesn't block the others
    - `DEPENDENCIES.md` points to the manifest instead of repeating the numbers
  - Delivers: `versions.yaml`, `scripts/check_versions.py`, an "Upgrading a
    version" section in `DEPENDENCIES.md` (manifest → plan → per-repo fix
    branches → tests → move the manifest)
- **Pre-work:** none
- **Out of scope:** doing an actual upgrade (FreeMoCap 2.0 stays a watch item)
- **Tests:** a manifest matching a fixture tree passes; a drifted pin is
  reported with file and line; `--plan` lists every location
